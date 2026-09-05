"""slack_bot/formatters.py — Block Kit message formatters.

Pure functions (no I/O) that convert RiskLens API response dicts into
Slack Block Kit block lists.  Independently testable.
"""

from __future__ import annotations

from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────


def _divider() -> dict[str, Any]:
    return {"type": "divider"}


def _section(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _header(text: str) -> dict[str, Any]:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.2f}%"


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}"


# ── Public formatters ─────────────────────────────────────────────────────────


def format_not_linked() -> list[dict[str, Any]]:
    """Blocks shown when the Slack user has not yet linked their account."""
    return [
        _section(
            ":lock: *Your Slack account isn't linked yet.*\n"
            "Generate a one-time code from the RiskLens web dashboard "
            "(*Account → Generate Slack Code*) then run:\n"
            "```/risklens login <your-code>```"
        )
    ]


def format_risk_status(
    portfolios: list[dict[str, Any]],
    risk: dict[str, Any],
) -> list[dict[str, Any]]:
    """Format portfolio risk snapshot as Block Kit blocks."""
    if not portfolios:
        return [_section(":warning: No portfolios found.")]

    portfolio_name = portfolios[0].get("name", "Your portfolio")

    regime = risk.get("market_regime") or {}
    regime_label = regime.get("label", "unknown").upper()
    stressed_pct = _pct(regime.get("stressed_probability"))

    var_95 = _money(risk.get("var_95"))
    cvar_95 = _money(risk.get("cvar_95"))
    volatility = _pct(risk.get("volatility"))
    sharpe = risk.get("sharpe_ratio")
    sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "—"

    blocks: list[dict[str, Any]] = [
        _header(f":bar_chart: RiskLens — {portfolio_name}"),
        _divider(),
        _section(
            f"*Market Regime:* {regime_label}  |  Stressed prob: {stressed_pct}\n"
            f"*VaR (95%):* {var_95}  |  *CVaR (95%):* {cvar_95}\n"
            f"*Volatility:* {volatility}  |  *Sharpe:* {sharpe_str}"
        ),
    ]

    # Concentration warnings
    conc = risk.get("concentration_warning")
    if conc:
        symbols = ", ".join(conc.get("symbols", []))
        blocks.append(
            _section(f":warning: *Concentration warning*: {conc.get('message', '')} ({symbols})")
        )

    return blocks


def format_whatif(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Format a what-if scenario response as Block Kit blocks."""
    scenario = response.get("scenario_result") or {}
    narration = response.get("narration")
    timed_out = response.get("timeout", False)

    var_before = _money(scenario.get("var_95_before"))
    var_after = _money(scenario.get("var_95_after"))
    cvar_before = _money(scenario.get("cvar_95_before"))
    cvar_after = _money(scenario.get("cvar_95_after"))

    blocks: list[dict[str, Any]] = [
        _header(":crystal_ball: What-If Scenario"),
        _divider(),
        _section(
            f"*VaR 95%:* {var_before} → {var_after}\n"
            f"*CVaR 95%:* {cvar_before} → {cvar_after}"
        ),
    ]

    if timed_out:
        blocks.append(_section("_AI narration timed out — numbers are still reliable._"))
    elif narration:
        blocks.append(_section(f":speech_balloon: {narration}"))

    return blocks


def format_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format a list of recent alerts as Block Kit blocks."""
    if not alerts:
        return [_section(":white_check_mark: No recent alerts.")]

    severity_emoji = {
        "SAFE": ":large_green_circle:",
        "WATCH": ":large_yellow_circle:",
        "HIGH": ":large_orange_circle:",
        "BREACH": ":red_circle:",
    }

    blocks: list[dict[str, Any]] = [_header(":bell: Recent Alerts"), _divider()]
    for alert in alerts[:5]:  # cap at 5 to keep messages compact
        sev = alert.get("severity", "").upper()
        emoji = severity_emoji.get(sev, ":white_circle:")
        fired = alert.get("fired_at", "")[:16].replace("T", " ")
        msg = alert.get("message", "")
        blocks.append(_section(f"{emoji} *{sev}* — {msg}\n_{fired}_"))

    if len(alerts) > 5:
        blocks.append(_section(f"_…and {len(alerts) - 5} more. View all on the dashboard._"))

    return blocks
