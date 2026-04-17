# Panasonic Smart China ERV

![Panasonic Smart China](custom_components/panasonic_smart_china/brand/logo.png)

Home Assistant custom integration for Panasonic Smart China ERV / fresh-air devices used with the China mainland "Panasonic Smart" app.

## Features

- Config flow based setup
- Reuses the Panasonic Smart China login and session flow
- Supports ERV devices in categories `0800` and `0850`
- Supports `SmallERV` and `MidERV`
- Exposes a `fan` entity for power and airflow control
- Exposes a `select` entity for `MidERV` run mode control

## MidERV run modes

- `heat_exchange`
- `internal_circulation`
- `sleep`
- `auto_eco`

## Notes

- China-only integration: this repository is intended for the mainland China Panasonic Smart app and cloud endpoints.
- This is a custom integration and is not affiliated with Panasonic.

## Installation

Install through HACS, restart Home Assistant, then add `Panasonic Smart China ERV` from Settings > Devices & Services.
