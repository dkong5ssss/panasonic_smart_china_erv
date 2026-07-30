from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    DOMAIN,
    SENSOR_INVALID_VALUES,
    SENSOR_KEYS_BY_SUBTYPE,
)
from .erv import async_get_coordinator

SENSOR_ALIASES = {
    "raCO2C": "raCo2C",
    "raTVC": "raTvC",
}


@dataclass(frozen=True)
class ERVSensorSpec:
    key: str
    name_suffix: str
    unique_suffix: str
    device_class: SensorDeviceClass | None
    unit: str | None
    icon: str | None = None


SENSOR_SPECS: tuple[ERVSensorSpec, ...] = (
    ERVSensorSpec(
        "oaPMC",
        "室外 PM2.5",
        "oa_pm25",
        SensorDeviceClass.PM25,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    ERVSensorSpec(
        "saPMC",
        "送风 PM2.5",
        "sa_pm25",
        SensorDeviceClass.PM25,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    ERVSensorSpec(
        "raPMC",
        "回风 PM2.5",
        "ra_pm25",
        SensorDeviceClass.PM25,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    ERVSensorSpec(
        "oaHumC",
        "室外湿度",
        "oa_humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
    ),
    ERVSensorSpec(
        "saHumC",
        "送风湿度",
        "sa_humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
    ),
    ERVSensorSpec(
        "raHumC",
        "回风湿度",
        "ra_humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
    ),
    ERVSensorSpec(
        "oaTeC",
        "室外温度",
        "oa_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    ERVSensorSpec(
        "saTeC",
        "送风温度",
        "sa_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    ERVSensorSpec(
        "raTeC",
        "回风温度",
        "ra_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    ERVSensorSpec(
        "raCO2C",
        "回风 CO2",
        "ra_co2",
        SensorDeviceClass.CO2,
        CONCENTRATION_PARTS_PER_MILLION,
    ),
    ERVSensorSpec(
        "raTVC",
        "回风 TVOC 等级",
        "ra_tvoc",
        None,
        None,
        icon="mdi:air-filter",
    ),
    ERVSensorSpec(
        "oaFilExTL",
        "外滤网剩余寿命",
        "oa_filter_life",
        None,
        UnitOfTime.HOURS,
        icon="mdi:air-filter",
    ),
    ERVSensorSpec(
        "saFilExTL",
        "送风滤网剩余寿命",
        "sa_filter_life",
        None,
        UnitOfTime.HOURS,
        icon="mdi:air-filter",
    ),
    ERVSensorSpec(
        "raFilExTL",
        "回风滤网剩余寿命",
        "ra_filter_life",
        None,
        UnitOfTime.HOURS,
        icon="mdi:air-filter",
    ),
    ERVSensorSpec(
        "resFilExTL",
        "新风集尘滤网剩余寿命",
        "res_filter_life",
        None,
        UnitOfTime.HOURS,
        icon="mdi:air-filter",
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Panasonic ERV sensor entities."""
    coordinator = await async_get_coordinator(hass, entry)
    allowed_keys = SENSOR_KEYS_BY_SUBTYPE.get(coordinator.device_subtype)
    if allowed_keys is None:
        data_keys = set((coordinator.data or {}).keys())
        specs = tuple(
            spec
            for spec in SENSOR_SPECS
            if spec.key in data_keys or SENSOR_ALIASES.get(spec.key) in data_keys
        )
    else:
        specs = tuple(spec for spec in SENSOR_SPECS if spec.key in allowed_keys)

    async_add_entities(
        PanasonicERVSensor(coordinator, entry, spec) for spec in specs
    )


class PanasonicERVSensor(CoordinatorEntity, SensorEntity):
    """Panasonic ERV measurement sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, spec: ERVSensorSpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_name = f"{entry.title} {spec.name_suffix}"
        self._attr_unique_id = f"panasonic_{device_id}_{spec.unique_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "manufacturer": "Panasonic",
            "model": coordinator.device_subtype,
            "name": entry.title,
        }
        if spec.device_class is not None:
            self._attr_device_class = spec.device_class
        if spec.unit is not None:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.icon:
            self._attr_icon = spec.icon

    @property
    def native_value(self):
        raw = self._raw_value()
        if raw in (None, ""):
            return None
        if self._is_invalid_value(raw):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

    def _raw_value(self):
        data = self.coordinator.data or {}
        raw = data.get(self._spec.key)
        if raw is not None:
            return raw
        alias = SENSOR_ALIASES.get(self._spec.key)
        if alias:
            return data.get(alias)
        return None

    def _is_invalid_value(self, raw) -> bool:
        try:
            numeric = int(raw)
        except (TypeError, ValueError):
            return False
        return numeric in SENSOR_INVALID_VALUES.get(self._spec.key, ())
