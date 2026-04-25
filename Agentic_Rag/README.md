# Stnapt Agentic RAG

A ReAct-style LLM agent that answers questions over mixed data sources — annual
report PDFs, a structured financials table, and live web search — with an
enterprise governance middleware layer called the **Stnapt Context Interceptor**.

**Corpus:** Indian IT Financials — Infosys, TCS, Wipro (FY2021–FY2024)  
**Model:** Anthropic Claude (`claude-haiku-4-5-20251001` for dev, configurable)  
**Stack:** Python · ChromaDB · SQLite · Tavily · Rich

---

## What this agent does

Most financial questions cannot be answered from a single source. A question like
*"How did Infosys and TCS margins compare in FY2024, and what drove each?"*
requires a precise number from a structured table **and** a qualitative explanation
from a 300-page annual report PDF. A single RAG pipeline cannot do this well.

This agent decides which tool to call for each question, chains tools when needed,
and composes a final answer that cites the exact source — down to the page number
or CSV row — for every factual claim.

---

## How the agent loop works

The loop in `agent.py` follows the **ReAct pattern** (Reason → Act → Observe),
implemented as a plain Python `while` loop. There are no framework wrappers.

```
1.  Receive user question.
2.  Send question + full message history + tool schemas to the LLM.
3.  If LLM returns a final answer (no tool call)  →  exit loop.
4.  If LLM returns tool_use blocks:
      for each block:
        a. Increment step counter.
        b. If step > 8  →  return structured refusal (hard cap).
        c. Dispatch the named tool.
        d. Pass raw output through stnapt_context_interceptor().
        e. Append wrapped result to message history and trace log.
5.  Go to step 2.
```

The loop has exactly two exit paths: a final answer, or the 8-step hard cap.
Both return a structured dict with `status`, `steps_used`, `trace`, and `citations`.

---

## The Stnapt context layer

Every tool result passes through `stnapt_context_interceptor()` before the LLM
sees it. The interceptor wraps the raw payload with four governance fields:

| Field | Example | Purpose |
|---|---|---|
| `stnapt_trace_id` | `SNPT-145D8C4A` | Unique citation handle for this retrieval event |
| `data_source_verified` | `True` | `False` for live web, `True` for controlled sources |
| `clearance` | `PUBLIC_FINANCIALS` | Data classification tag |
| `intercepted_at` | `2026-04-25T09:24:42Z` | UTC audit timestamp |

The system prompt instructs the LLM to cite the `stnapt_trace_id` in every
factual claim in its final answer, in the format `[SNPT-XXXXXXXX]`. Citations
are therefore machine-readable and traceable to a specific retrieval event —
not just a tool name.

**Example of a correctly cited answer:**
```
Infosys reported an operating margin of 20.7% in FY2024 [SNPT-145D8C4A].
```

In a production deployment this layer is where you would enforce row-level
access control, redact PII, apply data residency rules, and route events to a
compliance audit log.

---

## The three tools

| Tool | Purpose | Routes to |
|---|---|---|
| `search_docs` | Semantic search over annual report PDFs | ChromaDB vector store |
| `query_data` | Precise numbers and comparisons from structured data | SQLite (`financials` table) |
| `web_search` | Live or recent information only | Tavily API |

Tool selection is done entirely by the LLM using the descriptions in
`tools/tool_schemas.py`. Each description includes an explicit **"wrong tool
for"** paragraph so the model knows when *not* to call each tool.

---

## Setup

Requires Python 3.10+.

```bash
git clone <your-repo-url>
cd Agentic_Rag

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Open .env and add your ANTHROPIC_API_KEY and TAVILY_API_KEY
```

### Build the database

```bash
python scripts/build_db.py
# Creates data/financials.db from data/financials.csv
# Verify: sqlite3 data/financials.db "SELECT * FROM financials LIMIT 4;"
```

### Index the PDFs

Place the three annual report PDFs in `data/pdfs/`:
```
data/pdfs/infosys_ar_fy24.pdf
data/pdfs/tcs_ar_fy24.pdf
data/pdfs/wipro_ar_fy24.pdf
```
Download free from each company's investor relations website, then:
```bash
python scripts/ingest.py
# Chunks, embeds, writes to data/chroma_store/
# Takes 3–8 minutes depending on PDF size
```

**Verify both tools manually before running the agent:**
```bash
# Structured data check
sqlite3 data/financials.db \
  "SELECT company, fiscal_year, operating_margin_pct FROM financials;"

# Semantic search check
python -c "from tools.search_docs import run; \
           import json; print(json.dumps(run('Infosys operating margin FY24'), indent=2))"
```

Only proceed to the agent once both return sensible results.

---

## Running the agent

**Interactive demo (recommended):**
```bash
python3 demo.py
```

You will see a prompt with suggested questions. Type any question and press Enter.
Type `exit` to quit.

**Single question via CLI:**
```bash
python3 agent.py "What was TCS operating margin in FY2024?"
```

**Sample output:**
```
◆ STNAPT AGENT  question: What was Infosys operating margin in FY2024

step 1  query_data  input={"query": "SELECT operating_margin_pct ..."}
╭──── ⬡ stnapt.ai  interception ────╮
│  trace_id   SNPT-145D8C4A         │
│  tool       query_data            │
│  verified   ✓ VERIFIED            │
│  clearance  PUBLIC_FINANCIALS     │
│  step       1 / 8                 │
╰───────────────────────────────────╯
✓ FINAL ANSWER
Infosys reported an operating margin of 20.7% in FY2024 [SNPT-145D8C4A].

Steps used: 1 / 8  |  Status: SUCCESS
```

---

## Running the evaluation

```bash
python3 scripts/run_eval.py
```

Runs all 23 questions in `eval/questions.py` against the live agent and writes:
- `EVALUATION.md` — formatted report with traces, verdicts, and failure analysis
- `eval/eval_results.json` — raw output for further analysis

Expected runtime: 5–12 minutes. Use `claude-haiku-4-5-20251001` in `.env` during
development to keep API costs low (approx ₹50–100 for a full eval run).

---

## Project structure

```
agent.py                    Core loop + stnapt_context_interceptor()
demo.py                     Interactive CLI with suggested questions
tools/
  tool_schemas.py           LLM-facing tool definitions (name, description, schema)
  search_docs.py            ChromaDB semantic search wrapper
  query_data.py             SQLite / pandas query wrapper
  web_search.py             Tavily API wrapper
scripts/
  ingest.py                 Chunk PDFs, embed, write to ChromaDB
  build_db.py               Load financials.csv into SQLite
  build_financials_csv.py   Rebuild financials.csv from source data
  run_eval.py               Run eval set and write EVALUATION.md
eval/
  questions.py              23 evaluation questions across 4 categories
  eval_results.json         Generated by run_eval.py (gitignored)
data/
  pdfs/                     Annual report PDFs (gitignored)
  chroma_store/             ChromaDB vector store (gitignored)
  financials.db             SQLite database (gitignored)
  financials.csv            Source data — 12 rows, 3 companies, FY2021–FY2024
DESIGN.md                   Agent loop and tool schema documentation
EVALUATION.md               Evaluation report with actual agent outputs
.env.example                Required environment variables — no real keys
requirements.txt            Python dependencies
```

---

## Known limitations

**Natural-language to SQL translation is brittle.** The keyword fallback in
`query_data.py` handles standard phrasing but fails on unusual sentence
structures. The LLM usually generates valid SQL directly from the schema
description, bypassing the fallback — but this cannot be guaranteed for all
inputs.

**Out-of-corpus years are handled gracefully, not refused.** When asked for
FY2019 data, the agent correctly states the data is unavailable and shows what
years are available, then offers a web search fallback. It does not hallucinate
a number. This behaviour is intentional and verified in EQ-22 of the eval set.

**Hard cap returns a full refusal, not a partial answer.** Questions requiring
more than 8 retrieval steps return `HARD_CAP_REACHED` rather than a partial
answer. This is intentional — an uncited partial answer is worse than an honest
refusal.

**Web search results are unverified.** The `clearance: LIVE_WEB_UNVERIFIED`
tag signals this to the LLM. Historical financial questions should always use
`query_data` or `search_docs`. The tool descriptions enforce this explicitly.

**No cross-session memory.** Each `run_agent()` call is stateless. Follow-up
questions cannot reference a previous answer in the same conversation.

---

## Evaluation summary

| Category | Questions | Notes |
|---|---|---|
| Single-tool | 9 | Routed correctly in all tested cases |
| Multi-tool | 6 | Chains `query_data` + `search_docs` as expected |
| Refusal | 4 | Zero tool calls for out-of-domain questions |
| Edge cases | 4 | Out-of-corpus years, vague queries, ambiguous phrasing |

Full results with actual agent outputs in `EVALUATION.md`.

---

## Disclosure

AI coding assistants (Claude) were used during development. All design
decisions — tool schema wording, loop structure, the Stnapt interceptor
contract, the hard cap implementation — are the author's own and can be
explained and defended line by line during a live review.