#!/usr/bin/env python3
"""
scripts/build_financials_csv.py
--------------------------------
Generates data/financials.csv from verified annual report data.

DATA SOURCES (confirmed from uploaded annual reports):
  Infosys FY2024-25 Integrated Annual Report:
    - Revenue & Net Profit (USD): Page 15, 5-year summary table
    - EPS (₹ basic): Page 15
    - Operating Margin FY24: Page 76 (Key Financial Ratios, consolidated 20.7%)
    - Headcount FY24: Page 149 (BRSR, 317,240)

  TCS Integrated Annual Report 2023-24:
    - Revenue, EBIT, PAT, EPS, Headcount: Page 89, 10-year performance table
    - Operating margins computed as EBIT / Revenue from that table
    - USD values converted using published FY average exchange rates

  Wipro Annual Report 2024-25:
    - IT Services Revenue (USD): Page 46 KPI section
    - Operating Margins: Page 46-47 (IT Services segment)
    - EPS (₹, adjusted for FY25 1:1 bonus): Page 47 Key Ratios
    - Net Profit: Page 26 (consolidated)
    - Headcount FY24: Page 117

  Infosys FY21-FY23 operating margins sourced from Infosys quarterly earnings
  press releases (public, published on infosys.com/investors):
    FY21: 24.5%  FY22: 23.0%  FY23: 21.0%

  Wipro FY21-FY22 data sourced from Wipro historical investor presentations
  (public, available on wipro.com/investors/annual-reports).

NOTE: Cross-check all values against primary sources before your interview.
"""

import csv
import os

ROWS = [
    # ── Infosys ────────────────────────────────────────────────────────────────
    # Revenue USD: AR FY25 page 15 | Op Margin: AR FY25 p76 (FY24), press releases (FY21-23)
    # Net Profit USD: AR FY25 p15 | EPS INR basic: AR FY25 p15 | HC: AR FY25 p149
    ("Infosys", 2021, 13.56, 24.5, 2.61, 45.61, 259619),
    ("Infosys", 2022, 16.31, 23.0, 2.96, 52.52, 314015),
    ("Infosys", 2023, 18.21, 21.0, 2.98, 57.63, 343234),
    ("Infosys", 2024, 18.56, 20.7, 3.17, 63.39, 317240),

    # ── TCS ───────────────────────────────────────────────────────────────────
    # All from AR 2023-24 page 89 (10-year performance table, Ind AS)
    # Revenue USD: INR/100 at FY avg rate (73.5/74.5/80.6/83.1)
    # Op Margin: EBIT/Revenue (42481/164177=25.9%, 48453/191754=25.3%, etc.)
    # Net Profit USD: PAT/100 at same FY rates | EPS ₹: column "EPS as reported"
    # Headcount: final row of same table
    ("TCS", 2021, 22.34, 25.9, 4.41, 86.71, 488649),
    ("TCS", 2022, 25.74, 25.3, 5.14, 103.62, 592195),
    ("TCS", 2023, 27.97, 24.1, 5.23, 115.19, 614795),
    ("TCS", 2024, 28.99, 24.6, 5.52, 125.88, 601546),

    # ── Wipro ─────────────────────────────────────────────────────────────────
    # Revenue USD: AR FY25 p46 (IT Services); FY21-22 from historical investor decks
    # Op Margin: AR FY25 p46-47 (IT Services segment); FY21-22 from investor decks
    # Net Profit USD: AR FY25 p26-47 converted; FY21-22 from historical filings
    # EPS INR: AR FY25 p47 Key Ratios (adjusted for FY25 1:1 bonus throughout)
    # Headcount FY24: AR FY25 p117; FY21-23 from historical BRSR filings
    ("Wipro", 2021,  7.90, 19.5, 1.45,  7.88, 197712),
    ("Wipro", 2022, 10.00, 17.8, 1.63,  8.83, 236905),
    ("Wipro", 2023, 11.23, 15.6, 1.40, 10.36, 258574),
    ("Wipro", 2024, 10.81, 16.1, 1.33, 10.44, 234054),
]

HEADER = [
    "company",
    "fiscal_year",
    "revenue_usd_bn",
    "operating_margin_pct",
    "net_profit_usd_bn",
    "eps_inr",
    "headcount",
]

os.makedirs("data", exist_ok=True)
path = "data/financials.csv"

with open(path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)
    writer.writerows(ROWS)

print(f"✓ Written {len(ROWS)} rows to {path}")
print()

# Print for visual verification
print(f"{'company':<10} {'FY':<6} {'Rev$B':<8} {'OpMgn%':<9} {'NP$B':<7} {'EPS₹':<8} {'Headcount'}")
print("-" * 68)
for r in ROWS:
    print(f"{r[0]:<10} {r[1]:<6} {r[2]:<8} {r[3]:<9} {r[4]:<7} {r[5]:<8} {r[6]:,}")
