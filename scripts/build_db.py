"""scripts/build_db.py — load financials.csv into SQLite"""
import sqlite3
import pandas as pd
from pathlib import Path

CSV_PATH = Path("data/financials.csv")
DB_PATH  = Path("data/financials.db")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

df  = pd.read_csv(CSV_PATH)
con = sqlite3.connect(DB_PATH)
df.to_sql("financials", con, if_exists="replace", index=False)
con.close()

print(f"✓ Wrote {len(df)} rows to {DB_PATH}")
print(df.to_string())