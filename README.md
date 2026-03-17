# Panasonic Smart China ERV for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-blue.svg)](https://www.home-assistant.io/)

Home Assistant custom integration for Panasonic Smart China fresh-air and ERV devices used with the mainland China Panasonic Smart app.

This repository is focused on Panasonic fresh-air / ERV devices and keeps the original Panasonic Smart China login flow while adapting the control logic for fresh-air models.

## Features

- Supports Panasonic Smart China account login from Home Assistant config flow
- Reuses the original app login/session flow and device token generation logic from the vendor front-end JS
- Supports fresh-air device categories `0800` and `0850`
- Supports `SmallERV` and `MidERV` subtype families
- Exposes the device as a Home Assistant `fan` entity
- Supports power on/off and preset air-volume switching
- Polls cloud state regularly for status updates

## Supported devices

The integration currently targets Panasonic Smart China fresh-air devices exposed by the app as ERV-style devices, including:

- `0800` category fresh-air devices
- `0850` category fresh-air devices
- `SMALLERVxx` subtype variants
- `MIDERVxx` subtype variants

If your device is discovered but cannot be controlled, please capture and compare:

- `deviceId`
- `devSubTypeId`
- the status API response
- the control API response

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom integration repository.
3. Install `Panasonic Smart China ERV`.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/panasonic_smart_china` into your Home Assistant `/config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration from `Settings -> Devices & Services`.

## Configuration

1. Enter your Panasonic Smart China account phone number and password.
2. Select a discovered fresh-air device.
3. If needed, provide a device token override captured from the app.

In most cases the integration can now generate the device token automatically using the same logic as the Panasonic web front-end.

## Notes

- This integration is for the China-region Panasonic Smart app, not Comfort Cloud.
- Panasonic Smart China uses single-session style authentication. Logging in again on another client may invalidate the Home Assistant session.
- A deprecated `climate` shim is included only to avoid crashes from older installs; the actual entity type is `fan`.

## Repository layout

```text
custom_components/
  panasonic_smart_china/
```

## Disclaimer

This is an unofficial community integration. Use it at your own risk.
