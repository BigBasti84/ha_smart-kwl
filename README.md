# Smart KWL – Home Assistant Integration

Smart KWL is a generic, highly-configurable Home Assistant custom integration for managing the fan speed of a central ventilation system. It supports multi-sensor humidity and CO2 control, day/night/away/summer modes, and provides detailed diagnostics for every control action.

## Features

- **Multi-sensor support:** Use any number of humidity and CO2 sensors, each with individual min/max thresholds.
- **Gradual fan speed control:** Fan speed ramps up or down based on the worst-case demand from all sensors.
- **Modes:** Supports away, night, and summer modes with dedicated fan levels and time windows.
- **Periodic checks:** Control logic runs at a configurable interval (default 60s) to avoid excessive fan changes.
- **Verification:** After each fan speed change, the integration checks if the fan actually updated and retries if needed.
- **Information entities:** Exposes ON/OFF state, incoming/outgoing/outside/exhaust temperatures, and a detailed check log.
- **Dashboard card:** Ready-to-use Lovelace Markdown card for visualizing the last 10 control actions and their reasoning.

## Requirements

- Home Assistant Core 2024.1.0 or newer
- HACS (Home Assistant Community Store) for easy installation (recommended)
- A central fan entity controllable by percentage
- At least one humidity or CO2 sensor entity

## Installation

### HACS (Recommended)

1. **Add repository to HACS:**
	- Go to HACS > Integrations > Menu > Custom repositories
	- Add your GitHub repository URL (e.g. `https://github.com/your-user/smart_kwl`), select category "Integration"
2. **Install Smart KWL:**
	- Find "Smart KWL" in HACS Integrations and install
3. **Restart Home Assistant**
4. **Add the integration:**
	- Go to Settings > Devices & Services > Add Integration > Search for "Smart KWL"

### Manual

1. Copy the `custom_components/smart_kwl` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration as above

## Configuration

1. **Add a new Smart KWL integration** via the Home Assistant UI
2. **Select your fan entity** (must support percentage control)
3. **Select humidity and/or CO2 sensors** (multiple supported)
4. **For each sensor, set min/max thresholds** (defaults: humidity 45/60, CO2 700/900)
5. **Set min/max/default fan levels** (default: 1/8/2)
6. **(Optional) Configure away mode:** select a binary sensor and away fan level
7. **(Optional) Configure night mode:** enable, set start/end time, max night fan level, and summer night fan level
8. **(Optional) Configure summer mode:** select a binary sensor
9. **Set check interval** (default: 60s)
10. **(Optional) Select temperature sensors** for incoming, outgoing, outside, and exhaust air
11. Save and the integration will start controlling your fan

## Dashboard Card

A ready-to-use Markdown card is provided to visualize the last 10 control checks:

1. Copy the contents of `dashboard/smart_kwl_checks_card.yaml`
2. In Home Assistant, go to your dashboard, add a Manual card, and paste the YAML
3. The card will show:
	- Each check run (timestamped)
	- Per-sensor check details (type, entity, min/max, measured, result)
	- Summary and final action line (before/after fan speed, reason, status)

If your check log sensor is not `sensor.smart_kwl_check_log`, update the entity id in the card YAML.

## How it works

- Every check interval, the integration evaluates all configured sensors.
- For each sensor, it logs the min/max, measured value, and scaled demand.
- The highest demand across all humidity and CO2 sensors determines the fan ramp.
- Night, away, and summer modes override or cap the fan level as configured.
- After setting the fan speed, the integration verifies the change and retries if needed.
- All details are logged and available in the check log sensor for diagnostics.

## Troubleshooting

- **Integration not found in UI:**
  - Make sure you restarted Home Assistant after installing
  - For HACS, ensure the repository is added as an Integration, not Plugin
- **Fan not responding:**
  - Check that your fan entity supports percentage control
  - Review the check log sensor for errors or failed verifications
- **No check log output:**
  - Wait for at least one check interval to pass
  - Ensure the check log sensor is enabled and available

## Support & Contributions

- Issues: [GitHub Issues](https://github.com/your-user/smart_kwl/issues)
- Pull requests welcome! Please open an issue first for major changes.

---

© 2026 Your Name or Organization. Licensed under the MIT License.

Smart KWL is a generic, highly-configurable Home Assistant custom integration for managing the fan speed of a central ventilation system. It supports multi-sensor humidity and CO2 control, day/night/away/summer modes, and provides detailed diagnostics for every control action.

## Features

- **Multi-sensor support:** Use any number of humidity and CO2 sensors, each with individual min/max thresholds.
- **Gradual fan speed control:** Fan speed ramps up or down based on the worst-case demand from all sensors.
- **Modes:** Supports away, night, and summer modes with dedicated fan levels and time windows.
- **Periodic checks:** Control logic runs at a configurable interval (default 60s) to avoid excessive fan changes.
- **Verification:** After each fan speed change, the integration checks if the fan actually updated and retries if needed.
- **Information entities:** Exposes ON/OFF state, incoming/outgoing/outside/exhaust temperatures, and a detailed check log.
- **Dashboard card:** Ready-to-use Lovelace Markdown card for visualizing the last 10 control actions and their reasoning.

## Requirements

- Home Assistant Core 2024.1.0 or newer
- HACS (Home Assistant Community Store) for easy installation (recommended)
- A central fan entity controllable by percentage
- At least one humidity or CO2 sensor entity

## Installation

### HACS (Recommended)

1. **Add repository to HACS:**
	- Go to HACS > Integrations > Menu > Custom repositories
	- Add your GitHub repository URL (e.g. `https://github.com/your-user/smart_kwl`), select category "Integration"
2. **Install Smart KWL:**
	- Find "Smart KWL" in HACS Integrations and install
3. **Restart Home Assistant**
4. **Add the integration:**
	- Go to Settings > Devices & Services > Add Integration > Search for "Smart KWL"

### Manual

1. Copy the `custom_components/smart_kwl` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration as above

## Configuration

1. **Add a new Smart KWL integration** via the Home Assistant UI
2. **Select your fan entity** (must support percentage control)
3. **Select humidity and/or CO2 sensors** (multiple supported)
4. **For each sensor, set min/max thresholds** (defaults: humidity 45/60, CO2 700/900)
5. **Set min/max/default fan levels** (default: 1/8/2)
6. **(Optional) Configure away mode:** select a binary sensor and away fan level
7. **(Optional) Configure night mode:** enable, set start/end time, max night fan level, and summer night fan level
8. **(Optional) Configure summer mode:** select a binary sensor
9. **Set check interval** (default: 60s)
10. **(Optional) Select temperature sensors** for incoming, outgoing, outside, and exhaust air
11. Save and the integration will start controlling your fan

## Dashboard Card

A ready-to-use Markdown card is provided to visualize the last 10 control checks:

1. Copy the contents of `dashboard/smart_kwl_checks_card.yaml`
2. In Home Assistant, go to your dashboard, add a Manual card, and paste the YAML
3. The card will show:
	- Each check run (timestamped)
	- Per-sensor check details (type, entity, min/max, measured, result)
	- Summary and final action line (before/after fan speed, reason, status)

If your check log sensor is not `sensor.smart_kwl_check_log`, update the entity id in the card YAML.

## How it works

- Every check interval, the integration evaluates all configured sensors.
- For each sensor, it logs the min/max, measured value, and scaled demand.
- The highest demand across all humidity and CO2 sensors determines the fan ramp.
- Night, away, and summer modes override or cap the fan level as configured.
- After setting the fan speed, the integration verifies the change and retries if needed.
- All details are logged and available in the check log sensor for diagnostics.

## Troubleshooting

- **Integration not found in UI:**
  - Make sure you restarted Home Assistant after installing
  - For HACS, ensure the repository is added as an Integration, not Plugin
- **Fan not responding:**
  - Check that your fan entity supports percentage control
  - Review the check log sensor for errors or failed verifications
- **No check log output:**
  - Wait for at least one check interval to pass
  - Ensure the check log sensor is enabled and available

## Support & Contributions

- Issues: [GitHub Issues](https://github.com/your-user/smart_kwl/issues)
- Pull requests welcome! Please open an issue first for major changes.

---

© 2026 Your Name or Organization. Licensed under the MIT License.
>>>>>>> 8a2f65f (Initial commit: Smart KWL Home Assistant integration)
