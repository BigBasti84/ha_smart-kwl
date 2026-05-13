# Changelog

## [0.1.9] - 2026-05-13
### Fixed
- Fixed `AttributeError: property 'config_entry' has no setter` when opening integration options in HA 2024.x+

## [0.1.8] - 2026-05-13
### Fixed
- Fixed thread-safety issue in controller state-change scheduling that caused `coroutine was never awaited` warnings and instability
- Updated manifest documentation and issue tracker URLs to the actual repository

## [0.1.6] - 2026-05-13
### Added
- New Mushroom dashboard template at dashboard/smart_kwl_mushroom_dashboard.yaml
- New combined diagnostic sensors for CO2 and humidity including low/high thresholds
- New binary sensors for Summer Mode Active and Night Mode Active

## [0.1.5] - 2026-05-13
### Fixed
- Check log now always reports summer mode state via `summer_check` line
- Night decision logging now clearly shows when `night_summer` is applied

## [0.1.4] - 2026-05-13
### Fixed
- Dashboard card now auto-detects Smart KWL check log sensor entity ID instead of relying on a single hardcoded ID

## [0.1.3] - 2026-05-13
### Added
- Added Smart KWL integration icon at assets/smart_kwl_icon.svg

## [0.1.2] - 2026-05-13
### Changed
- Added explicit optional toggle for home/away mode in config flow
- Enforced validation: night max fan level must be higher than night summer fan level
- Updated defaults: night max fan level 5, night summer fan level 4
- Added controller fallbacks with warning logs when required entities are unavailable or invalid

## [0.1.1] - 2026-05-13
### Added
- Dedicated Smart KWL manual fan entity with discrete levels 1..8
- Support for climate target entities using fan_mode level mapping

### Changed
- Config flow fan level fields now use discrete 1..8 input constraints
- Improved config flow descriptions for optional fields and temperature mapping
- Threshold steps for humidity/CO2 now focus on min/max value entry only

## [0.1.0] - 2026-05-13
### Added
- Initial release for HACS custom integration
- Multi-sensor support (humidity, CO2)
- Configurable thresholds and modes
- Dashboard card and diagnostics
