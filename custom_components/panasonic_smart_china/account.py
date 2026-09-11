"""Shared Panasonic account session and legacy-entry absorption.

One Home Assistant config entry owns one Panasonic login. Every ERV device
on that account reuses this session so a silent re-login cannot kick a
sibling device (issue #5).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .account_data import (
    account_title,
    account_unique_id,
    is_unmerged_device_data,
    merge_unmerged_entries,
    same_account,
)
from .api import authenticate
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICES,
    CONF_FAMILY_ID,
    CONF_REAL_FAMILY_ID,
    CONF_SSID,
    CONF_USR_ID,
    DOMAIN,
    RELOGIN_COOLDOWN_SECONDS,
)

if TYPE_CHECKING:
    from .erv import PanasonicERVCoordinator

_LOGGER = logging.getLogger(__name__)


class PanasonicAccountSession:
    """One live SSID/session shared by every device on a config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        data = entry.data
        self.username: str | None = data.get(CONF_USERNAME)
        self.password: str | None = data.get(CONF_PASSWORD)
        self.usr_id: str | None = data.get(CONF_USR_ID)
        self.ssid: str | None = data.get(CONF_SSID)
        self.family_id: str | None = data.get(CONF_FAMILY_ID)
        self.real_family_id: str | None = data.get(CONF_REAL_FAMILY_ID)
        self._lock = asyncio.Lock()
        self._generation = 0
        self._last_relogin_ts = 0.0

    @property
    def generation(self) -> int:
        """Bumped after each successful re-login so siblings can reuse it."""
        return self._generation

    def request_headers(self, *, use_xtoken: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SmartApp",
            "Cookie": f"SSID={self.ssid}",
        }
        if use_xtoken:
            headers["xtoken"] = f"SSID={self.ssid}"
        return headers

    async def async_refresh_session(self, *, seen_generation: int | None = None) -> bool:
        """Re-login once and persist the new SSID onto this account entry.

        If a sibling already refreshed past ``seen_generation``, return True
        without logging in again. A successful login is enough even when the
        cloud omits familyId (common on some SmallERV accounts).
        """
        async with self._lock:
            if seen_generation is not None and self._generation > seen_generation:
                return True
            if not self.username or not self.password:
                return False
            now = time.monotonic()
            if (
                self._last_relogin_ts
                and now - self._last_relogin_ts < RELOGIN_COOLDOWN_SECONDS
            ):
                _LOGGER.debug(
                    "Skip account re-login for %s: cooldown active (%ds left)",
                    self.username,
                    int(RELOGIN_COOLDOWN_SECONDS - (now - self._last_relogin_ts)),
                )
                return False
            self._last_relogin_ts = now
            try:
                result = await authenticate(self.username, self.password)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Account re-login failed for %s: %s", self.username, err
                )
                return False

            self.usr_id = result["usrId"]
            self.ssid = result["ssId"]
            if result.get(CONF_FAMILY_ID) not in (None, ""):
                self.family_id = result[CONF_FAMILY_ID]
            if result.get(CONF_REAL_FAMILY_ID) not in (None, ""):
                self.real_family_id = result[CONF_REAL_FAMILY_ID]
            self._generation += 1
            self._persist()
            _LOGGER.info("Refreshed Panasonic session for account %s", self.username)
            return True

    def _persist(self) -> None:
        data = dict(self.entry.data)
        data[CONF_USR_ID] = self.usr_id
        data[CONF_SSID] = self.ssid
        if self.family_id is not None:
            data[CONF_FAMILY_ID] = self.family_id
        if self.real_family_id is not None:
            data[CONF_REAL_FAMILY_ID] = self.real_family_id
        self.hass.config_entries.async_update_entry(self.entry, data=data)


class PanasonicAccount:
    """Runtime container: shared session + per-device coordinators."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.session = PanasonicAccountSession(hass, entry)
        self.coordinators: dict[str, PanasonicERVCoordinator] = {}

    def device_name(self, device_id: str) -> str:
        record = (self.entry.data.get(CONF_DEVICES) or {}).get(device_id) or {}
        return record.get(CONF_DEVICE_NAME) or device_id

    async def async_setup(self) -> None:
        from .erv import PanasonicERVCoordinator

        devices = self.entry.data.get(CONF_DEVICES) or {}
        for device_id, info in devices.items():
            coordinator = PanasonicERVCoordinator(
                self.hass,
                self.entry,
                self.session,
                device_id,
                info,
            )
            self.coordinators[device_id] = coordinator
            await coordinator.async_refresh()


async def async_absorb_unmerged_entries(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Fold pre-1.8.0 per-device entries into one account entry.

    Returns True when ``entry`` is (or became) the surviving account entry
    and setup should continue. Returns False when ``entry`` should not be
    set up (it will be removed, or another entry is the survivor).

    Sibling removal is scheduled after the lock is released so we cannot
    deadlock with a sibling setup that is waiting on the same lock.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    lock: asyncio.Lock = domain_data.setdefault("migrate_lock", asyncio.Lock())

    async with lock:
        current = hass.config_entries.async_get_entry(entry.entry_id)
        if current is None:
            return False
        if not is_unmerged_device_data(current.data):
            return True

        all_entries = hass.config_entries.async_entries(DOMAIN)
        siblings = [
            candidate
            for candidate in all_entries
            if same_account(candidate.data, current.data)
            and (
                is_unmerged_device_data(candidate.data)
                or candidate.entry_id == current.entry_id
            )
        ]
        # Prefer an already-merged account entry for this login as the
        # survivor so we never create a second account entry.
        existing_account = next(
            (
                candidate
                for candidate in all_entries
                if candidate.entry_id != current.entry_id
                and not is_unmerged_device_data(candidate.data)
                and same_account(candidate.data, current.data)
            ),
            None,
        )
        siblings.sort(key=lambda item: item.entry_id)
        primary = existing_account or siblings[0]

        payloads = [(item.data, item.title) for item in siblings]
        if existing_account is not None:
            payloads.insert(0, (existing_account.data, existing_account.title))
        merged = merge_unmerged_entries(payloads)
        unique_id = account_unique_id(
            merged.get(CONF_USERNAME), merged.get(CONF_USR_ID)
        )
        title = account_title(merged.get(CONF_USERNAME), merged.get(CONF_USR_ID))

        # Keep a previously chosen account title when absorbing into it.
        if existing_account is not None and not is_unmerged_device_data(
            existing_account.data
        ):
            title = existing_account.title

        _LOGGER.info(
            "Merging %d Panasonic device entries into account %s (%d devices)",
            len(siblings),
            unique_id,
            len(merged.get(CONF_DEVICES) or {}),
        )
        hass.config_entries.async_update_entry(
            primary,
            unique_id=unique_id,
            title=title,
            data=merged,
            version=2,
        )

        leftovers = [item for item in siblings if item.entry_id != primary.entry_id]
        pending: list[str] = domain_data.setdefault("entries_to_remove", [])
        for leftover in leftovers:
            _transfer_devices_to_entry(hass, leftover, primary)
            if leftover.entry_id not in pending:
                pending.append(leftover.entry_id)

        return current.entry_id == primary.entry_id


def _transfer_devices_to_entry(
    hass: HomeAssistant, source: ConfigEntry, target: ConfigEntry
) -> None:
    """Move device-registry rows from a legacy entry onto the account entry."""
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, source.entry_id):
        registry.async_update_device(
            device.id,
            add_config_entry_id=target.entry_id,
        )


async def async_remove_pending_entries(hass: HomeAssistant) -> None:
    """Remove leftover per-device entries after the account entry is up."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    pending: list[str] = list(domain_data.get("entries_to_remove") or [])
    domain_data["entries_to_remove"] = []
    for entry_id in pending:
        if hass.config_entries.async_get_entry(entry_id) is None:
            continue
        try:
            await hass.config_entries.async_remove(entry_id)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not remove merged legacy entry %s: %s", entry_id, err)
