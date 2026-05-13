"""Constants for Smart KWL."""

DOMAIN = "smart_kwl"

CONF_FAN_ENTITY = "fan_entity"
CONF_HUMIDITY_SENSORS = "humidity_sensors"
CONF_CO2_SENSORS = "co2_sensors"
CONF_HUMIDITY_CONFIGS = "humidity_configs"
CONF_CO2_CONFIGS = "co2_configs"

CONF_MIN_FAN_LEVEL = "min_fan_level"
CONF_MAX_FAN_LEVEL = "max_fan_level"
CONF_DEFAULT_FAN_LEVEL = "default_fan_level"

CONF_AWAY_ENABLED = "away_enabled"
CONF_AWAY_SENSOR = "away_sensor"
CONF_AWAY_FAN_LEVEL = "away_fan_level"

CONF_NIGHT_ENABLED = "night_enabled"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"
CONF_NIGHT_MAX_FAN_LEVEL = "night_max_fan_level"
CONF_NIGHT_SUMMER_FAN_LEVEL = "night_summer_fan_level"

CONF_SUMMER_MODE_SENSOR = "summer_mode_sensor"
CONF_CHECK_INTERVAL = "check_interval"
CONF_MANUAL_INCREASE_HOLD_HOURS = "manual_increase_hold_hours"
CONF_MANUAL_OVERRIDE_DEFAULT_HOURS = "manual_override_default_hours"

CONF_INCOMING_TEMPERATURE_ENTITY = "incoming_temperature_entity"
CONF_OUTGOING_TEMPERATURE_ENTITY = "outgoing_temperature_entity"
CONF_OUTSIDE_TEMPERATURE_ENTITY = "outside_temperature_entity"
CONF_EXHAUST_TEMPERATURE_ENTITY = "exhaust_temperature_entity"

CONF_SENSOR_ENTITY_ID = "entity_id"
CONF_SENSOR_MIN = "min"
CONF_SENSOR_MAX = "max"

DEFAULT_HUMIDITY_MIN = 45.0
DEFAULT_HUMIDITY_MAX = 60.0
DEFAULT_CO2_MIN = 700.0
DEFAULT_CO2_MAX = 900.0

DEFAULT_MIN_FAN_LEVEL = 1
DEFAULT_MAX_FAN_LEVEL = 8
DEFAULT_FAN_LEVEL = 2
DEFAULT_AWAY_ENABLED = False
DEFAULT_AWAY_FAN_LEVEL = 1

DEFAULT_NIGHT_ENABLED = False
DEFAULT_NIGHT_START = "22:00:00"
DEFAULT_NIGHT_END = "06:00:00"
DEFAULT_NIGHT_MAX_FAN_LEVEL = 5
DEFAULT_NIGHT_SUMMER_FAN_LEVEL = 4

DEFAULT_CHECK_INTERVAL = 60
DEFAULT_MANUAL_INCREASE_HOLD_HOURS = 2
DEFAULT_MANUAL_OVERRIDE_DEFAULT_HOURS = 2

# Filter maintenance
FILTER_CLEAN_INTERVAL_DAYS = 60   # warn after 1 month (30d), red after 2 months (60d)
FILTER_WARN_DAYS = 30             # yellow threshold
FILTER_LIFETIME_MONTHS = 24       # total filter lifetime in months
FILTER_LIFETIME_WARN_DAYS = 30    # warn when this many days remain before end of life
