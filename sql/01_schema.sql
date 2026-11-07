-- =====================================================================
-- 01_schema.sql  |  Dubai real estate brokerage - analytics database
-- Dialect: SQLite 3.25+ (window functions). Notes for MySQL/PostgreSQL in README.
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS areas;

-- Dimension: communities / neighbourhoods
CREATE TABLE areas (
    area           TEXT PRIMARY KEY,
    segment        TEXT NOT NULL,          -- Prime / Waterfront / Urban / Affordable ...
    base_psf_aed   INTEGER NOT NULL        -- reference price per sqft
);

-- Dimension: brokerage sales agents
CREATE TABLE agents (
    agent_id    INTEGER PRIMARY KEY,
    agent_name  TEXT NOT NULL,
    team        TEXT NOT NULL,             -- Prime / Off-Plan / Secondary
    join_date   TEXT NOT NULL              -- ISO date YYYY-MM-DD
);

-- Fact: one row per closed deal
CREATE TABLE transactions (
    deal_id         INTEGER PRIMARY KEY,
    deal_date       TEXT    NOT NULL,      -- ISO date
    area            TEXT    NOT NULL REFERENCES areas(area),
    property_type   TEXT    NOT NULL CHECK (property_type IN ('Apartment','Villa','Townhouse')),
    bedrooms        INTEGER NOT NULL,      -- 0 = studio
    size_sqft       INTEGER NOT NULL CHECK (size_sqft > 0),
    price_aed       INTEGER NOT NULL CHECK (price_aed > 0),
    sale_type       TEXT    NOT NULL CHECK (sale_type IN ('Off-Plan','Secondary')),
    lead_channel    TEXT    NOT NULL,
    buyer_type      TEXT    NOT NULL CHECK (buyer_type IN ('Resident','Non-Resident')),
    agent_id        INTEGER NOT NULL REFERENCES agents(agent_id),
    commission_aed  INTEGER NOT NULL,      -- brokerage revenue on the deal
    days_to_close   INTEGER NOT NULL
);

CREATE INDEX idx_tx_date  ON transactions(deal_date);
CREATE INDEX idx_tx_area  ON transactions(area);
CREATE INDEX idx_tx_agent ON transactions(agent_id);

-- Convenience view: deals enriched with dimensions + derived columns
DROP VIEW IF EXISTS vw_deals;
CREATE VIEW vw_deals AS
SELECT  t.*,
        a.segment,
        g.agent_name,
        g.team,
        g.join_date,
        strftime('%Y',    t.deal_date)                       AS yr,
        strftime('%Y-%m', t.deal_date)                       AS ym,
        CAST(strftime('%m', t.deal_date) AS INTEGER)         AS mth,
        printf('%s-Q%d', strftime('%Y', t.deal_date),
               (CAST(strftime('%m', t.deal_date) AS INTEGER) + 2) / 3) AS yq,
        ROUND(1.0 * t.price_aed / t.size_sqft, 0)            AS psf_aed
FROM transactions t
JOIN areas  a ON a.area     = t.area
JOIN agents g ON g.agent_id = t.agent_id;
