# Changelog

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
