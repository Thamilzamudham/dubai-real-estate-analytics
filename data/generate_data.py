"""
Generates SYNTHETIC data for the Dubai real estate analytics portfolio project.
NOT real Dubai Land Department data. Replace with real open data (see README).

Outputs (in this folder):
  monthly_sales.csv   - monthly market sales series (for Excel time-series forecast)
  transactions.csv    - brokerage deal-level data (for SQL analysis)
  agents.csv, areas.csv - dimension tables
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
out = Path(__file__).parent

# ---------- 1. Monthly market series (Jan 2018 - Oct 2026) ----------
months = pd.date_range("2018-01-01", "2026-10-01", freq="MS")
n = len(months)
t = np.arange(n)

# Dubai-like pattern: flat 2018-19, COVID dip 2020, strong growth 2021-2025, cooling
trend = np.interp(t, [0, 24, 27, 36, 60, 94, n - 1],
                  [9.0, 8.5, 6.5, 12.0, 24.0, 38.0, 40.0])  # AED billions
season_idx = {1: 1.00, 2: 1.03, 3: 1.08, 4: 0.92, 5: 0.90, 6: 0.88,
              7: 0.86, 8: 0.84, 9: 0.97, 10: 1.08, 11: 1.12, 12: 1.15}
season = np.array([season_idx[m.month] for m in months])
noise = rng.normal(1.0, 0.04, n)
sales_value = trend * season * noise
avg_price_psf = np.interp(t, [0, 24, 36, 60, n - 1],
                          [1050, 980, 1100, 1550, 1900]) * rng.normal(1, 0.01, n)
txn_count = (sales_value * 1e9 / (avg_price_psf * 1100 * rng.normal(1, 0.03, n))).round().astype(int)

monthly = pd.DataFrame({
    "month": months.strftime("%Y-%m-%d"),
    "sales_value_aed_bn": sales_value.round(2),
    "transactions": txn_count,
    "avg_price_psf_aed": avg_price_psf.round(0).astype(int),
})
monthly.to_csv(out / "monthly_sales.csv", index=False)

# ---------- 2. Dimension tables ----------
areas = pd.DataFrame([
    ("Dubai Marina", "Waterfront", 2150, 0.18),
    ("Downtown Dubai", "Prime", 2650, 0.14),
    ("Palm Jumeirah", "Prime", 3100, 0.08),
    ("Business Bay", "Urban", 1900, 0.14),
    ("Jumeirah Village Circle", "Affordable", 1250, 0.16),
    ("Dubai Hills Estate", "Master Community", 2000, 0.10),
    ("Arabian Ranches", "Villa Community", 1600, 0.06),
    ("Dubai South", "Affordable", 950, 0.07),
    ("Al Barsha", "Urban", 1300, 0.07),
], columns=["area", "segment", "base_psf_aed", "share"])
areas[["area", "segment", "base_psf_aed"]].to_csv(out / "areas.csv", index=False)

agents = pd.DataFrame({
    "agent_id": range(1, 21),
    "agent_name": [f"Agent {chr(64 + i)}" for i in range(1, 21)],
    "team": rng.choice(["Prime Team", "Off-Plan Team", "Secondary Team"], 20),
    "join_date": pd.to_datetime("2021-01-01") + pd.to_timedelta(rng.integers(0, 1500, 20), unit="D"),
})
agents["join_date"] = agents["join_date"].dt.strftime("%Y-%m-%d")
agents.to_csv(out / "agents.csv", index=False)

# ---------- 3. Deal-level transactions (brokerage, 2023-01 .. 2026-10) ----------
N = 6000
start, end = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-10-31")
days = (end - start).days
# weight deal dates by growth + seasonality
d = start + pd.to_timedelta(rng.integers(0, days + 1, N * 2), unit="D")
w = np.array([season_idx[x.month] for x in d]) * (1 + np.asarray((d - start).days) / days)
d = d[rng.choice(len(d), N, replace=False, p=w / w.sum())]

area_pick = rng.choice(areas["area"], N, p=areas["share"] / areas["share"].sum())
base_psf = areas.set_index("area")["base_psf_aed"]
ptype = rng.choice(["Apartment", "Villa", "Townhouse"], N, p=[0.72, 0.18, 0.10])
beds = np.where(ptype == "Apartment", rng.choice([0, 1, 2, 3], N, p=[.12, .38, .35, .15]),
                rng.choice([3, 4, 5], N, p=[.4, .4, .2]))
size = np.where(ptype == "Apartment", 450 + beds * 330, 1900 + (beds - 3) * 900) * rng.normal(1, 0.12, N)
growth = 1 + 0.18 * (d - start).days / 365
psf = np.array([base_psf[a] for a in area_pick]) * growth * rng.normal(1, 0.08, N)
price = (size * psf).round(-3)

sale_type = rng.choice(["Off-Plan", "Secondary"], N, p=[0.55, 0.45])
channel = rng.choice(["Portal", "Referral", "Walk-in", "Social Media", "Developer Event"], N,
                     p=[.34, .22, .10, .22, .12])
buyer = rng.choice(["Resident", "Non-Resident"], N, p=[0.58, 0.42])
comm_rate = np.where(sale_type == "Off-Plan", 0.05, 0.02)
commission = (price * comm_rate).round(0)
# lead -> close days
days_to_close = np.where(sale_type == "Off-Plan", rng.gamma(3, 9, N), rng.gamma(4, 12, N)).round().astype(int) + 3

# assign each deal to an agent who had already joined by the deal date (skewed productivity weights)
agent_weight = rng.dirichlet(np.ones(20) * 3)
join_dt = pd.to_datetime(agents["join_date"]).values
deal_dt = pd.to_datetime(pd.Series(d)).values
assigned_agents = np.empty(N, dtype=int)
for i in range(N):
    ok = join_dt <= deal_dt[i]
    p = agent_weight * ok
    assigned_agents[i] = rng.choice(agents["agent_id"].values, p=p / p.sum())

tx = pd.DataFrame({
    "deal_id": np.arange(1, N + 1),
    "deal_date": pd.Series(d).dt.strftime("%Y-%m-%d").values,
    "area": area_pick,
    "property_type": ptype,
    "bedrooms": beds,
    "size_sqft": size.round(0).astype(int),
    "price_aed": price.astype(int),
    "sale_type": sale_type,
    "lead_channel": channel,
    "buyer_type": buyer,
    "agent_id": assigned_agents,
    "commission_aed": commission.astype(int),
    "days_to_close": days_to_close,
}).sort_values("deal_date").reset_index(drop=True)
tx["deal_id"] = np.arange(1, N + 1)
tx.to_csv(out / "transactions.csv", index=False)

print(monthly.tail(3)); print(tx.head(3)); print(len(monthly), len(tx))
