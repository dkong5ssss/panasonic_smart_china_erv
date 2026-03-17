import hashlib
import logging
import re

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TOKEN_OVERRIDE,
    CONF_SSID,
    CONF_DEVICE_SUBTYPE,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_MID_ERV,
    DEVICE_SUBTYPE_SMALL_ERV,
    DOMAIN,
    SUPPORTED_ERV_CATEGORIES,
    SUPPORTED_ERV_DEVICE_HINTS,
)

_LOGGER = logging.getLogger(__name__)

HEX_128_RE = re.compile(r"^[0-9a-fA-F]{128}$")

URL_LOGIN = "https://app.psmartcloud.com/App/UsrLogin"
URL_GET_DEV = "https://app.psmartcloud.com/App/UsrGetBindDevInfo"
URL_GET_TOKEN = "https://app.psmartcloud.com/App/UsrGetToken"


class PanasonicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._login_data = {}
        self._devices = {}
        self._temp_login_info = {}

    async def async_step_user(self, user_input=None):
        """Reuse the original Panasonic Smart China login flow."""
        errors = {}

        domain_data = self.hass.data.get(DOMAIN, {})
        cached_session = domain_data.get("session")

        if cached_session:
            _LOGGER.info("Found cached session, verifying validity")
            valid_devices = await self._get_devices_with_ssid(
                cached_session[CONF_USR_ID],
                cached_session[CONF_SSID],
            )
            if valid_devices:
                _LOGGER.info("Cached Panasonic session is still valid")
                self._login_data = {
                    CONF_USR_ID: cached_session[CONF_USR_ID],
                    CONF_SSID: cached_session[CONF_SSID],
                }
                self._devices = valid_devices
                return await self.async_step_device()

            _LOGGER.warning("Cached Panasonic session expired")
            if DOMAIN in self.hass.data:
                self.hass.data[DOMAIN]["session"] = None

        if user_input is not None:
            try:
                usr_id, ssid, devices = await self._authenticate_full_flow(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                if not devices:
                    return self.async_abort(reason="no_devices_found")

                self._login_data = {
                    CONF_USR_ID: usr_id,
                    CONF_SSID: ssid,
                }
                self._devices = devices

                self.hass.data.setdefault(DOMAIN, {})
                self.hass.data[DOMAIN]["session"] = {
                    CONF_USR_ID: usr_id,
                    CONF_SSID: ssid,
                    "devices": devices,
                    "familyId": self._temp_login_info.get("familyId"),
                    "realFamilyId": self._temp_login_info.get("realFamilyId"),
                }
                return await self.async_step_device()
            except Exception as err:
                _LOGGER.error("Panasonic login failed: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(self, user_input=None):
        """Select a supported ERV device."""
        errors = {}
        existing_ids = self._async_current_ids()

        available_devices = {}
        supported_device_count = 0
        for device_id, info in self._devices.items():
            device_subtype = self._get_device_subtype(device_id, info)
            if not device_subtype:
                continue
            supported_device_count += 1
            if f"panasonic_{device_id}" in existing_ids:
                continue
            name = info.get("deviceName", "Panasonic ERV")
            available_devices[device_id] = f"{name} ({device_id})"

        if not available_devices:
            if supported_device_count:
                return self.async_abort(reason="all_devices_configured")
            return self.async_abort(reason="no_supported_devices_found")

        if user_input is not None:
            selected_dev_id = user_input[CONF_DEVICE_ID]
            dev_info = self._devices.get(selected_dev_id, {})
            dev_name = dev_info.get("deviceName", "Panasonic ERV")
            device_subtype = self._get_device_subtype(selected_dev_id, dev_info)
            manual_token = user_input.get(CONF_DEVICE_TOKEN_OVERRIDE, "").strip()

            token = (
                manual_token
                or self._extract_device_token(dev_info)
                or self._generate_token(selected_dev_id)
            )
            if not device_subtype:
                errors["base"] = "no_supported_devices_found"
            elif not token:
                errors["base"] = "token_generation_failed"
            else:
                await self.async_set_unique_id(f"panasonic_{selected_dev_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=dev_name,
                    data={
                        CONF_USR_ID: self._login_data[CONF_USR_ID],
                        CONF_SSID: self._login_data[CONF_SSID],
                        CONF_DEVICE_ID: selected_dev_id,
                        CONF_DEVICE_SUBTYPE: device_subtype,
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.In(available_devices),
                    vol.Optional(CONF_DEVICE_TOKEN_OVERRIDE): str,
                }
            ),
            errors=errors,
        )

    async def _get_devices_with_ssid(self, usr_id, ssid):
        """Use SSID to verify the cached Panasonic session."""
        headers = {
            "User-Agent": "SmartApp",
            "Content-Type": "application/json",
            "Cookie": f"SSID={ssid}",
        }

        domain_data = self.hass.data.get(DOMAIN, {})
        session_cache = domain_data.get("session")
        if not session_cache or "familyId" not in session_cache:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    URL_GET_DEV,
                    json={
                        "id": 3,
                        "uiVersion": 4.0,
                        "params": {
                            "realFamilyId": session_cache["realFamilyId"],
                            "familyId": session_cache["familyId"],
                            "usrId": usr_id,
                        },
                    },
                    headers=headers,
                    ssl=False,
                ) as response:
                    if response.status != 200:
                        return None
                    dev_res = await response.json()
                    if "results" not in dev_res or "devList" not in dev_res["results"]:
                        return None

                    devices = {}
                    for dev in dev_res["results"]["devList"]:
                        devices[dev["deviceId"]] = dev["params"]
                    return devices
        except Exception:
            return None

    async def _authenticate_full_flow(self, username, password):
        """Keep the original Smart China login sequence unchanged."""
        headers = {"User-Agent": "SmartApp", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                URL_GET_TOKEN,
                json={
                    "id": 1,
                    "uiVersion": 4.0,
                    "params": {"usrId": username},
                },
                headers=headers,
                ssl=False,
            ) as response:
                data = await response.json()
                if "results" not in data:
                    raise RuntimeError("GetToken failed")
                token_start = data["results"]["token"]

            pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
            inter_md5 = hashlib.md5((pwd_md5 + username).encode()).hexdigest().upper()
            final_token = hashlib.md5((inter_md5 + token_start).encode()).hexdigest().upper()

            async with session.post(
                URL_LOGIN,
                json={
                    "id": 2,
                    "uiVersion": 4.0,
                    "params": {
                        "telId": "00:00:00:00:00:00",
                        "checkFailCount": 0,
                        "usrId": username,
                        "pwd": final_token,
                    },
                },
                headers=headers,
                ssl=False,
            ) as response:
                login_res = await response.json()
                if "results" not in login_res:
                    raise RuntimeError("Login failed")

                res = login_res["results"]
                real_usr_id = res["usrId"]
                ssid = res["ssId"]

                self._temp_login_info = {
                    "realFamilyId": res["realFamilyId"],
                    "familyId": res["familyId"],
                }

            headers["Cookie"] = f"SSID={ssid}"
            async with session.post(
                URL_GET_DEV,
                json={
                    "id": 3,
                    "uiVersion": 4.0,
                    "params": {
                        "realFamilyId": res["realFamilyId"],
                        "familyId": res["familyId"],
                        "usrId": real_usr_id,
                    },
                },
                headers=headers,
                ssl=False,
            ) as response:
                dev_res = await response.json()
                devices = {}
                if "results" in dev_res and "devList" in dev_res["results"]:
                    for dev in dev_res["results"]["devList"]:
                        devices[dev["deviceId"]] = dev["params"]
                return real_usr_id, ssid, devices

    def _generate_token(self, device_id):
        """Generate the Panasonic device token from the front-end JS logic."""
        try:
            parts = device_id.split("_")
            if len(parts) != 3:
                _LOGGER.error(
                    "Invalid deviceId format: %s (expected MAC_CATEGORY_SUFFIX)",
                    device_id,
                )
                return None

            # Match the vendor front-end JS exactly:
            # stoken = mac[6:] + '_' + category + '_' + mac[:6]
            # token = sha512(sha512(stoken) + '_' + suffix)
            # Keep the suffix case unchanged, otherwise ERV tokens will fail.
            mac_part = parts[0]
            category = parts[1]
            suffix = parts[2]

            if len(mac_part) < 6:
                _LOGGER.error("Invalid MAC part in deviceId: %s", device_id)
                return None

            stoken = mac_part[6:] + "_" + category + "_" + mac_part[:6]
            inner = hashlib.sha512(stoken.encode()).hexdigest()
            return hashlib.sha512((inner + "_" + suffix).encode()).hexdigest()
        except Exception as err:
            _LOGGER.error("Token generation failed for deviceId %s: %s", device_id, err)
            return None

    def _get_device_subtype(self, device_id: str, info: dict | None) -> str | None:
        """Infer the ERV subtype from device metadata first, then deviceId."""
        if info:
            subtype = str(info.get("devSubTypeId", "")).upper()
            matched_subtype = self._match_supported_subtype(subtype)
            if matched_subtype:
                return matched_subtype

        parts = device_id.split("_")
        if len(parts) == 3 and parts[1] in SUPPORTED_ERV_CATEGORIES:
            return DEVICE_SUBTYPE_SMALL_ERV

        upper_device_id = device_id.upper()
        matched_subtype = self._match_supported_subtype(upper_device_id)
        if matched_subtype:
            return matched_subtype
        return None

    def _match_supported_subtype(self, value: str) -> str | None:
        """Normalize vendor subtype variants such as SMALLERV03 and MIDERV02."""
        for supported_subtype in SUPPORTED_ERV_DEVICE_HINTS:
            if value.startswith(supported_subtype):
                return supported_subtype
        return None

    def _extract_device_token(self, dev_info):
        """Search device metadata for an already-issued device token."""
        return self._extract_token_from_value(dev_info)

    def _extract_token_from_value(self, value):
        """Recursively look for 128-char hex tokens in device metadata."""
        if isinstance(value, str):
            return value if HEX_128_RE.fullmatch(value) else None

        if isinstance(value, dict):
            preferred_keys = (
                "token",
                "devToken",
                "deviceToken",
                "accessToken",
            )
            for key in preferred_keys:
                token = self._extract_token_from_value(value.get(key))
                if token:
                    return token

            for nested_value in value.values():
                token = self._extract_token_from_value(nested_value)
                if token:
                    return token
            return None

        if isinstance(value, list):
            for item in value:
                token = self._extract_token_from_value(item)
                if token:
                    return token
            return None

        return None
