from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .erv import async_get_coordinator


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV select entities."""
    coordinator = await async_get_coordinator(hass, entry)
    entities = [PanasonicERVRunModeSelect(coordinator, entry.title)]
    entities.extend(
        PanasonicERVFieldSelect(coordinator, entry.title, config)
        for config in coordinator.extra_selects
    )
    async_add_entities(entities)


class PanasonicERVRunModeSelect(CoordinatorEntity, SelectEntity):
    """ERV run mode selector."""

    def __init__(self, coordinator, device_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{device_name} 运行模式"
        self._attr_unique_id = f"panasonic_{coordinator.device_id}_run_mode"
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
            and self.coordinator.supports_run_mode_select
        )

    @property
    def current_option(self) -> str | None:
        return self.coordinator.current_run_mode

    @property
    def options(self) -> list[str]:
        return self.coordinator.run_mode_options

    async def async_select_option(self, option: str) -> None:
        """Select a new ERV run mode."""
        await self.coordinator.async_set_run_mode(option)


class PanasonicERVFieldSelect(CoordinatorEntity, SelectEntity):
    """Protocol-configured selector for ERV settings."""

    def __init__(self, coordinator, device_name: str, config: dict) -> None:
        super().__init__(coordinator)
        self._field = config["field"]
        self._options_by_value = config["options"]
        self._values_by_option = {
            option: value for value, option in self._options_by_value.items()
        }
        self._available_when = config.get("available_when")
        self._attr_name = f"{device_name} {config['name_suffix']}"
        self._attr_unique_id = f"panasonic_{coordinator.device_id}_{config['suffix']}"
        self._attr_options = list(dict.fromkeys(self._options_by_value.values()))
        self._attr_icon = config.get("icon")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "manufacturer": "Panasonic",
            "model": coordinator.device_subtype,
            "name": device_name,
        }

    @property
    def available(self) -> bool:
        if not (
            self.coordinator.last_update_success
            and self.coordinator.supports_control_field(self._field)
        ):
            return False
        if not self._available_when:
            return True

        raw = self.coordinator.field_value(self._available_when["field"])
        try:
            return int(raw) == self._available_when["value"]
        except (TypeError, ValueError):
            return False

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.field_value(self._field)
        if raw in (None, ""):
            return None
        try:
            return self._options_by_value.get(int(raw))
        except (TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Select a new value for the protocol field."""
        if option not in self._values_by_option:
            raise HomeAssistantError(f"Unsupported ERV option: {option}")
        await self.coordinator.async_set_field(
            self._field,
            self._values_by_option[option],
        )
