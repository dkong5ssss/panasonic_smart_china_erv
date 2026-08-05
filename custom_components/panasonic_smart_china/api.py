"""Shared Panasonic Smart China cloud API helpers.

The GetToken -> Login -> GetDev login sequence lives here so both the config
flow (interactive login) and the runtime coordinator (silent re-login to
self-heal a missing familyId/SSID) can reuse the exact same flow.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp

from .tls import psmartcloud_fingerprint

_LOGGER = logging.getLogger(__name__)

URL_LOGIN = "https://app.psmartcloud.com/App/UsrLogin"
URL_GET_DEV = "https://app.psmartcloud.com/App/UsrGetBindDevInfo"
URL_GET_TOKEN = "https://app.psmartcloud.com/App/UsrGetToken"


async def authenticate(username: str, password: str) -> dict[str, Any]:
    """Run the full GetToken -> Login -> GetDev flow.

    Returns a dict with keys: usrId, ssId, familyId, realFamilyId, devices.
    Raises RuntimeError on any failed step.
    """
    headers = {"User-Agent": "SmartApp", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            URL_GET_TOKEN,
            json={"id": 1, "uiVersion": 4.0, "params": {"usrId": username}},
            headers=headers,
            ssl=psmartcloud_fingerprint(),
        ) as response:
            data = await response.json()
        if "results" not in data:
            raise RuntimeError("GetToken failed")

        token_start = data["results"]["token"]
        pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
        inter_md5 = hashlib.md5((pwd_md5 + username).encode()).hexdigest().upper()
        final_token = hashlib.md5((inter_md5 + token_start).encode()).hexdigest().upper()

        async with session.post(
            URL_LOGIN,
            json={
                "id": 2,
                "uiVersion": 4.0,
                "params": {
                    "telId": "00:00:00:00:00:00",
                    "checkFailCount": 0,
                    "usrId": username,
                    "pwd": final_token,
                },
            },
            headers=headers,
            ssl=psmartcloud_fingerprint(),
        ) as response:
            login_res = await response.json()
        if "results" not in login_res:
            raise RuntimeError("Login failed")

        res = login_res["results"]
        real_usr_id = res["usrId"]
        ssid = res["ssId"]
        family_id = res.get("familyId")
        real_family_id = res.get("realFamilyId")

        headers["Cookie"] = f"SSID={ssid}"
        devices: dict[str, Any] = {}
        async with session.post(
            URL_GET_DEV,
            json={
                "id": 3,
                "uiVersion": 4.0,
                "params": {
                    "realFamilyId": real_family_id,
                    "familyId": family_id,
                    "usrId": real_usr_id,
                },
            },
            headers=headers,
            ssl=psmartcloud_fingerprint(),
        ) as response:
            dev_res = await response.json()
        if "results" in dev_res and "devList" in dev_res["results"]:
            for dev in dev_res["results"]["devList"]:
                devices[dev["deviceId"]] = dev["params"]

        return {
            "usrId": real_usr_id,
            "ssId": ssid,
            "familyId": family_id,
            "realFamilyId": real_family_id,
            "devices": devices,
        }
