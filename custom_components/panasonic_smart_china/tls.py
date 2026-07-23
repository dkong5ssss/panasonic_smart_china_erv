"""TLS configuration for Panasonic Smart Cloud."""

import aiohttp


# app.psmartcloud.com uses a self-signed certificate without CA constraints.
# Pin its SHA-256 fingerprint instead of disabling TLS verification.
_PSMARTCLOUD_CERT_SHA256 = (
    "a03226da8dd2ef0ea7e390232eed88d27d36c9e1a3208439f20a4c37eec35948"
)


def psmartcloud_fingerprint() -> aiohttp.Fingerprint:
    """Return Panasonic Smart Cloud's pinned certificate fingerprint."""
    return aiohttp.Fingerprint(bytes.fromhex(_PSMARTCLOUD_CERT_SHA256))
