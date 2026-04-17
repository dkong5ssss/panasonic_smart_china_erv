from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .erv import async_get_coordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV select entities."""
    coordinator = await async_get_coordinator(hass, entry)
    if coordinator.supports_run_mode_select:
        async_add_entities([PanasonicERVRunModeSelect(coordinator, entry.title)])


class PanasonicERVRunModeSelect(CoordinatorEntity, SelectEntity):
    """MidERV run mode selector."""

    def __init__(self, coordinator, device_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{device_name} Run Mode"
        self._attr_unique_id = f"panasonic_{coordinator.device_id}_run_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "manufacturer": "Panasonic",
            "model": coordinator.device_subtype,
            "name": device_name,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        return self.coordinator.current_run_mode

    @property
    def options(self) -> list[str]:
        return self.coordinator.run_mode_options

    async def async_select_option(self, option: str) -> None:
        """Select a new MidERV run mode."""
        await self.coordinator.async_set_run_mode(option)
