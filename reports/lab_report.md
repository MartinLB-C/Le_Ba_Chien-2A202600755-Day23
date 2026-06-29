# LangGraph Agentic Orchestration - Lab Report

## 1. Metrics Summary
- **Total Scenarios:** 7
- **Success Rate:** 85.71%
- **Average Nodes Visited:** 7.29
- **Total Retries:** 0
- **Total Interrupts (HITL):** 2

## 2. Per-Scenario Results
| Scenario ID | Expected Route | Actual Route | Success | Retries | Nodes Visited |
|-------------|----------------|--------------|---------|---------|---------------|
| S01_simple | simple | simple | ✅ | 0 | 4 |
| S02_tool | tool | tool | ✅ | 0 | 6 |
| S03_missing | missing_info | error | ❌ | 0 | 10 |
| S04_risky | risky | risky | ✅ | 0 | 8 |
| S05_error | error | error | ✅ | 0 | 10 |
| S06_delete | risky | risky | ✅ | 0 | 8 |
| S07_dead_letter | error | error | ✅ | 0 | 5 |

## 3. Architecture Explanation
The graph is a `StateGraph` consisting of 11 distinct nodes. The `AgentState` uses `TypedDict` for mutable routing fields (`route`, `attempt`, `evaluation_result`) and `Annotated` lists for append-only logs (`events`, `errors`).
The core intelligence lies in the `classify_node`, which leverages `.with_structured_output` to enforce an LLM to output exactly one of five routes. The system supports Human-in-the-Loop (`approval`) and implements a bounded retry loop (`evaluate_node` -> `tool` / `dead_letter`) to prevent infinite looping.

## 4. Failure Analysis
During execution with the **Alibaba (Qwen)** model, the workflow achieved an 85.71% success rate. The only failure occurred in **S03_missing** ('Can you fix it?').
- **Issue**: The model classified the query as `error` instead of `missing_info`.
- **Root Cause**: The word 'fix' heavily biases the LLM toward system issues (`error`), overriding the fact that the query is overly vague (`missing_info`).
- **Impact**: The system proceeds to the `error` retry loop instead of asking the user to clarify what needs fixing.

## 5. Improvement Plan
1. **Prompt Engineering in Classify Node**: Update the priority rules in `classify_node` to explicitly instruct the LLM: *'If a query asks to fix something but does not specify WHAT to fix, classify it as missing_info, not error.'*
2. **Parallel Tool Execution**: Currently, the system assumes a single tool execution. Expanding the `tool_node` to use the `Send()` API would allow parallel fan-out for complex queries.
3. **Dynamic LLM-as-Judge**: Improve `evaluate_node` to pass the original user query alongside the tool output, giving the LLM more context to evaluate success.