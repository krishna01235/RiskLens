"""app/ai/tools.py — LangGraph tool functions for the AI Risk Analyst.

Architecture invariant (Phase 18 / ownership-and-security-review skill):
  - explain_risk_state: fetches already-computed numbers and returns them as
    structured data for the agent to NARRATE. Never invents a number.
  - evaluate_what_if: validates the model's parsed shocks via Pydantic BEFORE
    calling quant/scenarios.py. If Pydantic rejects the input, the function
    raises ValueError and the model receives an error message -- never a
    silently-wrong number.

These are plain Python callables; LangGraph wraps them as tools in agent.py.
No database or Redis access here -- the service layer passes pre-fetched data in.
"""

from __future__ import annotations

import json
import logging

import pandas as pd

from app.ai.schemas import ScenarioResultOut, ShocksPayload
from quant.scenarios import ScenarioResult, evaluate_scenario

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool 1 — explain_risk_state
# ---------------------------------------------------------------------------


def explain_risk_state(risk_snapshot: dict) -> str:
    """Return a JSON string of the current risk snapshot for the agent to narrate.

    The agent MUST use these exact numbers in its response.
    It must NOT state any metric it did not receive from this function.

    Parameters
    ----------
    risk_snapshot:
        Dict with keys matching RiskResponse / RiskMetrics fields.
        Passed in by the service layer; not fetched by the tool itself.

    Returns
    -------
    JSON string the agent reads and narrates from.
    """
    # Surface key metrics cleanly; drop internal plumbing keys the model
    # doesn't need (e.g. raw timestamps).
    output = {
        "portfolio_id": str(risk_snapshot.get("portfolio_id", "")),
        "data_status": risk_snapshot.get("data_status", "pending"),
        "metrics": risk_snapshot.get("metrics"),
        "risk_contributions": risk_snapshot.get("risk_contributions", []),
        "portfolio_value": risk_snapshot.get("portfolio_value"),
        "daily_pnl": risk_snapshot.get("daily_pnl"),
        "instruction": (
            "Use ONLY the numbers above in your explanation. "
            "Do not calculate or estimate any values. "
            "State units explicitly (e.g. '95% 1-day VaR')."
        ),
    }
    return json.dumps(output)


# ---------------------------------------------------------------------------
# Tool 2 — evaluate_what_if
# ---------------------------------------------------------------------------


def evaluate_what_if(
    shocks_json: str,
    weights_json: str,
    returns_json: str,
    portfolio_value: float = 1.0,
) -> str:
    """Parse the model's shock dict, validate it, and call the quant engine.

    The model must produce a valid JSON object as shocks_json.
    If Pydantic validation fails, this raises ValueError and the model
    receives an error message — it does NOT receive a fabricated number.

    Parameters
    ----------
    shocks_json:
        JSON string of {symbol: fractional_shock} produced by the LLM.
        Example: '{"NVDA": -0.20}'
    weights_json:
        JSON string of {symbol: weight} from the portfolio.
        Passed in by the service layer.
    returns_json:
        JSON string of {symbol: [return1, return2, ...]} historical returns.
        Passed in by the service layer (column-oriented DataFrame dict).
    portfolio_value:
        Portfolio value in home currency.

    Returns
    -------
    JSON string of ScenarioResultOut for the agent to narrate.

    Raises
    ------
    ValueError
        If shocks_json is malformed, shocks fail range validation,
        or a symbol is not in the portfolio.
    """
    # Step 1: Parse the model's output
    try:
        raw_shocks = json.loads(shocks_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Malformed shocks JSON: {exc}. "
            "Provide a valid JSON object like {{\"NVDA\": -0.20}}."
        ) from exc

    if not isinstance(raw_shocks, dict):
        raise ValueError(
            f"Expected a JSON object for shocks, got {type(raw_shocks).__name__}."
        )

    # Step 2: Pydantic validation (range check, non-empty, max symbols)
    try:
        validated = ShocksPayload(shocks=raw_shocks)
    except Exception as exc:
        raise ValueError(f"Shock validation failed: {exc}") from exc

    # Step 3: Parse portfolio weights
    try:
        weights: dict[str, float] = json.loads(weights_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed weights JSON: {exc}") from exc

    # Step 4: Reconstruct DataFrame from column-oriented dict
    try:
        returns_dict: dict[str, list[float]] = json.loads(returns_json)
        returns_df = pd.DataFrame(returns_dict)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Malformed returns JSON: {exc}") from exc

    # Step 5: Call the deterministic quant engine
    result: ScenarioResult = evaluate_scenario(
        weights=weights,
        returns_df=returns_df,
        shocks=validated.shocks,
        portfolio_value=portfolio_value,
    )

    # Step 6: Serialise and append narration hint
    out = ScenarioResultOut(
        shocks=result.shocks,
        var_95=result.var_95,
        cvar_95=result.cvar_95,
        var_95_baseline=result.var_95_baseline,
        cvar_95_baseline=result.cvar_95_baseline,
        expected_loss=result.expected_loss,
        portfolio_value=result.portfolio_value,
        insufficient_data=result.insufficient_data,
    )

    output = out.model_dump()
    output["instruction"] = (
        "Use ONLY the numbers in this result in your narration. "
        "Do not calculate or estimate any values. "
        "State the shock magnitude explicitly (e.g. 'a 20% fall in NVDA'). "
        "If insufficient_data is True, note that results are approximate."
    )
    return json.dumps(output)
