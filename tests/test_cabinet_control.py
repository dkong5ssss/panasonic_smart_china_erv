"""CABINET control regression tests (issue #10); cloud I/O is mocked.

Run with Python 3.13 and homeassistant==2025.3.4 installed:
    python -m unittest discover -s tests -v
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote

from tests.test_account_data import _load_package_module

const = _load_package_module("const", "const.py")
erv = _load_package_module("erv", "erv.py")


class FakeAccount:
    usr_id = "user"
    ssid = "ssid x"
    generation = 0

    def request_headers(self, use_xtoken=False):
        headers = {"Cookie": f"SSID={self.ssid}"}
        if use_xtoken:
            headers["xtoken"] = f"SSID={self.ssid}"
        return headers


def make_coordinator(subtype, dev_sub_type_id, device_name="客厅新风"):
    coordinator = erv.PanasonicERVCoordinator.__new__(erv.PanasonicERVCoordinator)
    coordinator._hass = MagicMock()
    coordinator._entry = MagicMock()
    coordinator._account = FakeAccount()
    coordinator._device_id = "AABBCCDDEEFF_0800_1"
    coordinator._device_name = device_name
    coordinator._token = "device-token"
    coordinator._dev_sub_type_id = dev_sub_type_id
    coordinator._apply_protocol(subtype)
    coordinator._last_params = coordinator._default_params.copy()
    coordinator._last_status_all_raw = {}
    coordinator._last_status_raw = {}
    coordinator._pre_sleep_run_mode = None
    coordinator._pre_sleep_air_volume = None
    coordinator._persist_detected_subtype = MagicMock()
    return coordinator


class CabinetCommandTests(unittest.IsolatedAsyncioTestCase):
    async def _send(self, coordinator, action):
        posted = []

        class Response:
            async def json(self):
                return {"results": {"todoId": 1}}

        class Session:
            async def post(self, url, json, headers, ssl):
                posted.append((url, json, headers))
                return Response()

        coordinator.async_set_updated_data = MagicMock()
        coordinator.async_request_refresh = AsyncMock()
        with patch.object(erv, "async_get_clientsession", lambda hass: Session()), \
                patch.object(erv.asyncio, "sleep", AsyncMock()):
            await action()
        return posted

    async def test_turn_on_sends_full_official_bean_and_referer(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-01")
        posted = await self._send(coordinator, coordinator.async_turn_on)
        self.assertEqual(len(posted), 1)

        url, body, headers = posted[0]
        self.assertTrue(url.endswith("/App/ADevSetStatusInfoFloorPlacedERV"))
        self.assertEqual(body["id"], 2)
        self.assertEqual(body["usrId"], "user")
        self.assertEqual(body["deviceId"], "AABBCCDDEEFF_0800_1")
        self.assertEqual(body["token"], "device-token")

        expected = dict(const.CABINET_SET_DEFAULT_PARAMS, runningStatus=1)
        self.assertEqual(body["params"], expected)
        self.assertEqual(len(expected), 23)
        self.assertNotIn("windPath", body["params"])
        self.assertIn("airDirection", body["params"])

        self.assertEqual(headers["xtoken"], "SSID=ssid x")
        referer = headers["Referer"]
        self.assertTrue(
            referer.startswith(
                "https://app.psmartcloud.com/ca/cn/0800/CABINET-01/index.html"
                "?deviceId=AABBCCDDEEFF_0800_1&usrId=user&SSID=ssid%20x"
                "&devType=CABINET-01&deviceName="
            )
        )
        self.assertTrue(referer.endswith(quote("客厅新风", safe="")))

    async def test_referer_falls_back_to_generic_cabinet_page(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, None)
        headers = coordinator._get_headers(for_set=True)
        self.assertIn("/0800/CABINET/index.html", headers["Referer"])
        self.assertIn("devType=CABINET", headers["Referer"])

    async def test_referer_is_only_sent_on_set(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-02")
        self.assertNotIn("Referer", coordinator._get_headers())
        self.assertIn("Referer", coordinator._get_headers(for_set=True))

    async def test_percentage_uses_five_cabinet_steps(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-01")
        coordinator._last_params = {**coordinator._last_params, "runSta": 1}

        posted = await self._send(
            coordinator, lambda: coordinator.async_set_percentage(100)
        )
        self.assertEqual(len(posted), 1)
        self.assertEqual(posted[0][1]["params"]["airVolume"], 5)
        self.assertEqual(coordinator.percentage, 100)

        posted = await self._send(
            coordinator, lambda: coordinator.async_set_percentage(66)
        )
        self.assertEqual(posted[0][1]["params"]["airVolume"], 4)

    async def test_internal_field_names_map_to_wire_names(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-01")
        coordinator._last_params = {**coordinator._last_params, "runSta": 1}

        self.assertTrue(coordinator.supports_control_field("holM"))
        posted = await self._send(
            coordinator, lambda: coordinator.async_set_field("holM", 1)
        )
        self.assertEqual(posted[0][1]["params"]["holidayMode"], 1)

        self.assertTrue(coordinator.supports_control_field("windPath"))
        posted = await self._send(
            coordinator, lambda: coordinator.async_set_field("windPath", 2)
        )
        self.assertEqual(posted[0][1]["params"]["airDirection"], 2)
        self.assertFalse(coordinator.supports_control_field("nonexistent"))

    def test_erv_keeps_three_speed_steps(self):
        cabinet = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-01")
        erv01 = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        self.assertEqual(cabinet._air_volume_steps, [1, 2, 3, 4, 5])
        self.assertEqual(erv01._air_volume_steps, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
