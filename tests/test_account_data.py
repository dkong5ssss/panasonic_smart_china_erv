import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "panasonic_smart_china"


def _load_package_module(name: str, filename: str):
    """Load a package submodule without executing panasonic_smart_china/__init__.py."""
    if "custom_components" not in sys.modules:
        cc = types.ModuleType("custom_components")
        cc.__path__ = [str(ROOT / "custom_components")]
        cc.__package__ = "custom_components"
        sys.modules["custom_components"] = cc
    pkg = "custom_components.panasonic_smart_china"
    if pkg not in sys.modules:
        psc = types.ModuleType(pkg)
        psc.__path__ = [str(PKG_DIR)]
        psc.__package__ = pkg
        sys.modules[pkg] = psc
    full_name = f"{pkg}.{name}"
    spec = importlib.util.spec_from_file_location(full_name, PKG_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


const = _load_package_module("const", "const.py")
account_data = _load_package_module("account_data", "account_data.py")

account_title = account_data.account_title
account_unique_id = account_data.account_unique_id
device_record_from_legacy = account_data.device_record_from_legacy
is_unmerged_device_data = account_data.is_unmerged_device_data
merge_unmerged_entries = account_data.merge_unmerged_entries
same_account = account_data.same_account

AUTH_ERROR_CODES = const.AUTH_ERROR_CODES
CONF_DEVICE_ID = const.CONF_DEVICE_ID
CONF_DEVICE_NAME = const.CONF_DEVICE_NAME
CONF_DEVICE_SUBTYPE = const.CONF_DEVICE_SUBTYPE
CONF_DEVICES = const.CONF_DEVICES
CONF_SSID = const.CONF_SSID
CONF_TOKEN = const.CONF_TOKEN
CONF_USR_ID = const.CONF_USR_ID


def _legacy_entry(device_id: str, title: str, **overrides) -> tuple[dict, str]:
    data = {
        "username": "13800000000",
        "password": "secret",
        CONF_USR_ID: "984571",
        CONF_SSID: "ssid-old",
        CONF_DEVICE_ID: device_id,
        CONF_TOKEN: f"token-{device_id.split('_')[0][-4:]}",
        CONF_DEVICE_SUBTYPE: "SMALLERV",
    }
    data.update(overrides)
    return data, title


class AccountDataTests(unittest.TestCase):
    def test_account_unique_id_prefers_username(self):
        self.assertEqual(
            account_unique_id("13800000000", "984571"),
            "panasonic_account_13800000000",
        )
        self.assertEqual(account_unique_id(None, "984571"), "panasonic_account_984571")

    def test_account_title(self):
        self.assertEqual(account_title("13800000000", "984571"), "Panasonic 13800000000")

    def test_unmerged_device_data(self):
        self.assertTrue(is_unmerged_device_data({CONF_DEVICE_ID: "abc"}))
        self.assertFalse(
            is_unmerged_device_data({CONF_DEVICES: {"abc": {CONF_TOKEN: "t"}}})
        )

    def test_same_account_by_username(self):
        self.assertTrue(
            same_account({"username": "13800000000"}, {"username": "13800000000"})
        )
        self.assertFalse(
            same_account({"username": "13800000000"}, {"username": "13900000000"})
        )

    def test_same_account_falls_back_to_usr_id(self):
        self.assertTrue(same_account({CONF_USR_ID: "984571"}, {CONF_USR_ID: "984571"}))

    def test_merge_two_smallerv_entries_like_issue_5(self):
        first, title_a = _legacy_entry(
            "10381F056C04_0800_Aircle-12-02",
            "1F Kitchen",
            **{CONF_SSID: "ssid-a"},
        )
        second, title_b = _legacy_entry(
            "10381F74FB16_0800_Aircle-12-02",
            "3F Elevator",
            **{CONF_SSID: "ssid-b"},
        )
        merged = merge_unmerged_entries([(first, title_a), (second, title_b)])

        self.assertEqual(merged["username"], "13800000000")
        self.assertEqual(merged["password"], "secret")
        self.assertEqual(merged[CONF_USR_ID], "984571")
        self.assertEqual(merged[CONF_SSID], "ssid-b")
        self.assertNotIn(CONF_DEVICE_ID, merged)
        devices = merged[CONF_DEVICES]
        self.assertEqual(len(devices), 2)
        self.assertEqual(
            devices["10381F056C04_0800_Aircle-12-02"][CONF_DEVICE_NAME],
            "1F Kitchen",
        )
        self.assertEqual(
            devices["10381F74FB16_0800_Aircle-12-02"][CONF_DEVICE_NAME],
            "3F Elevator",
        )
        self.assertEqual(
            devices["10381F056C04_0800_Aircle-12-02"][CONF_TOKEN],
            "token-6C04",
        )

    def test_merge_post_migrate_payload_still_unmerged(self):
        data, title = _legacy_entry("dev-a", "Kitchen")
        data[CONF_DEVICES] = {
            "dev-a": {
                CONF_TOKEN: "token-from-devices",
                CONF_DEVICE_SUBTYPE: "SMALLERV",
                CONF_DEVICE_NAME: "Kitchen",
            }
        }
        self.assertTrue(is_unmerged_device_data(data))
        merged = merge_unmerged_entries([(data, title)])
        self.assertNotIn(CONF_DEVICE_ID, merged)
        self.assertEqual(merged[CONF_DEVICES]["dev-a"][CONF_TOKEN], "token-from-devices")

    def test_merge_keeps_existing_family_id_when_later_entry_omits_it(self):
        first, title_a = _legacy_entry(
            "dev-a",
            "A",
            **{"familyId": "fam-1", "realFamilyId": "real-1"},
        )
        second, title_b = _legacy_entry("dev-b", "B")
        merged = merge_unmerged_entries([(first, title_a), (second, title_b)])
        self.assertEqual(merged["familyId"], "fam-1")
        self.assertEqual(merged["realFamilyId"], "real-1")

    def test_device_record_from_legacy_uses_entry_title(self):
        record = device_record_from_legacy(
            {
                CONF_TOKEN: "tok",
                CONF_DEVICE_SUBTYPE: "LD5C",
                "devSubTypeId": "LD5C",
            },
            "Kitchen ERV",
        )
        self.assertEqual(record[CONF_DEVICE_NAME], "Kitchen ERV")
        self.assertEqual(record[CONF_DEVICE_SUBTYPE], "LD5C")

    def test_auth_error_codes_include_session_kick(self):
        self.assertIn("4102", AUTH_ERROR_CODES)
        self.assertIn("3003", AUTH_ERROR_CODES)
        self.assertIn("3004", AUTH_ERROR_CODES)

    def test_cabinet_protocol_registered_and_beats_ld5c_score(self):
        self.assertIn("CABINET", const.SUPPORTED_ERV_SUBTYPES)
        self.assertIn("CABINET", const.SUPPORTED_ERV_DEVICE_HINTS)
        protocol = const.SUPPORTED_ERV_SUBTYPES["CABINET"]
        self.assertTrue(protocol["uses_status_all"])
        self.assertIn("InfoFloorPlacedERV", protocol["set_url"])
        self.assertGreater(
            len(const.CABINET_STATUS_ALL_FIELD_MAP),
            len(const.LD5C_STATUS_ALL_FIELD_MAP),
        )
        self.assertGreater(
            len(const.CABINET_SIGNATURE_KEYS),
            len(const.PROTOCOL_SIGNATURES["LD5C"]),
        )


if __name__ == "__main__":
    unittest.main()
