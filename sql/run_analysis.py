"""
Builds a local SQLite database from the CSVs, runs data-quality checks and all analysis
queries, and exports each result to sql/results/<name>.csv.

Usage (from repo root):   python sql/run_analysis.py
Needs only the Python standard library.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"
DATA = ROOT / "data"
OUT = SQL / "results"
OUT.mkdir(exist_ok=True)
DB = ROOT / "dubai_brokerage.db"

if sqlite3.sqlite_version_info < (3, 25):
    sys.exit(f"SQLite {sqlite3.sqlite_version} is too old - window functions need 3.25+")

if DB.exists():
    DB.unlink()
con = sqlite3.connect(DB)
con.executescript((SQL / "01_schema.sql").read_text())


def load(table, filename, cols):
    with open(DATA / filename, newline="") as f:
        rows = [tuple(r[c] for c in cols) for r in csv.DictReader(f)]
    con.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
    print(f"loaded {len(rows):>5} rows into {table}")


load("areas", "areas.csv", ["area", "segment", "base_psf_aed"])
load("agents", "agents.csv", ["agent_id", "agent_name", "team", "join_date"])
load("transactions", "transactions.csv",
     ["deal_id", "deal_date", "area", "property_type", "bedrooms", "size_sqft", "price_aed",
      "sale_type", "lead_channel", "buyer_type", "agent_id", "commission_aed", "days_to_close"])
con.commit()


def run_file(path, export=True):
    text = path.read_text()
    blocks = re.split(r"^-- name:\s*(\S+)\s*$", text, flags=re.M)[1:]
    for name, body in zip(blocks[0::2], blocks[1::2]):
        cur = con.execute(body.strip().rstrip(";"))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        if export:
            with open(OUT / f"{name}.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(cols)
                w.writerows(rows)
        yield name, cols, rows


print("\n=== DATA QUALITY CHECKS (expect 0 problem rows) ===")
bad = 0
for name, cols, rows in run_file(SQL / "02_data_quality_checks.sql", export=False):
    problem = (rows[0][0] if name == "dq6_deals_before_agent_joined" else len(rows))
    bad += problem
    print(f"{'OK ' if problem == 0 else 'FAIL'} {name}: {problem}")
if bad:
    sys.exit("Data quality checks failed - fix data before analysing.")

print("\n=== ANALYSIS QUERIES ===")
for name, cols, rows in run_file(SQL / "03_analysis_queries.sql"):
    print(f"\n-- {name}  ({len(rows)} rows)")
    print(" | ".join(cols))
    for r in rows[:6]:
        print(" | ".join(str(x) for x in r))
    if len(rows) > 6:
        print("...")
con.close()
print(f"\nResults exported to {OUT}")
