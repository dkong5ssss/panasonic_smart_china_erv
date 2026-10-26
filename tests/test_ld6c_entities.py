"""Entity regression tests; cloud/device I/O is mocked.

Run with Python 3.13 and homeassistant==2025.3.4 installed:
    python -m unittest discover -s tests -v
"""

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tests.test_account_data import _load_package_module

const = _load_package_module("const", "const.py")
package = sys.modules["custom_components.panasonic_smart_china"]
# Load entity modules without running integration setup or contacting the cloud.
with patch.object(package, "get_account", lambda hass, entry: hass, create=True):
    sensor = _load_package_module("sensor", "sensor.py")
    light = _load_package_module("light", "light.py")


class FakeCoordinator:
    def __init__(self, data=None, subtype="LD6C", device_id="test-erv"):
        self.data = data or {}
        self.device_subtype = subtype
        self.device_id = device_id
        self.device_name = "Test ERV"
        self.ha_device_info = {
            "identifiers": {(const.DOMAIN, device_id)},
            "manufacturer": "Panasonic",
        }
        self.last_update_success = True
        self.async_set_field = AsyncMock()
        self.listeners = []

    def field_value(self, key):
        return self.data.get(key)

    def supports_control_field(self, key):
        return key in const.SUPPORTED_ERV_SUBTYPES[self.device_subtype]["safe_control_keys"]

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def update(self, data):
        self.data = data
        for listener in list(self.listeners):
            listener()


def spec_for(key):
    return next(spec for spec in sensor.SENSOR_SPECS if spec.key == key)


class LD6CSensorTests(unittest.TestCase):
    def test_valid_optional_fields_keep_existing_entities(self):
        coordinator = FakeCoordinator({"raPMC": 12, "resFilClTL": 48})
        keys = {spec.key for spec in sensor._specs_for_coordinator(coordinator)}
        self.assertEqual(
            keys,
            set(const.SENSOR_KEYS_BY_SUBTYPE["LD6C"]) | {"raPMC", "resFilClTL"},
        )

    def test_optional_fields_not_created_for_missing_or_invalid_values(self):
        for raw in (None, "", 65535, "65535", "invalid", -1):
            with self.subTest(raw=raw):
                coordinator = FakeCoordinator({"raPMC": raw, "resFilClTL": raw})
                keys = {spec.key for spec in sensor._specs_for_coordinator(coordinator)}
                self.assertNotIn("raPMC", keys)
                self.assertNotIn("resFilClTL", keys)

    def test_zero_and_pm25_255_are_valid(self):
        coordinator = FakeCoordinator({"raPMC": 255, "resFilClTL": 0})
        keys = {spec.key for spec in sensor._specs_for_coordinator(coordinator)}
        self.assertIn("raPMC", keys)
        self.assertIn("resFilClTL", keys)
        self.assertEqual(
            sensor.PanasonicERVSensor(coordinator, spec_for("raPMC")).native_value,
            255,
        )
        self.assertEqual(
            sensor.PanasonicERVSensor(coordinator, spec_for("resFilClTL")).native_value,
            0,
        )

    def test_countdown_uses_hours_and_duration_class(self):
        entity = sensor.PanasonicERVSensor(
            FakeCoordinator({"resFilClTL": "48"}), spec_for("resFilClTL")
        )
        self.assertEqual(entity.native_value, 48)
        self.assertEqual(entity.native_unit_of_measurement, "h")
        self.assertEqual(entity.device_class, "duration")

    def test_existing_ra_pm25_identity_is_reused(self):
        entity = sensor.PanasonicERVSensor(
            FakeCoordinator({"raPMC": 12}), spec_for("raPMC")
        )
        self.assertEqual(entity.unique_id, "panasonic_test-erv_ra_pm25")
        self.assertEqual(entity.native_value, 12)

    def test_sensor_becomes_unknown_on_sentinel_after_discovery(self):
        for key in ("raPMC", "resFilClTL"):
            coordinator = FakeCoordinator({key: 42})
            entity = sensor.PanasonicERVSensor(coordinator, spec_for(key))
            coordinator.data[key] = "65535"
            self.assertIsNone(entity.native_value)
            coordinator.data[key] = 0
            self.assertEqual(entity.native_value, 0)

    def test_other_whitelisted_protocols_are_unchanged(self):
        for subtype in const.SENSOR_KEYS_BY_SUBTYPE:
            if subtype == "LD6C":
                continue
            with self.subTest(subtype=subtype):
                coordinator = FakeCoordinator(
                    {"raPMC": 12, "resFilClTL": 48}, subtype=subtype
                )
                self.assertEqual(
                    {spec.key for spec in sensor._specs_for_coordinator(coordinator)},
                    set(const.SENSOR_KEYS_BY_SUBTYPE[subtype])
                    & {spec.key for spec in sensor.SENSOR_SPECS},
                )


class LD6CLightTests(unittest.IsolatedAsyncioTestCase):
    async def test_commands_only_change_indicator(self):
        coordinator = FakeCoordinator({"breathLight": 0, "runSta": 0, "airVo": 2})
        entity = light.PanasonicERVBreathLight(coordinator)
        self.assertTrue(entity.available)
        self.assertFalse(entity.is_on)
        await entity.async_turn_on()
        coordinator.async_set_field.assert_awaited_once_with("breathLight", 1)
        coordinator.async_set_field.reset_mock()
        await entity.async_turn_off()
        coordinator.async_set_field.assert_awaited_once_with("breathLight", 0)
        self.assertEqual(entity.supported_color_modes, {light.ColorMode.ONOFF})

    async def test_light_state_validation_and_offline(self):
        coordinator = FakeCoordinator()
        entity = light.PanasonicERVBreathLight(coordinator)
        for raw, expected in ((0, False), ("0", False), (1, True), ("1", True)):
            coordinator.data = {"breathLight": raw}
            self.assertIs(entity.is_on, expected)
            self.assertTrue(entity.available)
        for raw in (None, "", 2, 255, "255", "invalid"):
            coordinator.data = {"breathLight": raw}
            self.assertIsNone(entity.is_on)
            self.assertFalse(entity.available)
        coordinator.data = {"breathLight": 1}
        coordinator.last_update_success = False
        self.assertFalse(entity.available)

    async def test_non_ld6c_has_no_indicator_entity(self):
        for subtype in const.SUPPORTED_ERV_SUBTYPES:
            if subtype != "LD6C":
                self.assertFalse(
                    light._supports_breath_light(
                        FakeCoordinator({"breathLight": 1}, subtype=subtype)
                    )
                )

    async def test_command_failure_is_not_swallowed(self):
        coordinator = FakeCoordinator({"breathLight": 0})
        coordinator.async_set_field.side_effect = RuntimeError("Device rejected command")
        with self.assertRaises(RuntimeError):
            await light.PanasonicERVBreathLight(coordinator).async_turn_on()


class LD6CDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def _setup(self, platform, coordinators):
        account = SimpleNamespace(
            coordinators={item.device_id: item for item in coordinators}
        )
        cleanup = []
        entry = SimpleNamespace(async_on_unload=cleanup.append)
        entities = []
        await platform.async_setup_entry(account, entry, entities.extend)
        return entities, cleanup

    async def test_sensor_late_discovery_is_unique_and_cleans_up(self):
        coordinator = FakeCoordinator({"raPMC": 65535, "resFilClTL": 65535})
        entities, cleanup = await self._setup(sensor, [coordinator])
        baseline = len(entities)
        coordinator.update({"raPMC": 12, "resFilClTL": 48})
        self.assertEqual(len(entities), baseline + 2)
        coordinator.update({"raPMC": 13, "resFilClTL": 47})
        self.assertEqual(len(entities), baseline + 2)
        coordinator.update({"raPMC": 65535, "resFilClTL": 65535})
        self.assertEqual(len(entities), baseline + 2)
        for unsubscribe in cleanup:
            unsubscribe()
        self.assertEqual(coordinator.listeners, [])

    async def test_light_late_discovery_is_unique_and_cleans_up(self):
        coordinator = FakeCoordinator({"breathLight": 255})
        entities, cleanup = await self._setup(light, [coordinator])
        self.assertEqual(entities, [])
        coordinator.update({"breathLight": 0})
        self.assertEqual(len(entities), 1)
        coordinator.update({"breathLight": 1})
        self.assertEqual(len(entities), 1)
        coordinator.update({"breathLight": 255})
        self.assertEqual(len(entities), 1)
        self.assertFalse(entities[0].available)
        for unsubscribe in cleanup:
            unsubscribe()
        self.assertEqual(coordinator.listeners, [])

    async def test_multiple_devices_have_distinct_entities(self):
        coordinators = [
            FakeCoordinator(
                {"breathLight": 0, "raPMC": 10, "resFilClTL": 0}, device_id=device
            )
            for device in ("erv-one", "erv-two")
        ]
        for platform in (sensor, light):
            with self.subTest(platform=platform.__name__):
                entities, cleanup = await self._setup(platform, coordinators)
                ids = [entity.unique_id for entity in entities]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(any("erv-one" in value for value in ids))
                self.assertTrue(any("erv-two" in value for value in ids))
                for unsubscribe in cleanup:
                    unsubscribe()


class ProtocolBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_protocol_retains_existing_sensor_discovery(self):
        coordinator = FakeCoordinator(
            {"raPMC": 12, "resFilClTL": 48, "oaTeC": 23}, subtype="UNKNOWN"
        )
        self.assertEqual(
            {spec.key for spec in sensor._specs_for_coordinator(coordinator)},
            {"raPMC", "oaTeC"},
        )

    async def test_auto_protocol_can_resolve_to_ld6c(self):
        coordinator = FakeCoordinator(
            {"resFilClTL": 48, "breathLight": 1}, subtype="AUTO"
        )
        account = SimpleNamespace(coordinators={coordinator.device_id: coordinator})
        cleanup = []
        entry = SimpleNamespace(async_on_unload=cleanup.append)
        sensors, lights = [], []
        await sensor.async_setup_entry(account, entry, sensors.extend)
        await light.async_setup_entry(account, entry, lights.extend)
        self.assertEqual(sensors, [])
        self.assertEqual(lights, [])
        coordinator.device_subtype = "LD6C"
        coordinator.update({"resFilClTL": 48, "breathLight": 1})
        self.assertTrue(any(item._spec.key == "resFilClTL" for item in sensors))
        self.assertEqual(len(lights), 1)
        for unsubscribe in cleanup:
            unsubscribe()
        self.assertEqual(coordinator.listeners, [])
