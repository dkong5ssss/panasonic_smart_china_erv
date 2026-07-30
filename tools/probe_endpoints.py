"""Generate a redacted ERV endpoint diagnostic report.

Usage:
    PMS_USER='phone' PMS_PASS='password' python tools/probe_endpoints.py --report

The script probes known Panasonic fresh-air GET endpoints and redacts account,
session, token, and device identifiers before writing a report that can be
attached to GitHub issues.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import re
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

FRESH_AIR_CATEGORIES = {"0800", "0850"}
GET_ENDPOINTS = (
    "ADevGetStatusDCERV",
    "ADevGetStatusNewDCERV",
    "ADevGetStatusMidERV",
    "ADevGetStatusSmallERV",
    "ADevGetStatusLD6C",
    "ADevGetStatusNeedsAP",
    "ADevGetStatusJDNeedsAP",
    "ADevGetStatusInfoERV",
    "ADevGetStatusInfoFloorPlacedERV",
)

SENSITIVE_KEYS = {
    "deviceid",
    "devid",
    "devicename",
    "devname",
    "deviceuuid",
    "mac",
    "devicemac",
    "sn",
    "devicesn",
    "usrid",
    "userid",
    "ssid",
    "token",
    "password",
    "pwd",
    "tel",
    "mobile",
    "familyid",
    "realfamilyid",
}
DEVICE_ID_RE = re.compile(r"\b[0-9a-f]{12}_\d{4}_[a-z0-9.-]+\b", re.IGNORECASE)


def redact(value: Any) -> Any:
    """Recursively redact account, session, token, and device identifiers."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            result[key] = "<redacted>" if normalized in SENSITIVE_KEYS else redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return DEVICE_ID_RE.sub(redact_device_match, value)
    return value


def redact_device_match(match: re.Match) -> str:
    digest = hashlib.sha256(match.group(0).encode()).hexdigest()[:10]
    return f"<device:{digest}>"


def device_category(device_id: str) -> str | None:
    parts = device_id.split("_")
    return parts[1] if len(parts) >= 2 else None


def device_token(device_id: str) -> str | None:
    parts = device_id.split("_")
    if len(parts) != 3:
        return None
    mac, category, suffix = parts[0].upper(), parts[1].upper(), parts[2]
    inner = hashlib.sha512(
        f"{mac[6:]}_{category}_{mac[:6]}".encode()
    ).hexdigest()
    return hashlib.sha512(f"{inner}_{suffix}".encode()).hexdigest()


def headers(ssid: str | None = None) -> dict[str, str]:
    result = {"User-Agent": "SmartApp", "Content-Type": "application/json"}
    if ssid:
        result["Cookie"] = f"SSID={ssid}"
    return result


async def post_json(
    session: aiohttp.ClientSession,
    url: str,
    payload: dict[str, Any],
    ssid: str | None = None,
) -> tuple[int, Any]:
    async with session.post(
        url,
        json=payload,
        headers=headers(ssid),
        ssl=psmartcloud_fingerprint(),
    ) as response:
        try:
            body = await response.json(content_type=None)
        except Exception:  # noqa: BLE001 - diagnostic report records raw text
            body = {"rawText": (await response.text())[:500]}
        return response.status, body


async def login(
    session: aiohttp.ClientSession,
    username: str,
    password: str,
) -> tuple[str, str, Any, Any]:
    _, token_response = await post_json(
        session,
        URL_GET_TOKEN,
        {"id": 1, "uiVersion": 4.0, "params": {"usrId": username}},
    )
    token_start = token_response.get("results", {}).get("token")
    if not token_start:
        raise RuntimeError(f"GetToken failed: {redact(token_response)}")

    pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
    inter_md5 = hashlib.md5((pwd_md5 + username).encode()).hexdigest().upper()
    final_token = hashlib.md5((inter_md5 + token_start).encode()).hexdigest().upper()

    _, login_response = await post_json(
        session,
        URL_LOGIN,
        {
            "id": 2,
            "uiVersion": 4.0,
            "params": {
                "telId": "00:00:00:00:00:00",
                "checkFailCount": 0,
                "usrId": username,
                "pwd": final_token,
            },
        },
    )
    results = login_response.get("results")
    if not isinstance(results, dict):
        raise RuntimeError(f"Login failed: {redact(login_response)}")
    return (
        results["usrId"],
        results["ssId"],
        results["familyId"],
        results["realFamilyId"],
    )


async def get_devices(
    session: aiohttp.ClientSession,
    usr_id: str,
    ssid: str,
    family_id: Any,
    real_family_id: Any,
) -> list[dict[str, Any]]:
    _, response = await post_json(
        session,
        URL_GET_DEV,
        {
            "id": 3,
            "uiVersion": 4.0,
            "params": {
                "realFamilyId": real_family_id,
                "familyId": family_id,
                "usrId": usr_id,
            },
        },
        ssid,
    )
    return response.get("results", {}).get("devList", [])


async def probe_endpoint(
    session: aiohttp.ClientSession,
    endpoint: str,
    device_id: str,
    usr_id: str,
    ssid: str,
    token: str,
) -> dict[str, Any]:
    try:
        status, body = await post_json(
            session,
            BASE_URL + endpoint,
            {
                "id": 1,
                "uiVersion": 4.0,
                "params": {"usrId": usr_id, "deviceId": device_id, "token": token},
            },
            ssid,
        )
    except Exception as error:  # noqa: BLE001 - keep diagnostics moving
        return {"status": "request_failed", "message": redact(str(error))}

    summary: dict[str, Any] = {"httpStatus": status}
    if isinstance(body, dict):
        if isinstance(body.get("results"), dict) and body["results"]:
            summary["status"] = "ok"
            summary["fieldCount"] = len(body["results"])
            summary["results"] = redact(body["results"])
        elif "error" in body:
            summary["status"] = "error"
            summary["error"] = redact(body["error"])
        else:
            summary["status"] = "unexpected"
            summary["response"] = redact(body)
    else:
        summary["status"] = "unexpected"
        summary["response"] = redact(body)
    return summary


def select_devices(
    devices: list[dict[str, Any]],
    *,
    all_devices: bool,
    device_index: int | None,
) -> list[dict[str, Any]]:
    candidates = devices if all_devices else [
        device
        for device in devices
        if device_category(str(device.get("deviceId", ""))) in FRESH_AIR_CATEGORIES
    ]
    if device_index is None:
        return candidates
    if device_index < 1 or device_index > len(candidates):
        raise RuntimeError(
            f"--device-index must be between 1 and {len(candidates)}"
        )
    return [candidates[device_index - 1]]


def device_snapshot(device: dict[str, Any]) -> dict[str, Any]:
    params = device.get("params", {})
    return {
        "category": device_category(str(device.get("deviceId", ""))),
        "model": params.get("deviceMNO"),
        "devSubTypeId": params.get("devSubTypeId"),
        "statusAll": redact(params.get("statusAll") or {}),
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    username = os.environ.get("PMS_USER")
    password = os.environ.get("PMS_PASS")
    if not username or not password:
        raise RuntimeError("Please set PMS_USER and PMS_PASS environment variables")

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("Logging in to Panasonic Smart China...")
        usr_id, ssid, family_id, real_family_id = await login(
            session, username, password
        )
        devices = await get_devices(session, usr_id, ssid, family_id, real_family_id)
        selected = select_devices(
            devices,
            all_devices=args.all_devices,
            device_index=args.device_index,
        )
        print(f"Found {len(devices)} devices; probing {len(selected)} device(s).")

        report = {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "mode": "all_devices" if args.all_devices else "fresh_air_only",
            "devices": [],
        }
        for index, device in enumerate(selected, 1):
            device_id = str(device.get("deviceId", ""))
            token = device_token(device_id)
            snapshot = device_snapshot(device)
            print(
                f"[{index}] model={snapshot.get('model') or '?'} "
                f"subtype={snapshot.get('devSubTypeId') or '?'}"
            )
            endpoint_results = {}
            if token is None:
                endpoint_results["token"] = {"status": "token_generation_failed"}
            else:
                for endpoint in GET_ENDPOINTS:
                    result = await probe_endpoint(
                        session, endpoint, device_id, usr_id, ssid, token
                    )
                    endpoint_results[endpoint] = result
                    print(
                        f"  {endpoint}: {result.get('status')}"
                        f" fields={result.get('fieldCount', 0)}"
                    )

            report["devices"].append(
                {**snapshot, "endpoints": endpoint_results}
            )
        return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        nargs="?",
        const="",
        help="Write a redacted JSON report. Optionally pass an output path.",
    )
    parser.add_argument(
        "--all-devices",
        action="store_true",
        help="Probe all devices instead of only category 0800/0850 devices.",
    )
    parser.add_argument(
        "--device-index",
        type=int,
        help="Probe only one selected device from the filtered list.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = asyncio.run(run(args))
    except Exception as error:  # noqa: BLE001 - CLI boundary
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.report is not None:
        path = (
            Path(args.report)
            if args.report
            else Path(f"endpoint_report_{time.strftime('%Y%m%d-%H%M%S')}.json")
        )
        path.write_text(
            json.dumps(redact(report), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Redacted report written to {path}")
    else:
        print(json.dumps(redact(report), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
