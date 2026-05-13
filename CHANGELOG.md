# Changelog

## [0.1.14] - 2026-05-13
### Added
- External manual fan change handling:
	- Manual decrease is held until a new automation event occurs
	- Manual increase is held for a configurable duration and can be exceeded by higher event-driven demand
- New integration settings:
	- `manual_increase_hold_hours`
	- `manual_override_default_hours`
- Timed manual override controls:
	- `number.smart_kwl_manual_override_level`
	- `number.smart_kwl_manual_override_duration`
	- `button.smart_kwl_apply_manual_override`
	- `binary_sensor.smart_kwl_manual_override_active`
- Extended check-log attributes with `change_history` for reliable dashboard rendering of recent level transitions

### Changed
- Dashboard updated with a dedicated Manual Override section and status entities
- Recent changes card now reads level transitions from `change_history` instead of short check-run parsing

## [0.1.13] - 2026-05-13
### Fixed
- Removed problematic static path registration in `__init__.py` that caused setup failure
- Replaced picture-elements diagram card with markdown flow diagram (simpler, no image URL issues)
- Dashboard now stable and loads correctly

## [0.1.12] - 2026-05-13
### Added
- Filter maintenance tracking: days since last cleaning, remaining lifetime, cleaning status (ok/due_soon/overdue)
- `button.smart_kwl_filters_cleaned` — press to record a filter cleaning event
- Filter data persisted via HA storage (survives restarts)
- Ventilation diagram card (`picture-elements`) with temperature overlays on all 4 air paths
- Filter status shown as color-coded icon (green/amber/red) on the diagram
- Full filter status dashboard card with last-cleaned date and install date
- SVG diagram served automatically from integration `www/` folder at `/local/smart_kwl_diagram.svg`

## [0.1.11] - 2026-05-13
### Fixed
- Ventilation On binary sensor now correctly shows On for climate entities (state is `heat`/`auto`, not `on`)
- Dashboard rewritten with direct entity IDs — no more loop-based discovery that silently failed
- Dashboard simplified: fewer template loops, cleaner cards

## [0.1.10] - 2026-05-13
### Fixed
- Added `device_info` to all entity classes (sensor, binary_sensor, fan) — required for `_attr_has_entity_name = True` in HA 2024.x+; without this, no entities were registered
- Removed Diagnostics card from dashboard
- Improved temperature history graph (all 4 temperature sensors)

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
