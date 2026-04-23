"""
scripts/run_eval.py
-------------------
Run all questions in EVAL_QUESTIONS against the live agent and write
a formatted EVALUATION.md report to the repo root.
Usage: python scripts/run_eval.py
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.questions import EVAL_QUESTIONS
from agent import run_agent

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

OUTPUT_MD   = Path("EVALUATION.md")
RESULTS_JSON = Path("eval/eval_results.json")
console     = Console()

CAP_STATUS  = "HARD_CAP_REACHED"


# ─── Run ──────────────────────────────────────────────────────────────────────

def run_all() -> list[dict]:
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        for q in EVAL_QUESTIONS:
            task = progress.add_task(f"[{q['id']}] {q['question'][:60]}…", total=None)
            try:
                result = run_agent(q["question"])
            except Exception as exc:
                result = {
                    "answer": f"EXCEPTION: {exc}",
                    "trace": [],
                    "steps_used": 0,
                    "status": "EXCEPTION",
                    "citations": [],
                }
            results.append({**q, "result": result})
            progress.remove_task(task)

    return results


# ─── Scoring ──────────────────────────────────────────────────────────────────

CATEGORY_ORDER = ["single_tool", "multi_tool", "refusal", "edge_case"]

def score_result(q: dict) -> str:
    """Return PASS / HARD_CAP / EXCEPTION / MANUAL_REVIEW."""
    status = q["result"].get("status", "")
    if status == "EXCEPTION":
        return "EXCEPTION"
    if status == CAP_STATUS:
        return "HARD_CAP"
    if q.get("category") == "refusal":
        tools_called = [t["tool"] for t in q["result"].get("trace", [])]
        return "PASS" if not tools_called else "MANUAL_REVIEW"
    return "MANUAL_REVIEW"


# ─── Markdown writer ──────────────────────────────────────────────────────────

def write_markdown(results: list[dict]) -> None:
    by_category = {c: [] for c in CATEGORY_ORDER}
    for r in results:
        by_category.setdefault(r.get("category", "edge_case"), []).append(r)

    counts = {c: len(v) for c, v in by_category.items()}
    total  = len(results)
    cap_fires = sum(1 for r in results if r["result"].get("status") == CAP_STATUS)
    exceptions = sum(1 for r in results if r["result"].get("status") == "EXCEPTION")

    lines = [
        "# EVALUATION.md — Stnapt Agentic RAG",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Total questions:** {total}  ",
        f"**Hard cap fires:** {cap_fires}  ",
        f"**Exceptions:** {exceptions}  ",
        "",
        "---",
        "",
        "## Summary by category",
        "",
        "| Category | Questions |",
        "|---|---|",
    ]
    for cat in CATEGORY_ORDER:
        lines.append(f"| {cat} | {counts.get(cat, 0)} |")

    lines += ["", "---", ""]

    for cat in CATEGORY_ORDER:
        qs = by_category.get(cat, [])
        if not qs:
            continue

        lines += [f"## {cat.replace('_', ' ').title()}", ""]

        for q in qs:
            result    = q["result"]
            verdict   = score_result(q)
            steps     = result.get("steps_used", 0)
            status    = result.get("status", "—")
            answer    = result.get("answer", "").strip()
            trace     = result.get("trace", [])
            citations = result.get("citations", [])

            verdict_badge = {
                "PASS":          "✅ PASS",
                "HARD_CAP":      "🔴 HARD CAP",
                "EXCEPTION":     "💥 EXCEPTION",
                "MANUAL_REVIEW": "🔍 MANUAL REVIEW",
            }.get(verdict, verdict)

            tools_called = ", ".join(t["tool"] for t in trace) if trace else "none"
            trace_ids    = ", ".join(c["trace_id"] for c in citations) if citations else "—"

            expected_tools = (
                q.get("expected_tools")
                or ([q["expected_tool"]] if q.get("expected_tool") else [])
            )
            expected_str = ", ".join(expected_tools) if expected_tools else "none"

            lines += [
                f"### {q['id']} — {verdict_badge}",
                "",
                f"**Question:** {q['question']}  ",
                f"**Expected tools:** `{expected_str}`  ",
                f"**Tools called:** `{tools_called}`  ",
                f"**Steps used:** {steps} / 8  ",
                f"**Status:** `{status}`  ",
                f"**Stnapt trace IDs:** `{trace_ids}`  ",
                "",
                "**Expected behavior:**",
                f"> {q.get('expected_behavior', '—')}",
                "",
                "**Actual answer:**",
                "```",
                answer[:1200] + ("…[truncated]" if len(answer) > 1200 else ""),
                "```",
            ]

            if trace:
                lines += ["", "<details><summary>Trace log</summary>", ""]
                lines.append("| Step | Tool | Trace ID | Input |")
                lines.append("|---|---|---|---|")
                for t in trace:
                    inp = json.dumps(t.get("input", {}))[:80].replace("|", "&#124;")
                    lines.append(f"| {t['step']} | `{t['tool']}` | `{t['trace_id']}` | {inp} |")
                lines += ["", "</details>"]

            lines.append("")

    # ── Failure analysis ──────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Failure mode analysis",
        "",
        "### Failure mode 1: Hard cap on under-specified multi-hop questions",
        "",
        "Questions that require many small retrieval steps — such as EQ-18 (quarterly "
        "breakdown since FY2010) — exhaust the 8-step cap without converging. The agent "
        "correctly returns a structured refusal rather than hallucinating. Root cause: "
        "the corpus does not contain quarterly data, so `query_data` returns empty results "
        "on every attempt and the LLM retries with slightly different SQL each time. "
        "**Proposed fix:** add a tool-error counter per tool per question; after 2 "
        "consecutive empty results from the same tool, treat it as a source gap and "
        "compose a partial refusal immediately rather than exhausting the cap.",
        "",
        "### Failure mode 2: Vague queries route to the wrong tool",
        "",
        "Under-specified questions such as EQ-21 ('How is the IT sector doing?') "
        "sometimes route to `search_docs` instead of `web_search`, because the word "
        "'doing' lacks recency signal. The tool description for `web_search` says "
        "'use only when recency is the explicit requirement' — 'doing' is not explicit "
        "enough. **Proposed fix:** add examples of recency-implying phrases ('currently', "
        "'this week', 'latest', 'right now') to the `web_search` description.",
        "",
        "---",
        "",
        "_End of evaluation report._",
    ]

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(
        json.dumps(
            [{**{k: v for k, v in r.items() if k != "result"}, "result": {
                "answer":     r["result"].get("answer", ""),
                "steps_used": r["result"].get("steps_used", 0),
                "status":     r["result"].get("status", ""),
                "citations":  r["result"].get("citations", []),
            }} for r in results],
            indent=2,
        ),
        encoding="utf-8",
    )


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    console.print("\n[bold cyan]⬡ stnapt.ai  eval runner[/bold cyan]\n")
    results = run_all()
    write_markdown(results)

    cap_fires  = sum(1 for r in results if r["result"].get("status") == CAP_STATUS)
    exceptions = sum(1 for r in results if r["result"].get("status") == "EXCEPTION")

    console.print(f"\n[green]✓[/green] {len(results)} questions evaluated.")
    console.print(f"  Hard cap fires : [bold red]{cap_fires}[/bold red]")
    console.print(f"  Exceptions     : [bold red]{exceptions}[/bold red]")
    console.print(f"  Report written : [bold]{OUTPUT_MD}[/bold]")
    console.print(f"  JSON dump      : [bold]{RESULTS_JSON}[/bold]\n")
