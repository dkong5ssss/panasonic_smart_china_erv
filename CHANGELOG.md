# Changelog

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
