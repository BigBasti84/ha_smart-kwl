# Changelog

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
