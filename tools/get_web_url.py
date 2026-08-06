"""列出账号下所有设备的官方 Web 控制页 URL（协议白嫖入口）。

松下云端的 Web 控制页（https://app.psmartcloud.com/ca/cn/<类别>/<子类型>/index.html）
是官方协议的免费文档：页面 JS（js/common/api_utility.js）直接写明该设备类型的
GET/SET 端点、字段表与值域，且无 App 的 SSL pinning 限制。本工具登录账号后为
每台设备生成 Web 控制页 URL，并可选探测页面是否存在（存在 = 该设备类型有官方
协议可读）。

用法:
    PMS_USER='手机号' PMS_PASS='密码' python3 tools/get_web_url.py [--probe]

不带 --probe 只输出 URL；带 --probe 会逐个请求页面并标记 HTTP 状态
（200 = 页面存在；404 = 该子类型无 web 页）。账号密码也可交互输入。

注意:
    URL 内含 SSID（会话凭证），请勿公开分享；重新登录后旧 URL 失效。
    子类型名≠型号名（如浴霸 devSubTypeId=FV-RB20VL1 但页面路径用 RB20VL1），
    工具会自动尝试常见变体。
"""

from __future__ import annotations

import asyncio
import getpass
import os
import ssl
import sys
import urllib.parse
from pathlib import Path

WEB_ROOT = "https://app.psmartcloud.com/ca/cn/"
# 常见子类型 -> 页面路径变体（devSubTypeId 与路径名不完全一致时的转换）
_SUBTYPE_PATH_TRANSFORMS = (
    lambda s: s,
    lambda s: s[3:] if s.upper().startswith("FV-") else s,  # FV-RB20VL1 -> RB20VL1
    lambda s: s.replace("-", ""),
)


def web_page_candidates(category: str, subtype: str) -> list[str]:
    """为设备生成候选 web 控制页 URL（去重保序）。"""
    seen: set[str] = set()
    urls: list[str] = []
    for transform in _SUBTYPE_PATH_TRANSFORMS:
        candidate = transform(subtype or "")
        if not candidate:
            continue
        url = f"{WEB_ROOT}{category}/{candidate}/index.html"
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def build_query_url(
    page_url: str,
    device_id: str,
    usr_id: str,
    ssid: str,
    device_name: str,
) -> str:
    """按官方页面约定的查询参数拼出可直接打开的控制链接。"""
    query = urllib.parse.urlencode(
        {
            "deviceId": device_id,
            "devType": "",
            "usrId": usr_id,
            "SSID": ssid,
            "deviceName": device_name,
        }
    )
    return f"{page_url}?{query}#topPage"


async def main() -> None:
    # 依赖（aiohttp、probe_endpoints）在运行时导入，模块顶层保持纯 stdlib，
    # 便于无依赖环境下 import 本模块做单元验证。
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import aiohttp
    import probe_endpoints  # 复用 login / get_devices / device_category

    async def check_page(session, url: str) -> int:
        """探测页面是否存在（自签证书环境用不验证的 SSL 上下文）。"""
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        try:
            async with session.get(
                url, ssl=ssl_ctx, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status
        except Exception:  # noqa: BLE001 - 网络异常按不可达处理
            return 0

    username = os.environ.get("PMS_USER")
    password = os.environ.get("PMS_PASS")
    if not username:
        username = input("松下智家账号（手机号）: ").strip()
    if not password:
        password = getpass.getpass("密码: ")
    do_probe = "--probe" in sys.argv or "-p" in sys.argv

    async with aiohttp.ClientSession() as session:
        usr_id, ssid, family_id, real_family_id = await probe_endpoints.login(
            session, username, password
        )
        devices = await probe_endpoints.get_devices(
            session, usr_id, ssid, family_id, real_family_id
        )
        if not devices:
            print("未找到设备。")
            return

        print(f"共 {len(devices)} 台设备\n" + "=" * 76)
        for dev in devices:
            params = dev.get("params", {})
            device_id = dev.get("deviceId", "")
            category = probe_endpoints.device_category(device_id) or "?"
            subtype = params.get("devSubTypeId", "")
            name = params.get("deviceName", "")
            print(f"设备: {name} | 类型: {subtype} | 类别: {category}")
            print(f"  deviceId: {device_id}")

            for url in web_page_candidates(category, subtype):
                if do_probe:
                    status = await check_page(session, url)
                    mark = "✅ 有 web 页" if status == 200 else (
                        "❌ 无 web 页" if status == 404 else f"⚠ HTTP {status}"
                    )
                    print(f"  [{mark}] {url}")
                    if status == 200:
                        print(
                            "      控制链接: "
                            f"{build_query_url(url, device_id, usr_id, ssid, name)}"
                        )
                else:
                    print(f"  {url}")
                    print(
                        "      控制链接: "
                        f"{build_query_url(url, device_id, usr_id, ssid, name)}"
                    )
            print("-" * 76)

        print("提示: URL 内含 SSID（会话凭证），请勿公开分享；账号重登后旧链接失效。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已取消。")
    except RuntimeError as err:
        print(f"错误: {err}")
        sys.exit(1)
