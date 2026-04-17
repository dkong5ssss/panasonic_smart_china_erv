from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .erv import async_get_coordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV fan entities."""
    coordinator = await async_get_coordinator(hass, entry)
    async_add_entities([PanasonicERVEntity(coordinator, entry.title)])


class PanasonicERVEntity(CoordinatorEntity, FanEntity):
    """Panasonic Smart China ERV fan entity."""

    def __init__(self, coordinator, name) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"panasonic_{coordinator.device_id}"
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.PRESET_MODE
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_on

    @property
    def preset_modes(self) -> list[str]:
        return self.coordinator.preset_modes

    @property
    def preset_mode(self) -> str:
        return self.coordinator.preset_mode

    @property
    def extra_state_attributes(self) -> dict:
        return self.coordinator.extra_state_attributes

    async def async_update(self) -> None:
        """Fetch the latest device status."""
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        """Turn the ERV on, optionally selecting a preset."""
        await self.coordinator.async_turn_on(preset_mode=preset_mode)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the ERV off."""
        await self.coordinator.async_turn_off()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set ERV air volume using HA preset modes."""
        await self.coordinator.async_set_preset_mode(preset_mode)
