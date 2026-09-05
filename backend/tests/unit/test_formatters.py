"""tests/unit/test_formatters.py — Unit tests for Block Kit formatters.

All formatters are pure functions with no I/O — tested with fixture dicts.
"""

from __future__ import annotations

import pytest

from slack_bot.formatters import (
    format_alerts,
    format_not_linked,
    format_risk_status,
    format_whatif,
)


# ── format_not_linked ─────────────────────────────────────────────────────────


def test_not_linked_returns_list():
    blocks = format_not_linked()
    assert isinstance(blocks, list)
    assert len(blocks) >= 1


def test_not_linked_contains_login_instruction():
    blocks = format_not_linked()
    full_text = str(blocks)
    assert "/risklens login" in full_text


# ── format_risk_status ────────────────────────────────────────────────────────


_PORTFOLIO = [{"id": "abc", "name": "My Portfolio"}]

_RISK = {
    "var_95": 1234.56,
    "cvar_95": 1800.00,
    "volatility": 0.18,
    "sharpe_ratio": 1.42,
    "market_regime": {"label": "stressed", "stressed_probability": 0.72},
    "concentration_warning": None,
}


def test_risk_status_returns_blocks():
    blocks = format_risk_status(_PORTFOLIO, _RISK)
    assert isinstance(blocks, list)
    assert len(blocks) >= 2


def test_risk_status_contains_portfolio_name():
    blocks = format_risk_status(_PORTFOLIO, _RISK)
    full_text = str(blocks)
    assert "My Portfolio" in full_text


def test_risk_status_contains_var():
    blocks = format_risk_status(_PORTFOLIO, _RISK)
    full_text = str(blocks)
    assert "1,234.56" in full_text


def test_risk_status_contains_regime():
    blocks = format_risk_status(_PORTFOLIO, _RISK)
    full_text = str(blocks)
    assert "STRESSED" in full_text


def test_risk_status_with_concentration_warning():
    risk = {**_RISK, "concentration_warning": {"message": "Over-concentrated", "symbols": ["AAPL"]}}
    blocks = format_risk_status(_PORTFOLIO, risk)
    full_text = str(blocks)
    assert "Over-concentrated" in full_text
    assert "AAPL" in full_text


def test_risk_status_no_portfolios():
    blocks = format_risk_status([], {})
    full_text = str(blocks)
    assert "No portfolios" in full_text


def test_risk_status_missing_optional_fields():
    """Formatter must not raise if optional fields are absent."""
    blocks = format_risk_status(_PORTFOLIO, {})
    assert isinstance(blocks, list)


# ── format_whatif ─────────────────────────────────────────────────────────────


_WHATIF_RESP = {
    "scenario_result": {
        "var_95_before": 1000.0,
        "var_95_after": 1400.0,
        "cvar_95_before": 1500.0,
        "cvar_95_after": 2100.0,
    },
    "narration": "Your portfolio risk increases by 40%.",
    "timeout": False,
}


def test_whatif_returns_blocks():
    blocks = format_whatif(_WHATIF_RESP)
    assert isinstance(blocks, list)
    assert len(blocks) >= 2


def test_whatif_shows_before_after_var():
    blocks = format_whatif(_WHATIF_RESP)
    full_text = str(blocks)
    assert "1,000.00" in full_text
    assert "1,400.00" in full_text


def test_whatif_shows_narration():
    blocks = format_whatif(_WHATIF_RESP)
    full_text = str(blocks)
    assert "40%" in full_text


def test_whatif_timeout_message():
    resp = {**_WHATIF_RESP, "timeout": True, "narration": None}
    blocks = format_whatif(resp)
    full_text = str(blocks)
    assert "timed out" in full_text


def test_whatif_no_narration_no_timeout():
    """Should not include a narration or timeout block when both are absent."""
    resp = {**_WHATIF_RESP, "narration": None, "timeout": False}
    blocks = format_whatif(resp)
    full_text = str(blocks)
    assert "timed out" not in full_text


def test_whatif_missing_scenario_result():
    """Formatter must not raise if scenario_result is absent."""
    blocks = format_whatif({})
    assert isinstance(blocks, list)


# ── format_alerts ─────────────────────────────────────────────────────────────


_ALERTS = [
    {
        "severity": "BREACH",
        "message": "VaR limit breached",
        "fired_at": "2026-09-05T10:00:00Z",
    },
    {
        "severity": "HIGH",
        "message": "Volatility spike",
        "fired_at": "2026-09-05T09:00:00Z",
    },
    {
        "severity": "WATCH",
        "message": "Concentration risk rising",
        "fired_at": "2026-09-05T08:00:00Z",
    },
]


def test_alerts_returns_blocks():
    blocks = format_alerts(_ALERTS)
    assert isinstance(blocks, list)
    assert len(blocks) >= 2


def test_alerts_shows_severity():
    blocks = format_alerts(_ALERTS)
    full_text = str(blocks)
    assert "BREACH" in full_text


def test_alerts_shows_message():
    blocks = format_alerts(_ALERTS)
    full_text = str(blocks)
    assert "VaR limit breached" in full_text


def test_alerts_empty_list():
    blocks = format_alerts([])
    full_text = str(blocks)
    assert "No recent alerts" in full_text


def test_alerts_caps_at_five():
    """More than 5 alerts should be capped and show overflow message."""
    many = _ALERTS * 3  # 9 alerts
    blocks = format_alerts(many)
    full_text = str(blocks)
    # Should show overflow notice
    assert "more" in full_text


def test_alerts_exactly_five_no_overflow():
    """Exactly 5 alerts — no overflow message needed."""
    five = (_ALERTS * 2)[:5]
    blocks = format_alerts(five)
    full_text = str(blocks)
    assert "more" not in full_text


def test_alerts_shows_timestamp():
    blocks = format_alerts(_ALERTS)
    full_text = str(blocks)
    # fired_at "2026-09-05T10:00:00Z" → "2026-09-05 10:00"
    assert "2026-09-05 10:00" in full_text
