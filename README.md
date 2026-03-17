# Panasonic Smart China ERV for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue.svg)](https://www.home-assistant.io/)

本项目参考并基于原项目 [mcdona1d/panasonic_smart_china](https://github.com/mcdona1d/panasonic_smart_china) 继续扩展，在此感谢原作者在松下智能家电中国区登录流程与前期逆向分析上的工作。

这是一个适用于 Home Assistant 的自定义集成，用于接入中国大陆地区“松下智能家电” App 下的松下新风 / ERV 设备。

本仓库聚焦于松下新风设备，在保留原项目登录流程与核心认证思路的基础上，扩展并适配了新风设备的控制逻辑。

## 功能特性

- 支持通过 Home Assistant 配置流程登录松下智能家电账号
- 复用松下智能家电原始登录 / 会话流程
- 复用厂商前端网页中的设备 Token 生成逻辑
- 支持 `0800` 与 `0850` 分类的新风设备
- 支持 `SmallERV` 与 `MidERV` 系列子类型
- 在 Home Assistant 中以 `fan` 实体形式提供控制
- 支持开关机与风量档位切换
- 支持定时轮询云端状态并同步到 Home Assistant

## 当前支持范围

当前集成主要面向松下智能家电 App 中以 ERV / 新风形式出现的设备，包括：

- `0800` 分类新风设备
- `0850` 分类新风设备
- `SMALLERVxx` 子类型设备
- `MIDERVxx` 子类型设备

如果设备能够发现但无法控制，建议提供以下信息用于排查：

- `deviceId`
- `devSubTypeId`
- 状态查询接口返回内容
- 控制接口返回内容

## 安装方法

### 通过 HACS 安装

1. 打开 HACS。
2. 将本仓库添加为自定义集成仓库。
3. 搜索并安装 `Panasonic Smart China ERV`。
4. 重启 Home Assistant。

### 手动安装

1. 将 `custom_components/panasonic_smart_china` 复制到 Home Assistant 的 `/config/custom_components/` 目录下。
2. 重启 Home Assistant。
3. 在 `设置 -> 设备与服务` 中添加集成。

## 配置说明

1. 输入松下智能家电账号的手机号与密码。
2. 选择已发现的新风设备。
3. 如有需要，可手动填写从 App 抓包获得的设备 Token。

在大多数情况下，集成可以直接按照松下前端网页中的同样逻辑自动生成设备 Token。

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
