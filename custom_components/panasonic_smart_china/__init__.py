from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .account import (
    PanasonicAccount,
    async_absorb_unmerged_entries,
    async_remove_pending_entries,
)
from .account_data import account_unique_id, is_unmerged_device_data
from .const import CONF_DEVICES, CONF_USR_ID, DOMAIN

PLATFORMS = ["fan", "select", "sensor", "switch"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Smart China from an account-level config entry."""
    hass.data.setdefault(DOMAIN, {})

    if is_unmerged_device_data(entry.data):
        should_setup = await async_absorb_unmerged_entries(hass, entry)
        if not should_setup:
            hass.async_create_task(async_remove_pending_entries(hass))
            return False
        updated = hass.config_entries.async_get_entry(entry.entry_id)
        if updated is None:
            return False
        entry = updated

    account = PanasonicAccount(hass, entry)
    await account.async_setup()
    hass.data[DOMAIN][entry.entry_id] = account

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (
                DOMAIN,
                account_unique_id(
                    entry.data.get(CONF_USERNAME), entry.data.get(CONF_USR_ID)
                ),
            )
        },
        manufacturer="Panasonic",
        name=entry.title,
        model="Panasonic Smart China",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    hass.async_create_task(async_remove_pending_entries(hass))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate a v1 per-device entry to the v2 data shape.

    The entry still represents a single device until ``async_setup_entry``
    absorbs sibling entries into one account entry.
    """
    if config_entry.version < 2:
        from .account_data import iter_device_records

        new_data = dict(config_entry.data)
        if CONF_DEVICES not in new_data:
            new_data[CONF_DEVICES] = iter_device_records(new_data, config_entry.title)
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)
    return True


def get_account(hass: HomeAssistant, entry: ConfigEntry) -> PanasonicAccount:
    """Return the runtime account container for a config entry."""
    return hass.data[DOMAIN][entry.entry_id]
