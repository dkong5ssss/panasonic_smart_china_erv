from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .erv import async_get_coordinator

PLATFORMS = ["fan", "select", "sensor", "switch"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("session", None)
    hass.data[DOMAIN].setdefault("coordinators", {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Smart China from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("session", None)
    hass.data[DOMAIN].setdefault("coordinators", {})
    await async_get_coordinator(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].get("coordinators", {}).pop(entry.entry_id, None)
    return unload_ok
