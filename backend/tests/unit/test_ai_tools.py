"""tests/unit/test_ai_tools.py — Tool-level unit tests (no LLM, no database).

Tests the tool functions directly:
  - evaluate_what_if: validates Pydantic boundary, correct ScenarioResult JSON
  - explain_risk_state: returns structured JSON for narration

The critical invariant: evaluate_what_if MUST raise ValueError for malformed or
out-of-range inputs, never return a fabricated number.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.ai.tools import evaluate_what_if, explain_risk_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _returns_json(n: int = 50, seed: int = 0) -> str:
    """Build a small historical returns JSON string for testing."""
    rng = np.random.default_rng(seed)
    data = {
        "AAPL": rng.normal(0.001, 0.01, n).tolist(),
        "NVDA": rng.normal(0.001, 0.02, n).tolist(),
    }
    return json.dumps(data)


def _weights_json() -> str:
    return json.dumps({"AAPL": 0.6, "NVDA": 0.4})


# ---------------------------------------------------------------------------
# evaluate_what_if — happy path
# ---------------------------------------------------------------------------


class TestEvaluateWhatIf:
    def test_valid_shock_returns_scenario_json(self) -> None:
        """A valid shock dict produces a JSON object with correct keys."""
        result_str = evaluate_what_if(
            shocks_json='{"NVDA": -0.20}',
            weights_json=_weights_json(),
            returns_json=_returns_json(),
            portfolio_value=100_000.0,
        )
        result = json.loads(result_str)
        assert "var_95" in result
        assert "cvar_95" in result
        assert "expected_loss" in result
        assert result["shocks"] == {"NVDA": -0.20}
        # Numbers are not fabricated — they come from the quant engine
        assert result["var_95"] > 0
        assert result["expected_loss"] > 0  # -20% shock -> positive loss

    def test_expected_loss_magnitude(self) -> None:
        """A -20% shock to NVDA (40% weight, $100k portfolio) = $8k expected loss."""
        result_str = evaluate_what_if(
            shocks_json='{"NVDA": -0.20}',
            weights_json=_weights_json(),
            returns_json=_returns_json(),
            portfolio_value=100_000.0,
        )
        result = json.loads(result_str)
        assert abs(result["expected_loss"] - 8_000.0) < 1.0

    def test_instruction_field_present(self) -> None:
        """The instruction field is included to guide the agent's narration."""
        result_str = evaluate_what_if(
            shocks_json='{"AAPL": -0.10}',
            weights_json=_weights_json(),
            returns_json=_returns_json(),
        )
        result = json.loads(result_str)
        assert "instruction" in result

    # -----------------------------------------------------------------------
    # evaluate_what_if — adversarial / malformed inputs
    # -----------------------------------------------------------------------

    def test_malformed_json_raises_value_error(self) -> None:
        """Malformed shocks_json must raise ValueError, not produce a number."""
        with pytest.raises(ValueError, match="Malformed shocks JSON"):
            evaluate_what_if(
                shocks_json="not-valid-json",
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )

    def test_non_dict_json_raises_value_error(self) -> None:
        """A JSON array instead of object must raise ValueError."""
        with pytest.raises(ValueError, match="Expected a JSON object"):
            evaluate_what_if(
                shocks_json='[{"NVDA": -0.20}]',
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )

    def test_out_of_range_shock_raises_value_error(self) -> None:
        """A shock of -1.5 fails Pydantic validation and raises ValueError."""
        with pytest.raises(ValueError, match="Shock validation failed"):
            evaluate_what_if(
                shocks_json='{"NVDA": -1.5}',
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )

    def test_exact_minus_one_shock_raises_value_error(self) -> None:
        """A shock of exactly -1.0 (liquidation) fails validation."""
        with pytest.raises(ValueError, match="Shock validation failed"):
            evaluate_what_if(
                shocks_json='{"NVDA": -1.0}',
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )

    def test_unknown_symbol_raises_value_error(self) -> None:
        """Shock for a symbol not in the portfolio raises ValueError."""
        with pytest.raises(ValueError, match="is not in the portfolio"):
            evaluate_what_if(
                shocks_json='{"TSLA": -0.15}',
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )

    def test_empty_shocks_raises_value_error(self) -> None:
        """An empty shocks dict fails Pydantic min_length=1 validation."""
        with pytest.raises(ValueError, match="Shock validation failed"):
            evaluate_what_if(
                shocks_json='{}',
                weights_json=_weights_json(),
                returns_json=_returns_json(),
            )


# ---------------------------------------------------------------------------
# explain_risk_state
# ---------------------------------------------------------------------------


class TestExplainRiskState:
    def test_returns_json_string(self) -> None:
        """explain_risk_state returns a JSON string with expected keys."""
        snapshot = {
            "portfolio_id": "abc-123",
            "data_status": "ready",
            "metrics": {"var_95": 0.025, "cvar_95": 0.032, "volatility": 0.18},
            "risk_contributions": [],
            "portfolio_value": "100000",
        }
        result_str = explain_risk_state(snapshot)
        result = json.loads(result_str)
        assert result["data_status"] == "ready"
        assert result["metrics"]["var_95"] == 0.025
        assert "instruction" in result

    def test_pending_state_preserved(self) -> None:
        """Pending data status is passed through without modification."""
        snapshot = {"portfolio_id": "x", "data_status": "pending"}
        result = json.loads(explain_risk_state(snapshot))
        assert result["data_status"] == "pending"

    def test_unknown_keys_ignored_gracefully(self) -> None:
        """Extra keys in the snapshot don't crash the function."""
        snapshot = {
            "portfolio_id": "y",
            "data_status": "ready",
            "unknown_internal_key": "some_value",
        }
        result_str = explain_risk_state(snapshot)
        result = json.loads(result_str)
        assert "instruction" in result
