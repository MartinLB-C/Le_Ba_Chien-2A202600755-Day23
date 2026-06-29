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
The graph is designed as a StateGraph with 11 distinct nodes. The state schema (`AgentState`) extends `TypedDict` to hold append-only fields like `events` and `errors`, while keeping mutable fields for routing (`route`, `attempt`, `evaluation_result`).
Routing relies on the outputs of the nodes. Specifically, the `classify_node` uses an LLM to enforce the priority rules and outputs a route. A retry loop is enforced via the `evaluate_node`, which dynamically checks tool outputs to decide if the graph needs to loop back to `tool_node` or proceed to `dead_letter` when attempt limits are reached.

## 4. Failure Analysis
1. **Unbounded Retry Loops**: We handle this by tracking the `attempt` counter in the state. Once `attempt >= max_attempts`, the conditional edge routes to `dead_letter`, ensuring the graph terminates.
2. **LLM Hallucinations on Classification**: By using `.with_structured_output`, we enforce that the LLM returns exactly one of the valid enums. This prevents the routing from crashing due to unexpected strings.

## 5. Improvement Plan
- Implement parallel fan-out for multiple tool calls by using the `Send()` API.
- Utilize a more robust evaluator (LLM-as-judge) for the tool output instead of simple string heuristic.
- Add comprehensive unit tests covering edge cases like token limits and context window exhaustion.