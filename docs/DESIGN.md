# DESIGN.md — Stnapt Agentic RAG

**Author:** [Your name]  
**Corpus:** Option A — Indian IT Financials (Infosys, TCS, Wipro)  
**Stack:** Python · Anthropic Claude API · ChromaDB · SQLite · Tavily

---

## 1. What This Agent Does

This is a small reasoning agent that answers questions over three kinds of data:
unstructured annual report PDFs, a structured financials table, and the live web.
The agent decides which tool to call for each question, can chain multiple tools
when a question requires both a number and an explanation, and composes a final
answer that cites the exact source used for each claim.

The distinguishing feature is the **stnapt.ai context layer**: a governance
middleware that wraps every tool result with enterprise metadata before it
re-enters the LLM context, simulating the kind of data provenance and access
control that production AI systems require.

---

## 2. Agent Loop — Step by Step

The loop lives entirely in `agent.py` and follows the **ReAct pattern**
(Reason → Act → Observe), implemented as a plain Python `while` loop with a
step counter. There is no framework wrapping the loop logic.

```
1. Receive the user's question.
2. Send question + full message history + tool schemas to the LLM.
3. If the LLM returns stop_reason = "end_turn"  →  extract final answer and exit.
4. If the LLM returns one or more tool_use blocks:
     For each tool_use block:
       a. Increment step counter. If step > MAX_STEPS (8) → return structured refusal.
       b. Call the named tool with the provided input arguments.
       c. Pass the raw output through stnapt_context_interceptor().
       d. Append the wrapped context object to the trace log.
       e. Append the wrapped result as a tool_result message.
5. Append the assistant turn and all tool_results to the message history.
6. Go to step 2.
```

The loop terminates in exactly two ways: the LLM produces a final answer
(`end_turn`), or the step counter reaches 8 (`HARD_CAP_REACHED`).

---

## 3. Tool Schemas

Each tool has a name, an LLM-facing description, and typed input schema.
The descriptions are written for the model, not for a human reader. Each
description explicitly states **when to use** and **when not to use** the tool,
which is the primary mechanism for correct tool routing.

| Tool | Purpose | Input | Output |
|---|---|---|---|
| `search_docs` | Semantic search over annual report PDFs | Natural language query | Top-3 chunks with source file and page number |
| `query_data` | Query structured financials table | SQL SELECT or plain-English question | Rows + columns + row count + SQL executed |
| `web_search` | Live web search for recent information | Short query ≤ 10 words | Top-3 snippets with URL and publication date |

Full schemas are in `tools/tool_schemas.py`.

---

## 4. The Stnapt Context Layer

### What it does

Every tool result passes through `stnapt_context_interceptor()` before the
LLM sees it. The interceptor wraps the raw tool output with four governance
fields:

| Field | Value | Purpose |
|---|---|---|
| `stnapt_trace_id` | `SNPT-` + 8 random hex chars | Unique citation handle for this retrieval event |
| `data_source_verified` | `True` for `search_docs`/`query_data`, `False` for `web_search` | Signals whether the data came from a controlled, auditable source |
| `clearance` | `PUBLIC_FINANCIALS` or `LIVE_WEB_UNVERIFIED` | Data classification tag for access control |
| `intercepted_at` | UTC ISO timestamp | Audit log timestamp |

### Why it matters for citations

The system prompt instructs the LLM that every factual claim in its final answer
must include the `stnapt_trace_id` of the result it came from, in the format
`[SNPT-XXXXXXXX]`. This makes citations machine-readable and traceable back to
a specific retrieval event, not just a tool name.

### Why it matters for governance

In a production deployment, the interceptor would be the place to enforce row-
level access control, redact PII, apply jurisdiction-based data residency rules,
and route audit events to a compliance log. In this assignment it simulates that
layer without requiring a full backend.

---

## 5. Preventing Infinite Loops

The agent cannot loop more than 8 times. This is enforced in code, not by prompt
instruction, through a step counter that is checked at the top of every iteration:

```python
if step >= MAX_STEPS:
    return structured_refusal_dict
```

The check fires before the LLM is called, so even if the model emits a tool call
on step 8, the cap fires before the tool is dispatched. The refusal is a
structured dict (not an exception) so calling code can inspect `status`,
`steps_used`, and the partial `trace`.

Questions designed to cause a loop — for example, a question with no answer in
any of the three sources — will exhaust the cap and return the structured refusal.
This is demonstrated in evaluation questions EQ-17 and EQ-18.

---

## 6. Tool Routing Logic

Tool selection is performed entirely by the LLM, guided by the descriptions in
`tool_schemas.py`. The agent loop does not contain any keyword matching or
routing rules. The descriptions are the only routing mechanism.

Design choices that improve routing accuracy:
- Each description includes an explicit "wrong tool" paragraph, telling the model
  which tool **not** to use for a given type of question.
- The `query_data` description lists the exact column names in the database, so
  the model can form valid SQL without hallucinating column names.
- The `web_search` description includes a negative instruction ("Do NOT use this
  tool speculatively as a fallback") which reduces gratuitous web calls.

---

## 7. Multi-Tool Composition

For questions that require both a number and an explanation, the LLM naturally
chains tools: it calls `query_data` for the metric, then `search_docs` for the
commentary, then composes an answer that cites both `stnapt_trace_id` values.
The message history accumulates all tool results, so the LLM has full context
when composing the final answer.

---

## 8. Known Failure Modes

1. **Natural-language to SQL translation is brittle.** The `_natural_to_sql()`
   helper in `query_data.py` uses keyword matching. Questions phrased unusually
   may produce wrong SQL. Mitigation: the LLM is shown the schema and often
   produces valid SQL directly, bypassing the keyword fallback.

2. **Retrieval quality degrades on vague queries.** If the user asks "what did
   the companies say about margins" without specifying a year or company,
   `search_docs` returns chunks from multiple companies and years, which can
   confuse the answer composition step.

3. **`web_search` results are unverified.** The `clearance` tag signals this,
   but the LLM can still incorporate incorrect live data. The system prompt
   instructs the model to prefer `search_docs` and `query_data` for historical
   information.

4. **Hard cap produces partial answers.** If a multi-hop question requires more
   than 8 retrieval steps, the agent returns a refusal instead of a partial
   answer. This is intentional — a partial answer with missing citations is
   worse than an honest refusal.

---

## 9. File Map

```
agent.py                    Core agent loop + stnapt_context_interceptor()
tools/
  tool_schemas.py           LLM-facing tool definitions (name, description, input schema)
  search_docs.py            Chroma vector store wrapper
  query_data.py             SQLite / pandas query wrapper
  web_search.py             Tavily API wrapper
data/
  chroma_store/             Local vector store (built by ingest.py)
  financials.db             SQLite database (built by build_db.py)
scripts/
  ingest.py                 Chunk PDFs, embed, write to Chroma
  build_db.py               Populate financials.db from the hand-built CSV
  verify_tools.py           Run 5 retrieval + 3 SQL queries to confirm tool quality
eval/
  questions.py              20 evaluation questions with expected answers
  run_eval.py               Run all 20 questions and write results to eval_results.json
EVALUATION.md               Evaluation report with actual agent outputs
README.md                   Setup and run instructions
.env.example                Required environment variables (no real keys)
requirements.txt            Python dependencies
```
