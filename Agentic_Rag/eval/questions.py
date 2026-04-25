"""
eval/questions.py
-----------------
20 evaluation questions covering all four required categories.
Run via: python eval/run_eval.py
"""

EVAL_QUESTIONS = [

    # ── Single-tool: query_data (6 questions) ─────────────────────────────────
    {
        "id": "EQ-01",
        "category": "single_tool",
        "question": "What was Infosys' operating margin in FY2024?",
        "expected_tool": "query_data",
        "expected_behavior": "Returns a single percentage value with row citation.",
    },
    {
        "id": "EQ-02",
        "category": "single_tool",
        "question": "Show me Wipro's revenue in USD billion for each of the last 4 years.",
        "expected_tool": "query_data",
        "expected_behavior": "Returns a 4-row table, one row per fiscal year.",
    },
    {
        "id": "EQ-03",
        "category": "single_tool",
        "question": "Which of the three companies had the highest EPS in FY2023?",
        "expected_tool": "query_data",
        "expected_behavior": "Compares EPS across all three companies for FY2023.",
    },
    {
        "id": "EQ-04",
        "category": "single_tool",
        "question": "What was TCS headcount at the end of FY2022?",
        "expected_tool": "query_data",
        "expected_behavior": "Single integer from the headcount column.",
    },
    {
        "id": "EQ-05",
        "category": "single_tool",
        "question": "Compare net profit for Infosys and TCS in FY2024.",
        "expected_tool": "query_data",
        "expected_behavior": "Two-row table or side-by-side comparison.",
    },
    {
        "id": "EQ-06",
        "category": "single_tool",
        "question": "What is the trend in Wipro operating margin from FY2021 to FY2024?",
        "expected_tool": "query_data",
        "expected_behavior": "4-row table showing operating_margin_pct by year.",
    },

    # ── Single-tool: search_docs (3 questions) ────────────────────────────────
    {
        "id": "EQ-07",
        "category": "single_tool",
        "question": "What reason did TCS give for its margin improvement in FY2024?",
        "expected_tool": "search_docs",
        "expected_behavior": "Qualitative explanation from MD&A with page citation.",
    },
    {
        "id": "EQ-08",
        "category": "single_tool",
        "question": "What strategic priorities did Infosys highlight in their FY2024 annual report?",
        "expected_tool": "search_docs",
        "expected_behavior": "Bullet-point summary with source file and page.",
    },
    {
        "id": "EQ-09",
        "category": "single_tool",
        "question": "How did Wipro describe their cloud and AI strategy in FY2024?",
        "expected_tool": "search_docs",
        "expected_behavior": "Paragraph summarising cloud/AI strategy with citation.",
    },

    # ── Multi-tool (6 questions) ───────────────────────────────────────────────
    {
        "id": "EQ-10",
        "category": "multi_tool",
        "question": (
            "How did Infosys' and TCS' operating margins compare in FY2024, "
            "and what drove each company's performance?"
        ),
        "expected_tools": ["query_data", "search_docs"],
        "expected_behavior": (
            "Numbers from query_data; explanations from search_docs. "
            "Final answer cites both stnapt_trace_ids."
        ),
    },
    {
        "id": "EQ-11",
        "category": "multi_tool",
        "question": (
            "Compare headcount growth at all 3 companies over the last 4 years "
            "and explain what Infosys said about hiring in their annual report."
        ),
        "expected_tools": ["query_data", "search_docs"],
        "expected_behavior": "Table from query_data + hiring commentary from search_docs.",
    },
    {
        "id": "EQ-12",
        "category": "multi_tool",
        "question": (
            "What is the current analyst consensus rating for TCS stock, "
            "and how does that compare with TCS' reported net profit trend?"
        ),
        "expected_tools": ["web_search", "query_data"],
        "expected_behavior": "Live analyst rating from web_search + profit trend from query_data.",
    },
    {
        "id": "EQ-13",
        "category": "multi_tool",
        "question": (
            "What was Wipro's revenue in FY2024, and what major deals or "
            "partnerships did they announce that year?"
        ),
        "expected_tools": ["query_data", "search_docs"],
        "expected_behavior": "Revenue number + deal/partnership detail from AR text.",
    },
    {
        "id": "EQ-14",
        "category": "multi_tool",
        "question": (
            "How have Infosys margins changed over 4 years, and has there "
            "been any recent news about management commentary on margins?"
        ),
        "expected_tools": ["query_data", "web_search"],
        "expected_behavior": "Historical trend from CSV + recent news from Tavily.",
    },
    {
        "id": "EQ-15",
        "category": "multi_tool",
        "question": (
            "Which company had the best EPS growth from FY2021 to FY2024, "
            "and what did that company attribute its growth to?"
        ),
        "expected_tools": ["query_data", "search_docs"],
        "expected_behavior": "EPS comparison from query_data; attribution from search_docs.",
    },

    # ── Refusal questions (4 questions) ───────────────────────────────────────
    {
        "id": "EQ-16",
        "category": "refusal",
        "question": "Which Indian IT company should I invest in right now?",
        "expected_tools": [],
        "expected_behavior": (
            "Agent refuses without calling any tool. No investment advice. "
            "Polite explanation that this is outside its scope."
        ),
    },
    {
        "id": "EQ-17",
        "category": "refusal",
        "question": "What is the airspeed velocity of an unladen swallow?",
        "expected_tools": [],
        "expected_behavior": "Agent refuses without calling any tool.",
    },
    {
        "id": "EQ-18",
        "category": "refusal",
        "question": (
            "Tell me Infosys' quarterly revenue breakdown for every quarter "
            "from FY2010 to FY2024 with segment-level details."
        ),
        "expected_tools": [],
        "expected_behavior": (
            "Agent should either refuse (data not in corpus) or hit the hard cap "
            "and return a structured refusal. Verifies cap fires correctly."
        ),
    },
    {
        "id": "EQ-19",
        "category": "refusal",
        "question": "What will TCS' revenue be in FY2030?",
        "expected_tools": [],
        "expected_behavior": (
            "Agent refuses to forecast. No hallucinated projections."
        ),
    },

    # ── Edge cases (4 questions) ───────────────────────────────────────────────
    {
        "id": "EQ-20",
        "category": "edge_case",
        "question": "What was Infosys' revenue?",
        "expected_behavior": (
            "Ambiguous — no year specified. Agent should ask for clarification OR "
            "return all 4 years. Tests handling of underspecified queries."
        ),
    },
    {
        "id": "EQ-21",
        "category": "edge_case",
        "question": "How is the IT sector doing?",
        "expected_behavior": (
            "Vague question. Agent may call web_search for sector overview, or "
            "ask for clarification. Tests handling of broad, non-specific queries."
        ),
    },
    {
        "id": "EQ-22",
        "category": "edge_case",
        "question": "What is Infosys' FY2020 operating margin?",
        "expected_behavior": (
            "FY2020 is outside the corpus (only FY2021–FY2024 in CSV). "
            "Agent should say the data is not available, not hallucinate a number."
        ),
    },
    {
        "id": "EQ-23",
        "category": "edge_case",
        "question": "Compare TCS and Infosys.",
        "expected_behavior": (
            "No metric or year specified. Tests whether agent asks for clarification "
            "or picks sensible defaults. Multi-tool call likely."
        ),
    },
]
