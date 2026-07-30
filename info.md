# Panasonic Smart China ERV

![Panasonic Smart China](custom_components/panasonic_smart_china/brand/logo.png)

Home Assistant custom integration for Panasonic Smart China ERV / fresh-air devices used with the China mainland "Panasonic Smart" app.

## Features

- Config flow based setup
- Reuses the Panasonic Smart China login and session flow
- Supports ERV devices in categories `0800` and `0850`
- Supports `SmallERV`, `MidERV`, `MidERV Dehumid`, and `DCERV-03`
- Exposes a `fan` entity for power and airflow control
- Exposes `select` entities for run modes, MidERV filter maintenance, and DCERV-03 pressure/filter/air-quality settings
- Exposes ERV `sensor` entities for PM2.5, temperature, humidity, CO2, TVOC, and filter-life data when the device reports those fields
- Filters Panasonic protocol sentinel values such as `127`, `255`, and `65535`
- Includes a redacted read-only endpoint diagnostic script under `tools/`

## MidERV run modes

- `heat_exchange`
- `external_circulation`
- `internal_circulation`
- `sleep`
- `auto_eco`

## DCERV-03

DCERV-03 devices use the Panasonic App `ADevGetStatusDCERV` and
`ADevSetStatusDCERV` endpoints, with support for power, airflow, run mode,
pressure mode, custom supply/exhaust airflow, filter cycles, PM2.5 threshold,
CO2 threshold, TVOC threshold, and stable sensor fields.

## Notes

- China-only integration: this repository is intended for the mainland China Panasonic Smart app and cloud endpoints.
- This is a custom integration and is not affiliated with Panasonic.

## Installation

Install through HACS, restart Home Assistant, then add `Panasonic Smart China ERV` from Settings > Devices & Services.
