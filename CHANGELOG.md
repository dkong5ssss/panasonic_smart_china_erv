# Changelog

## 1.7.0

- **设备识别改为纯数据驱动**：不再使用写死的型号白名单（此前 `25ZDP1C` 子串匹配曾把 FY-25ZDP1C 误判为 MidERV）。识别顺序改为：云端 `devSubTypeId` 前缀 → statusAll 字段签名（`PROTOCOL_SIGNATURES` 指纹表）→ `AUTO` 兜底。
- **未知设备也可添加**：识别不出的设备会以 `[自动识别]` 标签出现在配置流程中，添加后由运行时探测循环自动收敛到真实协议并写回配置，无需等作者发版适配新机型。
- 删除 `MID_ERV_MODEL_HINTS` / `LD5C_MODEL_HINTS` / `DEHUMID_MID_ERV_MODEL_HINTS` / `DC_ERV_MODEL_HINTS` 四个型号集合。
- 指纹表基于真实设备数据构建：SmallERV（filSet/oaFilExPM，实测）、LD5C（runningStatus/runningMode/airVolume，社区抓包实测）等。

## 1.6.0

- **修复 FY-25ZDP1C（LD5C）状态读取与控制问题（issue #1）**。此前该机型被误判为 `MIDERV`，从 `ADevGetStatusMidERV` 端点读取控制状态，但 LD5C 的控制字段（`runningStatus` / `runningMode` / `airVolume`）只存在于设备列表 `statusAll` 中，导致 `runSta` / `runM` / `airVo` 一直停留在默认值，出现"打开后几秒自动关闭"（乐观更新后被刷新回落）且无法控制。
- 新增 `LD5C` 子类型协议：控制状态从 `UsrGetBindDevInfo` 设备列表 `statusAll` 读取并映射（`runningStatus→runSta`、`runningMode→runM`、`airVolume→airVo`），传感器继续由 `ADevGetStatusMidERV` 端点提供。
- LD5C 运行模式按实机抓包对齐：热交换（0）/ 内循环（2）/ 外循环（5）；风量弱 / 中 / 强（1/2/3）。
- `FY-25ZDP1C` 型号提示从 `MIDERV` 移入 `LD5C`，并支持从 `statusAll` 签名自动识别 LD5C 设备；已配置为 MIDERV 的 LD5C 设备会在下次轮询时自动切换到 LD5C 协议。
- 配置流程保存 `familyId` / `realFamilyId`（LD5C 状态读取需要）；不再把中文设备名当作 token 源产生 `Invalid deviceId format` 报错。
- 注意：LD5C 的 SET 控制端点仍以 `ADevSetStatusMidERV` 为准（社区实测 `LD5C` / `LD6C` / `DCERV` SET 端点均无效），如仍有控制异常请提供 `ADevSetStatusMidERV` 返回便于继续核对。

## 1.5.0

- Added DCERV-03 support with the App `ADevGetStatusDCERV` / `ADevSetStatusDCERV` endpoints, DCERV run modes, weak/strong airflow mapping, pressure controls, custom supply/exhaust airflow settings, filter cycle settings, and PM2.5/CO2/TVOC threshold selects.
- Added an ERV `sensor` platform for PM2.5, temperature, humidity, CO2, TVOC, and filter-life fields, with field-specific filtering for Panasonic protocol sentinels such as `127`, `255`, and `65535`.
- Added MidERV filter maintenance selects for PM2.5 filter replacement, return-air filter replacement, and clean-reminder cycles.
- Added a holiday-mode switch for ERV protocols exposing `holM`.
- Added `tools/probe_endpoints.py`, a read-only redacted diagnostic script for collecting endpoint/status reports without disabling TLS verification.

## 1.4.4

- Delayed the post-command ERV status refresh by 5 seconds so Panasonic cloud `todoId` control requests have time to apply before Home Assistant polls the confirmed state.
- This mirrors the timing used by a user-confirmed MidERV implementation and avoids immediately reverting the UI to the pre-command state when the cloud still returns stale status.

## 1.4.3

- Restored compatibility with Panasonic Smart Cloud's self-signed TLS certificate by pinning its SHA-256 fingerprint.
- Kept certificate verification enabled for login, discovery, status, and control requests instead of falling back to insecure `ssl=False` requests.

## 1.4.2

- Fixed standard MidERV control payloads to preserve Panasonic's `255` / `127` "do not change" sentinel values instead of replacing them with the latest status response.
- Split MidERV power, airflow, and run-mode updates into protocol-safe single-field commands, preventing `fan.set_percentage` and preset changes from being ignored by affected devices.
- Extended the ZDP1C MidERV model mapping to the FY-15, FY-35, and FY-50 family variants, including `CX` suffix models.
- Kept the smaller model-specific payload used by dehumidifying MidERV devices unchanged.

## 1.4.1

- Removed disabled TLS certificate verification from Panasonic cloud API requests so login, session, token, and device-control traffic uses the default verified HTTPS context.

## 1.4.0

- Added model-specific protocol mapping for `FY-25ZDP1C` so it is treated as a MidERV device instead of falling back to SmallERV.
- Added support for `FV-35ZXC1C` / `35ZXC1C` dehumidifying MidERV devices, using the MidERV cloud endpoints with the smaller `runSta`/`runM` control payload observed from the Panasonic app.
- Added the MidERV external-circulation run mode and exposed `offline` / `dehumid` status fields as entity attributes.
- Fixed JSON-RPC style Panasonic errors such as `{"error":{"code":4106}}` being ignored after control commands.

## 1.3.9

- Fixed a regression in `1.3.8` where some ERV devices were incorrectly treated as unavailable because their valid status payload did not include the specific fields used by the new probe filter.
- ERV probing now rejects only truly empty status payloads instead of requiring a narrow set of keys, restoring compatibility while still avoiding the empty-response issue from unsupported endpoints.
- Kept the immediate post-command refresh added in `1.3.8` so Home Assistant still updates from confirmed cloud state after a control action.

## 1.3.8

- Tightened ERV status probing so unsupported endpoints that return empty or placeholder payloads are no longer treated as valid device state.
- Fixed a regression where some MidERV-capable devices could remain stuck on the SmallERV protocol, causing panel operations to fail and app-side state changes not to propagate back into Home Assistant.
- Added an immediate refresh after successful ERV control commands so the fan state in Home Assistant updates from the cloud-confirmed device status instead of waiting for the next polling cycle.

## 1.3.7

- Improved ERV subtype detection during config flow so devices exposing `runM` or other MidERV status signatures are registered as `MIDERV` immediately.
- Persist runtime subtype upgrades back into the config entry so older `SMALLERV` entries can self-heal after refresh instead of staying stuck without run mode controls.
- This specifically addresses ERV devices such as `FY-25ZDP1C` that support internal circulation in the Panasonic app but were previously misclassified.

## 1.3.6

- Remapped ERV fan controls so airflow now uses `percentage` and MidERV run mode uses `preset_mode`.
- This allows Home Assistant fan cards to show airflow and run mode controls on the same fan entity.
- Kept the standalone run mode `select` entity for compatibility.

## 1.3.5

- Always create the ERV run mode `select` entity so it is no longer missed because of platform setup timing.
- Renamed the run mode entity to use a clearer Chinese label: `运行模式`.

## 1.3.4

- Improved ERV subtype probing to prefer the protocol with stronger signature keys.
- Fixed cases where run-mode-capable devices could be pinned to `SmallERV` too early, preventing the `MidERV` run mode `select` entity from appearing.

## 1.3.3

- Removed an unrelated YOLO training notebook that had been accidentally committed to the repository.
- No integration behavior or supported device logic changed in this release.

## 1.3.2

- Fixed validation issues reported by Home Assistant and HACS checks.
- Added `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` for config-entry-only setup validation.
- Reordered `manifest.json` keys to match manifest validation requirements.
- Updated GitHub Actions workflows to `actions/checkout@v5` to avoid Node.js 20 deprecation warnings.

## 1.3.1

- Added local brand assets under `custom_components/panasonic_smart_china/brand/` for modern Home Assistant and HACS validation.
- Added `issue_tracker`, `integration_type`, and `codeowners` metadata to the integration manifest.
- Added English translations for the config flow to better match custom integration localization requirements.
- Added `info.md`, GitHub Actions validation workflows, and GitHub issue templates to prepare the repository for HACS default inclusion.
- Added Home Assistant device registry information for ERV fan and select entities.

## 1.3.0

- Added a dedicated `select` entity for `MidERV` run mode control.
- Supported `heat_exchange`, `internal_circulation`, `sleep`, and `auto_eco` run modes through the existing `runM` field.
- Kept existing `fan` airflow control unchanged for both `SmallERV` and `MidERV`.
- Refactored ERV polling and command handling into a shared coordinator so `fan` and `select` stay in sync and avoid duplicate cloud requests.
