"""
tool_schemas.py
---------------
Three tool definitions for the Stnapt Agentic RAG system.
Descriptions are written for the LLM, not for a human reader.
Each description tells the model WHEN to use the tool AND when NOT to.
"""

TOOLS = [
    {
        "name": "search_docs",
        "description": (
            "Use this tool when the question requires information that would appear "
            "in a company's annual report, management commentary, MD&A section, "
            "chairman's letter, or any long-form narrative text. This tool performs "
            "semantic similarity search over a local vector store indexed from PDF "
            "annual reports for Infosys, TCS, and Wipro. It is the RIGHT tool for "
            "questions like 'what reason did TCS give for margin improvement' or "
            "'what strategic priorities did Infosys highlight'. It is the WRONG tool "
            "for precise numbers (use query_data) or for anything that happened after "
            "the report publication date (use web_search). Returns the top-3 most "
            "relevant text chunks with source filename and page number."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A natural language question or phrase describing the "
                        "information you want from the documents. Be specific: "
                        "include the company name and topic (e.g. 'Infosys FY24 "
                        "operating margin explanation MD&A'). Under 30 words."
                    )
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "query_data",
        "description": (
            "Use this tool when the question requires a precise number, ratio, "
            "year-over-year comparison, or aggregation that can be answered from "
            "structured tabular data. This tool queries a SQLite database (or pandas "
            "DataFrame) containing 4 years of key financials for Infosys, TCS, and "
            "Wipro: revenue, operating_margin, net_profit, eps, and headcount. It is "
            "the RIGHT tool for questions like 'what was Infosys revenue in FY24' or "
            "'compare headcount growth across all 3 companies'. It is the WRONG tool "
            "for qualitative explanations (use search_docs) or live/current data "
            "(use web_search). Returns a table or scalar with column names and row "
            "count so you can cite the exact row."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Either a valid SQLite SELECT statement against the "
                        "'financials' table (columns: company, fiscal_year, "
                        "revenue_usd_bn, operating_margin_pct, net_profit_usd_bn, "
                        "eps_inr, headcount) OR a plain-English question about the "
                        "data. Examples: \"SELECT operating_margin_pct FROM "
                        "financials WHERE company='Infosys' AND fiscal_year=2024\" "
                        "or \"compare revenue for all companies in FY2023\"."
                    )
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Use this tool ONLY when the question requires information that is "
            "recent, live, or cannot possibly be in a static document or CSV — "
            "such as current stock prices, analyst ratings published this week, "
            "recent earnings calls, executive appointments, or news from the last "
            "few months. It is the RIGHT tool for 'what is the current stock price "
            "of Infosys' or 'what happened to IT sector stocks last week'. It is "
            "the WRONG tool for historical financials (use query_data) or annual "
            "report content (use search_docs). Do NOT use this tool speculatively "
            "as a fallback — only call it when recency is the explicit requirement. "
            "Returns the top-3 result snippets with URL and publication date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A short, specific search query under 10 words. Include "
                        "company name and topic. Good: 'Infosys stock price today'. "
                        "Bad: 'tell me about Infosys financial performance over the "
                        "years including operating margin and revenue growth trends'."
                    )
                }
            },
            "required": ["query"]
        }
    }
]
