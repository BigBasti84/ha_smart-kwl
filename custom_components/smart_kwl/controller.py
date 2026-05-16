"""Runtime controller for Smart KWL."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, State
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AWAY_ENABLED,
    CONF_AWAY_FAN_LEVEL,
    CONF_AWAY_SENSOR,
    CONF_CHECK_INTERVAL,
    CONF_CO2_CONFIGS,
    CONF_DEFAULT_FAN_LEVEL,
    CONF_FAN_ENTITY,
    CONF_FILTER_LIFETIME_ENTITY,
    CONF_HUMIDITY_CONFIGS,
    CONF_MAX_FAN_LEVEL,
    CONF_MANUAL_INCREASE_HOLD_HOURS,
    CONF_MANUAL_OVERRIDE_DEFAULT_HOURS,
    CONF_MIN_FAN_LEVEL,
    CONF_NIGHT_ENABLED,
    CONF_NIGHT_END,
    CONF_NIGHT_MAX_FAN_LEVEL,
    CONF_NIGHT_START,
    CONF_NIGHT_SUMMER_FAN_LEVEL,
    CONF_SENSOR_ENTITY_ID,
    CONF_SENSOR_MAX,
    CONF_SENSOR_MIN,
    CONF_SUMMER_MODE_SENSOR,
    DEFAULT_FILTER_LIFETIME_ENTITY,
    DEFAULT_MANUAL_INCREASE_HOLD_HOURS,
    DEFAULT_MANUAL_OVERRIDE_DEFAULT_HOURS,
    FILTER_CLEAN_INTERVAL_DAYS,
    FILTER_LIFETIME_WARN_DAYS,
    FILTER_WARN_DAYS,
)
from .filter_store import FilterStore
from .override_store import OverrideStore

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ControlDecision:
    """Computed ventilation target."""

    level: int
    percentage: int
    reason: str


@dataclass(slots=True)
class ControlEvaluation:
    """Full control evaluation with details for diagnostics."""

    decision: ControlDecision
    detail_lines: list[str]


class SmartKwlController:
    """Evaluate configured sensors and drive the target fan entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsub_state: CALLBACK_TYPE | None = None
        self._unsub_interval: CALLBACK_TYPE | None = None
        self._unsub_post_start_check: CALLBACK_TYPE | None = None
        self._last_apply: datetime | None = None
        self._last_level: int | None = None
        self._last_commanded_level: int | None = None
        self._listeners: list[Callable[[], None]] = []
        self._warned_unavailable: set[str] = set()
        self._warned_invalid: set[str] = set()
        self._filter_store: FilterStore | None = None
        self._override_store: OverrideStore | None = None
        self._external_increase_hold_until: datetime | None = None
        self._external_increase_level: int | None = None
        self._external_decrease_level: int | None = None
        self._external_decrease_reference_auto_level: int | None = None
        self._last_fan_change_hardware: bool = False
        self._manual_override_until: datetime | None = None
        self._manual_override_level: int | None = None
        self._pending_manual_override_level: int = int(self._config(CONF_DEFAULT_FAN_LEVEL, 2))
        self._pending_manual_override_hours: int = int(
            self._config(CONF_MANUAL_OVERRIDE_DEFAULT_HOURS, DEFAULT_MANUAL_OVERRIDE_DEFAULT_HOURS)
        )
        self._status: dict[str, Any] = {
            "last_reason": "init",
            "target_level": None,
            "target_percentage": None,
            "humidity_combined": None,
            "humidity_low": None,
            "humidity_high": None,
            "co2_combined": None,
            "co2_low": None,
            "co2_high": None,
            "summer_mode_active": False,
            "night_mode_active": False,
            "last_apply_success": None,
            "last_error": None,
            "last_apply": None,
            "last_action_line": "",
            "last_check_lines": [],
            "check_history": [],
            "change_history": [],
            "manual_override_active": False,
            "manual_override_level": None,
            "manual_override_until": None,
            "manual_override_pending_level": self._pending_manual_override_level,
            "manual_override_pending_hours": self._pending_manual_override_hours,
            "external_manual_hold": "none",
            "filter_last_cleaned": None,
            "filter_lifetime_entity": None,
            "filter_months_remaining": None,
            "filter_days_since_cleaning": None,
            "filter_days_remaining_life": None,
            "filter_cleaning_status": "unknown",
            "filter_lifetime_status": "ok",
        }

    async def async_start(self) -> None:
        """Start tracking configured entities and periodic checks."""
        min_level, max_level = self.level_bounds()
        self._pending_manual_override_level = max(min_level, min(max_level, self._pending_manual_override_level))
        self._pending_manual_override_hours = max(1, min(24, self._pending_manual_override_hours))
        self._status["manual_override_pending_level"] = self._pending_manual_override_level
        self._status["manual_override_pending_hours"] = self._pending_manual_override_hours

        self._filter_store = FilterStore(self.hass, self.entry.entry_id)
        await self._filter_store.async_load()
        self._update_filter_status()

        self._override_store = OverrideStore(self.hass, self.entry.entry_id)
        await self._override_store.async_load()
        # Restore a previously active timed override if it has not yet expired.
        saved_level = self._override_store.override_level
        saved_until = self._override_store.override_until
        if saved_level is not None and saved_until is not None:
            try:
                restored_until = datetime.fromisoformat(saved_until)
                # Make timezone-aware if necessary for comparison with utcnow().
                if restored_until.tzinfo is None:
                    restored_until = dt_util.as_utc(restored_until)
                if restored_until > dt_util.utcnow():
                    self._manual_override_level = saved_level
                    self._manual_override_until = restored_until
                    self._status["manual_override_active"] = True
                    self._status["manual_override_level"] = saved_level
                    self._status["manual_override_until"] = restored_until.isoformat()
                    _LOGGER.info(
                        "Smart KWL: restored manual override level=%s until=%s",
                        saved_level,
                        restored_until.isoformat(),
                    )
                else:
                    # Override expired while HA was offline — clear storage.
                    await self._override_store.async_clear_override()
            except (ValueError, TypeError):
                await self._override_store.async_clear_override()

        entities = [self._config(CONF_FAN_ENTITY)]
        entities.extend(self._sensor_entities(CONF_HUMIDITY_CONFIGS))
        entities.extend(self._sensor_entities(CONF_CO2_CONFIGS))

        away_sensor = self._config(CONF_AWAY_SENSOR)
        if away_sensor:
            entities.append(away_sensor)

        summer_mode_sensor = self._config(CONF_SUMMER_MODE_SENSOR)
        if summer_mode_sensor:
            entities.append(summer_mode_sensor)

        lifetime_entity = self._config(CONF_FILTER_LIFETIME_ENTITY, DEFAULT_FILTER_LIFETIME_ENTITY)
        if lifetime_entity:
            entities.append(lifetime_entity)

        interval = timedelta(seconds=int(self._config(CONF_CHECK_INTERVAL, 60)))
        self._unsub_state = async_track_state_change_event(self.hass, entities, self._async_handle_state_event)
        self._unsub_interval = async_track_time_interval(self.hass, self._async_handle_interval_event, interval)

        await self._async_recalculate(force=True)

        # Run a second verification shortly after startup/reload to catch
        # late-restored entity states and enforce target speed if needed.
        if self._unsub_post_start_check is not None:
            self._unsub_post_start_check()
        self._unsub_post_start_check = async_call_later(self.hass, 20, self._async_post_start_check)

    async def async_stop(self) -> None:
        """Stop tracking configured entities."""
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
        if self._unsub_post_start_check is not None:
            self._unsub_post_start_check()
            self._unsub_post_start_check = None

    def _async_post_start_check(self, _now) -> None:
        """Re-run enforcement check shortly after startup/reload."""
        self._unsub_post_start_check = None
        self.hass.async_create_task(self._async_recalculate(force=True))

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for state updates used by info entities."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @property
    def status(self) -> dict[str, Any]:
        """Return controller status for entity diagnostics."""
        return dict(self._status)

    def fan_state(self) -> State | None:
        """Return current fan state."""
        return self._state(self._config(CONF_FAN_ENTITY))

    def level_bounds(self) -> tuple[int, int]:
        """Return configured minimum and maximum fan levels."""
        return (int(self._config(CONF_MIN_FAN_LEVEL, 1)), int(self._config(CONF_MAX_FAN_LEVEL, 8)))

    def current_percentage(self) -> int | None:
        """Return current effective fan percentage for diagnostics and entities."""
        fan_entity = self._config(CONF_FAN_ENTITY)
        return self._fan_percentage(fan_entity)

    def current_level(self) -> int | None:
        """Return current effective fan level."""
        _, max_level = self.level_bounds()
        return self._percentage_to_level(self.current_percentage(), max_level)

    def pending_manual_override_level(self) -> int:
        """Return configured pending manual override level."""
        return self._pending_manual_override_level

    def pending_manual_override_hours(self) -> int:
        """Return configured pending manual override duration in hours."""
        return self._pending_manual_override_hours

    def set_pending_manual_override_level(self, level: int) -> None:
        """Update pending manual override level for dashboard control."""
        min_level, max_level = self.level_bounds()
        self._pending_manual_override_level = max(min_level, min(max_level, int(level)))
        self._status["manual_override_pending_level"] = self._pending_manual_override_level
        self._notify()

    def set_pending_manual_override_hours(self, hours: int) -> None:
        """Update pending manual override duration in hours."""
        self._pending_manual_override_hours = max(1, min(24, int(hours)))
        self._status["manual_override_pending_hours"] = self._pending_manual_override_hours
        self._notify()

    async def async_apply_manual_override(self) -> bool:
        """Activate a fixed manual fan level for the configured duration."""
        if self._status.get("manual_override_active"):
            return False

        min_level, max_level = self.level_bounds()
        level = max(min_level, min(max_level, int(self._pending_manual_override_level)))
        hours = max(1, min(24, int(self._pending_manual_override_hours)))
        now = dt_util.utcnow()

        self._manual_override_level = level
        self._manual_override_until = now + timedelta(hours=hours)
        self._status["manual_override_active"] = True
        self._status["manual_override_level"] = level
        self._status["manual_override_until"] = self._manual_override_until.isoformat()

        # Persist so the override survives HA restarts.
        if self._override_store is not None:
            await self._override_store.async_save_override(level, self._manual_override_until.isoformat())

        # Manual override supersedes temporary external holds.
        self._external_increase_hold_until = None
        self._external_increase_level = None
        self._external_decrease_level = None
        self._external_decrease_reference_auto_level = None
        self._status["external_manual_hold"] = "none"

        decision = ControlDecision(
            level=level,
            percentage=self._level_to_percentage(level, max_level),
            reason="manual_override",
        )

        fan_entity = self._config(CONF_FAN_ENTITY)
        before_percentage = self._fan_percentage(fan_entity)
        before_level = self._percentage_to_level(before_percentage, max_level)

        # Pre-set guard so concurrent recalculates during the internal sleep
        # do not misclassify this controller write as a hardware change.
        self._last_commanded_level = level
        self._last_apply = now

        success = await self._apply_fan_level_with_verification(decision)
        after_percentage = self._fan_percentage(fan_entity)
        after_level = self._percentage_to_level(after_percentage, max_level)

        self._status["target_level"] = level
        self._status["target_percentage"] = decision.percentage
        self._status["last_reason"] = "manual_override"
        self._status["last_apply_success"] = success
        self._status["last_apply"] = now.isoformat()
        if success:
            self._last_level = after_level if after_level is not None else level
            self._last_commanded_level = self._last_level
            self._status["last_error"] = None
            self._append_check_run(
                [
                    "manual_override | target_level=%s | duration_hours=%s" % (level, hours),
                    "manual_override | active_until=%s" % self._manual_override_until.isoformat(),
                ],
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    "manual_override",
                    "applied",
                ),
            )
        else:
            self._status["last_error"] = "failed_to_verify_fan_speed"
            self._append_check_run(
                ["manual_override | target_level=%s | duration_hours=%s" % (level, hours)],
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    "manual_override",
                    "verification_failed",
                ),
            )

        self._notify()
        return success

    async def async_cancel_manual_override(self) -> None:
        """Cancel manual override and resume automatic control immediately."""
        if not self._status.get("manual_override_active"):
            return

        self._manual_override_until = None
        self._manual_override_level = None
        self._status["manual_override_active"] = False
        self._status["manual_override_level"] = None
        self._status["manual_override_until"] = None

        # Clear persisted override.
        if self._override_store is not None:
            await self._override_store.async_clear_override()

        # Also clear external hardware-manual hold so cancel fully returns
        # control to automation logic.
        self._external_increase_hold_until = None
        self._external_increase_level = None
        self._external_decrease_level = None
        self._external_decrease_reference_auto_level = None
        self._status["external_manual_hold"] = "none"

        self._append_check_run(
            ["manual_override | cancelled=yes", "manual_external | cancelled=yes"],
            self._action_line(
                self.current_level(),
                self.current_percentage(),
                self.current_level(),
                self.current_percentage(),
                "manual_override_cancel",
                "cancelled",
            ),
        )

        await self._async_recalculate(force=True)
        self._notify()

    async def async_mark_filters_cleaned(self) -> None:
        """Record that filters have been cleaned right now."""
        if self._filter_store is not None:
            await self._filter_store.async_mark_cleaned()
            self._update_filter_status()
            self._notify_listeners()

    def _update_filter_status(self) -> None:
        """Recompute filter status from store data into _status dict."""
        if self._filter_store is None:
            return
        now = datetime.now()
        last_cleaned_str = self._filter_store.last_cleaned
        lifetime_entity = self._config(CONF_FILTER_LIFETIME_ENTITY, DEFAULT_FILTER_LIFETIME_ENTITY)

        # Days since last cleaning
        if last_cleaned_str:
            days_since = (now - datetime.fromisoformat(last_cleaned_str)).days
        else:
            days_since = None

        # Remaining lifetime from service-counter sensor (value in months remaining).
        months_remaining: float | None = None
        days_remaining: int | None = None
        if lifetime_entity:
            lifetime_state = self._state(lifetime_entity)
            if lifetime_state is not None:
                parsed_months = self._float_state(lifetime_state)
                if parsed_months is not None:
                    months_remaining = max(0.0, parsed_months)
                    days_remaining = int(round(months_remaining * 30))

        # Cleaning status
        if days_since is None:
            cleaning_status = "unknown"
        elif days_since >= FILTER_CLEAN_INTERVAL_DAYS:
            cleaning_status = "overdue"
        elif days_since >= FILTER_WARN_DAYS:
            cleaning_status = "due_soon"
        else:
            cleaning_status = "ok"

        # Lifetime status
        if days_remaining is None:
            lifetime_status = "unknown"
        elif days_remaining <= FILTER_LIFETIME_WARN_DAYS:
            lifetime_status = "replace_soon"
        else:
            lifetime_status = "ok"

        formatted_last_cleaned = None
        if last_cleaned_str:
            try:
                formatted_last_cleaned = datetime.fromisoformat(last_cleaned_str).strftime("%d-%m-%Y")
            except ValueError:
                formatted_last_cleaned = last_cleaned_str

        self._status["filter_last_cleaned"] = formatted_last_cleaned
        self._status["filter_lifetime_entity"] = lifetime_entity
        self._status["filter_months_remaining"] = months_remaining
        self._status["filter_days_since_cleaning"] = days_since
        self._status["filter_days_remaining_life"] = days_remaining
        self._status["filter_cleaning_status"] = cleaning_status
        self._status["filter_lifetime_status"] = lifetime_status

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # noqa: BLE001
                pass

    async def async_set_manual_level(self, level: int) -> bool:
        """Set fan to a specific level immediately and record diagnostics."""
        min_level, max_level = self.level_bounds()
        target_level = max(min_level, min(max_level, int(level)))
        decision = ControlDecision(
            level=target_level,
            percentage=self._level_to_percentage(target_level, max_level),
            reason="manual",
        )

        fan_entity = self._config(CONF_FAN_ENTITY)
        before_percentage = self._fan_percentage(fan_entity)
        before_level = self._percentage_to_level(before_percentage, max_level)

        # Pre-set guard before the await.
        self._last_commanded_level = target_level
        self._last_apply = dt_util.utcnow()

        success = await self._apply_fan_level_with_verification(decision)

        after_percentage = self._fan_percentage(fan_entity)
        after_level = self._percentage_to_level(after_percentage, max_level)
        self._status["target_level"] = target_level
        self._status["target_percentage"] = decision.percentage
        self._status["last_reason"] = "manual"
        self._status["last_apply_success"] = success
        self._status["last_apply"] = dt_util.utcnow().isoformat()
        if success:
            self._last_level = after_level if after_level is not None else target_level
            self._last_commanded_level = self._last_level
            self._status["last_error"] = None
            self._append_check_run(
                ["manual_set | target_level=%s | target_percentage=%s" % (target_level, decision.percentage)],
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    "manual",
                    "applied",
                ),
            )
        else:
            self._status["last_error"] = "failed_to_verify_fan_speed"
            self._append_check_run(
                ["manual_set | target_level=%s | target_percentage=%s" % (target_level, decision.percentage)],
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    "manual",
                    "verification_failed",
                ),
            )

        self._notify()
        return success

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _handle_external_manual_change(
        self,
        observed_level: int | None,
        auto_level: int,
        now: datetime,
        detail_lines: list[str],
    ) -> None:
        """Detect fan speed changes not initiated by this controller."""
        if observed_level is None:
            return
        if self._last_level is None:
            self._last_level = observed_level
            return
        if observed_level == self._last_level:
            return

        if not self._last_fan_change_hardware:
            self._last_level = observed_level
            detail_lines.append(
                "manual_external | ignored=non_hardware_origin | observed_level=%s"
                % observed_level
            )
            return

        # Ignore controller-applied changes: either within the 15 s write window,
        # or if the observed level matches the last commanded level (catches the
        # race where the state event fires during the internal sleep in
        # _apply_fan_level_with_verification before _last_apply is finalised).
        if self._last_commanded_level is not None and observed_level == self._last_commanded_level:
            self._last_level = observed_level
            detail_lines.append(
                "manual_external | ignored=matches_commanded_level | observed_level=%s"
                % observed_level
            )
            return
        if (
            self._last_apply is not None
            and self._last_commanded_level is not None
            and now - self._last_apply <= timedelta(seconds=30)
        ):
            self._last_level = observed_level
            detail_lines.append(
                "manual_external | ignored=controller_applied_window | observed_level=%s"
                % observed_level
            )
            return

        previous_level = self._last_level

        if observed_level > self._last_level:
            hold_hours = int(self._config(CONF_MANUAL_INCREASE_HOLD_HOURS, DEFAULT_MANUAL_INCREASE_HOLD_HOURS))
            self._external_increase_level = observed_level
            self._external_increase_hold_until = now + timedelta(hours=hold_hours)
            self._external_decrease_level = None
            self._external_decrease_reference_auto_level = None
            self._status["external_manual_hold"] = "increase"
            detail_lines.append(
                "manual_external | type=increase | observed_level=%s | hold_until=%s"
                % (observed_level, self._external_increase_hold_until.isoformat())
            )
            self._append_change_history_event(
                now.isoformat(),
                previous_level,
                observed_level,
                "manual_hardware_increase",
                "observed",
            )
        else:
            self._external_decrease_level = observed_level
            self._external_decrease_reference_auto_level = auto_level
            self._external_increase_level = None
            self._external_increase_hold_until = None
            self._status["external_manual_hold"] = "decrease"
            detail_lines.append(
                "manual_external | type=decrease | observed_level=%s | base_auto_level=%s"
                % (observed_level, auto_level)
            )
            self._append_change_history_event(
                now.isoformat(),
                previous_level,
                observed_level,
                "manual_hardware_decrease",
                "observed",
            )

        self._last_level = observed_level

    def _apply_manual_constraints(
        self,
        decision: ControlDecision,
        now: datetime,
        detail_lines: list[str],
    ) -> ControlDecision:
        """Apply manual override and external hold rules to automation decision."""
        min_level, max_level = self.level_bounds()
        target_level = decision.level
        reason = decision.reason

        # Explicit dashboard manual override fixes speed for duration.
        if self._manual_override_until is not None and self._manual_override_level is not None:
            if now < self._manual_override_until:
                target_level = max(min_level, min(max_level, self._manual_override_level))
                reason = "manual_override"
                self._status["manual_override_active"] = True
                self._status["manual_override_level"] = target_level
                self._status["manual_override_until"] = self._manual_override_until.isoformat()
                detail_lines.append(
                    "manual_override | active=yes | level=%s | until=%s"
                    % (target_level, self._manual_override_until.isoformat())
                )
                return ControlDecision(
                    level=target_level,
                    percentage=self._level_to_percentage(target_level, max_level),
                    reason=reason,
                )

            self._manual_override_until = None
            self._manual_override_level = None
            self._status["manual_override_active"] = False
            self._status["manual_override_level"] = None
            self._status["manual_override_until"] = None
            detail_lines.append("manual_override | active=no | reason=expired")
            if self._override_store is not None:
                self.hass.async_create_task(self._override_store.async_clear_override())

        self._status["manual_override_active"] = False
        self._status["manual_override_level"] = None
        self._status["manual_override_until"] = None

        # External manual increase: keep at least this level for configured hold duration.
        if self._external_increase_hold_until is not None and self._external_increase_level is not None:
            if now < self._external_increase_hold_until:
                if target_level < self._external_increase_level:
                    target_level = self._external_increase_level
                    reason = "manual_external_increase_hold"
                    detail_lines.append(
                        "manual_hold | type=increase | enforced_level=%s | until=%s"
                        % (target_level, self._external_increase_hold_until.isoformat())
                    )
                else:
                    # Event-driven increase beyond manual level is allowed immediately.
                    self._external_increase_hold_until = None
                    self._external_increase_level = None
                    self._status["external_manual_hold"] = "none"
                    detail_lines.append("manual_hold | type=increase | released=auto_higher")
            else:
                self._external_increase_hold_until = None
                self._external_increase_level = None
                self._status["external_manual_hold"] = "none"
                detail_lines.append("manual_hold | type=increase | released=expired")

        # External manual decrease: keep reduced level until automation decision changes.
        if self._external_decrease_level is not None:
            if self._external_decrease_reference_auto_level is None:
                self._external_decrease_reference_auto_level = target_level

            if target_level == self._external_decrease_reference_auto_level:
                if target_level > self._external_decrease_level:
                    target_level = self._external_decrease_level
                    reason = "manual_external_decrease_hold"
                    detail_lines.append(
                        "manual_hold | type=decrease | enforced_level=%s | waiting_for_new_event=yes"
                        % target_level
                    )
            else:
                self._external_decrease_level = None
                self._external_decrease_reference_auto_level = None
                self._status["external_manual_hold"] = "none"
                detail_lines.append("manual_hold | type=decrease | released=new_event")

        if self._external_increase_level is not None and self._external_increase_hold_until is not None:
            self._status["external_manual_hold"] = "increase"
        elif self._external_decrease_level is not None:
            self._status["external_manual_hold"] = "decrease"
        else:
            self._status["external_manual_hold"] = "none"

        return ControlDecision(
            level=max(min_level, min(max_level, target_level)),
            percentage=self._level_to_percentage(max(min_level, min(max_level, target_level)), max_level),
            reason=reason,
        )

    def _sensor_entities(self, key: str) -> list[str]:
        configs: list[dict[str, Any]] = self._config(key, [])
        return [cfg.get(CONF_SENSOR_ENTITY_ID) for cfg in configs if cfg.get(CONF_SENSOR_ENTITY_ID)]

    def _config(self, key: str, default: Any = None) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key, default))

    def _schedule_recalculate(self, force: bool) -> None:
        """Schedule recalculation on the Home Assistant event loop."""

        def _run() -> None:
            self.hass.async_create_task(self._async_recalculate(force=force))

        self.hass.loop.call_soon_threadsafe(_run)

    def _async_handle_state_event(self, event) -> None:
        fan_entity = self._config(CONF_FAN_ENTITY)
        if fan_entity and event.data.get("entity_id") == fan_entity:
            new_state = event.data.get("new_state")
            if new_state is not None:
                context = new_state.context
                self._last_fan_change_hardware = (
                    context is not None and context.user_id is None and context.parent_id is None
                )

        # State changes only queue recalculation; min interval applies writes.
        self._schedule_recalculate(force=False)

    async def _async_handle_interval_event(self, now) -> None:
        await self._async_recalculate(force=False)

    async def _async_recalculate(self, force: bool) -> None:
        evaluation = self._compute_target()
        if evaluation is None:
            return

        decision = evaluation.decision
        fan_entity = self._config(CONF_FAN_ENTITY)
        before_percentage = self._fan_percentage(fan_entity)
        before_level = self._percentage_to_level(before_percentage, int(self._config(CONF_MAX_FAN_LEVEL, 8)))

        now = dt_util.utcnow()
        self._handle_external_manual_change(before_level, decision.level, now, evaluation.detail_lines)
        decision = self._apply_manual_constraints(decision, now, evaluation.detail_lines)

        self._status["target_level"] = decision.level
        self._status["target_percentage"] = decision.percentage
        self._status["last_reason"] = decision.reason

        # Compare computed target with currently observed fan level.
        actual_matches_target = before_level is not None and before_level == decision.level
        if not actual_matches_target:
            evaluation.detail_lines.append(
                "sync_check | expected_level=%s | observed_level=%s | action=force_apply"
                % (decision.level, self._fmt_level(before_level))
            )

        interval = timedelta(seconds=int(self._config(CONF_CHECK_INTERVAL, 60)))
        if (
            not force
            and actual_matches_target
            and self._last_apply is not None
            and now - self._last_apply < interval
        ):
            after_percentage = self._fan_percentage(fan_entity)
            after_level = self._percentage_to_level(after_percentage, int(self._config(CONF_MAX_FAN_LEVEL, 8)))
            self._append_check_run(
                evaluation.detail_lines,
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    decision.reason,
                    "skipped_interval",
                ),
            )
            self._notify()
            return

        if self._last_level == decision.level and actual_matches_target and not force:
            after_percentage = self._fan_percentage(fan_entity)
            after_level = self._percentage_to_level(after_percentage, int(self._config(CONF_MAX_FAN_LEVEL, 8)))
            self._append_check_run(
                evaluation.detail_lines,
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    decision.reason,
                    "unchanged",
                ),
            )
            self._notify()
            return

        # Set guard fields BEFORE the await so concurrent recalculates triggered
        # by the fan state-change event (which fires during the internal sleep)
        # will see the correct commanded level and skip false hardware detection.
        self._last_commanded_level = decision.level
        self._last_apply = now

        success = await self._apply_fan_level_with_verification(decision)
        after_percentage = self._fan_percentage(fan_entity)
        after_level = self._percentage_to_level(after_percentage, int(self._config(CONF_MAX_FAN_LEVEL, 8)))
        self._status["last_apply_success"] = success
        self._status["last_apply"] = now.isoformat()
        if success:
            self._last_level = after_level if after_level is not None else decision.level
            self._last_commanded_level = self._last_level
            self._status["last_error"] = None
            self._append_check_run(
                evaluation.detail_lines,
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    decision.reason,
                    "applied",
                ),
            )
        else:
            self._status["last_error"] = "failed_to_verify_fan_speed"
            self._append_check_run(
                evaluation.detail_lines,
                self._action_line(
                    before_level,
                    before_percentage,
                    after_level,
                    after_percentage,
                    decision.reason,
                    "verification_failed",
                ),
            )
        self._notify()

    def _compute_target(self) -> ControlEvaluation | None:
        min_level = int(self._config(CONF_MIN_FAN_LEVEL, 1))
        max_level = int(self._config(CONF_MAX_FAN_LEVEL, 8))
        default_level = int(self._config(CONF_DEFAULT_FAN_LEVEL, min_level))

        if min_level > max_level:
            return None

        away_level = int(self._config(CONF_AWAY_FAN_LEVEL, min_level))
        away_enabled = bool(self._config(CONF_AWAY_ENABLED, False))
        away_sensor = self._state(self._config(CONF_AWAY_SENSOR)) if away_enabled else None
        away_active = away_enabled and away_sensor is not None and away_sensor.state == STATE_ON

        base_level = away_level if away_active else default_level
        base_level = max(min_level, min(max_level, base_level))

        detail_lines: list[str] = []
        humidity_ratio, humidity_lines, humidity_current, humidity_low, humidity_high = self._evaluate_sensor_group(
            "humidity", self._config(CONF_HUMIDITY_CONFIGS, [])
        )
        co2_ratio, co2_lines, co2_current, co2_low, co2_high = self._evaluate_sensor_group(
            "co2", self._config(CONF_CO2_CONFIGS, [])
        )
        detail_lines.extend(humidity_lines)
        detail_lines.extend(co2_lines)

        self._status["humidity_combined"] = humidity_current
        self._status["humidity_low"] = humidity_low
        self._status["humidity_high"] = humidity_high
        self._status["co2_combined"] = co2_current
        self._status["co2_low"] = co2_low
        self._status["co2_high"] = co2_high

        demand_ratio = max(humidity_ratio, co2_ratio)

        sensor_reason = "idle"
        if humidity_ratio >= co2_ratio and humidity_ratio > 0:
            sensor_reason = "humidity"
        elif co2_ratio > 0:
            sensor_reason = "co2"

        target_level = base_level + int(round(demand_ratio * (max_level - base_level)))
        target_level = max(min_level, min(max_level, target_level))
        reason = f"{sensor_reason}_base_{'away' if away_active else 'default'}"
        detail_lines.append(
            "summary | base_level=%s | humidity_ratio=%.2f | co2_ratio=%.2f | demand_ratio=%.2f | pre_night_level=%s"
            % (base_level, humidity_ratio, co2_ratio, demand_ratio, target_level)
        )

        summer_sensor_entity = self._config(CONF_SUMMER_MODE_SENSOR)
        summer_state = self._state(summer_sensor_entity)
        summer_active = summer_state is not None and summer_state.state == STATE_ON
        self._status["summer_mode_active"] = summer_active
        detail_lines.append(
            "summer_check | sensor=%s | active=%s"
            % (summer_sensor_entity or "none", "yes" if summer_active else "no")
        )

        night_active = self._is_night_active()
        self._status["night_mode_active"] = night_active
        if night_active:
            night_target = default_level
            if summer_active:
                night_target = int(self._config(CONF_NIGHT_SUMMER_FAN_LEVEL, default_level))
                reason = "night_summer"
                detail_lines.append("night_check | active=yes | summer_mode=on")
            else:
                reason = "night"
                detail_lines.append("night_check | active=yes | summer_mode=off")

            night_max = int(self._config(CONF_NIGHT_MAX_FAN_LEVEL, max_level))
            night_max = max(min_level, min(max_level, night_max))
            night_target = max(min_level, min(night_max, night_target))
            target_level = night_target
            detail_lines.append("night_result | target_level=%s | night_max=%s" % (target_level, night_max))
        else:
            detail_lines.append("night_check | active=no")

        target_percentage = self._level_to_percentage(target_level, max_level)
        detail_lines.append("target | level=%s | percentage=%s | reason=%s" % (target_level, target_percentage, reason))
        return ControlEvaluation(
            decision=ControlDecision(level=target_level, percentage=target_percentage, reason=reason),
            detail_lines=detail_lines,
        )

    def _is_night_active(self) -> bool:
        if not self._config(CONF_NIGHT_ENABLED, False):
            return False

        start = self._parse_time(self._config(CONF_NIGHT_START, "22:00:00"))
        end = self._parse_time(self._config(CONF_NIGHT_END, "06:00:00"))
        now = dt_util.now().time()

        if start <= end:
            return start <= now < end
        return now >= start or now < end

    @staticmethod
    def _parse_time(value: Any) -> time:
        if isinstance(value, time):
            return value
        parsed = time.fromisoformat(str(value))
        return parsed

    def _evaluate_sensor_group(
        self,
        kind: str,
        configs: list[dict[str, Any]],
    ) -> tuple[float, list[str], float | None, float | None, float | None]:
        ratio = 0.0
        lines: list[str] = []
        combined_value: float | None = None
        combined_low: float | None = None
        combined_high: float | None = None

        for cfg in configs:
            entity_id = cfg.get(CONF_SENSOR_ENTITY_ID)
            if not entity_id:
                continue

            min_v = float(cfg.get(CONF_SENSOR_MIN, 0.0))
            max_v = float(cfg.get(CONF_SENSOR_MAX, 100.0))
            state = self._state(entity_id)
            if state is None:
                lines.append(
                    "%s_check | sensor=%s | min=%.2f | max=%.2f | measured=unavailable | result=skipped"
                    % (kind, entity_id, min_v, max_v)
                )
                continue

            value = self._float_state(state)
            if value is None:
                self._warn_invalid_once(entity_id, f"Entity {entity_id} has non-numeric state '{state.state}'. Falling back to ignore this sensor until valid.")
                lines.append(
                    "%s_check | sensor=%s | min=%.2f | max=%.2f | measured=%s | result=invalid"
                    % (kind, entity_id, min_v, max_v, state.state)
                )
                continue

            sensor_ratio = self._scale_to_unit(value, min_v, max_v)
            ratio = max(ratio, sensor_ratio)
            if combined_value is None or sensor_ratio >= ratio:
                combined_value = value
                combined_low = min_v
                combined_high = max_v
            lines.append(
                "%s_check | sensor=%s | min=%.2f | max=%.2f | measured=%.2f | result=%.2f"
                % (kind, entity_id, min_v, max_v, value, sensor_ratio)
            )

        if not lines:
            lines.append("%s_check | sensor=none | result=not_configured" % kind)

        lines.append("%s_check | group_worst_result=%.2f" % (kind, ratio))
        return ratio, lines, combined_value, combined_low, combined_high

    async def _apply_fan_level_with_verification(self, decision: ControlDecision) -> bool:
        fan_entity = self._config(CONF_FAN_ENTITY)
        if not fan_entity:
            _LOGGER.warning("No target entity configured. Cannot apply fan level.")
            return False

        # Try once and retry once if verification fails.
        for attempt in (1, 2):
            try:
                if fan_entity.startswith("fan."):
                    await self.hass.services.async_call(
                        "fan",
                        "set_percentage",
                        {"entity_id": fan_entity, "percentage": decision.percentage},
                        blocking=True,
                    )
                elif fan_entity.startswith("climate."):
                    await self.hass.services.async_call(
                        "climate",
                        "set_fan_mode",
                        {"entity_id": fan_entity, "fan_mode": str(decision.level)},
                        blocking=True,
                    )
                else:
                    _LOGGER.warning("Unsupported target entity domain for %s", fan_entity)
                    return False
            except Exception as err:  # pragma: no cover - defensive runtime fallback
                _LOGGER.warning("Failed to call service for %s: %s", fan_entity, err)
                continue

            await asyncio.sleep(1)

            actual_percentage = self._fan_percentage(fan_entity)
            if actual_percentage is not None and abs(actual_percentage - decision.percentage) <= 5:
                return True

            _LOGGER.warning(
                "Fan percentage verification failed on attempt %s for %s. Expected=%s, actual=%s",
                attempt,
                fan_entity,
                decision.percentage,
                actual_percentage,
            )

        return False

    def _fan_percentage(self, fan_entity: str) -> int | None:
        fan_state = self.hass.states.get(fan_entity)
        if fan_state is None:
            self._warn_unavailable_once(fan_entity, f"Target entity {fan_entity} is unavailable. Falling back until it returns.")
            return None
        self._clear_unavailable_warning(fan_entity)

        if fan_state.state == STATE_OFF:
            return 0

        _, max_level = self.level_bounds()

        if fan_entity.startswith("climate."):
            raw_mode = fan_state.attributes.get("fan_mode")
            try:
                level = int(raw_mode)
            except (TypeError, ValueError):
                self._warn_invalid_once(
                    fan_entity,
                    f"Climate entity {fan_entity} has invalid fan_mode '{raw_mode}'. Falling back until valid.",
                )
                return None
            self._clear_invalid_warning(fan_entity)
            return self._level_to_percentage(level, max_level)

        raw_percentage = fan_state.attributes.get("percentage")
        if raw_percentage is None:
            self._warn_invalid_once(
                fan_entity,
                f"Fan entity {fan_entity} has no percentage attribute. Falling back until available.",
            )
            return None

        try:
            percentage = int(raw_percentage)
            self._clear_invalid_warning(fan_entity)
            return percentage
        except (TypeError, ValueError):
            self._warn_invalid_once(
                fan_entity,
                f"Fan entity {fan_entity} has invalid percentage '{raw_percentage}'. Falling back until valid.",
            )
            return None

    def _append_check_run(self, detail_lines: list[str], action_line: str) -> None:
        timestamp = dt_util.now().isoformat()
        lines = [f"check_run | at={timestamp}"] + detail_lines + [action_line]
        history: list[list[str]] = list(self._status.get("check_history", []))
        history.insert(0, lines)
        self._status["check_history"] = history[:10]
        self._status["last_check_lines"] = lines
        self._status["last_action_line"] = action_line

        change = self._parse_action_change(timestamp, action_line)
        if change is not None:
            self._append_change_history_event(
                change["at"],
                int(change["before_level"]),
                int(change["after_level"]),
                change["reason"],
                change["status"],
            )

    def _append_change_history_event(
        self,
        timestamp: str,
        before_level: int,
        after_level: int,
        reason: str,
        status: str,
    ) -> None:
        """Append a normalized level-change event for dashboard history cards."""
        change_history: list[dict[str, str]] = list(self._status.get("change_history", []))
        change_history.insert(
            0,
            {
                "at": timestamp,
                "before_level": str(before_level),
                "after_level": str(after_level),
                "reason": reason,
                "status": status,
            },
        )
        # Keep the latest 50 level-change events for dashboard display.
        self._status["change_history"] = change_history[:50]

    @staticmethod
    def _parse_action_change(timestamp: str, action_line: str) -> dict[str, str] | None:
        """Extract level-change details from an action log line."""
        if not action_line.startswith("action |"):
            return None

        def _extract(field: str) -> str | None:
            token = f"{field}="
            if token not in action_line:
                return None
            return action_line.split(token, 1)[1].split(" |", 1)[0].strip()

        before_raw = _extract("before_level")
        after_raw = _extract("after_level")
        reason = _extract("reason") or "unknown"
        status = _extract("status") or "unknown"
        if before_raw is None or after_raw is None:
            return None

        before_level = before_raw.split(" ", 1)[0]
        after_level = after_raw.split(" ", 1)[0]
        if before_level in {"n/a", "None"} or after_level in {"n/a", "None"}:
            return None
        if before_level == after_level:
            return None

        return {
            "at": timestamp,
            "before_level": before_level,
            "after_level": after_level,
            "reason": reason,
            "status": status,
        }

    @staticmethod
    def _fmt_level(level: int | None) -> str:
        return "n/a" if level is None else str(level)

    @staticmethod
    def _fmt_percentage(percentage: int | None) -> str:
        return "n/a" if percentage is None else f"{percentage}%"

    def _action_line(
        self,
        before_level: int | None,
        before_percentage: int | None,
        after_level: int | None,
        after_percentage: int | None,
        reason: str,
        status: str,
    ) -> str:
        return (
            "action | before_level=%s (%s) | after_level=%s (%s) | reason=%s | status=%s"
            % (
                self._fmt_level(before_level),
                self._fmt_percentage(before_percentage),
                self._fmt_level(after_level),
                self._fmt_percentage(after_percentage),
                reason,
                status,
            )
        )

    @staticmethod
    def _percentage_to_level(percentage: int | None, max_level: int) -> int | None:
        if percentage is None or max_level <= 0:
            return None
        return max(0, min(max_level, int(round((percentage / 100) * max_level))))

    @staticmethod
    def _level_to_percentage(level: int, max_level: int) -> int:
        if max_level <= 0:
            return 0
        return max(1, min(100, int(round((level / max_level) * 100))))

    def _state(self, entity_id: str | None) -> State | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            self._warn_unavailable_once(entity_id, f"Entity {entity_id} is missing/unavailable. Falling back until it returns.")
            return None
        if state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            self._warn_unavailable_once(entity_id, f"Entity {entity_id} state is {state.state}. Falling back until it becomes available.")
            return None
        self._clear_unavailable_warning(entity_id)
        return state

    def _warn_unavailable_once(self, entity_id: str, message: str) -> None:
        if entity_id in self._warned_unavailable:
            return
        self._warned_unavailable.add(entity_id)
        _LOGGER.warning(message)

    def _clear_unavailable_warning(self, entity_id: str) -> None:
        self._warned_unavailable.discard(entity_id)

    def _warn_invalid_once(self, entity_id: str, message: str) -> None:
        if entity_id in self._warned_invalid:
            return
        self._warned_invalid.add(entity_id)
        _LOGGER.warning(message)

    def _clear_invalid_warning(self, entity_id: str) -> None:
        self._warned_invalid.discard(entity_id)

    @staticmethod
    def _float_state(state: State) -> float | None:
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _scale_to_unit(value: float, minimum: float, maximum: float) -> float:
        if maximum <= minimum:
            return 1.0 if value >= maximum else 0.0
        if value <= minimum:
            return 0.0
        if value >= maximum:
            return 1.0
        return (value - minimum) / (maximum - minimum)
