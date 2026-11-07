-- =====================================================================
-- 03_analysis_queries.sql  |  Business analysis for a Dubai real estate brokerage
-- Each block starts with "-- name:" (used by run_analysis.py to export results).
-- SQL skills shown: JOINs, CTEs, window functions (LAG, RANK, NTILE, running SUM,
-- moving AVG), conditional aggregation, cohort-style grouping, Pareto analysis.
-- =====================================================================

-- name: q01_kpi_overview
-- Q: What does the business look like at a glance?
SELECT  COUNT(*)                                   AS deals,
        ROUND(SUM(price_aed) / 1e6, 1)             AS sales_volume_aed_m,
        ROUND(SUM(commission_aed) / 1e6, 2)        AS revenue_aed_m,
        ROUND(AVG(price_aed) / 1e6, 2)             AS avg_deal_size_aed_m,
        ROUND(100.0 * SUM(commission_aed) / SUM(price_aed), 2) AS blended_commission_pct,
        ROUND(AVG(days_to_close), 1)               AS avg_days_to_close
FROM transactions;

-- name: q02_yearly_revenue_growth
-- Q: How is revenue growing year over year? 2026 only has Jan-Oct, so compare like-for-like YTD
--    (Jan-Oct of every year) as well as full-year totals.
WITH y AS (
    SELECT yr,
           COUNT(*)                                                    AS deals,
           SUM(commission_aed)                                         AS revenue,
           SUM(CASE WHEN mth <= 10 THEN commission_aed ELSE 0 END)     AS ytd_revenue
    FROM vw_deals GROUP BY yr
)
SELECT  yr, deals,
        ROUND(revenue / 1e6, 2)                                        AS full_year_revenue_aed_m,
        ROUND(ytd_revenue / 1e6, 2)                                    AS jan_oct_revenue_aed_m,
        ROUND(100.0 * (ytd_revenue - LAG(ytd_revenue) OVER (ORDER BY yr))
                    / LAG(ytd_revenue) OVER (ORDER BY yr), 1)          AS ytd_yoy_growth_pct
FROM y ORDER BY yr;

-- name: q03_monthly_revenue_trend
-- Q: What is the monthly trend, smoothed? (MoM growth + 3-month moving average)
WITH m AS (
    SELECT ym, COUNT(*) AS deals, SUM(commission_aed) AS revenue
    FROM vw_deals GROUP BY ym
)
SELECT  ym, deals,
        ROUND(revenue / 1e6, 2) AS revenue_aed_m,
        ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY ym))
                    / LAG(revenue) OVER (ORDER BY ym), 1)               AS mom_pct,
        ROUND(AVG(revenue) OVER (ORDER BY ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) / 1e6, 2)
                                                                         AS ma3_revenue_aed_m
FROM m ORDER BY ym;

-- name: q04_seasonality_by_calendar_month
-- Q: Which calendar months are strongest? (uses full years 2023-2025 only, to avoid partial-year bias)
WITH m AS (
    SELECT yr, mth, SUM(commission_aed) AS revenue
    FROM vw_deals WHERE yr IN ('2023','2024','2025') GROUP BY yr, mth
)
SELECT  mth,
        ROUND(AVG(revenue) / 1e6, 2) AS avg_revenue_aed_m,
        ROUND(AVG(revenue) / (SELECT AVG(revenue) FROM m), 3) AS seasonal_index
FROM m GROUP BY mth ORDER BY mth;

-- name: q05_revenue_by_area
-- Q: Which areas drive revenue, and how concentrated are we?
WITH a AS (
    SELECT area, segment, COUNT(*) AS deals,
           SUM(commission_aed) AS revenue, AVG(psf_aed) AS avg_psf
    FROM vw_deals GROUP BY area, segment
)
SELECT  RANK() OVER (ORDER BY revenue DESC)                          AS rnk,
        area, segment, deals,
        ROUND(revenue / 1e6, 2)                                     AS revenue_aed_m,
        ROUND(100.0 * revenue / SUM(revenue) OVER (), 1)            AS pct_of_revenue,
        ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC)
                    / SUM(revenue) OVER (), 1)                      AS cumulative_pct,
        ROUND(revenue * 1.0 / deals / 1e3, 0)                       AS revenue_per_deal_aed_k,
        ROUND(avg_psf, 0)                                           AS avg_psf_aed
FROM a ORDER BY revenue DESC;

-- name: q06_offplan_vs_secondary
-- Q: Off-plan pays 5%, secondary 2% - what is the real trade-off including speed to close?
SELECT  sale_type,
        COUNT(*)                                       AS deals,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS pct_of_deals,
        ROUND(SUM(commission_aed) / 1e6, 2)            AS revenue_aed_m,
        ROUND(100.0 * SUM(commission_aed) / SUM(SUM(commission_aed)) OVER (), 1) AS pct_of_revenue,
        ROUND(AVG(commission_aed) / 1e3, 0)            AS avg_revenue_per_deal_aed_k,
        ROUND(AVG(days_to_close), 1)                   AS avg_days_to_close,
        ROUND(SUM(commission_aed) / SUM(days_to_close) / 1e3, 1)         AS revenue_per_deal_day_aed_k
FROM transactions GROUP BY sale_type;

-- name: q07_lead_channel_performance
-- Q: Which lead sources deserve more marketing budget?
SELECT  lead_channel,
        COUNT(*)                                        AS deals,
        ROUND(SUM(commission_aed) / 1e6, 2)             AS revenue_aed_m,
        ROUND(100.0 * SUM(commission_aed) / SUM(SUM(commission_aed)) OVER (), 1) AS pct_of_revenue,
        ROUND(AVG(commission_aed) / 1e3, 0)             AS revenue_per_deal_aed_k,
        ROUND(AVG(days_to_close), 1)                    AS avg_days_to_close,
        ROUND(100.0 * SUM(CASE WHEN sale_type = 'Off-Plan' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_offplan
FROM transactions GROUP BY lead_channel ORDER BY revenue_aed_m DESC;

-- name: q08_buyer_type_by_area
-- Q: Where does non-resident (investor) demand concentrate?
SELECT  area,
        COUNT(*) AS deals,
        ROUND(100.0 * SUM(CASE WHEN buyer_type = 'Non-Resident' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_non_resident,
        ROUND(AVG(CASE WHEN buyer_type = 'Non-Resident' THEN price_aed END) / 1e6, 2) AS avg_price_nonres_aed_m,
        ROUND(AVG(CASE WHEN buyer_type = 'Resident'     THEN price_aed END) / 1e6, 2) AS avg_price_res_aed_m
FROM transactions GROUP BY area ORDER BY pct_non_resident DESC;

-- name: q09_agent_leaderboard
-- Q: How is individual productivity distributed? (rank, quartile, vs. team average)
WITH a AS (
    SELECT agent_id, agent_name, team, COUNT(*) AS deals, SUM(commission_aed) AS revenue,
           AVG(days_to_close) AS avg_days
    FROM vw_deals GROUP BY agent_id, agent_name, team
)
SELECT  RANK()  OVER (ORDER BY revenue DESC)                           AS rnk,
        NTILE(4) OVER (ORDER BY revenue DESC)                          AS quartile,
        agent_name, team, deals,
        ROUND(revenue / 1e6, 2)                                       AS revenue_aed_m,
        ROUND(100.0 * revenue / AVG(revenue) OVER (PARTITION BY team) - 100, 0) AS vs_team_avg_pct,
        ROUND(avg_days, 1)                                            AS avg_days_to_close
FROM a ORDER BY revenue DESC;

-- name: q10_pareto_agents
-- Q: Is revenue dependent on a handful of agents? (how many agents make 50% / 80% of revenue)
WITH a AS (
    SELECT agent_id, SUM(commission_aed) AS revenue FROM transactions GROUP BY agent_id
), c AS (
    SELECT agent_id, revenue,
           ROW_NUMBER() OVER (ORDER BY revenue DESC)                              AS n_agents,
           1.0 * SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS cum_share
    FROM a
)
SELECT  (SELECT MIN(n_agents) FROM c WHERE cum_share >= 0.5) AS agents_for_50pct_revenue,
        (SELECT MIN(n_agents) FROM c WHERE cum_share >= 0.8) AS agents_for_80pct_revenue,
        (SELECT COUNT(*) FROM c)                              AS total_agents;

-- name: q11_top_agent_per_team
-- Q: Who is the top performer in each team? (ROW_NUMBER within partition)
WITH a AS (
    SELECT team, agent_name, SUM(commission_aed) AS revenue, COUNT(*) AS deals
    FROM vw_deals GROUP BY team, agent_name
), r AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY team ORDER BY revenue DESC) AS rn FROM a
)
SELECT team, agent_name, deals, ROUND(revenue / 1e6, 2) AS revenue_aed_m
FROM r WHERE rn <= 2 ORDER BY team, rn;

-- name: q12_price_per_sqft_growth_by_area
-- Q: Where are prices rising fastest? (average AED/sqft by year, YoY change, 2023 -> 2025 full years)
WITH p AS (
    SELECT area, yr, ROUND(AVG(psf_aed), 0) AS psf FROM vw_deals GROUP BY area, yr
)
SELECT  area,
        MAX(CASE WHEN yr = '2023' THEN psf END)                         AS psf_2023,
        MAX(CASE WHEN yr = '2024' THEN psf END)                         AS psf_2024,
        MAX(CASE WHEN yr = '2025' THEN psf END)                         AS psf_2025,
        ROUND(100.0 * (MAX(CASE WHEN yr = '2025' THEN psf END)
                     / MAX(CASE WHEN yr = '2023' THEN psf END) - 1), 1) AS growth_2023_25_pct
FROM p GROUP BY area ORDER BY growth_2023_25_pct DESC;

-- name: q13_agent_ramp_up_by_tenure
-- Q: How long does a new agent take to become productive?
-- Method: revenue per AGENT-MONTH by tenure bucket (a recursive CTE builds a calendar so that
--         every month an agent was on the books counts in the denominator, even months with no deals).
WITH RECURSIVE cal(m) AS (
    SELECT '2023-01-01'
    UNION ALL
    SELECT date(m, '+1 month') FROM cal WHERE m < '2026-10-01'
),
agent_months AS (
    SELECT g.agent_id, c.m,
           CAST((julianday(c.m) - julianday(g.join_date)) / 30.4 AS INTEGER) AS tenure_m
    FROM agents g JOIN cal c ON c.m >= date(g.join_date, 'start of month')
),
bucketed AS (
    SELECT agent_id, m,
           CASE WHEN tenure_m < 6  THEN '1) 0-5 months'
                WHEN tenure_m < 12 THEN '2) 6-11 months'
                WHEN tenure_m < 24 THEN '3) 12-23 months'
                ELSE                    '4) 24+ months' END AS bucket
    FROM agent_months
),
exposure AS (SELECT bucket, COUNT(*) AS agent_months FROM bucketed GROUP BY bucket),
rev AS (
    SELECT b.bucket, COUNT(*) AS deals, SUM(d.commission_aed) AS revenue
    FROM vw_deals d
    JOIN bucketed b ON b.agent_id = d.agent_id AND b.m = date(d.deal_date, 'start of month')
    GROUP BY b.bucket
)
SELECT  e.bucket AS tenure_bucket, e.agent_months, r.deals,
        ROUND(1.0 * r.deals / e.agent_months, 2)            AS deals_per_agent_month,
        ROUND(r.revenue / e.agent_months / 1e3, 1)          AS revenue_per_agent_month_aed_k
FROM exposure e JOIN rev r USING (bucket) ORDER BY e.bucket;

-- name: q14_slow_deals_by_segment
-- Q: Which segments take longest to close - where is working capital / agent time tied up?
SELECT  segment, sale_type,
        COUNT(*)                          AS deals,
        ROUND(AVG(days_to_close), 1)      AS avg_days,
        MAX(days_to_close)                AS max_days,
        ROUND(100.0 * SUM(CASE WHEN days_to_close > 60 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_over_60_days
FROM vw_deals GROUP BY segment, sale_type ORDER BY avg_days DESC;
