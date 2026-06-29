"""Node functions for the LangGraph workflow."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from .llm import get_llm
from .state import AgentState, make_event


def intake_node(state: AgentState) -> dict:
    """Normalize raw query. This node is provided as a working example."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


class RouteClassification(BaseModel):
    route: Literal["simple", "tool", "missing_info", "risky", "error"] = Field(
        description=(
            "Classify the query into one of these routes: risky, tool, "
            "missing_info, error, simple. Priority: risky > tool > "
            "missing_info > error > simple"
        )
    )


def classify_node(state: AgentState) -> dict:
    llm = get_llm().with_structured_output(RouteClassification)
    query = state.get("query", "")

    prompt = f"""
    You are an intent classifier for a customer support agent.
    Classify the following query into exactly one of these routes:
    - risky: Actions with side effects like refunds, deletions, sending emails, cancellations
    - tool: Information lookups like order status, tracking, search queries
    - missing_info: Vague or incomplete queries lacking actionable context
    - error: Queries describing system failures, timeouts, crashes, or service unavailable
    - simple: General questions answerable without tools or actions
    
    Priority guide: risky > tool > missing_info > error > simple.
    
    Query: {query}
    """

    try:
        classification = llm.invoke(prompt)
        route = classification.route
    except Exception:
        # Fallback in case of parsing errors
        route = "simple"

    risk_level = "high" if route == "risky" else "low"

    return {
        "route": route,
        "risk_level": risk_level,
        "events": [make_event("classify", "completed", f"classified as {route}")],
    }


def tool_node(state: AgentState) -> dict:
    attempt = state.get("attempt", 0)
    route = state.get("route", "")

    if route == "error" and attempt < 2:
        result = "ERROR: Simulated transient failure."
    else:
        result = "SUCCESS: Mock tool result."

    return {
        "tool_results": [result],
        "events": [make_event("tool", "completed", f"tool returned {result[:20]}")],
    }


class EvaluationResult(BaseModel):
    evaluation: Literal["needs_retry", "success"] = Field(
        description=(
            "Whether the tool result is satisfactory (success) "
            "or needs retry (needs_retry)."
        )
    )


def evaluate_node(state: AgentState) -> dict:
    tool_results = state.get("tool_results", [])
    latest_result = tool_results[-1] if tool_results else ""

    # LLM-as-judge
    llm = get_llm().with_structured_output(EvaluationResult)
    prompt = (
        "Evaluate the following tool result. If it contains an error or "
        "failure message, it needs retry. Otherwise it is a success.\n"
        f"Tool result: {latest_result}"
    )
    try:
        eval_result = llm.invoke(prompt).evaluation
    except Exception:
        # Fallback to heuristic
        eval_result = "needs_retry" if "ERROR" in latest_result.upper() else "success"

    return {
        "evaluation_result": eval_result,
        "events": [make_event("evaluate", "completed", f"evaluated as {eval_result}")],
    }


def answer_node(state: AgentState) -> dict:
    llm = get_llm()
    query = state.get("query", "")
    tool_results = state.get("tool_results", [])
    approval = state.get("approval", {})

    context = ""
    if tool_results:
        context += f"Tool Results: {tool_results[-1]}\n"
    if approval:
        context += f"Approval: {approval}\n"

    prompt = f"""
    You are a helpful customer support agent.
    Provide a final, helpful response to the customer based on their query
    and the available context.
    
    Customer Query: {query}
    Context: {context}
    """

    response = llm.invoke(prompt)
    answer = response.content

    return {
        "final_answer": answer,
        "events": [make_event("answer", "completed", "answer generated")],
    }


def ask_clarification_node(state: AgentState) -> dict:
    llm = get_llm()
    query = state.get("query", "")

    prompt = f"""
    The customer asked a vague or incomplete query. Generate a specific
    clarification question to ask them.
    Customer Query: {query}
    """

    response = llm.invoke(prompt)
    question = response.content

    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("ask_clarification", "completed", "clarification asked")],
    }


def risky_action_node(state: AgentState) -> dict:
    query = state.get("query", "")
    llm = get_llm()

    prompt = f"""
    The customer requested a risky action. Describe the proposed action
    and why it requires approval.
    Customer Query: {query}
    """
    response = llm.invoke(prompt)
    action_desc = response.content

    return {
        "proposed_action": action_desc,
        "events": [make_event("risky_action", "completed", "risky action prepared")],
    }


def approval_node(state: AgentState) -> dict:
    if os.getenv("LANGGRAPH_INTERRUPT", "false").lower() == "true":
        import langgraph.types

        decision = langgraph.types.interrupt("Approval required for risky action.")
        if isinstance(decision, dict):
            approved = decision.get("approved", False)
            comment = decision.get("comment", "")
        elif isinstance(decision, bool):
            approved = decision
            comment = ""
        else:
            approved = str(decision).lower() in ["yes", "true", "y"]
            comment = str(decision)
    else:
        approved = True
        comment = "Auto-approved mock"

    approval_data = {
        "approved": approved,
        "reviewer": "human"
        if os.getenv("LANGGRAPH_INTERRUPT", "false").lower() == "true"
        else "mock-reviewer",
        "comment": comment,
    }

    return {
        "approval": approval_data,
        "events": [make_event("approval", "completed", f"approval decided: {approved}")],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    attempt = state.get("attempt", 0) + 1
    error_msg = f"Transient failure on attempt {attempt}"

    return {
        "attempt": attempt,
        "errors": [error_msg],
        "events": [make_event("retry_or_fallback", "completed", f"retry attempt {attempt}")],
    }


def dead_letter_node(state: AgentState) -> dict:
    ans = (
        "We apologize, but we could not complete your request due to "
        "system errors. Please try again later."
    )
    return {
        "final_answer": ans,
        "events": [make_event("dead_letter", "completed", "max retries exceeded")],
    }


def finalize_node(state: AgentState) -> dict:
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
