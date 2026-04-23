"""
agent.py
--------
Stnapt.ai Agentic RAG — core agent loop.
ReAct-style (Reason → Act → Observe) with an 8-step hard cap.
The stnapt_context_interceptor() wraps every tool result with
enterprise governance metadata before it re-enters the LLM context.

Author: [your name]
Corpus: Indian IT Financials (Infosys, TCS, Wipro) — Option A
"""

import uuid
import json
import anthropic
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from tools.tool_schemas import TOOLS
from tools.search_docs import run as search_docs
from tools.query_data import run as query_data
from tools.web_search import run as web_search

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_STEPS   = 8
MODEL       = "claude-opus-4-6"
console     = Console()

# ─── Stnapt Context Interceptor ───────────────────────────────────────────────

def stnapt_context_interceptor(tool_name: str, raw_output: dict, step: int) -> dict:
    """
    Governance middleware. Every tool result passes through here before it is
    appended to the agent context or shown to the LLM.

    Adds:
      - stnapt_trace_id   : globally unique ID for this specific retrieval event.
                            The LLM is instructed to cite this in its final answer.
      - data_source_verified : True signals the payload came from a known,
                               controlled source — not arbitrary internet content.
      - clearance         : data classification tag. Agents operating behind the
                            Stnapt governance firewall use this to decide whether
                            a result can be shared with a given audience.
      - intercepted_at    : UTC timestamp of interception, for audit logs.
    """
    trace_id = f"SNPT-{uuid.uuid4().hex[:8].upper()}"

    clearance_map = {
        "search_docs": "PUBLIC_FINANCIALS",
        "query_data":  "PUBLIC_FINANCIALS",
        "web_search":  "LIVE_WEB_UNVERIFIED",
    }

    wrapped = {
        "stnapt_trace_id":       trace_id,
        "step":                  step,
        "tool":                  tool_name,
        "data_source_verified":  tool_name != "web_search",   # live web is unverified
        "clearance":             clearance_map.get(tool_name, "UNKNOWN"),
        "intercepted_at":        datetime.now(timezone.utc).isoformat(),
        "payload":               raw_output,
    }

    _log_interception(wrapped)
    return wrapped


def _log_interception(ctx: dict) -> None:
    """Render a structured Stnapt interception panel to the terminal."""
    verified_str  = "[green]✓ VERIFIED[/green]" if ctx["data_source_verified"] else "[yellow]~ LIVE WEB[/yellow]"
    clearance_col = "green" if "PUBLIC" in ctx["clearance"] else "yellow"

    table = Table(box=box.MINIMAL, show_header=False, padding=(0, 1))
    table.add_column("key",   style="dim", width=24)
    table.add_column("value", style="bold")
    table.add_row("trace_id",   f"[cyan]{ctx['stnapt_trace_id']}[/cyan]")
    table.add_row("tool",       ctx["tool"])
    table.add_row("verified",   verified_str)
    table.add_row("clearance",  f"[{clearance_col}]{ctx['clearance']}[/{clearance_col}]")
    table.add_row("step",       f"{ctx['step']} / {MAX_STEPS}")
    table.add_row("at",         ctx["intercepted_at"])

    console.print(Panel(table, title="[bold]⬡ stnapt.ai  interception[/bold]",
                        border_style="cyan", expand=False))


# ─── Tool Dispatcher ──────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_docs": search_docs,
    "query_data":  query_data,
    "web_search":  web_search,
}

def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """Call the named tool and return its raw output dict."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except Exception as exc:
        return {"error": str(exc), "tool": tool_name}


# ─── Agent Loop ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a financial research agent operating behind the stnapt.ai
enterprise governance firewall. Every piece of information you receive from a tool
has been intercepted and tagged with a stnapt_trace_id by the Stnapt context layer.

Rules you must follow:
1. You have access to three tools: search_docs, query_data, and web_search.
   Use each only for its stated purpose. Prefer query_data for numbers,
   search_docs for qualitative explanations, web_search for live/recent data.
2. When you compose your final answer, every factual claim must include the
   stnapt_trace_id of the tool result it came from, in the format [SNPT-XXXXXXXX].
3. If you cannot answer the question from the available tools and data,
   say so clearly. Do NOT guess or hallucinate numbers.
4. For questions that are outside your domain (investment advice, personal opinions,
   unrelated topics), refuse politely without calling any tool.
5. You are operating inside a loop with a hard cap of 8 tool calls.
   Be efficient: plan before you act."""


def run_agent(question: str) -> dict:
    """
    Main agent loop. ReAct style: the LLM reasons, calls a tool,
    observes the result, and repeats until it can answer or hits the cap.

    Returns a dict with keys: answer, citations, trace, steps_used.
    """
    client   = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]
    trace    = []
    step     = 0

    console.print(f"\n[bold cyan]◆ STNAPT AGENT[/bold cyan]  [dim]question:[/dim] {question}\n")

    while True:

        # ── Hard cap enforcement ──────────────────────────────────────────────
        if step >= MAX_STEPS:
            refusal = {
                "answer":     (
                    "The agent reached the 8-step hard cap without producing a "
                    "complete answer. This question may require information not "
                    "available in the current corpus, or the retrieval chain is "
                    "not converging. Please rephrase or check your data sources."
                ),
                "citations":  [],
                "trace":      trace,
                "steps_used": step,
                "status":     "HARD_CAP_REACHED",
            }
            console.print(Panel("[bold red]⚠  HARD CAP REACHED[/bold red]  —  returning structured refusal",
                                border_style="red"))
            return refusal

        # ── LLM reason step ──────────────────────────────────────────────────
        response = client.messages.create(
            model      = MODEL,
            max_tokens = 1024,
            system     = SYSTEM_PROMPT,
            tools      = TOOLS,
            messages   = messages,
        )

        # ── Terminal: no tool call → final answer ────────────────────────────
        if response.stop_reason == "end_turn":
            answer_text = "".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            console.print(Panel(
                f"[bold green]✓ FINAL ANSWER[/bold green]\n\n{answer_text}",
                border_style="green"
            ))
            return {
                "answer":     answer_text,
                "citations":  _extract_trace_ids(trace),
                "trace":      trace,
                "steps_used": step,
                "status":     "SUCCESS",
            }

        # ── Act: execute every tool_use block in this response ────────────────
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            step += 1
            tool_name  = block.name
            tool_input = block.input

            console.print(f"[dim]step {step}[/dim]  [bold]{tool_name}[/bold]  input={json.dumps(tool_input)[:120]}")

            # Dispatch → intercept → log
            raw_output  = dispatch_tool(tool_name, tool_input)
            ctx_payload = stnapt_context_interceptor(tool_name, raw_output, step)

            trace.append({
                "step":     step,
                "tool":     tool_name,
                "input":    tool_input,
                "trace_id": ctx_payload["stnapt_trace_id"],
                "output":   raw_output,
            })

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     json.dumps(ctx_payload),   # LLM sees the full wrapped payload
            })

        # ── Append assistant turn + all tool results to messages ─────────────
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_trace_ids(trace: list) -> list[dict]:
    return [{"step": t["step"], "tool": t["tool"], "trace_id": t["trace_id"]} for t in trace]


def print_trace_report(result: dict) -> None:
    """Pretty-print the full trace report to the terminal."""
    console.rule("[bold cyan]⬡ stnapt.ai  trace report[/bold cyan]")
    for entry in result["trace"]:
        console.print(
            f"  [dim]step {entry['step']}[/dim]  "
            f"tool=[bold]{entry['tool']}[/bold]  "
            f"trace=[cyan]{entry['trace_id']}[/cyan]  "
            f"input={json.dumps(entry['input'])[:80]}"
        )
    console.print(f"\n  Steps used: [bold]{result['steps_used']}[/bold] / {MAX_STEPS}")
    console.print(f"  Status:     [bold]{result['status']}[/bold]")
    console.rule()


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Question: ")
    result = run_agent(q)
    print_trace_report(result)
