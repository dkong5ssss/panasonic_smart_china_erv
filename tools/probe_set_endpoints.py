"""Probe likely Info-family SET endpoints for a cabinet-style ERV.

Mirrors the LD5C v1.7.3 fix: the device's native vocabulary is long
camelCase (runningStatus/runningMode/airVolume), the cloud SET endpoint
expects identity at top level + xtoken header + Info-family long field
names. The official diagnostic report's GET probes used the wrong payload
shape (identity nested in params), which is why InfoERV/InfoFloorPlacedERV
returned 4099 there.

This script tries each candidate endpoint with the correct Info-family
payload, sends an idempotent SET (runningStatus=current, no change) and
records the response so we can see which endpoint the cloud actually
accepts for this device.

Usage:
    PMS_USER='phone' PMS_PASS='password' python tools/probe_set_endpoints.py
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import aiohttp

REPO_ROOT = Path(__file__).resolve().parents[1]
TLS_PATH = REPO_ROOT / "custom_components" / "panasonic_smart_china" / "tls.py"

_TLS_SPEC = importlib.util.spec_from_file_location("panasonic_tls", TLS_PATH)
if _TLS_SPEC is None or _TLS_SPEC.loader is None:
    raise RuntimeError(f"Unable to load TLS helper from {TLS_PATH}")
_TLS_MODULE = importlib.util.module_from_spec(_TLS_SPEC)
_TLS_SPEC.loader.exec_module(_TLS_MODULE)
psmartcloud_fingerprint = _TLS_MODULE.psmartcloud_fingerprint

BASE_URL = "https://app.psmartcloud.com/App/"
URL_GET_TOKEN = BASE_URL + "UsrGetToken"
URL_LOGIN = BASE_URL + "UsrLogin"
URL_GET_DEV = BASE_URL + "UsrGetBindDevInfo"


def redact(value: Any) -> Any:
    """Redact sensitive fields before printing."""
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in {"token", "pwd", "ssid", "usrid", "deviceid", "password"} else v)
                for k, v in value.items()}
    return value


async def login(session: aiohttp.ClientSession, username: str, password: str) -> tuple[str, str, Any, Any]:
    """Full GetToken -> Login flow, returns (usrId, ssId, familyId, realFamilyId)."""
    async with session.post(
        URL_GET_TOKEN,
        json={"id": 1, "uiVersion": 4.0, "params": {"usrId": username}},
        headers={"User-Agent": "SmartApp", "Content-Type": "application/json"},
        ssl=psmartcloud_fingerprint(),
    ) as r:
        data = await r.json()
    token_start = data.get("results", {}).get("token")
    if not token_start:
        raise RuntimeError("GetToken failed")
    pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
    inter = hashlib.md5((pwd_md5 + username).encode()).hexdigest().upper()
    final = hashlib.md5((inter + token_start).encode()).hexdigest().upper()
    async with session.post(
        URL_LOGIN,
        json={"id": 2, "uiVersion": 4.0,
              "params": {"telId": "00:00:00:00:00:00", "checkFailCount": 0,
                         "usrId": username, "pwd": final}},
        headers={"User-Agent": "SmartApp", "Content-Type": "application/json"},
        ssl=psmartcloud_fingerprint(),
    ) as r:
        data = await r.json()
    results = data.get("results", {})
    if not isinstance(results, dict):
        raise RuntimeError("Login failed")
    return results["usrId"], results["ssId"], results.get("familyId"), results.get("realFamilyId")


async def get_device(session: aiohttp.ClientSession, usr_id: str, ssid: str, family_id, real_family_id) -> dict:
    async with session.post(
        URL_GET_DEV,
        json={"id": 3, "uiVersion": 4.0,
              "params": {"realFamilyId": real_family_id, "familyId": family_id, "usrId": usr_id}},
        headers={"User-Agent": "SmartApp", "Content-Type": "application/json",
                 "Cookie": f"SSID={ssid}"},
        ssl=psmartcloud_fingerprint(),
    ) as r:
        data = await r.json()
    for dev in data.get("results", {}).get("devList", []):
        if dev.get("deviceId"):
            return dev
    raise RuntimeError("No cabinet device found in account")


def device_token(device_id: str) -> str | None:
    """Replicate Panasonic front-end JS token generation."""
    parts = str(device_id).split("_")
    if len(parts) != 3:
        return None
    mac, cat, suffix = parts[0].upper(), parts[1].upper(), parts[2]
    if len(mac) < 6:
        return None
    inner = hashlib.sha512(f"{mac[6:]}_{cat}_{mac[:6]}".encode()).hexdigest()
    return hashlib.sha512(f"{inner}_{suffix}".encode()).hexdigest()


async def probe_set(
    session: aiohttp.ClientSession,
    endpoint: str,
    usr_id: str,
    ssid: str,
    device_id: str,
    token: str,
    running_status: int,
) -> dict:
    """Probe a SET endpoint with Info-family payload format (identity at top level)."""
    url = BASE_URL + endpoint
    payload = {
        "id": 0,
        "usrId": usr_id,
        "deviceId": device_id,
        "token": token,
        "params": {
            "runningStatus": running_status,  # Idempotent: keep current state
        },
    }
    headers = {
        "User-Agent": "SmartApp",
        "Content-Type": "application/json",
        "Cookie": f"SSID={ssid}",
        "xtoken": f"SSID={ssid}",  # Info-family auth header
    }
    try:
        async with session.post(url, json=payload, headers=headers,
                                 ssl=psmartcloud_fingerprint()) as r:
            try:
                body = await r.json(content_type=None)
            except Exception:
                body = {"rawText": (await r.text())[:300]}
            return {"httpStatus": r.status, "response": redact(body)}
    except Exception as e:
        return {"httpStatus": None, "error": str(e)}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("PMS_USER"))
    parser.add_argument("--pass", dest="password", default=os.environ.get("PMS_PASS"))
    args = parser.parse_args()
    if not args.user or not args.password:
        print("Set PMS_USER / PMS_PASS or pass --user / --pass", file=sys.stderr)
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        print("→ Logging in...")
        usr_id, ssid, family_id, real_family_id = await login(session, args.user, args.password)
        print(f"  usrId={usr_id}  familyId={family_id}  realFamilyId={real_family_id}")

        print("→ Fetching devices...")
        device = await get_device(session, usr_id, ssid, family_id, real_family_id)
        device_id = device["deviceId"]
        print(f"  deviceId={device_id}")
        print(f"  devSubTypeId={device.get('params', {}).get('devSubTypeId')}")
        print(f"  model={device.get('params', {}).get('model')}")
        status_all = device.get("params", {}).get("statusAll") or {}
        try:
            running_status = int(status_all.get("runningStatus", 0))
        except (TypeError, ValueError):
            running_status = 0
        print(f"  runningStatus={running_status}  (will send idempotent SET keeping this state)")
        print()

        token = device_token(device_id)
        if not token:
            print("ERROR: could not generate device token", file=sys.stderr)
            sys.exit(1)

        # Endpoints to probe. Order: Info-family variants first (most likely),
        # then old-protocol variants as fallback reference.
        endpoints = [
            "ADevSetStatusInfoCABINET-02",   # Most specific
            "ADevSetStatusInfoCABINET",      # Generic cabinet
            "ADevSetStatusInfoERV",          # The 4099 one in diagnostic
            "ADevSetStatusInfoFloorPlacedERV",  # The other 4099 one
            "ADevSetStatusLD5C",             # Known-working for LD5C; may match
            "ADevSetStatusInfoERV2",         # Guess
            "ADevSetStatusCABINET-02",       # Old protocol, specific
            "ADevSetStatusCABINET",          # Old protocol, generic
        ]
        print("→ Probing SET endpoints with Info-family payload (idempotent, no state change)...")
        print()
        for ep in endpoints:
            result = await probe_set(session, ep, usr_id, ssid, device_id, token, running_status)
            http = result.get("httpStatus")
            resp = result.get("response", {})
            err = resp.get("error") if isinstance(resp, dict) else None
            results = resp.get("results") if isinstance(resp, dict) else None
            errcode = (resp.get("errorCode") if isinstance(resp, dict) else None) or (
                err.get("code") if isinstance(err, dict) else None
            )
            verdict = "✓ ACCEPTED" if results is not None else (
                f"✗ {errcode}" if errcode else f"✗ HTTP {http}"
            )
            print(f"  {ep:42s}  HTTP {http}  {verdict}")
            if results is not None:
                print(f"    results keys: {sorted(results.keys())[:8]}...")
            elif err:
                print(f"    error: {err}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
