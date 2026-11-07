-- =====================================================================
-- 02_data_quality_checks.sql  |  run BEFORE any analysis. Every check should return 0 rows / 0.
-- =====================================================================

-- name: dq1_duplicate_deal_ids
SELECT deal_id, COUNT(*) AS n FROM transactions GROUP BY deal_id HAVING COUNT(*) > 1;

-- name: dq2_orphan_agents
SELECT t.deal_id FROM transactions t LEFT JOIN agents a USING (agent_id) WHERE a.agent_id IS NULL;

-- name: dq3_orphan_areas
SELECT t.deal_id FROM transactions t LEFT JOIN areas a USING (area) WHERE a.area IS NULL;

-- name: dq4_commission_rate_outliers
-- Off-plan should be ~5%, secondary ~2%. Flag anything outside that band.
SELECT deal_id, sale_type, ROUND(100.0 * commission_aed / price_aed, 2) AS comm_pct
FROM transactions
WHERE (sale_type = 'Off-Plan'  AND ABS(1.0 * commission_aed / price_aed - 0.05) > 0.005)
   OR (sale_type = 'Secondary' AND ABS(1.0 * commission_aed / price_aed - 0.02) > 0.005);

-- name: dq5_price_per_sqft_outliers
-- Flag deals more than 3x / less than 1/3 of the area's median-ish reference price.
SELECT t.deal_id, t.area, ROUND(1.0 * t.price_aed / t.size_sqft) AS psf, a.base_psf_aed
FROM transactions t JOIN areas a USING (area)
WHERE 1.0 * t.price_aed / t.size_sqft > 3 * a.base_psf_aed
   OR 1.0 * t.price_aed / t.size_sqft < a.base_psf_aed / 3.0;

-- name: dq6_deals_before_agent_joined
-- Agents cannot close deals before their join date.
SELECT COUNT(*) AS deals_before_join FROM vw_deals WHERE deal_date < join_date;
