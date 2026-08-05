# Panasonic Smart China ERV for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-18BCF2.svg)](https://www.home-assistant.io/)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=panasonic_smart_china)

<p align="center">
  <img src="custom_components/panasonic_smart_china/brand/logo.png" width="200" alt="Panasonic Smart China">
</p>

本项目参考并基于原项目 [mcdona1d/panasonic_smart_china](https://github.com/mcdona1d/panasonic_smart_china) 继续扩展，在此感谢原作者在松下智能家电中国区登录流程与前期逆向分析上的工作。

这是一个适用于 Home Assistant 的自定义集成，用于接入中国大陆地区“松下智能家电” App 下的松下新风 / ERV 设备。

本仓库聚焦于松下新风设备，在保留原项目登录流程与核心认证思路的基础上，扩展并适配了新风设备的控制逻辑。

## 功能特性

- 支持通过 Home Assistant 配置流程登录松下智能家电账号
- 复用松下智能家电原始登录 / 会话流程
- 复用厂商前端网页中的设备 Token 生成逻辑
- 支持 `0800` 与 `0850` 分类的新风设备
- 支持 `SmallERV`、`MidERV`、`MidERV Dehumid` 与 `DCERV-03` 系列子类型
- 在 Home Assistant 中以 `fan` 实体形式提供控制
- 支持开关机与风量档位切换
- 支持 `MidERV` 的运行模式切换：热交换、外循环、内循环、睡眠、自动 ECO
- 支持 `MidERV` 滤网更换周期与清洗提醒设置
- 支持 `DCERV-03` 的运行模式、压差模式、自定义送排风、滤网周期和 PM2.5 / CO2 / TVOC 阈值设置
- 支持 ERV 传感器实体：PM2.5、温湿度、CO2、TVOC、滤网剩余寿命等
- 自动过滤松下协议占位值，避免把 `127`、`255`、`65535` 显示为真实传感器读数
- 支持定时轮询云端状态并同步到 Home Assistant

## 当前支持范围

当前集成主要面向松下智能家电 App 中以 ERV / 新风形式出现的设备，包括：

| 机型 / 系列 | 子类型 | category | 支持状态 |
| --- | --- | --- | --- |
| FY-35ZJD2C 等 | `DCERV-03` / `DCERV*` | `0800` | 已加入完整协议支持，含控制、设置和稳定传感器 |
| FY/FV ZDP1C 系列 | `MIDERV*` | `0800` | 支持开关、风量、运行模式和滤网维护设置（FY-25ZDP1C 除外，见下） |
| FY-25ZDP1C 等 | `LD5C` | `0800` | 支持开关、风量、运行模式（热交换 / 内循环 / 外循环） |
| FV-35ZXC1C / 35ZXC1C | `MIDERV_DEHUMID` | `0800` | 支持除湿型 MidERV 精简控制 payload |
| SmallERV 系列 | `SMALLERV*` | `0850` | 支持开关和风量控制 |

`DCERV-03` 传感器会创建已知稳定字段；其他 ERV 机型只会为状态响应中真实出现的传感器字段创建实体。

如果设备能够发现但无法控制，建议提供以下信息用于排查：

- `deviceId`
- `devSubTypeId`
- 状态查询接口返回内容
- 控制接口返回内容

## 安装方法

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=panasonic_smart_china)

### 通过 HACS 安装（推荐）

1. 打开 Home Assistant 中的 HACS。
2. 搜索 `Panasonic Smart China ERV` 并下载安装。
3. 或手动添加自定义仓库：`https://github.com/dkong5ssss/panasonic_smart_china_erv`。
4. 重启 Home Assistant。

## 配置说明

1. 输入松下智能家电账号的手机号与密码。
2. 选择已发现的新风设备。
3. 如有需要，可手动填写从 App 抓包获得的设备 Token。

在大多数情况下，集成可以直接按照松下前端网页中的同样逻辑自动生成设备 Token。

## 实体说明

- 所有受支持设备都会创建一个 `fan` 实体，用于开关和风量控制。
- 支持运行模式的设备会额外创建一个 `select` 实体，用于切换运行模式。
- `MidERV` 会额外创建滤网更换周期与清洗提醒 `select` 实体。
- `DCERV-03` 会额外创建压差模式、自定义送排风、滤网周期和空气质量阈值 `select` 实体。
- 支持 `holM` 的设备会创建假日模式 `switch` 实体。
- 返回 PM2.5、温湿度、CO2、TVOC 或滤网寿命字段的设备会创建对应 `sensor` 实体。

## 诊断报告

如果设备能够发现但传感器未知、数值异常或部分功能不可用，可在仓库根目录运行只读诊断脚本：

```bash
python -m pip install aiohttp
PMS_USER='松下智家账号' PMS_PASS='松下智家密码' python tools/probe_endpoints.py --report
```

脚本会生成 `endpoint_report_*.json`，自动隐藏账号、会话、token 和设备唯一标识。可以把该 JSON 附加到 GitHub issue，帮助确认真实 `devSubTypeId`、`statusAll` 字段和各 GET 端点返回内容。

## 注意事项

- 本集成仅适用于中国区“松下智能家电” App，不适用于 Comfort Cloud。
- 松下智能家电通常是单会话风格认证，如果你在手机 App 上重新登录，Home Assistant 中的会话可能失效。
- 仓库中保留了一个兼容用的 `climate` 占位文件，仅用于避免旧版本安装时崩溃；实际设备实体类型为 `fan`。

## 仓库结构

```text
custom_components/
  panasonic_smart_china/
```

## 免责声明

本项目为非官方社区集成，请自行评估风险并承担使用后果。
