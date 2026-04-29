from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_SUBTYPE,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_SMALL_ERV,
    DOMAIN,
    PRESET_LOW,
    SUPPORTED_ERV_SUBTYPES,
)

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = timedelta(seconds=30)


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
        self._device_subtype = config.get(CONF_DEVICE_SUBTYPE, DEVICE_SUBTYPE_SMALL_ERV)
        self._apply_protocol(self._device_subtype)
        self._last_params = self._default_params.copy()
        super().__init__(
            hass,
            _LOGGER,
            name=f"panasonic_erv_{self._device_id}",
            update_interval=POLLING_INTERVAL,
        )

    def _apply_protocol(self, device_subtype: str) -> None:
        """Load endpoint and payload rules for the selected ERV subtype."""
        protocol = SUPPORTED_ERV_SUBTYPES.get(
            device_subtype,
            SUPPORTED_ERV_SUBTYPES[DEVICE_SUBTYPE_SMALL_ERV],
        )
        self._device_subtype = device_subtype
        self._default_params = protocol["default_params"]
        self._safe_control_keys = protocol["safe_control_keys"]
        self._preset_to_air_volume = protocol["preset_to_air_volume"]
        self._air_volume_to_preset = protocol["air_volume_to_preset"]
        self._air_volume_steps = protocol.get("air_volume_steps", [])
        self._run_mode_to_option = protocol.get("run_mode_to_option", {})
        self._option_to_run_mode = protocol.get("option_to_run_mode", {})
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
        return self._last_params.get("runSta") == 1

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

        current_air_volume = self._last_params.get("airVo")
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
        return self._run_mode_to_option.get(self._last_params.get("runM"))

    @property
    def supports_run_mode_select(self) -> bool:
        return bool(self._option_to_run_mode)

    @property
    def extra_state_attributes(self) -> dict:
        attrs = {
            "device_id": self._device_id,
            "device_subtype": self._device_subtype,
            "runSta": self._last_params.get("runSta"),
            "airVo": self._last_params.get("airVo"),
            "runM": self._last_params.get("runM"),
            "filSet": self._last_params.get("filSet"),
            "oaFilExPM": self._last_params.get("oaFilExPM"),
            "saFilEx": self._last_params.get("saFilEx"),
            "raFilEx": self._last_params.get("raFilEx"),
        }
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
        await self.async_send_command({"runSta": 1, "airVo": air_volume})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set ERV run mode using HA preset modes."""
        if preset_mode not in self._option_to_run_mode:
            _LOGGER.warning("Unsupported ERV run mode requested: %s", preset_mode)
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
        await self.async_send_command({"runSta": 1, "runM": run_mode})

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
        probe_order = [self._device_subtype]
        for subtype in SUPPORTED_ERV_SUBTYPES:
            if subtype not in probe_order:
                probe_order.append(subtype)

        candidates: list[tuple[int, int, int, str, dict]] = []

        for subtype in probe_order:
            protocol = SUPPORTED_ERV_SUBTYPES[subtype]
            try:
                json_data = await self._request_status(protocol["get_url"])
            except Exception as err:
                _LOGGER.debug("Fetch ERV status failed via %s: %s", subtype, err)
                continue

            error_code = str(json_data.get("errorCode", ""))
            if error_code in {"3003", "3004"}:
                raise RuntimeError(f"Panasonic SSID expired for device {self._device_id}")

            error = json_data.get("error")
            if isinstance(error, dict) and "token" in str(error.get("message", "")):
                raise RuntimeError(
                    f"Panasonic device token rejected for {self._device_id}: {error}"
                )

            results = json_data.get("results")
            if not isinstance(results, dict):
                _LOGGER.debug(
                    "ERV status probe failed for %s via %s: %s",
                    self._device_id,
                    subtype,
                    json_data,
                )
                continue

            merged = protocol["default_params"].copy()
            merged.update(results)
            signature_score = sum(
                1 for key in protocol.get("signature_keys", set()) if key in results
            )
            has_run_mode = 1 if "runM" in results else 0
            # Probe all known protocols and prefer the richest signature match.
            # This avoids pinning MidERV-capable devices to SmallERV just because
            # the generic SmallERV endpoint returned a partial response first.
            candidates.append(
                (
                    has_run_mode,
                    signature_score,
                    -probe_order.index(subtype),
                    subtype,
                    merged,
                )
            )

        if not candidates:
            return None

        _, _, _, detected_subtype, merged = max(candidates)

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

    async def _request_status(self, url: str):
        """Send a raw ERV status request to a specific endpoint."""
        payload = {
            "id": 2,
            "params": {
                "token": self._token,
                "deviceId": self._device_id,
                "usrId": self._usr_id,
            },
        }
        session = async_get_clientsession(self._hass)
        async with async_timeout.timeout(10):
            response = await session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                ssl=False,
            )
            return await response.json()

    async def async_send_command(self, changes: dict) -> None:
        """Read-modify-write using the ERV payload shape from the capture."""
        latest_params = await self._fetch_status()
        current_params = self._default_params.copy()
        current_params.update(self._last_params)
        if latest_params:
            current_params.update(latest_params)
        else:
            _LOGGER.warning(
                "Could not fetch latest ERV status for %s, using cached values",
                self._device_id,
            )

        current_params.update(changes)
        current_params[CONF_DEVICE_ID] = self._device_id
        current_params[CONF_TOKEN] = self._token
        current_params[CONF_USR_ID] = self._usr_id

        params = {
            key: current_params[key]
            for key in self._safe_control_keys
            if key in current_params
        }

        session = async_get_clientsession(self._hass)
        async with async_timeout.timeout(10):
            response = await session.post(
                self._url_set,
                json={
                    "id": 0,
                    "params": params,
                },
                headers=self._get_headers(),
                ssl=False,
            )
            response_json = await response.json()

        error_code = str(response_json.get("errorCode", ""))
        if error_code and error_code != "0":
            raise RuntimeError(
                f"Panasonic ERV set command failed for {self._device_id}: {response_json}"
            )

        self._last_params = self._default_params.copy()
        self._last_params.update(params)
        self.async_set_updated_data(self._last_params)

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "User-Agent": "SmartApp",
            "Cookie": f"SSID={self._ssid}",
        }
