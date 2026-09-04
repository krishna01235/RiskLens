"""app/ai/agent.py — LangGraph StateGraph for the AI Risk Analyst.

Architecture (Phase 18):
  - Two entry points: run_explain_graph / run_what_if_graph
  - The model is instructed it MUST call a tool for every numeric claim.
  - Ambiguous questions trigger a clarifying question (or explicit assumption),
    never a silently-guessed magnitude.
  - LLM call is wrapped in an asyncio timeout; on timeout the function returns
    a sentinel so the numeric result still renders in the UI.

Tool-calling boundary test: the Pydantic validation in tools.evaluate_what_if
is the last defence — any adversarial or malformed tool call is rejected here
before it can produce a fabricated number.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool as lc_tool
from langgraph.graph import END, StateGraph

from app.ai.tools import evaluate_what_if, explain_risk_state

logger = logging.getLogger(__name__)

_LLM_TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_EXPLAIN_SYSTEM = """You are a professional quantitative risk analyst.
Your job is to explain the portfolio risk metrics to the user in clear, plain language.

RULES (non-negotiable):
1. You MUST call the `explain_risk_state` tool FIRST to retrieve the risk data.
2. You MUST use ONLY the numbers returned by the tool. Never state a number you computed yourself.
3. State units explicitly (e.g. "95% 1-day VaR", "annualised volatility").
4. Keep the explanation concise (3-5 sentences) and jargon-free.
5. If data_status is "pending" or "insufficient_data", say so clearly instead of guessing.
"""

_WHAT_IF_SYSTEM = """You are a professional quantitative risk analyst.
Your job is to evaluate a portfolio what-if scenario and explain the results.

RULES (non-negotiable):
1. Parse the user's question into a JSON shock dictionary: {symbol: fractional_change}.
   Example: "NVDA falls 20%" -> {"NVDA": -0.20}
2. Call the `evaluate_what_if` tool with that JSON to get the real numbers.
3. Use ONLY the numbers returned by the tool in your narration. Never estimate outcomes yourself.
4. If the question is AMBIGUOUS (e.g. "what if the market crashes"):
   - Either ask ONE clarifying question about the magnitude, OR
   - State your assumed mapping explicitly BEFORE calling the tool.
   Never silently guess a magnitude.
5. State the shock magnitude explicitly in your response (e.g. "a 20% fall in NVDA").
6. If insufficient_data is true in the result, note that results are approximate.
"""

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    messages: list[BaseMessage]
    # Injected context (passed into the graph, not fetched by the tool)
    risk_snapshot: dict  # for explain
    weights_json: str    # for what-if
    returns_json: str    # for what-if
    portfolio_value: float
    # Output
    scenario_result_json: str | None
    clarification_needed: bool
    clarification_question: str | None


# ---------------------------------------------------------------------------
# LangChain tool wrappers
# ---------------------------------------------------------------------------

@lc_tool
def lc_explain_risk_state(risk_snapshot_json: str) -> str:
    """Retrieve the structured risk state for narration.

    Args:
        risk_snapshot_json: JSON string of the risk snapshot to explain.
    """
    try:
        snapshot = json.loads(risk_snapshot_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid risk_snapshot_json"})
    return explain_risk_state(snapshot)


@lc_tool
def lc_evaluate_what_if(shocks_json: str) -> str:
    """Evaluate a scenario by applying shocks to the portfolio.

    The context (weights, returns, portfolio_value) is injected separately.
    This tool only receives the shocks — the service layer provides the portfolio data.

    Args:
        shocks_json: JSON object string mapping symbol to fractional shock.
            Example: '{"NVDA": -0.20}'
    """
    # Placeholder — the actual call is made in the node which has full context.
    # This signature exists so the LLM sees the tool; the node intercepts the call.
    return shocks_json  # node replaces this


# ---------------------------------------------------------------------------
# Graph builder helpers
# ---------------------------------------------------------------------------

def _build_llm(api_key: str, model: str = "claude-3-5-haiku-20241022") -> ChatAnthropic:
    return ChatAnthropic(api_key=api_key, model=model, max_tokens=1024)  # type: ignore[call-arg]


def _is_tool_call(message: BaseMessage) -> bool:
    return (
        isinstance(message, AIMessage)
        and bool(getattr(message, "tool_calls", None))
    )


# ---------------------------------------------------------------------------
# Explain graph
# ---------------------------------------------------------------------------

def build_explain_graph(api_key: str, model: str = "claude-3-5-haiku-20241022") -> Any:
    """Build the LangGraph graph for the explain flow."""
    llm = _build_llm(api_key, model).bind_tools([lc_explain_risk_state])

    def call_model(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    def call_tool(state: AgentState) -> dict:
        last = state["messages"][-1]
        results: list[BaseMessage] = []
        for tc in last.tool_calls:  # type: ignore[union-attr]
            if tc["name"] == "lc_explain_risk_state":
                # Inject the snapshot from state rather than trusting model's arg
                result_str = explain_risk_state(state["risk_snapshot"])
            else:
                result_str = json.dumps({"error": f"Unknown tool: {tc['name']}"})
            results.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))
        return {"messages": state["messages"] + results}

    def should_continue(state: AgentState) -> str:
        return "tool" if _is_tool_call(state["messages"][-1]) else END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tool", call_tool)
    graph.set_entry_point("model")
    graph.add_conditional_edges("model", should_continue, {"tool": "tool", END: END})
    graph.add_edge("tool", "model")
    return graph.compile()


# ---------------------------------------------------------------------------
# What-If graph
# ---------------------------------------------------------------------------

def build_what_if_graph(api_key: str, model: str = "claude-3-5-haiku-20241022") -> Any:
    """Build the LangGraph graph for the what-if flow."""
    llm = _build_llm(api_key, model).bind_tools([lc_evaluate_what_if])

    def call_model(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    def call_tool(state: AgentState) -> dict:
        last = state["messages"][-1]
        results: list[BaseMessage] = []
        scenario_json: str | None = None

        for tc in last.tool_calls:  # type: ignore[union-attr]
            if tc["name"] == "lc_evaluate_what_if":
                shocks_arg = tc["args"].get("shocks_json", "{}")
                try:
                    result_str = evaluate_what_if(
                        shocks_json=shocks_arg,
                        weights_json=state["weights_json"],
                        returns_json=state["returns_json"],
                        portfolio_value=state["portfolio_value"],
                    )
                    scenario_json = result_str
                except ValueError as exc:
                    result_str = json.dumps({"error": str(exc)})
            else:
                result_str = json.dumps({"error": f"Unknown tool: {tc['name']}"})
            results.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))

        updates: dict = {"messages": state["messages"] + results}
        if scenario_json is not None:
            updates["scenario_result_json"] = scenario_json
        return updates

    def should_continue(state: AgentState) -> str:
        return "tool" if _is_tool_call(state["messages"][-1]) else END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tool", call_tool)
    graph.set_entry_point("model")
    graph.add_conditional_edges("model", should_continue, {"tool": "tool", END: END})
    graph.add_edge("tool", "model")
    return graph.compile()


# ---------------------------------------------------------------------------
# Public async entry points
# ---------------------------------------------------------------------------

async def run_explain_graph(
    api_key: str,
    risk_snapshot: dict,
    model: str = "claude-3-5-haiku-20241022",
) -> tuple[str | None, bool]:
    """Run the explain flow; returns (narration, timeout_flag).

    The LLM call is wrapped in an asyncio timeout. On timeout the numbers
    still render (they come from risk_snapshot directly); narration is None.
    """
    graph = build_explain_graph(api_key, model)
    initial: AgentState = {
        "messages": [
            HumanMessage(content=(
                f"Please explain the risk state for this portfolio. "
                f"First call the explain_risk_state tool with: {json.dumps(risk_snapshot)}"
            ))
        ],
        "risk_snapshot": risk_snapshot,
        "weights_json": "{}",
        "returns_json": "{}",
        "portfolio_value": 1.0,
        "scenario_result_json": None,
        "clarification_needed": False,
        "clarification_question": None,
    }
    try:
        final_state = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, graph.invoke, initial),
            timeout=_LLM_TIMEOUT_SECONDS,
        )
        last = final_state["messages"][-1]
        narration = last.content if isinstance(last, AIMessage) else None
        return narration, False
    except asyncio.TimeoutError:
        logger.warning("explain_graph timed out after %ds", _LLM_TIMEOUT_SECONDS)
        return None, True


async def run_what_if_graph(
    api_key: str,
    question: str,
    weights_json: str,
    returns_json: str,
    portfolio_value: float,
    model: str = "claude-3-5-haiku-20241022",
) -> tuple[str | None, str | None, bool, bool, str | None]:
    """Run the what-if flow.

    Returns:
        (scenario_result_json, narration, clarification_needed, timeout, clarification_question)
    """
    graph = build_what_if_graph(api_key, model)

    system_ctx = (
        f"Portfolio weights JSON: {weights_json}\n"
        f"Historical returns available (call the tool to evaluate).\n"
        f"Portfolio value: {portfolio_value}"
    )

    initial: AgentState = {
        "messages": [
            HumanMessage(content=f"{question}\n\nContext:\n{system_ctx}")
        ],
        "risk_snapshot": {},
        "weights_json": weights_json,
        "returns_json": returns_json,
        "portfolio_value": portfolio_value,
        "scenario_result_json": None,
        "clarification_needed": False,
        "clarification_question": None,
    }

    # Prepend the system prompt
    from langchain_core.messages import SystemMessage
    initial["messages"] = [SystemMessage(content=_WHAT_IF_SYSTEM)] + initial["messages"]

    try:
        final_state = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, graph.invoke, initial),
            timeout=_LLM_TIMEOUT_SECONDS,
        )
        last = final_state["messages"][-1]
        narration = last.content if isinstance(last, AIMessage) else None
        scenario_json = final_state.get("scenario_result_json")

        # Detect clarification: no tool was called and narration contains a question mark
        clarification_needed = scenario_json is None and narration and "?" in narration
        clarification_question = narration if clarification_needed else None

        return scenario_json, narration, bool(clarification_needed), False, clarification_question
    except asyncio.TimeoutError:
        logger.warning("what_if_graph timed out after %ds", _LLM_TIMEOUT_SECONDS)
        return None, None, False, True, None
