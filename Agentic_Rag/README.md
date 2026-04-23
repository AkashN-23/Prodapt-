# Stnapt Agentic RAG

A small LLM reasoning agent that answers questions over mixed data sources — annual report PDFs, a structured financials table, and live web search — using a ReAct-style loop with an enterprise governance middleware layer.

**Corpus:** Indian IT Financials — Infosys, TCS, Wipro (FY2021–FY2024)  
**Model:** Anthropic Claude (configurable via `AGENT_MODEL` in `.env`)  
**Stack:** Python · ChromaDB · SQLite · Tavily · Rich

---

## How the agent works

The agent loop in `agent.py` follows the **ReAct pattern** (Reason → Act → Observe) implemented as a plain `while` loop with no framework wrappers.

```
1. User question enters the loop.
2. LLM receives the question, full message history, and three tool schemas.
3. If the LLM returns stop_reason = end_turn  →  extract final answer and exit.
4. If the LLM returns tool_use blocks:
     for each block:
       a. Increment step counter.
       b. If step > 8  →  return structured refusal immediately (hard cap).
       c. Dispatch the named tool.
       d. Pass raw output through stnapt_context_interceptor().
       e. Append wrapped result to message history and trace log.
5. Go to step 2.
```

The loop has exactly two exit paths: a final answer, or the 8-step hard cap. Both are handled as structured return values — the caller can always inspect `status`, `steps_used`, and `trace`.

---

## The Stnapt context layer

Every tool result passes through `stnapt_context_interceptor()` before the LLM sees it. The interceptor wraps the raw payload with four governance fields:

| Field | Example value | Purpose |
|---|---|---|
| `stnapt_trace_id` | `SNPT-3F8A2C1D` | Unique citation handle for this retrieval event |
| `data_source_verified` | `True` / `False` | `False` for live web results, `True` for controlled sources |
| `clearance` | `PUBLIC_FINANCIALS` | Data classification tag |
| `intercepted_at` | `2024-09-01T10:32:11Z` | UTC audit timestamp |

The system prompt instructs the LLM that every factual claim in its final answer must include the `stnapt_trace_id` of the result it came from, in the format `[SNPT-XXXXXXXX]`. Citations are therefore machine-readable and traceable to a specific retrieval event — not just a tool name.

In a production deployment this layer is where you would enforce row-level access control, redact PII, and route events to a compliance log. Here it simulates that contract without requiring a backend.

---

## Setup

Requires Python 3.11+.

```bash
git clone <your-repo-url>
cd stnapt-agentic-rag

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and TAVILY_API_KEY
```

### 1. Build the financials database

Add your hand-built CSV at `data/financials.csv` with columns:
`company, fiscal_year, revenue_usd_bn, operating_margin_pct, net_profit_usd_bn, eps_inr, headcount`

```bash
python scripts/build_db.py
# Output: data/financials.db
```

Verify manually before continuing:
```bash
sqlite3 data/financials.db "SELECT * FROM financials LIMIT 5;"
```

### 2. Ingest annual report PDFs

Place the three annual report PDFs in `data/pdfs/`:
- `infosys_ar_fy24.pdf`
- `tcs_ar_fy24.pdf`
- `wipro_ar_fy24.pdf`

(Download free from each company's investor relations website.)

```bash
python scripts/ingest.py
# Chunks, embeds, and writes to data/chroma_store/
```

Verify retrieval quality before wiring the agent:
```bash
python scripts/verify_tools.py
# Runs 5 doc queries and 3 SQL queries; prints results for manual inspection
```

---

## Running the agent

**Interactive CLI:**
```bash
python agent.py "What was Infosys' operating margin in FY2024?"
```

**Single question, piped:**
```bash
echo "Compare TCS and Wipro revenue FY2023" | python agent.py
```

The terminal output shows each Stnapt interception panel as it fires, followed by the final answer and a trace report.

---

## Running the evaluation

```bash
python scripts/run_eval.py
```

This runs all 23 questions in `eval/questions.py` against the live agent, writes `EVALUATION.md` to the repo root, and dumps raw results to `eval/eval_results.json`. The hard cap question (EQ-18) and the refusal questions (EQ-16, EQ-17, EQ-19) are included in the run — do not skip them.

Expected runtime: 5–12 minutes depending on model and API latency. Use `AGENT_MODEL=claude-haiku-4-5-20251001` in `.env` to keep costs low during development.

---

## Project structure

```
agent.py                    Core loop + stnapt_context_interceptor()
tools/
  tool_schemas.py           LLM-facing tool definitions
  search_docs.py            ChromaDB semantic search wrapper
  query_data.py             SQLite / pandas query wrapper
  web_search.py             Tavily API wrapper
scripts/
  ingest.py                 Chunk PDFs and write to ChromaDB
  build_db.py               Populate financials.db from CSV
  verify_tools.py           Manual retrieval quality checks
  run_eval.py               Run eval set and write EVALUATION.md
eval/
  questions.py              23 evaluation questions
  eval_results.json         Generated by run_eval.py (gitignored)
data/
  pdfs/                     Annual report PDFs (gitignored)
  chroma_store/             Vector store (gitignored)
  financials.db             SQLite database (gitignored)
  financials.csv            Source data for build_db.py
DESIGN.md                   Agent loop and tool schema documentation
EVALUATION.md               Generated evaluation report
.env.example                Required environment variables (no real keys)
requirements.txt
```

---

## Known limitations

**Natural-language to SQL translation is brittle.** The keyword-based fallback in `query_data.py` handles common question patterns but fails on unusual phrasing. The LLM often generates valid SQL directly from the schema description, which bypasses the fallback — but this cannot be guaranteed.

**Retrieval degrades on vague queries.** When the user omits a company name or fiscal year, `search_docs` returns chunks from multiple sources and years. The LLM may conflate them in the composed answer. The system prompt does not currently instruct the model to ask for clarification before calling a tool.

**Hard cap produces a full refusal rather than a partial answer.** This is intentional — a partial answer with uncited claims is worse than an honest refusal. However, it means some genuinely answerable multi-hop questions that require more than 8 steps will be refused rather than partially answered. A per-tool error counter would allow earlier graceful termination.

**Live web results are unverified.** The `clearance: LIVE_WEB_UNVERIFIED` tag signals this to the LLM, but the model can still incorporate incorrect information from `web_search`. Historical financial questions should always use `query_data` or `search_docs` rather than web search, and the tool descriptions are written to enforce this.

**No cross-session memory.** Each `run_agent()` call is stateless. Follow-up questions cannot reference a previous answer.

---

## Disclosure

AI coding assistants (Claude) were used during development. All design decisions — tool schema wording, loop structure, the Stnapt interceptor contract — are the author's own and can be explained and defended line by line.
