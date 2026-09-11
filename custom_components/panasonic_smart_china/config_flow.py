import hashlib
import logging
import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .account_data import (
    account_title,
    account_unique_id,
    device_record,
)
from .api import authenticate, list_bound_devices
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_SUBTYPE,
    CONF_DEVICES,
    CONF_DEV_SUB_TYPE_ID,
    CONF_FAMILY_ID,
    CONF_REAL_FAMILY_ID,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_AUTO,
    DOMAIN,
    PROTOCOL_SIGNATURES,
    SUPPORTED_ERV_DEVICE_HINTS,
)

_LOGGER = logging.getLogger(__name__)

HEX_128_RE = re.compile(r"^[0-9a-fA-F]{128}$")


class PanasonicDiscoveryMixin:
    """Shared token generation and subtype inference for config/options."""

    def _generate_token(self, device_id):
        """Generate the Panasonic device token from the front-end JS logic."""
        try:
            parts = str(device_id).split("_")
            if len(parts) != 3:
                _LOGGER.debug(
                    "Skip token source with invalid deviceId format: %s",
                    device_id,
                )
                return None

            mac_part = parts[0].upper()
            category = parts[1].upper()
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

    def _generate_token_from_device_info(self, device_id: str, info: dict) -> str | None:
        """Generate a token from the API id or vendor MAC_CATEGORY_SUFFIX name."""
        token_sources = [
            str(info.get(key, ""))
            for key in ("deviceName", "devName", "name")
            if info.get(key)
        ]
        token_sources.append(device_id)

        for token_source in token_sources:
            token = self._generate_token(token_source)
            if token:
                return token
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

    def _resolve_token(self, device_id: str, info: dict) -> str | None:
        return (
            self._extract_device_token(info)
            or self._generate_token_from_device_info(device_id, info)
        )

    def _get_device_subtype(self, device_id: str, info: dict | None) -> str:
        """Infer the ERV subtype from device data.

        Pure data-driven inference, no hard-coded model lists:
          1. devSubTypeId from the Panasonic cloud (authoritative) matched by
             supported prefix (e.g. LD5C, MIDERV02, SMALLERV03).
          2. statusAll field signature matched against PROTOCOL_SIGNATURES.
          3. Fall back to AUTO so the device is still configurable; the
             runtime probe loop converges on the real protocol and persists it.
        """
        if info:
            subtype = str(info.get("devSubTypeId", "")).upper()
            matched_subtype = self._match_supported_subtype(subtype)
            if matched_subtype:
                return matched_subtype

            matched_subtype = self._match_protocol_signature(info)
            if matched_subtype:
                return matched_subtype

        upper_device_id = str(device_id).upper()
        matched_subtype = self._match_supported_subtype(upper_device_id)
        if matched_subtype:
            return matched_subtype

        return DEVICE_SUBTYPE_AUTO

    def _match_supported_subtype(self, value: str) -> str | None:
        """Normalize vendor subtype variants such as SMALLERV03 and MIDERV02."""
        for supported_subtype in sorted(
            SUPPORTED_ERV_DEVICE_HINTS,
            key=len,
            reverse=True,
        ):
            if value.startswith(supported_subtype):
                return supported_subtype
        return None

    def _match_protocol_signature(self, info: dict) -> str | None:
        """Match device metadata against the protocol signature table."""
        candidate_dicts = [info]

        status_all = info.get("statusAll")
        if isinstance(status_all, dict):
            candidate_dicts.append(status_all)

        best_subtype: str | None = None
        best_score = 0
        for subtype, signature_keys in PROTOCOL_SIGNATURES.items():
            score = max(
                sum(1 for key in signature_keys if key in candidate)
                for candidate in candidate_dicts
            )
            if score > best_score:
                best_subtype = subtype
                best_score = score

        return best_subtype if best_score >= 2 else None

    def _device_choice_label(self, device_id: str, info: dict) -> str:
        name = info.get("deviceName") or info.get("devName") or "Panasonic ERV"
        subtype = self._get_device_subtype(device_id, info)
        if subtype == DEVICE_SUBTYPE_AUTO:
            return f"{name} ({device_id}) [自动识别]"
        return f"{name} ({device_id})"

    def _available_device_labels(self, devices: dict) -> dict[str, str]:
        return {
            device_id: self._device_choice_label(device_id, info)
            for device_id, info in devices.items()
        }

    def _build_device_records(self, selected_ids: list[str], cloud_devices: dict) -> dict:
        records = {}
        for device_id in selected_ids:
            info = cloud_devices.get(device_id) or {}
            token = self._resolve_token(device_id, info)
            if not token:
                continue
            records[device_id] = device_record(
                token=token,
                subtype=self._get_device_subtype(device_id, info),
                sub_type_id=info.get("devSubTypeId"),
                name=info.get("deviceName") or info.get("devName") or device_id,
            )
        return records


class PanasonicConfigFlow(
    PanasonicDiscoveryMixin, config_entries.ConfigFlow, domain=DOMAIN
):
    VERSION = 2

    def __init__(self) -> None:
        self._login_data: dict = {}
        self._devices: dict = {}
        self._username: str | None = None
        self._password: str | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input=None):
        """Log in to a Panasonic Smart China account."""
        errors = {}

        if user_input is not None:
            try:
                result = await authenticate(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except Exception as err:
                _LOGGER.error("Panasonic login failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not result.get("devices"):
                    return self.async_abort(reason="no_devices_found")

                unique_id = account_unique_id(
                    user_input[CONF_USERNAME], result.get("usrId")
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                self._username = user_input[CONF_USERNAME]
                self._password = user_input[CONF_PASSWORD]
                self._login_data = {
                    CONF_USR_ID: result["usrId"],
                    CONF_SSID: result["ssId"],
                    CONF_FAMILY_ID: result.get("familyId"),
                    CONF_REAL_FAMILY_ID: result.get("realFamilyId"),
                }
                self._devices = result["devices"]
                return await self.async_step_devices()

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

    async def async_step_devices(self, user_input=None):
        """Select one or more ERV devices on this account."""
        errors = {}
        labels = self._available_device_labels(self._devices)
        if not labels:
            return self.async_abort(reason="no_supported_devices_found")

        if user_input is not None:
            selected = user_input.get(CONF_DEVICES) or []
            if isinstance(selected, str):
                selected = [selected]
            records = self._build_device_records(list(selected), self._devices)
            if not selected:
                errors["base"] = "no_devices_selected"
            elif not records:
                errors["base"] = "token_generation_failed"
            else:
                return self.async_create_entry(
                    title=account_title(self._username, self._login_data[CONF_USR_ID]),
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_USR_ID: self._login_data[CONF_USR_ID],
                        CONF_SSID: self._login_data[CONF_SSID],
                        CONF_FAMILY_ID: self._login_data.get(CONF_FAMILY_ID),
                        CONF_REAL_FAMILY_ID: self._login_data.get(CONF_REAL_FAMILY_ID),
                        CONF_DEVICES: records,
                    },
                )

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICES, default=list(labels.keys())
                    ): cv.multi_select(labels),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Re-authenticate when stored credentials no longer work."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._reauth_entry
        username = (entry.data if entry else {}).get(CONF_USERNAME, "")

        if user_input is not None and entry is not None:
            password = user_input[CONF_PASSWORD]
            try:
                result = await authenticate(username, password)
            except Exception as err:
                _LOGGER.error("Panasonic reauth failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                new_data = dict(entry.data)
                new_data[CONF_PASSWORD] = password
                new_data[CONF_USR_ID] = result["usrId"]
                new_data[CONF_SSID] = result["ssId"]
                if result.get("familyId") not in (None, ""):
                    new_data[CONF_FAMILY_ID] = result["familyId"]
                if result.get("realFamilyId") not in (None, ""):
                    new_data[CONF_REAL_FAMILY_ID] = result["realFamilyId"]
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": username},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        flow = PanasonicOptionsFlow()
        flow._config_entry = config_entry
        return flow


class PanasonicOptionsFlow(PanasonicDiscoveryMixin, config_entries.OptionsFlow):
    """Add or remove ERV devices on an existing account entry."""

    def __init__(self) -> None:
        self._config_entry: config_entries.ConfigEntry | None = None
        self._cloud_devices: dict = {}

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        return getattr(self, "config_entry", None) or self._config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        entry = self._entry

        if not self._cloud_devices:
            devices = await self._async_load_cloud_devices(entry)
            if not devices:
                errors["base"] = "cannot_connect"
            else:
                self._cloud_devices = devices

        labels = self._available_device_labels(self._cloud_devices)
        if not labels and not errors:
            return self.async_abort(reason="no_supported_devices_found")

        current_ids = list((entry.data.get(CONF_DEVICES) or {}).keys())
        default_ids = [device_id for device_id in current_ids if device_id in labels]
        if not default_ids:
            default_ids = list(labels.keys())

        if user_input is not None and not errors:
            selected = user_input.get(CONF_DEVICES) or []
            if isinstance(selected, str):
                selected = [selected]
            if not selected:
                errors["base"] = "no_devices_selected"
            else:
                existing = dict(entry.data.get(CONF_DEVICES) or {})
                records = self._build_device_records(list(selected), self._cloud_devices)
                if not records:
                    errors["base"] = "token_generation_failed"
                else:
                    # Keep previously stored tokens/names for devices that
                    # were already on this account so entity unique_ids stay
                    # stable across option edits.
                    for device_id, record in records.items():
                        previous = existing.get(device_id)
                        if not previous:
                            continue
                        if previous.get(CONF_TOKEN):
                            record[CONF_TOKEN] = previous[CONF_TOKEN]
                        if previous.get(CONF_DEVICE_SUBTYPE):
                            record[CONF_DEVICE_SUBTYPE] = previous[CONF_DEVICE_SUBTYPE]
                        if previous.get(CONF_DEVICE_NAME):
                            record[CONF_DEVICE_NAME] = previous[CONF_DEVICE_NAME]
                        if previous.get(CONF_DEV_SUB_TYPE_ID):
                            record[CONF_DEV_SUB_TYPE_ID] = previous[
                                CONF_DEV_SUB_TYPE_ID
                            ]
                    new_data = dict(entry.data)
                    new_data[CONF_DEVICES] = records
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_create_entry(title="", data={})

        if errors.get("base") == "cannot_connect":
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICES, default=default_ids): cv.multi_select(
                        labels
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_load_cloud_devices(self, entry) -> dict | None:
        """Prefer the live SSID; only re-login if the session is already dead."""
        devices = await list_bound_devices(
            entry.data.get(CONF_USR_ID),
            entry.data.get(CONF_SSID),
            entry.data.get(CONF_FAMILY_ID),
            entry.data.get(CONF_REAL_FAMILY_ID),
        )
        if devices:
            return devices
        username = entry.data.get(CONF_USERNAME)
        password = entry.data.get(CONF_PASSWORD)
        if not username or not password:
            return None
        try:
            result = await authenticate(username, password)
        except Exception as err:
            _LOGGER.error("Panasonic options login failed: %s", err)
            return None
        new_data = dict(entry.data)
        new_data[CONF_USR_ID] = result["usrId"]
        new_data[CONF_SSID] = result["ssId"]
        if result.get("familyId") not in (None, ""):
            new_data[CONF_FAMILY_ID] = result["familyId"]
        if result.get("realFamilyId") not in (None, ""):
            new_data[CONF_REAL_FAMILY_ID] = result["realFamilyId"]
        self.hass.config_entries.async_update_entry(entry, data=new_data)
        return result.get("devices") or {}
