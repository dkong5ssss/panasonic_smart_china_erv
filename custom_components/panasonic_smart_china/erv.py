from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import authenticate
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_SUBTYPE,
    CONF_FAMILY_ID,
    CONF_REAL_FAMILY_ID,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_SMALL_ERV,
    DOMAIN,
    PRESET_LOW,
    RELOGIN_COOLDOWN_SECONDS,
    SUPPORTED_ERV_SUBTYPES,
)
from .tls import psmartcloud_fingerprint

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = timedelta(seconds=30)
COMMAND_REFRESH_DELAY = 5

URL_GET_DEV = "https://app.psmartcloud.com/App/UsrGetBindDevInfo"


async def async_get_coordinator(hass, entry):
    """Create or reuse the shared ERV coordinator for one config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinators = domain_data.setdefault("coordinators", {})
    coordinator = coordinators.get(entry.entry_id)
    if coordinator is None:
        coordinator = PanasonicERVCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        coordinators[entry.entry_id] = coordinator
    return coordinator


class PanasonicERVCoordinator(DataUpdateCoordinator[dict]):
    """Shared ERV API client and state container."""

    def __init__(self, hass, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        config = entry.data
        self._usr_id = config[CONF_USR_ID]
        self._device_id = config[CONF_DEVICE_ID]
        self._token = config[CONF_TOKEN]
        self._ssid = config[CONF_SSID]
        self._family_id = config.get(CONF_FAMILY_ID)
        self._real_family_id = config.get(CONF_REAL_FAMILY_ID)
        # Credentials stored since v1.7.1 let the runtime silently re-login to
        # self-heal a missing/stale familyId or SSID.
        self._username = config.get(CONF_USERNAME)
        self._password = config.get(CONF_PASSWORD)
        self._device_subtype = config.get(CONF_DEVICE_SUBTYPE, DEVICE_SUBTYPE_SMALL_ERV)
        self._apply_protocol(self._device_subtype)
        self._last_params = self._default_params.copy()
        self._last_status_all_raw: dict = {}
        self._last_status_raw: dict = {}
        super().__init__(
            hass,
            _LOGGER,
            name=f"panasonic_erv_{self._device_id}",
            update_interval=POLLING_INTERVAL,
        )

    def _apply_protocol(self, device_subtype: str) -> None:
        """Load endpoint and payload rules for the selected ERV subtype."""
        # AUTO devices have not been pinned to a protocol yet; start with the
        # SmallERV rules and let the runtime probe loop converge on the real
        # subtype on the first fetch.
        if device_subtype not in SUPPORTED_ERV_SUBTYPES:
            device_subtype = DEVICE_SUBTYPE_SMALL_ERV
        protocol = SUPPORTED_ERV_SUBTYPES[device_subtype]
        self._device_subtype = device_subtype
        self._default_params = protocol["default_params"]
        self._control_params = protocol["control_params"]
        self._merge_current_status_for_control = protocol[
            "merge_current_status_for_control"
        ]
        self._single_field_commands = protocol["single_field_commands"]
        self._safe_control_keys = protocol["safe_control_keys"]
        self._preset_to_air_volume = protocol["preset_to_air_volume"]
        self._air_volume_to_preset = protocol["air_volume_to_preset"]
        self._air_volume_steps = protocol.get("air_volume_steps", [])
        self._run_mode_to_option = protocol.get("run_mode_to_option", {})
        self._option_to_run_mode = protocol.get("option_to_run_mode", {})
        self._extra_selects = tuple(protocol.get("extra_selects", ()))
        self._status_request_id = protocol.get("status_request_id", 2)
        self._status_ui_version = protocol.get("status_ui_version")
        self._set_request_id = protocol.get("set_request_id", 0)
        self._uses_status_all = protocol.get("uses_status_all", False)
        self._status_all_field_map = protocol.get("status_all_field_map", {})
        self._set_field_name_map = protocol.get("set_field_name_map", {})
        self._set_identity_top_level = protocol.get("set_identity_top_level", False)
        self._use_xtoken_header = protocol.get("use_xtoken_header", False)
        self._supports_holiday_switch = protocol.get("supports_holiday_switch", True)
        self._url_get = protocol["get_url"]
        self._url_set = protocol["set_url"]

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def device_subtype(self) -> str:
        return self._device_subtype

    @property
    def is_on(self) -> bool:
        return self._int_param("runSta") == 1

    @property
    def preset_modes(self) -> list[str]:
        return list(self._option_to_run_mode.keys())

    @property
    def preset_mode(self) -> str | None:
        return self.current_run_mode

    @property
    def percentage_step(self) -> int | None:
        if not self._air_volume_steps:
            return None
        return max(1, 100 // len(self._air_volume_steps))

    @property
    def percentage(self) -> int | None:
        if not self._air_volume_steps:
            return None
        if not self.is_on:
            return 0

        current_air_volume = self._int_param("airVo")
        try:
            current_index = self._air_volume_steps.index(current_air_volume)
        except ValueError:
            current_index = 0

        return ((current_index + 1) * 100) // len(self._air_volume_steps)

    @property
    def run_mode_options(self) -> list[str]:
        return list(self._option_to_run_mode.keys())

    @property
    def current_run_mode(self) -> str | None:
        return self._run_mode_to_option.get(self._int_param("runM"))

    @property
    def supports_run_mode_select(self) -> bool:
        return bool(self._option_to_run_mode)

    @property
    def extra_selects(self) -> tuple[dict, ...]:
        return self._extra_selects

    def supports_control_field(self, field: str) -> bool:
        return field in self._safe_control_keys

    @property
    def supports_holiday_switch(self) -> bool:
        """Whether the holiday-mode switch entity should be exposed."""
        return self._supports_holiday_switch

    def field_value(self, field: str):
        return self._last_params.get(field)

    def _int_param(self, field: str) -> int | None:
        raw = self._last_params.get(field)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        attrs = {
            "device_id": self._device_id,
            "device_subtype": self._device_subtype,
            "offline": self._last_params.get("offline"),
            "runSta": self._last_params.get("runSta"),
            "airVo": self._last_params.get("airVo"),
            "runM": self._last_params.get("runM"),
            "dehumid": self._last_params.get("dehumid"),
            "filSet": self._last_params.get("filSet"),
            "oaFilExPM": self._last_params.get("oaFilExPM"),
            "saFilEx": self._last_params.get("saFilEx"),
            "raFilEx": self._last_params.get("raFilEx"),
        }
        for key in (
            "holM",
            "preSet",
            "preM",
            "pmSen",
            "coSen",
            "tvSen",
            "userSupWind",
            "userExhWind",
            "oaFilEx",
            "saFilCl",
            "raFilCl",
            "oaPMC",
            "saPMC",
            "raPMC",
            "oaHumC",
            "raHumC",
            "oaTeC",
            "saTeC",
            "raTeC",
            "raCO2C",
            "raTVC",
            "oaFilExTL",
            "saFilExTL",
            "raFilExTL",
        ):
            if key in self._last_params:
                attrs[key] = self._last_params.get(key)
        if self.current_run_mode is not None:
            attrs["run_mode"] = self.current_run_mode
        return attrs

    async def _async_update_data(self) -> dict:
        """Fetch the latest ERV status."""
        data = await self._fetch_status()
        if data is None:
            raise RuntimeError(
                f"Could not fetch ERV status for {self._device_id} using any known subtype"
            )
        return data

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
    ) -> None:
        """Turn the ERV on, optionally selecting speed and run mode."""
        if self._single_field_commands:
            commands = [{"runSta": 1}]
            if percentage is not None:
                air_volume = self._percentage_to_air_volume(percentage)
                if air_volume is not None:
                    commands.append({"airVo": air_volume})
            if preset_mode in self._option_to_run_mode:
                commands.append({"runM": self._option_to_run_mode[preset_mode]})
            await self._async_send_command_sequence(commands)
            return

        changes = {"runSta": 1}
        if percentage is not None:
            air_volume = self._percentage_to_air_volume(percentage)
            if air_volume is not None:
                changes["airVo"] = air_volume
        if preset_mode in self._option_to_run_mode:
            changes["runM"] = self._option_to_run_mode[preset_mode]
        await self.async_send_command(changes)

    async def async_turn_off(self) -> None:
        """Turn the ERV off."""
        await self.async_send_command({"runSta": 0})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set ERV air volume using HA percentage semantics."""
        air_volume = self._percentage_to_air_volume(percentage)
        if air_volume is None:
            await self.async_turn_off()
            return

        if self._single_field_commands:
            commands = []
            if not self.is_on:
                commands.append({"runSta": 1})
            commands.append({"airVo": air_volume})
            await self._async_send_command_sequence(commands)
            return

        await self.async_send_command({"runSta": 1, "airVo": air_volume})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set ERV run mode using HA preset modes."""
        if preset_mode not in self._option_to_run_mode:
            _LOGGER.warning("Unsupported ERV run mode requested: %s", preset_mode)
            return

        if self._single_field_commands:
            commands = []
            if not self.is_on:
                commands.append({"runSta": 1})
            commands.append({"runM": self._option_to_run_mode[preset_mode]})
            await self._async_send_command_sequence(commands)
            return

        await self.async_send_command(
            {"runSta": 1, "runM": self._option_to_run_mode[preset_mode]}
        )

    async def async_set_run_mode(self, option: str) -> None:
        """Set the MidERV run mode."""
        run_mode = self._option_to_run_mode.get(option)
        if run_mode is None:
            _LOGGER.warning("Unsupported ERV run mode requested: %s", option)
            return

        if self._single_field_commands:
            commands = []
            if not self.is_on:
                commands.append({"runSta": 1})
            commands.append({"runM": run_mode})
            await self._async_send_command_sequence(commands)
            return

        await self.async_send_command({"runSta": 1, "runM": run_mode})

    async def async_set_field(self, field: str, value: int) -> None:
        """Set a protocol field exposed through an auxiliary entity."""
        if not self.supports_control_field(field):
            _LOGGER.warning("Unsupported ERV control field requested: %s", field)
            return
        await self.async_send_command({field: value})

    async def _async_send_command_sequence(self, commands: list[dict]) -> None:
        """Send protocol-safe commands in order and refresh after the final one."""
        for index, changes in enumerate(commands):
            await self.async_send_command(
                changes,
                refresh=index == len(commands) - 1,
            )

    def _percentage_to_air_volume(self, percentage: int) -> int | None:
        """Map a HA percentage to the nearest supported ERV air volume."""
        if not self._air_volume_steps:
            return None
        if percentage <= 0:
            return None

        level_count = len(self._air_volume_steps)
        level = min(level_count, max(1, (percentage * level_count + 99) // 100))
        return self._air_volume_steps[level - 1]

    async def _fetch_status(self):
        """Fetch the current ERV status."""
        probe_order = [
            subtype
            for subtype in (self._device_subtype,)
            if subtype in SUPPORTED_ERV_SUBTYPES
        ]
        for subtype in SUPPORTED_ERV_SUBTYPES:
            if subtype not in probe_order:
                probe_order.append(subtype)

        candidates: list[tuple[int, int, int, int, str, dict]] = []
        probe_errors = []

        for subtype in probe_order:
            protocol = SUPPORTED_ERV_SUBTYPES[subtype]
            try:
                json_data = await self._request_status(protocol)
            except Exception as err:
                _LOGGER.debug("Fetch ERV status failed via %s: %s", subtype, err)
                continue

            error = json_data.get("error")
            if isinstance(error, dict) and "token" in str(error.get("message", "")):
                raise RuntimeError(
                    f"Panasonic device token rejected for {self._device_id}: {error}"
                )

            error_code = self._response_error_code(json_data)
            if error_code in {"3003", "3004"}:
                raise RuntimeError(f"Panasonic SSID expired for device {self._device_id}")
            if error_code and error_code != "0":
                probe_errors.append((subtype, json_data))
                _LOGGER.debug(
                    "ERV status probe returned error for %s via %s: %s",
                    self._device_id,
                    subtype,
                    json_data,
                )
                continue

            results = json_data.get("results")
            if not isinstance(results, dict):
                _LOGGER.debug(
                    "ERV status probe failed for %s via %s: %s",
                    self._device_id,
                    subtype,
                    json_data,
                )
                continue

            if not results:
                _LOGGER.debug(
                    "ERV status probe returned empty state for %s via %s: %s",
                    self._device_id,
                    subtype,
                    json_data,
                )
                continue

            merged = protocol["default_params"].copy()
            merged.update(results)
            if protocol.get("uses_status_all"):
                # LD5C legacy: signature judged on the RAW statusAll payload
                # keys (runningStatus/runningMode/airVolume...). The mapped
                # names (runSta/runM/airVo) collide with common fields that
                # the live MidERV endpoint returns for EVERY device, which
                # would misclassify SmallERV/MidERV devices as LD5C.
                raw_status_all = self._last_status_all_raw or {}
                raw_keys = set(protocol.get("status_all_field_map", {}).keys())
                signature_score = sum(
                    1 for key in raw_keys if key in raw_status_all
                )
            elif protocol.get("status_all_field_map"):
                # Info-family protocols (LD5C): the live Info GET returns the
                # device's own long camelCase names; score against the raw
                # pre-mapping response for the same collision reason.
                raw_status = self._last_status_raw or {}
                raw_keys = set(protocol.get("status_all_field_map", {}).keys())
                signature_score = sum(
                    1 for key in raw_keys if key in raw_status
                )
            else:
                signature_score = sum(
                    1 for key in protocol.get("signature_keys", set()) if key in results
                )
            known_run_mode = self._known_run_mode_score(protocol, results)
            # Probe all known protocols and prefer the richest signature match.
            # This avoids pinning MidERV-capable devices to SmallERV just because
            # the generic SmallERV endpoint returned a partial response first.
            candidates.append(
                (
                    known_run_mode,
                    signature_score,
                    len(results),
                    -probe_order.index(subtype),
                    subtype,
                    merged,
                )
            )

        if not candidates:
            if probe_errors:
                # Auth-related failures (e.g. 4102 认证错误 / 3003 / 3004)
                # mean the session went stale. Give the silent re-login a
                # chance to refresh credentials before surfacing the error;
                # the next poll retries with the fresh session.
                try:
                    await self._try_self_heal_family_id()
                except Exception:  # noqa: BLE001
                    pass
                raise RuntimeError(
                    f"Could not fetch ERV status for {self._device_id}: {probe_errors[-1][1]}"
                )
            return None

        _, _, _, _, detected_subtype, merged = max(candidates)

        if detected_subtype != self._device_subtype:
            _LOGGER.info(
                "Detected ERV subtype %s for device %s",
                detected_subtype,
                self._device_id,
            )
            self._apply_protocol(detected_subtype)
            self._persist_detected_subtype(detected_subtype)

        self._last_params = merged
        self.data = merged
        return merged

    def _persist_detected_subtype(self, detected_subtype: str) -> None:
        """Persist runtime subtype upgrades so old config entries self-heal."""
        if self._entry.data.get(CONF_DEVICE_SUBTYPE) == detected_subtype:
            return

        self._hass.config_entries.async_update_entry(
            self._entry,
            data={**self._entry.data, CONF_DEVICE_SUBTYPE: detected_subtype},
        )

    def _known_run_mode_score(self, protocol: dict, results: dict) -> int:
        """Return 1 only when runM is meaningful for the candidate protocol."""
        run_mode_map = protocol.get("run_mode_to_option", {})
        if "runM" not in results:
            return 0
        try:
            return 1 if int(results["runM"]) in run_mode_map else 0
        except (TypeError, ValueError):
            return 0

    async def _request_status(self, protocol: dict):
        """Send a raw ERV status request to a specific endpoint."""
        if protocol.get("uses_status_all"):
            # LD5C legacy: control fields (runningStatus/runningMode/airVolume)
            # only exist in the device-list statusAll payload; sensors come
            # from the live MidERV endpoint. Merge both into one result dict.
            json_data = await self._request_status_endpoint(protocol)
            if json_data is None:
                return None
            status_all = await self._request_status_all()
            # Keep the raw payload around so the probe loop can score the
            # LD5C signature against its own field names instead of the
            # mapped runSta/runM/airVo (which every endpoint returns).
            self._last_status_all_raw = status_all or {}
            if status_all:
                mapped = {
                    internal: status_all[external]
                    for external, internal in self._status_all_field_map.items()
                    if external in status_all
                }
                results = json_data.get("results")
                if isinstance(results, dict):
                    results.update(mapped)
                    json_data["results"] = results
                else:
                    json_data["results"] = mapped
            return json_data

        json_data = await self._request_status_endpoint(protocol)
        if json_data is None:
            return None

        # Protocols with a response field map (LD5C Info endpoints) return
        # their own long camelCase names; map them to the internal names the
        # entity code consumes and keep the raw response for signature scoring.
        field_map = protocol.get("status_all_field_map")
        if field_map:
            results = json_data.get("results")
            if isinstance(results, dict):
                self._last_status_raw = results
                mapped = {
                    internal: results[external]
                    for external, internal in field_map.items()
                    if external in results
                }
                new_results = {
                    key: value
                    for key, value in results.items()
                    if key not in field_map
                }
                new_results.update(mapped)
                json_data["results"] = new_results
        return json_data

    async def _request_status_all(self) -> dict | None:
        """Fetch the device-list statusAll payload used by LD5C control state.

        Requires familyId/realFamilyId, stored in the config entry by the
        config flow (or self-healed via a silent re-login since v1.7.1).
        Some accounts never receive familyId in the UsrLogin response, yet
        UsrGetBindDevInfo still answers the device list without it (the
        params are tolerated as null), so we send the request anyway
        instead of bailing out when they are missing.
        Returns None when the request fails.
        """
        if not self._family_id or not self._real_family_id:
            healed = await self._try_self_heal_family_id()
            if not healed:
                _LOGGER.debug(
                    "No familyId stored for %s; requesting statusAll without it",
                    self._device_id,
                )

        payload = {
            "id": 3,
            "uiVersion": 4.0,
            "params": {
                "realFamilyId": self._real_family_id,
                "familyId": self._family_id,
                "usrId": self._usr_id,
            },
        }
        session = async_get_clientsession(self._hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.post(
                    URL_GET_DEV,
                    json=payload,
                    headers=self._get_headers(),
                    ssl=psmartcloud_fingerprint(),
                )
                dev_res = await response.json()
        except Exception as err:
            _LOGGER.debug("LD5C statusAll fetch failed for %s: %s", self._device_id, err)
            return None

        for dev in dev_res.get("results", {}).get("devList", []):
            if dev.get("deviceId") == self._device_id:
                status_all = dev.get("params", {}).get("statusAll") or {}
                # Panasonic returns statusAll values as strings; normalize to
                # int so control payloads and attribute display stay clean.
                return self._normalize_status_all(status_all)
        return None

    async def _try_self_heal_family_id(self) -> bool:
        """Silently re-login to fetch familyId/realFamilyId and write them back.

        Uses credentials stored in the config entry (v1.7.1+). A cooldown keeps
        re-logins rare because a new login kicks the previous cloud session
        (e.g. the Panasonic phone app).
        """
        if not self._username or not self._password:
            return False

        domain_data = self._hass.data.setdefault(DOMAIN, {})
        now = time.monotonic()
        last_ts = domain_data.get("last_relogin_ts", 0)
        if now - last_ts < RELOGIN_COOLDOWN_SECONDS:
            _LOGGER.debug(
                "Skip silent re-login for %s: cooldown active (%ds left)",
                self._device_id,
                int(RELOGIN_COOLDOWN_SECONDS - (now - last_ts)),
            )
            return False
        domain_data["last_relogin_ts"] = now

        try:
            result = await authenticate(self._username, self._password)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Silent re-login failed for %s: %s", self._device_id, err)
            return False

        new_data = {**self._entry.data}
        new_data[CONF_USR_ID] = result["usrId"]
        new_data[CONF_SSID] = result["ssId"]
        if result.get(CONF_FAMILY_ID) is not None:
            new_data[CONF_FAMILY_ID] = result[CONF_FAMILY_ID]
        if result.get(CONF_REAL_FAMILY_ID) is not None:
            new_data[CONF_REAL_FAMILY_ID] = result[CONF_REAL_FAMILY_ID]
        self._hass.config_entries.async_update_entry(self._entry, data=new_data)

        # Refresh in-memory state so the retry below uses the new values.
        self._usr_id = result["usrId"]
        self._ssid = result["ssId"]
        self._family_id = new_data.get(CONF_FAMILY_ID)
        self._real_family_id = new_data.get(CONF_REAL_FAMILY_ID)

        if not self._family_id or not self._real_family_id:
            _LOGGER.warning(
                "Silent re-login for %s did not return familyId; "
                "the account may need re-adding",
                self._device_id,
            )
            return False

        _LOGGER.info("Self-healed familyId for %s via silent re-login", self._device_id)
        return True

    @staticmethod
    def _normalize_status_all(status_all: dict) -> dict:
        """Convert statusAll string values to int where possible."""
        normalized = {}
        for key, value in status_all.items():
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = value
        return normalized

    async def _request_status_endpoint(self, protocol: dict):
        """Send a raw ERV status request to the configured status endpoint."""
        payload = {
            "id": protocol.get("status_request_id", 2),
            "params": {
                "token": self._token,
                "deviceId": self._device_id,
                "usrId": self._usr_id,
            },
        }
        if protocol.get("status_identity_top_level"):
            # Info-family endpoints expect usrId/deviceId/token at the top
            # level of the request body (official web page request shape).
            payload = {
                "id": protocol.get("status_request_id", 2),
                CONF_USR_ID: self._usr_id,
                CONF_DEVICE_ID: self._device_id,
                CONF_TOKEN: self._token,
            }
        if protocol.get("status_ui_version") is not None:
            payload["uiVersion"] = protocol["status_ui_version"]
        session = async_get_clientsession(self._hass)
        async with async_timeout.timeout(10):
            response = await session.post(
                protocol["get_url"],
                json=payload,
                headers=self._get_headers(),
                ssl=psmartcloud_fingerprint(),
            )
            return await response.json()

    async def async_send_command(
        self,
        changes: dict,
        *,
        refresh: bool = True,
    ) -> None:
        """Send a control request using the selected ERV protocol rules."""
        # Protocols with a set field map (LD5C) speak their own wire field
        # names (runningStatus/runningMode/airVolume) and send the full bean
        # with only the target field changed - exactly like the official
        # Panasonic web control page - so no live status merge is performed.
        if self._set_field_name_map:
            changes = {
                self._set_field_name_map.get(key, key): value
                for key, value in changes.items()
            }

        latest_params = None
        if self._merge_current_status_for_control:
            latest_params = await self._fetch_status()

        current_params = self._control_params.copy()
        if self._merge_current_status_for_control:
            current_params.update(self._last_params)
            if latest_params:
                current_params.update(latest_params)

        current_params.update(changes)
        if not self._set_identity_top_level:
            current_params[CONF_DEVICE_ID] = self._device_id
            current_params[CONF_TOKEN] = self._token
            current_params[CONF_USR_ID] = self._usr_id

        params = {
            key: current_params[key]
            for key in self._safe_control_keys
            if key in current_params
        }

        body = {"id": self._set_request_id, "params": params}
        if self._set_identity_top_level:
            # Info-family endpoints expect usrId/deviceId/token at the top
            # level of the request body (official web page request shape).
            body = {
                "id": self._set_request_id,
                CONF_USR_ID: self._usr_id,
                CONF_DEVICE_ID: self._device_id,
                CONF_TOKEN: self._token,
                "params": params,
            }

        log_body = {
            key: ("***" if key == CONF_TOKEN else value)
            for key, value in body.items()
        }
        log_body["params"] = {
            key: ("***" if key in (CONF_TOKEN, "token") else value)
            for key, value in params.items()
        }
        _LOGGER.debug(
            "ERV set %s -> %s body=%s",
            self._device_id,
            self._url_set,
            log_body,
        )

        session = async_get_clientsession(self._hass)
        async with async_timeout.timeout(10):
            response = await session.post(
                self._url_set,
                json=body,
                headers=self._get_headers(),
                ssl=psmartcloud_fingerprint(),
            )
            response_json = await response.json()

        _LOGGER.debug("ERV set response %s: %s", self._device_id, response_json)

        error_code = self._response_error_code(response_json)
        if error_code and error_code != "0":
            raise RuntimeError(
                f"Panasonic ERV set command failed for {self._device_id}: {response_json}"
            )

        optimistic_params = self._default_params.copy()
        optimistic_params.update(self._last_params)
        optimistic_params.update(changes)
        self._last_params = optimistic_params
        self.async_set_updated_data(self._last_params)
        if refresh:
            await asyncio.sleep(COMMAND_REFRESH_DELAY)
            await self.async_request_refresh()

    def _response_error_code(self, response_json: dict) -> str:
        """Return either Panasonic errorCode or JSON-RPC style error.code."""
        error_code = response_json.get("errorCode")
        if error_code not in (None, ""):
            return str(error_code)

        error = response_json.get("error")
        if isinstance(error, dict):
            nested_code = error.get("code")
            if nested_code not in (None, ""):
                return str(nested_code)
        return ""

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SmartApp",
            "Cookie": f"SSID={self._ssid}",
        }
        if self._use_xtoken_header:
            # Info-family endpoints are controlled through the same auth
            # header the official web control page sends.
            headers["xtoken"] = f"SSID={self._ssid}"
        return headers
