# Changelog

## 1.7.7

- **LD6C 运行模式/风量枚举对齐松下 App 反编译数据（issue #4 修正 v1.7.6 猜测）**。数据来自社区对松下 App `Ld6cBeanConvert` 的逆向（rudyll 仓库）：运行模式 **1=热交换 / 4=内循环 / 6=自动ECO / 7=消毒**，风量 **0=静音 / 1=低 / 2=高**（v1.7.6 误用 DCERV 的 0/1 双档，已修正为三档）。LD6C 现在支持运行模式切换（含独有的消毒模式）。
- **LD6C SET payload 对齐 App `Ld6cDevStateSetBean`**：字段从 12 个扩到完整 bean（31 个控制字段 + 6 组定时器 + res1-10，255=保持/127=定时器保持），覆盖 winDir/heatM/nanoe/dehumid/humidSet/breathLight/airBind/滤网重置等，控制更完整。
- **新增 NEWDCERV 子类型**（App `NewDevSetBean` 家族）：GET `ADevGetStatusNewDCERV` / SET `ADevSetStatusNewDCERV`（端点存活已验证），独立签名键（`pmFstFilCl`/`pmFstFilEx`/`returnInFilEx`/`InLoopFilEx`，与其他机型零冲突），复用 DCERV 运行模式/风量枚举。
- **运行时自动端点发现（新机型免发版）**：配置项新增保存云端 `devSubTypeId`；未识别机型（AUTO）启动后自动探测其专属端点 `ADevGetStatus{devSubTypeId}` / `ADevSetStatus{devSubTypeId}`，按响应字段数自动胜出——**新机型无需等待发版即可读取状态和传感器**，控制先用 LD6C 完整 bean 兜底。识别出的新机型只需补枚举映射即可正式收录。
- 其他协议（SmallERV/MidERV/DCERV/LD5C/NEWDCERV）不受影响。

## 1.7.6

- **新增 LD6C 子类型协议支持（issue #4，FV-50ZDP2C）**。用户诊断报告确认该机型云端 `devSubTypeId` 为 `LD6C`，此前被 DCERV 签名部分命中而误选 DCERV 协议——但 DCERV 的 GET 端点对 LD6C 设备返回的全是无效哨兵值（65535/127/255），导致传感器 unknown、自定义送/排风不可用。
- **LD6C 使用自己的端点**：GET `ADevGetStatusLD6C`（返回 134 个字段，含真实控制状态与传感器值）、SET `ADevSetStatusLD6C`（老协议短名风格）。已实测确认：无 Info 家族变体（`ADevSetStatusInfoLD6C` / `ADevGetStatusInfoLD6C` 均 404）、无官方 Web 控制页（`0800/LD6C` 404）——LD6C 确认走老协议，与 LD5C（Info 家族）不同。
- **识别签名用 LD6C 独有字段**（`autoAirVo`/`breathLight`/`co2Sen`/`nanoe`/`slfSendW`/`venAirVo`/`winDir` 等 22 个），与 DCERV（`coSen`/`userSupWind`/`aircJoi`）、MidERV（`HeatM`/`autoSen`）、LD5C（长驼峰名）零冲突，不会把别的机型误判为 LD6C，也不会再让 LD6C 落回 DCERV。
- **LD6C 传感器收敛为设备实际存在的 7 项**：室外 PM2.5 / 温度 / 湿度 + 外滤网、送风滤网、回风滤网、恢复滤网剩余寿命（送/回风 PM2.5、CO2、TVOC 等该机型不存在的字段不再创建 unknown 实体）。
- **LD6C 控制**：开关、风量（DCERV 风格弱/强）、压差模式/正压强度、自定义送/排风量（`slfSendW`/`slfOutW`，preSet=自定义模式时可用）。**运行模式枚举尚未实测确认，暂不暴露**（社区探测 `ADevSetStatusLD6C` 返回 todoId 但设备不动作，疑似字段词汇问题——待实机确认枚举后补模式切换，v1.7.7+）。
- 其他协议（SmallERV/MidERV/DCERV/LD5C）不受影响。

## 1.7.5

- **修复 LD5C 传感器全部显示 unknown（issue #1，v1.7.4 实测后反馈）**。v1.7.4 将 GET 切到官方实时端点 `ADevGetStatusInfoLD5C` 后，控制字段（开关/模式/风量）已实时同步，但**该端点的传感器字段对 LD5C 全是无效哨兵**（65535/255/127），导致全部传感器 unknown——设备真实传感器数据由 MidERV 端点提供。v1.7.5 改为**混合数据源**：控制字段读 Info GET（实时），传感器读 MidERV GET（真实值）按白名单合并，互不覆盖。
- **LD5C 传感器收敛为设备实际存在的 4 项**（室外 PM2.5 / 室外温度 / 室外湿度 / 回风滤网剩余寿命）：通过 `SENSOR_KEYS_BY_SUBTYPE` 白名单控制，送风/回风 PM2.5 等该机型不存在的字段不再创建 unknown 实体。
- 其他协议（SmallERV/MidERV/DCERV）不受影响。

## 1.7.4

- **修复 LD5C 状态读取不同步（issue #1，v1.7.3 实测后反馈）**。v1.7.3 控制已真实生效（开关/模式/风量均可控制设备），但 UI 仍会在几秒后跳回关闭/unknown——根因：状态读取仍走「MidERV 端点 + 设备列表 statusAll 合并」，而 statusAll 是**云端缓存**，控制命令执行后不刷新（仅面板操作时同步）。v1.7.4 将 LD5C 的 GET 一并切换到官方实时端点 **`ADevGetStatusInfoLD5C`**（与 SET 同属 Info 家族，官方 Web 控制页即以此显示实时状态），长驼峰字段（`runningStatus`/`runningMode`/`airVolume` + 传感器）映射为内部字段名。
- **LD5C 传感器扩充**：实时 Info GET 返回送风/回风/室外全量 PM2.5、温度、湿度（此前仅室外 3 项），实体自动出现。
- **LD5C 不再依赖设备列表 statusAll / familyId**：无 familyId 账号（iamkloudz）不再触发 silent re-login 与相关告警。
- 协议探测评分改为基于 Info 端点原始长字段名，避免映射后短名与通用字段冲突的误判（延续 v1.7.2 的教训）。
- 其他协议（SmallERV/MidERV/DCERV）不受影响。

## 1.7.3

- **修复 LD5C（FY-25ZDP1C）控制完全不生效的问题（issue #1，实测根因）**。此前控制命令走 `ADevSetStatusMidERV` 端点、字段用 MidERV 风格的短名（`runSta`/`runM`/`airVo`）——云端接收请求并返回成功，但 LD5C 设备不认这套字段，命令被静默丢弃，表现为"UI 点击后几秒自动回退、硬件无反应"。经排查松下官方 Web 控制页（`app.psmartcloud.com/ca/cn/0800/LD5C/`，无 SSL pinning，页面 JS 即官方协议源码）确认：LD5C 的专用控制端点是 **`ADevSetStatusInfoLD5C`**（此前社区探测的 `ADevSetStatusLD5C` 因少了 `Info` 而 404 被误排除），字段为设备原生长驼峰名（`runningStatus`/`runningMode`/`airVolume`/`heatingMode`/`pPressureMode`/`autoSensitivity`/滤网周期/定时器等 19 项），每次请求发送完整字段表、255=保持（定时器 127=保持）、只改目标字段；身份字段（`usrId`/`deviceId`/`token`）放在请求体顶层，认证头同时携带 `xtoken`。v1.7.3 按官方实现重写 LD5C 控制链路。
- **LD5C 不再展示假日模式开关**（用户实测 FY-25ZDP1C 官方 App 无假日模式功能；web 页也无此控件）。
- **控制请求/响应增加 debug 日志（脱敏）**：`ERV set <设备> -> <端点> body=...` 与 `ERV set response <设备>: ...`，便于今后远程排查控制链路。
- 其他协议（SmallERV/MidERV/DCERV）控制逻辑不受影响（行为不变）。

## 1.7.2

- **修复运行时探测把 SmallERV/MidERV 误判为 LD5C 的回归（实测发现）**。根因：LD5C 的运行时签名用了映射后的内部字段名（`runSta`/`runM`/`airVo`），而实时状态端点（`ADevGetStatusMidERV`）对**任何**设备都会返回这些通用字段，导致 SmallERV 设备在探测评分中误命中 LD5C 签名而被错误切换协议。现改为只按 `statusAll` 原始字段（`runningStatus`/`runningMode`/`airVolume`/`holidayMode`/`windPath`）判定 LD5C，与配置流程的指纹表保持一致。已误判设备会在下次轮询自动收敛回正确协议。
- **LD5C statusAll 不再依赖 familyId 硬守卫**：部分账号的登录响应（UsrLogin）不返回 `familyId`/`realFamilyId`（issue #1 中 iamkloudz 实测），而 `UsrGetBindDevInfo` 设备列表接口在参数为空时仍能正常返回——现在缺失 familyId 时也照常发起请求，成功即用、失败才降级，不再每 30 秒重复告警。此类账号也无需再删除重加集成。
- **探测全失败时先静默重登再报错**：认证类错误（4102 / 3003 / 3004，SSID 过期）时先尝试用配置项内保存的账号密码静默重登刷新会话，下一次轮询即可用新会话恢复，避免连续报错。

## 1.7.1

- **修复 LD5C 设备升级后仍无法控制的问题（issue #1）**。根因：v1.6.0 起 LD5C 控制状态需要从设备列表接口读取，该接口必须携带登录时返回的 `familyId` / `realFamilyId`，但旧版本（≤1.5.0）创建的配置项里没有保存这两个字段，导致 `statusAll` 每次轮询都失败，`runSta` / `runM` / `airVo` 停留在默认值。
- **运行时自愈**：配置项新增保存松下账号密码（HA 加密存储），LD5C 发现 `familyId` 缺失时自动静默重新登录并原地写回配置项（带 300 秒冷却防抖，避免频繁重登踢掉手机 App 会话）。此后登录过期 / 字段缺失均自动续期，无需用户干预。
- **修复配置流程缓存路径 bug**：复用旧登录缓存时若缓存缺少 `familyId`，不再把空值带入新配置项，改为强制完整登录。
- **代码重构**：登录流程（GetToken → Login → GetDev）从 config flow 抽离为公共 `api.authenticate()`，供交互式登录与运行时自愈共用，行为不变。
- 注意：v1.7.1 之前添加的配置项没有账号密码，自愈无法自动生效——**请删除集成后重新添加一次**（输入松下账号密码），之后永久自愈。

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
