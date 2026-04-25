#!/usr/bin/env python3
"""
demo.py
-------
Interactive CLI for the Stnapt Agentic RAG system.
Run:  python3 demo.py
Type a question and press Enter. Type 'exit' or 'quit' to stop.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent, print_trace_report
from rich.console import Console
from rich.panel import Panel

console = Console()

BANNER = """
[bold cyan]
  ┌─────────────────────────────────────────────┐
  │         ⬡  stnapt.ai  Agent Demo            │
  │   Indian IT Financials  ·  Infosys/TCS/Wipro │
  │   Type [bold white]exit[/bold white][bold cyan] to quit                          │
  └─────────────────────────────────────────────┘
[/bold cyan]"""

SUGGESTED = [
    "1  →  What was Infosys operating margin in FY2024?",
    "2  →  What reason did TCS give for its margin performance in FY2024?",
    "3  →  What is the current stock price of Infosys?",
    "4  →  How did Infosys and TCS margins compare in FY2024, and what drove each?",
    "5  →  Show revenue growth for all 3 companies FY2021 to FY2024.",
    "6  →  Which company should I invest in right now?   (refusal demo)",
    "7  →  What was Wipro revenue in FY2019?             (out-of-scope demo)",
    "8  →  Quarterly revenue breakdown FY2010 to FY2024  (hard cap demo)",
]


def main():
    console.print(BANNER)
    console.print("[dim]Suggested demo questions:[/dim]\n")
    for s in SUGGESTED:
        console.print(f"  [dim]{s}[/dim]")
    console.print()

    while True:
        try:
            question = console.input("[bold cyan]⬡  Ask>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Bye.[/dim]")
            break

        result = run_agent(question)
        print_trace_report(result)
        console.print()


if __name__ == "__main__":
    main()