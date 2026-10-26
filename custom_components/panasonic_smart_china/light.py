"""Optional LD6C breathing indicator light."""

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_account
from .const import DEVICE_SUBTYPE_LD6C

BREATH_LIGHT_FIELD = "breathLight"


def _light_value(coordinator) -> int | None:
    raw = coordinator.field_value(BREATH_LIGHT_FIELD)
    # Accept both JSON integers and their string representation. Other
    # protocol values (notably 255 = unsupported/keep) are not "on".
    if raw in (0, "0"):
        return 0
    if raw in (1, "1"):
        return 1
    return None


def _supports_breath_light(coordinator) -> bool:
    return (
        coordinator.device_subtype == DEVICE_SUBTYPE_LD6C
        and coordinator.supports_control_field(BREATH_LIGHT_FIELD)
        and _light_value(coordinator) is not None
    )


async def async_setup_entry(hass, entry, async_add_entities):
    """Add lights only after a device reports a supported indicator state."""
    account = get_account(hass, entry)
    added: set[str] = set()

    def _add_entities() -> None:
        entities = []
        for coordinator in account.coordinators.values():
            if (
                coordinator.device_id not in added
                and _supports_breath_light(coordinator)
            ):
                added.add(coordinator.device_id)
                entities.append(PanasonicERVBreathLight(coordinator))
        if entities:
            async_add_entities(entities)

    _add_entities()
    for coordinator in account.coordinators.values():
        entry.async_on_unload(coordinator.async_add_listener(_add_entities))


class PanasonicERVBreathLight(CoordinatorEntity, LightEntity):
    """Control the indicator independently of the ERV fan power."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} 呼吸灯"
        self._attr_unique_id = f"panasonic_{coordinator.device_id}_breath_light"
        self._attr_device_info = coordinator.ha_device_info

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and _supports_breath_light(
            self.coordinator
        )

    @property
    def is_on(self) -> bool | None:
        value = _light_value(self.coordinator)
        return None if value is None else value == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_field(BREATH_LIGHT_FIELD, 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_field(BREATH_LIGHT_FIELD, 0)
