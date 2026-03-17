import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Compatibility shim for old climate-based installs."""
    _LOGGER.warning(
        "The climate platform for panasonic_smart_china is deprecated. "
        "This build only exposes fan entities for ERV devices."
    )
    return
