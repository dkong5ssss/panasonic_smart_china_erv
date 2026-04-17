# Changelog

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
