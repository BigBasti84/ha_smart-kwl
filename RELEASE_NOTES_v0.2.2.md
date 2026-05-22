## Smart KWL v0.2.2

### Fixed
- Added summer-heat base-speed handling: when outside air is hotter than incoming air by the configured delta, the controller lowers the default fan base speed to the configured summer heat level.
- Kept humidity and CO2 as higher-priority inputs above the base speed, so they can still raise fan speed when demand requires it.
- Suppressed false humidity/CO2 reason text when the computed target remains at the configured default speed.
- Dashboard flow chart and recent changes now only show a reason when the fan target differs from the configured default speed.

### Included In This Tag
- Summer-heat base-speed control.
- Reason visibility cleanup for the flow chart and recent changes.
- Version bump and release documentation for 0.2.2.
