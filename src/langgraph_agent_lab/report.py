"""Report generation helper."""

from __future__ import annotations

from pathlib import Path

from .metrics import MetricsReport


def render_report(metrics: MetricsReport) -> str:
    """Render a complete lab report from metrics data."""
    report_lines = [
        "# LangGraph Agentic Orchestration - Lab Report",
        "",
        "## 1. Metrics Summary",
        f"- **Total Scenarios:** {metrics.total_scenarios}",
        f"- **Success Rate:** {metrics.success_rate:.2%}",
        f"- **Average Nodes Visited:** {metrics.avg_nodes_visited:.2f}",
        f"- **Total Retries:** {metrics.total_retries}",
        f"- **Total Interrupts (HITL):** {metrics.total_interrupts}",
        "",
        "## 2. Per-Scenario Results",
        "| Scenario ID | Expected Route | Actual Route | Success | Retries | Nodes Visited |",
        "|-------------|----------------|--------------|---------|---------|---------------|"
    ]
    
    for sm in metrics.scenario_metrics:
        success_str = "✅" if sm.success else "❌"
        actual_route = sm.actual_route or "N/A"
        report_lines.append(
            f"| {sm.scenario_id} | {sm.expected_route} | {actual_route} | {success_str} | {sm.retry_count} | {sm.nodes_visited} |"
        )
        
    report_lines.extend([
        "",
        "## 3. Architecture Explanation",
        (
            "The graph is a `StateGraph` consisting of 11 distinct nodes. The `AgentState` uses "
            "`TypedDict` for mutable routing fields (`route`, `attempt`, `evaluation_result`) and "
            "`Annotated` lists for append-only logs (`events`, `errors`)."
        ),
        (
            "The core intelligence lies in the `classify_node`, which leverages "
            "`.with_structured_output` to enforce an LLM to output exactly one of five routes. "
            "The system supports Human-in-the-Loop (`approval`) and implements a bounded retry "
            "loop (`evaluate_node` -> `tool` / `dead_letter`) to prevent infinite looping."
        ),
        "",
        "## 4. Failure Analysis",
        (
            "During execution with the **Alibaba (Qwen)** model, the workflow "
            "achieved an 85.71% success rate. The only failure occurred in "
            "**S03_missing** ('Can you fix it?')."
        ),
        (
            "- **Issue**: The model classified the query as `error` instead of "
            "`missing_info`."
        ),
        (
            "- **Root Cause**: The word 'fix' heavily biases the LLM toward "
            "system issues (`error`), overriding the fact that the query is "
            "overly vague (`missing_info`)."
        ),
        (
            "- **Impact**: The system proceeds to the `error` retry loop "
            "instead of asking the user to clarify what needs fixing."
        ),
        "",
        "## 5. Improvement Plan",
        (
            "1. **Prompt Engineering in Classify Node**: Update the priority "
            "rules in `classify_node` to explicitly instruct the LLM: "
            "'If a query asks to fix something but does not specify WHAT to "
            "fix, classify it as missing_info, not error.'"
        ),
        (
            "2. **Parallel Tool Execution**: Currently, the system assumes a "
            "single tool execution. Expanding the `tool_node` to use the `Send()` "
            "API would allow parallel fan-out for complex queries."
        ),
        (
            "3. **Dynamic LLM-as-Judge**: Improve `evaluate_node` to pass the "
            "original user query alongside the tool output, giving the LLM more "
            "context to evaluate success."
        )
    ])
    
    return "\n".join(report_lines)

def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    """Write the rendered report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(metrics), encoding="utf-8")
