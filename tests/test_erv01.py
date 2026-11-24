"""ERV-01 (FV-09ZVDH1C, issue #8) regression tests; cloud I/O is mocked.

Run with Python 3.13 and homeassistant==2025.3.4 installed:
    python -m unittest discover -s tests -v
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.test_account_data import _load_package_module

const = _load_package_module("const", "const.py")
erv = _load_package_module("erv", "erv.py")
config_flow = _load_package_module("config_flow", "config_flow.py")

# statusAll as returned by UsrGetBindDevInfo for a real FV-09ZVDH1C
# (timer values replaced with keep-sentinels).
ERV01_STATUS_ALL = {
    "airVolume": "1", "alarmStatus": "0", "autoSensitivity": "2",
    "hardVersion": "0", "heatingMode": "0", "holidayMode": "0",
    "oaFilterClCycle": "255", "oaFilterClTimeLeft": "65535",
    "oaFilterExCycle": "255", "oaFilterExTimeLeft": "65535",
    "oaHumidityCur": "100", "oaHumidityMax": "100", "oaPM25Cur": "57",
    "oaPM25Max": "62", "oaTempCur": "18", "oaTempMax": "18",
    "offTimerHour": "127", "offTimerMinute": "127", "offTimerSetting": "255",
    "onTimerHour": "127", "onTimerMinute": "127", "onTimerSetting": "255",
    "pPressureMode": "0", "pm25SensorClTimeLeft": "249",
    "raHumidityCur": "98", "raHumidityMax": "98", "raPM25Cur": "1",
    "raPM25Max": "1", "raTempCur": "20", "raTempMax": "20",
    "runningMode": "3", "runningStatus": "0", "saFilterClCycle": "1",
    "saFilterClTimeLeft": "969", "saFilterExCycle": "1",
    "saFilterExTimeLeft": "969", "saFilterExist": "255",
    "saHumidityCur": "255", "saHumidityMax": "255", "saPM25Cur": "0",
    "saPM25Max": "0", "saTempCur": "20", "saTempMax": "20",
    "serverTime": "0", "softVersion": "0", "windPath": "0",
}

# ADevGetStatusMidERV response for the same unit (timer table trimmed).
ERV01_MIDERV_RESULTS = {
    "clockDisplayFlag": 0, "oaHumC": 54, "oaPMC": 113, "oaTeC": 13,
    "offline": 0, "preSet": 3, "raFilEx": 0, "raFilExTL": 4320,
}


class FakeAccount:
    usr_id = "user"
    generation = 0

    def request_headers(self, use_xtoken=False):
        return {"xtoken": "SSID=x"} if use_xtoken else {}


def make_coordinator(subtype, dev_sub_type_id):
    coordinator = erv.PanasonicERVCoordinator.__new__(erv.PanasonicERVCoordinator)
    coordinator._hass = MagicMock()
    coordinator._entry = MagicMock()
    coordinator._account = FakeAccount()
    coordinator._device_id = "AABBCCDDEEFF_0800_1"
    coordinator._token = "device-token"
    coordinator._device_name = "Bedroom"
    coordinator._dev_sub_type_id = dev_sub_type_id
    coordinator._apply_protocol(subtype)
    coordinator._last_params = coordinator._default_params.copy()
    coordinator._last_status_all_raw = {}
    coordinator._last_status_raw = {}
    coordinator._persist_detected_subtype = MagicMock()
    return coordinator


def mock_cloud(coordinator, status_all):
    async def endpoint(protocol):
        if protocol["get_url"].endswith("ADevGetStatusMidERV"):
            return {"results": dict(ERV01_MIDERV_RESULTS)}
        return {"error": {"code": 4099, "message": "missing"}}

    async def request_all():
        return coordinator._normalize_status_all(dict(status_all))

    coordinator._request_status_endpoint = endpoint
    coordinator._request_status_all = request_all


class ERV01DetectionTests(unittest.TestCase):
    def test_dev_sub_type_id_maps_to_erv(self):
        mixin = config_flow.PanasonicDiscoveryMixin()
        self.assertEqual(
            mixin._get_device_subtype("x", {"devSubTypeId": "ERV-01"}),
            const.DEVICE_SUBTYPE_ERV,
        )

    def test_other_prefixes_unchanged(self):
        mixin = config_flow.PanasonicDiscoveryMixin()
        for raw, expected in (
            ("CABINET-01", const.DEVICE_SUBTYPE_CABINET),
            ("SMALLERV03", const.DEVICE_SUBTYPE_SMALL_ERV),
            ("MIDERV02", const.DEVICE_SUBTYPE_MID_ERV),
            ("NEWDCERV", const.DEVICE_SUBTYPE_NEW_DC_ERV),
            ("DCERV-03", const.DEVICE_SUBTYPE_DC_ERV),
            ("LD6C", const.DEVICE_SUBTYPE_LD6C),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    mixin._get_device_subtype("x", {"devSubTypeId": raw}), expected
                )


class ERV01ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_entry_pinned_to_cabinet_migrates_to_erv(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "ERV-01")
        mock_cloud(coordinator, ERV01_STATUS_ALL)
        data = await coordinator._fetch_status()
        self.assertEqual(coordinator.device_subtype, const.DEVICE_SUBTYPE_ERV)
        coordinator._persist_detected_subtype.assert_called_once_with(
            const.DEVICE_SUBTYPE_ERV
        )
        self.assertTrue(coordinator._url_set.endswith("ADevSetStatusInfoERV"))
        self.assertEqual(data["runM"], 3)
        self.assertEqual(data["oaTeC"], 13)
        self.assertEqual(data["saPMC"], 0)

    async def test_erv_entry_stays_erv(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        mock_cloud(coordinator, ERV01_STATUS_ALL)
        await coordinator._fetch_status()
        self.assertEqual(coordinator.device_subtype, const.DEVICE_SUBTYPE_ERV)
        coordinator._persist_detected_subtype.assert_not_called()

    async def test_cabinet_unit_never_moves_to_erv(self):
        # Even a cabinet statusAll that carries every ERV-only key must not
        # switch a CABINET-* device onto the ERV SET endpoint.
        status_all = {**ERV01_STATUS_ALL, "raCO2Cur": "600", "raCO2Max": "700"}
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_CABINET, "CABINET-01")
        mock_cloud(coordinator, status_all)
        await coordinator._fetch_status()
        self.assertEqual(coordinator.device_subtype, const.DEVICE_SUBTYPE_CABINET)
        coordinator._persist_detected_subtype.assert_not_called()


class ERV01CommandTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_turn_on_sends_full_official_bean(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        posted = await self._send(coordinator, coordinator.async_turn_on)
        self.assertEqual(len(posted), 1)
        url, body, headers = posted[0]
        self.assertTrue(url.endswith("/App/ADevSetStatusInfoERV"))
        self.assertEqual(headers, {"xtoken": "SSID=x"})
        self.assertEqual(body["usrId"], "user")
        self.assertEqual(body["deviceId"], "AABBCCDDEEFF_0800_1")
        self.assertEqual(body["token"], "device-token")
        expected = dict(const.ERV_SET_DEFAULT_PARAMS, runningStatus=1)
        self.assertEqual(body["params"], expected)

    async def test_sleep_mode_also_sets_low_air_volume(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        coordinator._last_params = {**coordinator._last_params, "runSta": 1}
        posted = await self._send(
            coordinator, lambda: coordinator.async_set_run_mode(const.RUN_MODE_SLEEP)
        )
        self.assertEqual(len(posted), 1)
        params = posted[0][1]["params"]
        self.assertEqual(params["runningMode"], 3)
        self.assertEqual(params["airVolume"], 1)
        self.assertEqual(params["runningStatus"], 255)

    async def test_other_mode_leaves_air_volume(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        coordinator._last_params = {**coordinator._last_params, "runSta": 1}
        posted = await self._send(
            coordinator,
            lambda: coordinator.async_set_run_mode(const.RUN_MODE_HEAT_EXCHANGE),
        )
        params = posted[0][1]["params"]
        self.assertEqual(params["runningMode"], 0)
        self.assertEqual(params["airVolume"], 255)

    def test_no_external_circulation_option(self):
        coordinator = make_coordinator(const.DEVICE_SUBTYPE_ERV, "ERV-01")
        self.assertNotIn(const.RUN_MODE_EXTERNAL_CIRCULATION, coordinator.run_mode_options)


if __name__ == "__main__":
    unittest.main()
