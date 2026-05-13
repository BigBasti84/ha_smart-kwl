"""Config flow for Smart KWL."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_AWAY_FAN_LEVEL,
    CONF_AWAY_SENSOR,
    CONF_CHECK_INTERVAL,
    CONF_CO2_CONFIGS,
    CONF_CO2_SENSORS,
    CONF_DEFAULT_FAN_LEVEL,
    CONF_EXHAUST_TEMPERATURE_ENTITY,
    CONF_FAN_ENTITY,
    CONF_HUMIDITY_CONFIGS,
    CONF_HUMIDITY_SENSORS,
    CONF_INCOMING_TEMPERATURE_ENTITY,
    CONF_MAX_FAN_LEVEL,
    CONF_MIN_FAN_LEVEL,
    CONF_NIGHT_ENABLED,
    CONF_NIGHT_END,
    CONF_NIGHT_MAX_FAN_LEVEL,
    CONF_NIGHT_START,
    CONF_NIGHT_SUMMER_FAN_LEVEL,
    CONF_OUTGOING_TEMPERATURE_ENTITY,
    CONF_OUTSIDE_TEMPERATURE_ENTITY,
    CONF_SENSOR_ENTITY_ID,
    CONF_SENSOR_MAX,
    CONF_SENSOR_MIN,
    CONF_SUMMER_MODE_SENSOR,
    DEFAULT_AWAY_FAN_LEVEL,
    DEFAULT_CHECK_INTERVAL,
    DEFAULT_CO2_MAX,
    DEFAULT_CO2_MIN,
    DEFAULT_FAN_LEVEL,
    DEFAULT_HUMIDITY_MAX,
    DEFAULT_HUMIDITY_MIN,
    DEFAULT_MAX_FAN_LEVEL,
    DEFAULT_MIN_FAN_LEVEL,
    DEFAULT_NIGHT_ENABLED,
    DEFAULT_NIGHT_END,
    DEFAULT_NIGHT_MAX_FAN_LEVEL,
    DEFAULT_NIGHT_START,
    DEFAULT_NIGHT_SUMMER_FAN_LEVEL,
    DOMAIN,
)


def _sensor_selector(multiple: bool = False) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", multiple=multiple))


def _binary_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="binary_sensor"))


def _fan_target_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["fan", "climate"]))


def _level_selector(default: Any) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=8, step=1, mode=selector.NumberSelectorMode.BOX),
    )


def _int_in_range(value: Any, minimum: int, maximum: int) -> bool:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return False
    return minimum <= parsed <= maximum


class SmartKwlFlowMixin:
    """Shared state machine for config and options flow."""

    def _reset_state(self) -> None:
        self._data: dict[str, Any] = {}
        self._humidity_configs: list[dict[str, Any]] = []
        self._co2_configs: list[dict[str, Any]] = []
        self._humidity_index = 0
        self._co2_index = 0

    def _load_existing_thresholds(self, configs: list[dict[str, Any]], key: str) -> dict[str, tuple[float, float]]:
        out: dict[str, tuple[float, float]] = {}
        for cfg in configs:
            entity_id = cfg.get(CONF_SENSOR_ENTITY_ID)
            if entity_id:
                out[entity_id] = (
                    float(cfg.get(CONF_SENSOR_MIN, DEFAULT_HUMIDITY_MIN if key == CONF_HUMIDITY_CONFIGS else DEFAULT_CO2_MIN)),
                    float(cfg.get(CONF_SENSOR_MAX, DEFAULT_HUMIDITY_MAX if key == CONF_HUMIDITY_CONFIGS else DEFAULT_CO2_MAX)),
                )
        return out

    def _general_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Smart KWL")): str,
                vol.Required(CONF_FAN_ENTITY, default=defaults.get(CONF_FAN_ENTITY)): _fan_target_selector(),
                vol.Required(CONF_HUMIDITY_SENSORS, default=defaults.get(CONF_HUMIDITY_SENSORS, [])): _sensor_selector(multiple=True),
                vol.Required(CONF_CO2_SENSORS, default=defaults.get(CONF_CO2_SENSORS, [])): _sensor_selector(multiple=True),
                vol.Required(CONF_MIN_FAN_LEVEL, default=defaults.get(CONF_MIN_FAN_LEVEL, DEFAULT_MIN_FAN_LEVEL)): _level_selector(defaults.get(CONF_MIN_FAN_LEVEL, DEFAULT_MIN_FAN_LEVEL)),
                vol.Required(CONF_MAX_FAN_LEVEL, default=defaults.get(CONF_MAX_FAN_LEVEL, DEFAULT_MAX_FAN_LEVEL)): _level_selector(defaults.get(CONF_MAX_FAN_LEVEL, DEFAULT_MAX_FAN_LEVEL)),
                vol.Required(CONF_DEFAULT_FAN_LEVEL, default=defaults.get(CONF_DEFAULT_FAN_LEVEL, DEFAULT_FAN_LEVEL)): _level_selector(defaults.get(CONF_DEFAULT_FAN_LEVEL, DEFAULT_FAN_LEVEL)),
                vol.Optional(CONF_AWAY_SENSOR, default=defaults.get(CONF_AWAY_SENSOR)): _binary_selector(),
                vol.Optional(CONF_AWAY_FAN_LEVEL, default=defaults.get(CONF_AWAY_FAN_LEVEL, DEFAULT_AWAY_FAN_LEVEL)): _level_selector(defaults.get(CONF_AWAY_FAN_LEVEL, DEFAULT_AWAY_FAN_LEVEL)),
                vol.Required(CONF_NIGHT_ENABLED, default=defaults.get(CONF_NIGHT_ENABLED, DEFAULT_NIGHT_ENABLED)): bool,
                vol.Required(CONF_NIGHT_START, default=defaults.get(CONF_NIGHT_START, DEFAULT_NIGHT_START)): selector.TimeSelector(),
                vol.Required(CONF_NIGHT_END, default=defaults.get(CONF_NIGHT_END, DEFAULT_NIGHT_END)): selector.TimeSelector(),
                vol.Required(CONF_NIGHT_MAX_FAN_LEVEL, default=defaults.get(CONF_NIGHT_MAX_FAN_LEVEL, DEFAULT_NIGHT_MAX_FAN_LEVEL)): _level_selector(defaults.get(CONF_NIGHT_MAX_FAN_LEVEL, DEFAULT_NIGHT_MAX_FAN_LEVEL)),
                vol.Required(CONF_NIGHT_SUMMER_FAN_LEVEL, default=defaults.get(CONF_NIGHT_SUMMER_FAN_LEVEL, DEFAULT_NIGHT_SUMMER_FAN_LEVEL)): _level_selector(defaults.get(CONF_NIGHT_SUMMER_FAN_LEVEL, DEFAULT_NIGHT_SUMMER_FAN_LEVEL)),
                vol.Optional(CONF_SUMMER_MODE_SENSOR, default=defaults.get(CONF_SUMMER_MODE_SENSOR)): _binary_selector(),
                vol.Required(CONF_CHECK_INTERVAL, default=defaults.get(CONF_CHECK_INTERVAL, DEFAULT_CHECK_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(CONF_INCOMING_TEMPERATURE_ENTITY, default=defaults.get(CONF_INCOMING_TEMPERATURE_ENTITY)): _sensor_selector(),
                vol.Optional(CONF_OUTGOING_TEMPERATURE_ENTITY, default=defaults.get(CONF_OUTGOING_TEMPERATURE_ENTITY)): _sensor_selector(),
                vol.Optional(CONF_OUTSIDE_TEMPERATURE_ENTITY, default=defaults.get(CONF_OUTSIDE_TEMPERATURE_ENTITY)): _sensor_selector(),
                vol.Optional(CONF_EXHAUST_TEMPERATURE_ENTITY, default=defaults.get(CONF_EXHAUST_TEMPERATURE_ENTITY)): _sensor_selector(),
            }
        )

    def _threshold_schema(self, entity_id: str, min_default: float, max_default: float) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_SENSOR_MIN, default=min_default): vol.Coerce(float),
                vol.Required(CONF_SENSOR_MAX, default=max_default): vol.Coerce(float),
            }
        )

    def _validate_general(self, user_input: dict[str, Any]) -> str | None:
        min_level = int(user_input[CONF_MIN_FAN_LEVEL])
        max_level = int(user_input[CONF_MAX_FAN_LEVEL])
        default_level = int(user_input[CONF_DEFAULT_FAN_LEVEL])

        if min_level > max_level:
            return "fan_level_range"
        if not _int_in_range(default_level, min_level, max_level):
            return "default_level_range"

        away_sensor = user_input.get(CONF_AWAY_SENSOR)
        away_level = user_input.get(CONF_AWAY_FAN_LEVEL)
        if away_sensor and away_level is not None and not _int_in_range(away_level, min_level, max_level):
            return "away_level_range"

        if not user_input.get(CONF_HUMIDITY_SENSORS) and not user_input.get(CONF_CO2_SENSORS):
            return "no_control_sensors"

        if user_input.get(CONF_NIGHT_ENABLED):
            night_max = int(user_input[CONF_NIGHT_MAX_FAN_LEVEL])
            night_summer = int(user_input[CONF_NIGHT_SUMMER_FAN_LEVEL])
            if not _int_in_range(night_max, min_level, max_level):
                return "night_max_range"
            if not _int_in_range(night_summer, min_level, max_level):
                return "night_summer_range"

        return None

    def _prepare_threshold_steps(self, user_input: dict[str, Any], existing: dict[str, Any]) -> None:
        humidity_entities = user_input.get(CONF_HUMIDITY_SENSORS, [])
        co2_entities = user_input.get(CONF_CO2_SENSORS, [])

        self._data = dict(user_input)
        self._humidity_configs = []
        self._co2_configs = []
        self._humidity_index = 0
        self._co2_index = 0

        self._humidity_defaults = self._load_existing_thresholds(existing.get(CONF_HUMIDITY_CONFIGS, []), CONF_HUMIDITY_CONFIGS)
        self._co2_defaults = self._load_existing_thresholds(existing.get(CONF_CO2_CONFIGS, []), CONF_CO2_CONFIGS)

        self._data[CONF_HUMIDITY_SENSORS] = humidity_entities
        self._data[CONF_CO2_SENSORS] = co2_entities

    def _finalize_data(self) -> dict[str, Any]:
        data = dict(self._data)
        data[CONF_HUMIDITY_CONFIGS] = self._humidity_configs
        data[CONF_CO2_CONFIGS] = self._co2_configs
        data.pop(CONF_HUMIDITY_SENSORS, None)
        data.pop(CONF_CO2_SENSORS, None)
        return data

    async def _next_step_or_create(self):
        if self._humidity_index < len(self._data.get(CONF_HUMIDITY_SENSORS, [])):
            return await self.async_step_humidity_threshold()
        if self._co2_index < len(self._data.get(CONF_CO2_SENSORS, [])):
            return await self.async_step_co2_threshold()
        return None

    async def async_step_humidity_threshold(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        sensors: list[str] = self._data.get(CONF_HUMIDITY_SENSORS, [])
        if self._humidity_index >= len(sensors):
            return await self.async_step_co2_threshold()

        entity_id = sensors[self._humidity_index]
        d_min, d_max = self._humidity_defaults.get(entity_id, (DEFAULT_HUMIDITY_MIN, DEFAULT_HUMIDITY_MAX))

        if user_input is not None:
            if user_input[CONF_SENSOR_MIN] > user_input[CONF_SENSOR_MAX]:
                errors["base"] = "sensor_range"
            else:
                self._humidity_configs.append(
                    {
                        CONF_SENSOR_ENTITY_ID: entity_id,
                        CONF_SENSOR_MIN: float(user_input[CONF_SENSOR_MIN]),
                        CONF_SENSOR_MAX: float(user_input[CONF_SENSOR_MAX]),
                    }
                )
                self._humidity_index += 1
                return await self._next_step_or_create()

        return self.async_show_form(
            step_id="humidity_threshold",
            data_schema=self._threshold_schema(entity_id, d_min, d_max),
            errors=errors,
            description_placeholders={"entity_id": entity_id, "sensor_type": "humidity", "default_min": str(d_min), "default_max": str(d_max)},
        )

    async def async_step_co2_threshold(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        sensors: list[str] = self._data.get(CONF_CO2_SENSORS, [])
        if self._co2_index >= len(sensors):
            return self._create_or_update_entry()

        entity_id = sensors[self._co2_index]
        d_min, d_max = self._co2_defaults.get(entity_id, (DEFAULT_CO2_MIN, DEFAULT_CO2_MAX))

        if user_input is not None:
            if user_input[CONF_SENSOR_MIN] > user_input[CONF_SENSOR_MAX]:
                errors["base"] = "sensor_range"
            else:
                self._co2_configs.append(
                    {
                        CONF_SENSOR_ENTITY_ID: entity_id,
                        CONF_SENSOR_MIN: float(user_input[CONF_SENSOR_MIN]),
                        CONF_SENSOR_MAX: float(user_input[CONF_SENSOR_MAX]),
                    }
                )
                self._co2_index += 1
                return await self._next_step_or_create()

        return self.async_show_form(
            step_id="co2_threshold",
            data_schema=self._threshold_schema(entity_id, d_min, d_max),
            errors=errors,
            description_placeholders={"entity_id": entity_id, "sensor_type": "CO2", "default_min": str(d_min), "default_max": str(d_max)},
        )


class SmartKwlConfigFlow(SmartKwlFlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart KWL."""

    VERSION = 1

    def __init__(self) -> None:
        self._reset_state()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            error = self._validate_general(user_input)
            if error is None:
                self._prepare_threshold_steps(user_input, {})
                return await self._next_step_or_create()
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self._general_schema(user_input or {}),
            errors=errors,
            description_placeholders={
                "level_min": "1",
                "level_max": "8",
                "incoming_expl": "Incoming: fresh outdoor air entering the unit (before heat exchanger).",
                "outgoing_expl": "Outgoing: supply air leaving the unit to your rooms (after heat exchanger).",
                "outside_expl": "Outside: optional ambient outdoor reference sensor.",
                "exhaust_expl": "Exhaust: extract air from rooms entering the unit (before heat exchanger).",
            },
        )

    def _create_or_update_entry(self):
        title = self._data.get(CONF_NAME, "Smart KWL")
        data = self._finalize_data()
        data.pop(CONF_NAME, None)
        return self.async_create_entry(title=title, data=data)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SmartKwlOptionsFlow(config_entry)


class SmartKwlOptionsFlow(SmartKwlFlowMixin, config_entries.OptionsFlow):
    """Handle options for Smart KWL."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._reset_state()

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        current[CONF_NAME] = self.config_entry.title

        if CONF_HUMIDITY_CONFIGS in current and CONF_HUMIDITY_SENSORS not in current:
            current[CONF_HUMIDITY_SENSORS] = [cfg.get(CONF_SENSOR_ENTITY_ID) for cfg in current[CONF_HUMIDITY_CONFIGS] if cfg.get(CONF_SENSOR_ENTITY_ID)]
        if CONF_CO2_CONFIGS in current and CONF_CO2_SENSORS not in current:
            current[CONF_CO2_SENSORS] = [cfg.get(CONF_SENSOR_ENTITY_ID) for cfg in current[CONF_CO2_CONFIGS] if cfg.get(CONF_SENSOR_ENTITY_ID)]

        if user_input is not None:
            error = self._validate_general(user_input)
            if error is None:
                self._prepare_threshold_steps(user_input, current)
                return await self._next_step_or_create()
            errors["base"] = error

        return self.async_show_form(
            step_id="init",
            data_schema=self._general_schema(current),
            errors=errors,
            description_placeholders={
                "level_min": "1",
                "level_max": "8",
                "incoming_expl": "Incoming: fresh outdoor air entering the unit (before heat exchanger).",
                "outgoing_expl": "Outgoing: supply air leaving the unit to your rooms (after heat exchanger).",
                "outside_expl": "Outside: optional ambient outdoor reference sensor.",
                "exhaust_expl": "Exhaust: extract air from rooms entering the unit (before heat exchanger).",
            },
        )

    def _create_or_update_entry(self):
        data = self._finalize_data()
        data.pop(CONF_NAME, None)
        return self.async_create_entry(title="", data=data)
