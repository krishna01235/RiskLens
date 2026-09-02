"""alerts/state_machine.py -- SAFE/WATCH/HIGH/BREACH state machine.

Pure functions, zero I/O.  All business logic lives here so it can be
unit-tested in isolation with no database or Redis dependency.

State Definitions (utilization = cvar / max_cvar)
--------------------------------------------------
SAFE    [0.0,  watch_threshold)
WATCH   [watch_threshold, high_threshold)
HIGH    [high_threshold,  breach_threshold)
BREACH  [breach_threshold, inf)

Anti-Oscillation Guards
-----------------------
1. Same-state suppression: no alert if new_state == prev_state.
2. Minimum-interval guard: no alert if last alert was < min_interval_s ago.
3. BREACH hysteresis: once in BREACH, state only drops to HIGH when
   utilization falls below breach_threshold - hysteresis_pct.  This
   prevents boundary flapping on tick noise right at 100%.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

AlertState = Literal["SAFE", "WATCH", "HIGH", "BREACH"]

# Default anti-oscillation constants (all configurable via budget object)
_DEFAULT_MIN_INTERVAL_S: int = 300          # 5 minutes between alerts
_DEFAULT_HYSTERESIS_PCT: float = 0.05       # 5% below breach before exiting BREACH


def compute_state(
    utilization: float,
    watch_threshold: float,
    high_threshold: float,
    breach_threshold: float,
    prev_state: AlertState | None = None,
    hysteresis_pct: float = _DEFAULT_HYSTERESIS_PCT,
) -> AlertState:
    """Map a CVaR utilization ratio to an AlertState.

    Parameters
    ----------
    utilization : float
        cvar / max_cvar  (can be > 1.0 when in breach)
    watch_threshold, high_threshold, breach_threshold : float
        Budget thresholds (fractions, e.g. 0.60, 0.80, 1.00).
    prev_state : AlertState | None
        The current state.  Required for BREACH hysteresis.
    hysteresis_pct : float
        How far below breach_threshold utilization must fall before
        exiting BREACH state (prevents boundary oscillation).
    """
    if utilization >= breach_threshold:
        return "BREACH"

    # BREACH hysteresis: stay in BREACH until utilization drops below
    # (breach_threshold - hysteresis_pct).
    if prev_state == "BREACH" and utilization >= breach_threshold - hysteresis_pct:
        return "BREACH"

    if utilization >= high_threshold:
        return "HIGH"
    if utilization >= watch_threshold:
        return "WATCH"
    return "SAFE"


def should_fire_alert(
    prev_state: AlertState | None,
    new_state: AlertState,
    last_alert_at: datetime | None,
    min_interval_s: int = _DEFAULT_MIN_INTERVAL_S,
) -> bool:
    """Return True if a genuine new alert should be written and published.

    Rules (applied in order; all must be satisfied):
    1. State must have changed.
    2. Minimum interval since last alert must have elapsed.

    Parameters
    ----------
    prev_state : AlertState | None
        None means "no previous state" (first run) -> always fire if state != SAFE.
    new_state : AlertState
    last_alert_at : datetime | None
        UTC timestamp of the last alert fired for this portfolio.
    min_interval_s : int
        Minimum seconds between consecutive alerts (anti-oscillation).
    """
    # Rule 1: state must change
    if prev_state == new_state:
        return False

    # First-run: only fire if entering a non-SAFE state
    if prev_state is None:
        return new_state != "SAFE"

    # Rule 2: minimum interval guard
    if last_alert_at is not None:
        elapsed = (datetime.now(UTC) - last_alert_at).total_seconds()
        if elapsed < min_interval_s:
            return False

    return True


def utilization(cvar: float, max_cvar: float) -> float:
    """Compute utilization ratio safely (avoids ZeroDivisionError)."""
    if max_cvar <= 0:
        return 0.0
    return cvar / max_cvar
