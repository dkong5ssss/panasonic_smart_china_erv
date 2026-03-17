from datetime import timedelta
import logging

import async_timeout

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_SUBTYPE,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_SMALL_ERV,
    PRESET_LOW,
    SUPPORTED_ERV_SUBTYPES,
)

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV fan entities."""
    async_add_entities([PanasonicERVEntity(hass, entry.data, entry.title)])


class PanasonicERVEntity(FanEntity):
    """Panasonic Smart China ERV entity using subtype-specific endpoints."""

    def __init__(self, hass, config, name) -> None:
        self._hass = hass
        self._usr_id = config[CONF_USR_ID]
        self._device_id = config[CONF_DEVICE_ID]
        self._token = config[CONF_TOKEN]
        self._ssid = config[CONF_SSID]
        self._device_subtype = config.get(CONF_DEVICE_SUBTYPE, DEVICE_SUBTYPE_SMALL_ERV)
        self._apply_protocol(self._device_subtype)

        self._attr_name = name
        self._attr_unique_id = f"panasonic_{self._device_id}"
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.PRESET_MODE
        )

        self._is_on = False
        self._preset_mode = PRESET_LOW
        self._available = True
        self._last_params = self._default_params.copy()
        self._unsub_polling = None

    def _apply_protocol(self, device_subtype: str) -> None:
        """Load endpoint and payload rules for the selected ERV subtype."""
        protocol = SUPPORTED_ERV_SUBTYPES.get(
            device_subtype,
            SUPPORTED_ERV_SUBTYPES[DEVICE_SUBTYPE_SMALL_ERV],
        )
        self._device_subtype = device_subtype
        self._protocol = protocol
        self._default_params = protocol["default_params"]
        self._safe_control_keys = protocol["safe_control_keys"]
        self._preset_to_air_volume = protocol["preset_to_air_volume"]
        self._air_volume_to_preset = protocol["air_volume_to_preset"]
        self._url_get = protocol["get_url"]
        self._url_set = protocol["set_url"]

    @property
    def should_poll(self) -> bool:
        """Disable Home Assistant default polling."""
        return False

    async def async_added_to_hass(self) -> None:
        """Start interval polling when the entity is added."""
        await super().async_added_to_hass()
        self._unsub_polling = async_track_time_interval(
            self._hass,
            self._async_update_interval_wrapper,
            POLLING_INTERVAL,
        )
        await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the interval handler."""
        if self._unsub_polling:
            self._unsub_polling()
            self._unsub_polling = None
        await super().async_will_remove_from_hass()

    async def _async_update_interval_wrapper(self, now) -> None:
        """Run the scheduled refresh."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def preset_modes(self) -> list[str]:
        return list(self._preset_to_air_volume.keys())

    @property
    def preset_mode(self) -> str:
        return self._preset_mode

    @property
    def extra_state_attributes(self) -> dict:
        return {
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

    async def async_update(self) -> None:
        """Fetch the latest device status."""
        await self._fetch_status(update_internal_state=True)

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        """Turn the ERV on, optionally selecting a preset."""
        changes = {"runSta": 1}
        if preset_mode in self._preset_to_air_volume:
            changes["airVo"] = self._preset_to_air_volume[preset_mode]
        await self._send_command(changes)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the ERV off."""
        await self._send_command({"runSta": 0})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set ERV air volume using HA preset modes."""
        if preset_mode not in self._preset_to_air_volume:
            _LOGGER.warning("Unsupported ERV preset mode requested: %s", preset_mode)
            return
        await self._send_command(
            {
                "runSta": 1,
                "airVo": self._preset_to_air_volume[preset_mode],
            }
        )

    async def _fetch_status(self, update_internal_state: bool = True):
        """Fetch the current ERV status."""
        try:
            probe_order = [self._device_subtype]
            for subtype in SUPPORTED_ERV_SUBTYPES:
                if subtype not in probe_order:
                    probe_order.append(subtype)

            for subtype in probe_order:
                protocol = SUPPORTED_ERV_SUBTYPES[subtype]
                json_data = await self._request_status(protocol["get_url"])
                if json_data is None:
                    continue

                error_code = str(json_data.get("errorCode", ""))
                if error_code in {"3003", "3004"}:
                    self._available = False
                    _LOGGER.error("Panasonic SSID expired for device %s", self._device_id)
                    return None

                error = json_data.get("error")
                if isinstance(error, dict) and "token" in str(error.get("message", "")):
                    self._available = False
                    _LOGGER.error(
                        "Panasonic device token rejected for %s: %s",
                        self._device_id,
                        error,
                    )
                    return None

                results = json_data.get("results")
                if not isinstance(results, dict):
                    _LOGGER.debug(
                        "ERV status probe failed for %s via %s: %s",
                        self._device_id,
                        subtype,
                        json_data,
                    )
                    continue

                if subtype != self._device_subtype:
                    _LOGGER.info(
                        "Detected ERV subtype %s for device %s",
                        subtype,
                        self._device_id,
                    )
                    self._apply_protocol(subtype)

                merged = self._default_params.copy()
                merged.update(results)
                self._last_params = merged
                self._available = True

                if update_internal_state:
                    self._update_local_state(merged)

                return merged

            self._available = False
            _LOGGER.warning(
                "Could not fetch ERV status for %s using any known subtype",
                self._device_id,
            )
            return None
        except Exception as err:
            self._available = False
            _LOGGER.debug("Fetch ERV status failed: %s", err)
            return None

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

    def _update_local_state(self, params: dict) -> None:
        """Map raw ERV status into HA fan state."""
        self._is_on = params.get("runSta") == 1
        self._preset_mode = self._air_volume_to_preset.get(
            params.get("airVo"),
            PRESET_LOW,
        )

    async def _send_command(self, changes: dict) -> None:
        """Read-modify-write using the ERV payload shape from the capture."""
        latest_params = await self._fetch_status(update_internal_state=False)
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

        try:
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
                _LOGGER.error(
                    "Panasonic ERV set command failed for %s: %s",
                    self._device_id,
                    response_json,
                )
                self._available = False
                return

            self._last_params = self._default_params.copy()
            self._last_params.update(params)
            self._update_local_state(self._last_params)
            self._available = True
            self.async_write_ha_state()
        except Exception as err:
            self._available = False
            _LOGGER.error("Panasonic ERV set failed for %s: %s", self._device_id, err)

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "User-Agent": "SmartApp",
            "Cookie": f"SSID={self._ssid}",
        }
