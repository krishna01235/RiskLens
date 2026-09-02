"""
tests/unit/test_state_machine.py -- Unit tests for app/alerts/state_machine.py

All tests are pure-function checks (no DB, no Redis, no network).
Key scenarios covered:
  1. compute_state: all four bands, boundary values
  2. BREACH hysteresis: stays in BREACH until utilization drops below threshold
  3. should_fire_alert: same-state suppression, min-interval guard, first-run
  4. Adversarial: sequence hovering at breach boundary fires exactly one alert
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.alerts.state_machine import (
    AlertState,
    compute_state,
    should_fire_alert,
    utilization,
)

# Default thresholds used across tests
W = 0.60   # watch
H = 0.80   # high
B = 1.00   # breach
HYS = 0.05 # hysteresis


# ---------------------------------------------------------------------------
# 1. compute_state: four bands, exact boundaries
# ---------------------------------------------------------------------------


class TestComputeState:
    def _state(self, u: float, prev: AlertState | None = None) -> AlertState:
        return compute_state(u, W, H, B, prev_state=prev, hysteresis_pct=HYS)

    def test_safe_below_watch(self):
        assert self._state(0.0) == "SAFE"
        assert self._state(0.59) == "SAFE"

    def test_watch_at_lower_boundary(self):
        assert self._state(0.60) == "WATCH"
        assert self._state(0.79) == "WATCH"

    def test_high_at_lower_boundary(self):
        assert self._state(0.80) == "HIGH"
        assert self._state(0.99) == "HIGH"

    def test_breach_at_exactly_one(self):
        assert self._state(1.00) == "BREACH"

    def test_breach_above_one(self):
        assert self._state(1.50) == "BREACH"

    def test_zero_utilization_is_safe(self):
        assert self._state(0.0) == "SAFE"

    def test_boundary_just_below_watch(self):
        assert self._state(0.5999) == "SAFE"

    def test_boundary_just_below_high(self):
        assert self._state(0.7999) == "WATCH"

    def test_boundary_just_below_breach(self):
        assert self._state(0.9999) == "HIGH"


# ---------------------------------------------------------------------------
# 2. BREACH hysteresis
# ---------------------------------------------------------------------------


class TestBreachHysteresis:
    """Once in BREACH, utilization must drop below (B - HYS) to exit."""

    def _state(self, u: float, prev: AlertState | None) -> AlertState:
        return compute_state(u, W, H, B, prev_state=prev, hysteresis_pct=HYS)

    def test_stays_breach_just_below_threshold(self):
        # 0.99 < 1.00 (breach) but still >= 0.95 (breach - hysteresis)
        # -> must stay BREACH
        assert self._state(0.99, prev="BREACH") == "BREACH"

    def test_exits_breach_below_hysteresis_band(self):
        # 0.94 < 0.95 -> exits BREACH into HIGH
        assert self._state(0.94, prev="BREACH") == "HIGH"

    def test_exits_breach_exactly_at_band_boundary(self):
        # 0.9499 < 0.95 -> exits
        assert self._state(0.9499, prev="BREACH") == "HIGH"

    def test_no_hysteresis_applied_from_non_breach(self):
        # Coming from HIGH, normal thresholds apply
        assert self._state(0.99, prev="HIGH") == "HIGH"
        assert self._state(0.96, prev="SAFE") == "HIGH"


# ---------------------------------------------------------------------------
# 3. should_fire_alert: suppression and min-interval guard
# ---------------------------------------------------------------------------


class TestShouldFireAlert:
    _LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)
    _JUST_NOW = datetime.now(UTC) - timedelta(seconds=10)  # within 5 min

    def test_same_state_never_fires(self):
        for state in ("SAFE", "WATCH", "HIGH", "BREACH"):
            assert not should_fire_alert(state, state, self._LONG_AGO)  # type: ignore

    def test_genuine_transition_fires_when_interval_elapsed(self):
        assert should_fire_alert("SAFE", "WATCH", self._LONG_AGO)
        assert should_fire_alert("WATCH", "HIGH", self._LONG_AGO)
        assert should_fire_alert("HIGH", "BREACH", self._LONG_AGO)

    def test_min_interval_suppresses_rapid_transition(self):
        # last alert was 10s ago; min_interval is 300s -> suppress
        assert not should_fire_alert("SAFE", "WATCH", self._JUST_NOW, min_interval_s=300)

    def test_min_interval_allows_after_elapsed(self):
        long_ago = datetime.now(UTC) - timedelta(seconds=301)
        assert should_fire_alert("SAFE", "WATCH", long_ago, min_interval_s=300)

    def test_no_previous_alert_safe_to_safe_no_fire(self):
        # First run, state is SAFE: no alert
        assert not should_fire_alert(None, "SAFE", None)

    def test_no_previous_alert_first_breach_fires(self):
        assert should_fire_alert(None, "BREACH", None)

    def test_no_previous_alert_first_watch_fires(self):
        assert should_fire_alert(None, "WATCH", None)

    def test_no_last_alert_at_fires_on_transition(self):
        # prev_state set but no previous alert timestamp
        assert should_fire_alert("SAFE", "BREACH", None)

    def test_downgrade_fires_too(self):
        # Recovering from BREACH to HIGH is also a genuine transition
        assert should_fire_alert("BREACH", "HIGH", self._LONG_AGO)


# ---------------------------------------------------------------------------
# 4. Adversarial: sequence hovering at boundary fires EXACTLY ONCE
# ---------------------------------------------------------------------------


class TestAdversarialBoundaryHovering:
    """
    Simulate a portfolio whose CVaR oscillates between 99% and 101% of budget
    with no significant time gap between ticks.

    Expected behavior:
      - First crossing into BREACH: one alert
      - Subsequent ticks within hysteresis band: zero alerts (state stays BREACH)
      - Recovery below hysteresis: one alert (BREACH -> HIGH)
    """

    def test_boundary_hovering_fires_exactly_twice(self):
        """
        Tick sequence (utilization, expected state after hysteresis):
          0.99 (from SAFE) -> WATCH ... -> HIGH -> ... -> BREACH (1 alert)
          oscillate 0.99-1.01 while in BREACH -> stays BREACH (0 alerts)
          drop to 0.94 -> HIGH (1 alert = recovery)

        Total: 2 alerts (enter BREACH, exit BREACH)
        """
        ticks = [0.50, 0.65, 0.82, 1.01,  # SAFE, WATCH, HIGH, BREACH
                 0.99, 1.01, 0.99, 1.01,   # hovering in hysteresis band
                 0.94]                       # exits BREACH -> HIGH

        prev_state: AlertState | None = None
        # Fix last_alert_at to a long time ago to isolate the hysteresis logic
        last_alert_at: datetime | None = datetime(2000, 1, 1, tzinfo=UTC)
        alert_count = 0
        states: list[AlertState] = []

        for u in ticks:
            new_state = compute_state(u, W, H, B, prev_state=prev_state, hysteresis_pct=HYS)
            states.append(new_state)
            if should_fire_alert(prev_state, new_state, last_alert_at, min_interval_s=0):
                alert_count += 1
                last_alert_at = datetime.now(UTC)
            prev_state = new_state

        # Exactly: SAFE->WATCH, WATCH->HIGH, HIGH->BREACH, (hovering=0), BREACH->HIGH
        assert alert_count == 4, f"Expected 4 alerts, got {alert_count}. States: {states}"

        # Hovering ticks (indices 4-7) must ALL be BREACH
        for i in range(4, 8):
            assert states[i] == "BREACH", f"tick {i}: expected BREACH got {states[i]}"

        # Recovery tick (index 8) must be HIGH
        assert states[8] == "HIGH"

    def test_single_spike_and_recovery_fires_exactly_twice(self):
        """A clean spike up and back down produces two alerts."""
        ticks = [0.0, 1.05, 0.0]  # SAFE -> BREACH -> SAFE
        last_alert_at: datetime | None = datetime(2000, 1, 1, tzinfo=UTC)
        prev_state: AlertState | None = None
        alert_count = 0

        for u in ticks:
            new_state = compute_state(u, W, H, B, prev_state=prev_state)
            if should_fire_alert(prev_state, new_state, last_alert_at, min_interval_s=0):
                alert_count += 1
                last_alert_at = datetime.now(UTC)
            prev_state = new_state

        assert alert_count == 2  # SAFE->BREACH, BREACH->SAFE


# ---------------------------------------------------------------------------
# 5. utilization() helper
# ---------------------------------------------------------------------------


class TestUtilizationHelper:
    def test_basic(self):
        assert abs(utilization(5.0, 10.0) - 0.5) < 1e-9

    def test_zero_max_cvar_returns_zero(self):
        assert utilization(100.0, 0.0) == 0.0

    def test_exactly_one(self):
        assert abs(utilization(1000.0, 1000.0) - 1.0) < 1e-9

    def test_over_budget(self):
        assert utilization(150.0, 100.0) == 1.5
