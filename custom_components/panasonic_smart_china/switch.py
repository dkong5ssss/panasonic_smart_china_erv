from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .erv import async_get_coordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV switch entities."""
    coordinator = await async_get_coordinator(hass, entry)
    async_add_entities([PanasonicERVHolidaySwitch(coordinator, entry.title)])


class PanasonicERVHolidaySwitch(CoordinatorEntity, SwitchEntity):
    """ERV holiday mode switch."""

    _attr_icon = "mdi:beach"

    def __init__(self, coordinator, device_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{device_name} 假日模式"
        self._attr_unique_id = f"panasonic_{coordinator.device_id}_holiday"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "manufacturer": "Panasonic",
            "model": coordinator.device_subtype,
            "name": device_name,
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.supports_control_field("holM")
        )

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.field_value("holM")
        if raw in (None, ""):
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return None if value == 255 else value == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_field("holM", 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_field("holM", 0)
