"""
tools/query_data.py
-------------------
Structured query tool for the financials SQLite database.
Accepts either a raw SQL SELECT statement or a plain-English question
(plain English is translated to SQL by a lightweight helper).

Schema:
  CREATE TABLE financials (
      company            TEXT,    -- 'Infosys' | 'TCS' | 'Wipro'
      fiscal_year        INTEGER, -- 2021 | 2022 | 2023 | 2024
      revenue_usd_bn     REAL,
      operating_margin_pct REAL,
      net_profit_usd_bn  REAL,
      eps_inr            REAL,
      headcount          INTEGER
  );
"""

import os
import re
import sqlite3
import pandas as pd
from typing import Union


DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/financials.db")


def _is_sql(query: str) -> bool:
    return query.strip().upper().startswith("SELECT")


def _natural_to_sql(question: str) -> str:
    """
    Minimal keyword-based translation for common question patterns.
    For production, swap this with a small LLM call (cached).
    """
    q = question.lower()
    company_map = {"infosys": "Infosys", "tcs": "TCS", "wipro": "Wipro"}
    year_match  = re.search(r"fy\s?(\d{2,4})", q)
    fiscal_year = int("20" + year_match.group(1)[-2:]) if year_match else None

    company = next((v for k, v in company_map.items() if k in q), None)

    col_map = {
        "operating margin": "operating_margin_pct",
        "revenue":          "revenue_usd_bn",
        "net profit":       "net_profit_usd_bn",
        "eps":              "eps_inr",
        "headcount":        "headcount",
    }
    col = next((v for k, v in col_map.items() if k in q), "*")

    where_clauses = []
    if company:
        where_clauses.append(f"company = '{company}'")
    if fiscal_year:
        where_clauses.append(f"fiscal_year = {fiscal_year}")

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return f"SELECT {col} FROM financials {where} ORDER BY fiscal_year"


def run(query: str) -> dict:
    """
    Execute a SQL query or translate a natural-language question and execute it.

    Returns:
        {
            "rows":         list of dicts  (each dict is one row),
            "columns":      list of str,
            "row_count":    int,
            "sql_executed": str            # the exact SQL that ran
        }
    """
    sql = query if _is_sql(query) else _natural_to_sql(query)

    try:
        con = sqlite3.connect(DB_PATH)
        df  = pd.read_sql_query(sql, con)
        con.close()

        return {
            "rows":         df.to_dict(orient="records"),
            "columns":      list(df.columns),
            "row_count":    len(df),
            "sql_executed": sql,
        }

    except Exception as exc:
        return {
            "error":        str(exc),
            "sql_executed": sql,
            "rows":         [],
            "columns":      [],
            "row_count":    0,
        }
