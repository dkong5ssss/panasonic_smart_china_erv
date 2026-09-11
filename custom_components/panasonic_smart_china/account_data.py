"""Pure account/config-entry data helpers (no Home Assistant imports).

These functions are used by the runtime account session, config flow, and
legacy-entry absorption, and are unit-tested without Home Assistant.
"""
from __future__ import annotations

from typing import Any

from .const import (
    ACCOUNT_UNIQUE_ID_PREFIX,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SUBTYPE,
    CONF_DEV_SUB_TYPE_ID,
    CONF_DEVICES,
    CONF_FAMILY_ID,
    CONF_REAL_FAMILY_ID,
    CONF_SSID,
    CONF_TOKEN,
    CONF_USR_ID,
    DEVICE_SUBTYPE_SMALL_ERV,
)


def account_unique_id(username: str | None, usr_id: str | None) -> str:
    """Stable unique_id for one Panasonic account config entry."""
    if username:
        return f"{ACCOUNT_UNIQUE_ID_PREFIX}{username}"
    return f"{ACCOUNT_UNIQUE_ID_PREFIX}{usr_id}"


def is_account_unique_id(unique_id: str | None) -> bool:
    return bool(unique_id) and str(unique_id).startswith(ACCOUNT_UNIQUE_ID_PREFIX)


def is_unmerged_device_data(data: dict[str, Any]) -> bool:
    """True when this entry still represents a single pre-1.8.0 device."""
    return CONF_DEVICE_ID in data


# Home Assistant's CONF_USERNAME / CONF_PASSWORD string values; kept as
# literals so this module can be unit-tested without Home Assistant.
_CONF_USERNAME = "username"
_CONF_PASSWORD = "password"


def same_account(data_a: dict[str, Any], data_b: dict[str, Any]) -> bool:
    """Match two entries that belong to the same Panasonic login."""
    # Username is the preferred key; fall back to cloud usrId when an old
    # entry was created before credentials were stored (pre-1.7.1).
    user_a = data_a.get(_CONF_USERNAME)
    user_b = data_b.get(_CONF_USERNAME)
    if user_a and user_b:
        return user_a == user_b
    usr_a = data_a.get(CONF_USR_ID)
    usr_b = data_b.get(CONF_USR_ID)
    return bool(usr_a) and usr_a == usr_b


def device_record(
    *,
    token: str | None,
    subtype: str | None,
    sub_type_id: str | None,
    name: str | None,
) -> dict[str, Any]:
    """Build the per-device record stored under CONF_DEVICES."""
    record: dict[str, Any] = {
        CONF_TOKEN: token,
        CONF_DEVICE_SUBTYPE: subtype or DEVICE_SUBTYPE_SMALL_ERV,
        CONF_DEVICE_NAME: name,
    }
    if sub_type_id:
        record[CONF_DEV_SUB_TYPE_ID] = sub_type_id
    return record


def device_record_from_legacy(data: dict[str, Any], title: str) -> dict[str, Any]:
    """Convert a v1 device-level config entry into a devices{} record."""
    return device_record(
        token=data.get(CONF_TOKEN),
        subtype=data.get(CONF_DEVICE_SUBTYPE),
        sub_type_id=data.get(CONF_DEV_SUB_TYPE_ID),
        name=title,
    )


def iter_device_records(data: dict[str, Any], title: str) -> dict[str, dict[str, Any]]:
    """Collect device records from either a legacy or account-shaped payload."""
    devices: dict[str, dict[str, Any]] = {}
    device_id = data.get(CONF_DEVICE_ID)
    if device_id:
        devices[str(device_id)] = device_record_from_legacy(data, title)
    stored = data.get(CONF_DEVICES)
    if isinstance(stored, dict):
        for stored_id, record in stored.items():
            if not isinstance(record, dict):
                continue
            merged = dict(record)
            merged.setdefault(CONF_DEVICE_NAME, title)
            devices[str(stored_id)] = merged
    return devices


def merge_unmerged_entries(
    payloads: list[tuple[dict[str, Any], str]],
) -> dict[str, Any]:
    """Merge one or more v1/unmerged entries into a single account payload.

    Session fields: username/password from the first entry that has them;
    usrId and family ids from the last non-empty value; SSID from the last
    entry (still may be stale — runtime refresh replaces it).
    """
    devices: dict[str, dict[str, Any]] = {}
    username = None
    password = None
    usr_id = None
    ssid = None
    family_id = None
    real_family_id = None

    for data, title in payloads:
        if data.get(_CONF_USERNAME) and not username:
            username = data[_CONF_USERNAME]
        if data.get(_CONF_PASSWORD) and not password:
            password = data[_CONF_PASSWORD]
        if data.get(CONF_USR_ID):
            usr_id = data[CONF_USR_ID]
        if data.get(CONF_SSID):
            ssid = data[CONF_SSID]
        if data.get(CONF_FAMILY_ID) not in (None, ""):
            family_id = data[CONF_FAMILY_ID]
        if data.get(CONF_REAL_FAMILY_ID) not in (None, ""):
            real_family_id = data[CONF_REAL_FAMILY_ID]
        devices.update(iter_device_records(data, title))

    merged: dict[str, Any] = {
        CONF_USR_ID: usr_id,
        CONF_SSID: ssid,
        CONF_DEVICES: devices,
    }
    if username:
        merged[_CONF_USERNAME] = username
    if password:
        merged[_CONF_PASSWORD] = password
    if family_id is not None:
        merged[CONF_FAMILY_ID] = family_id
    if real_family_id is not None:
        merged[CONF_REAL_FAMILY_ID] = real_family_id
    return merged


def account_title(username: str | None, usr_id: str | None) -> str:
    """Human-readable config entry title for an account."""
    if username:
        return f"Panasonic {username}"
    return f"Panasonic {usr_id}"
