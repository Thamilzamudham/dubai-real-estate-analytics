# Business Analysis: Recommendations for a Dubai Real Estate Brokerage

> **Read this first:** the dataset in this repo is **synthetic**. The findings below show *how I turn query
> output into decisions*. The numbers are illustrative; with real DLD / company data the conclusions will differ.
> Where the data told me nothing useful, I say so rather than inventing a story.

## Business question
*Where does a mid-size Dubai brokerage earn its revenue, what is likely to happen over the next 12 months,
and what management actions would improve revenue and productivity?*

## Findings and what I would do about them

### 1. Off-plan is the engine, and also the concentration risk
Off-plan is 55% of deals but **75% of revenue** (5% vs 2% commission). It also closes faster
(30 vs 51 days), so revenue per deal-day is about **4x higher** (AED 6.2k vs 1.5k).
*(SQL: `q06`)*
- **Action:** protect developer relationships and off-plan inventory access (developer events are already 13% of revenue).
- **Risk to monitor:** a single regulatory or developer-supply shock hits 3/4 of revenue. Track off-plan share monthly and set an alert threshold.
- **Idea:** give secondary-market agents a small bonus for deals that close under 45 days, since slow secondary deals tie up agent time at a 2% fee.

### 2. Revenue is concentrated in two areas and a few agents
- Dubai Marina + Downtown = **~40% of revenue**; top five areas = 75%. *(`q05`)*
- **6 of 20 agents generate 50% of revenue; 12 generate 80%.** One agent alone handles ~16% of deals. *(`q09`, `q10`)*
- **Action:** (a) a retention plan for top-quartile agents, since losing one is a visible revenue hit; (b) pair them with
  bottom-quartile agents on leads they cannot cover; (c) cross-train a deputy for the highest-volume agent.

### 3. Strong, seasonal growth, but the straight-line forecast is probably optimistic
- Like-for-like Jan-Oct revenue grew **+32.9%, +25.8%, +21.2%** (2024, 2025, 2026): still growing, but decelerating. *(`q02`)*
- December runs about 30% above an average month and July about 15% below. *(`q04`; matches the Excel seasonal index)*
- The Excel model forecasts **AED 508bn (+12.7%)** market sales for the next 12 months, but its backtest **over-forecast
  all 12 test months (bias -5.7%)** because growth has slowed. The bias-adjusted view is **AED 481bn (+6.6%)**.
  Backtest error (MAPE) was 6.0% vs 7.9% for a naive "same month last year" benchmark.
- **Action:** plan headcount and marketing spend against the cautious (+6.6%) case, front-load campaigns before
  September-December, and use the July-August trough for training and onboarding.

### 4. Things the data did *not* show (important to say honestly)
- **Lead channels are indistinguishable on quality:** revenue per deal ~AED 132-146k and ~39-40 days to close across all five channels (`q07`).
  Portal is simply the biggest by volume (33% of revenue). On this data there is no case for moving budget between channels; on real data, rerun `q07` with cost-per-lead to get cost-per-closed-deal.
- **Non-resident share is flat (~41-45%) across areas** (`q08`) and **price growth is similar everywhere (~30-35% 2023-25)** (`q12`): no area-specific pricing play.
- **Agent ramp-up looks flat once exposure is normalised** (`q13`). A naive version of this query suggested new agents earn a third of veterans, but that was an artifact of veterans having more months on the books. Lesson: always divide by *time at risk*.

## Limitations
1. Synthetic data; relationships between variables are simple by construction.
2. Excel forecast uses a linear trend over 36 months; it cannot anticipate regulatory or macro shocks and its band is constant over the horizon.
3. No cost data, so "revenue" is commission income, not profit.

## Next steps with real data
1. Replace `monthly_sales.csv` with Dubai Land Department monthly sales (Dubai Pulse open data) and re-run the workbook.
2. Join marketing spend by channel to compute cost per closed deal and ROI.
3. Add lead-stage data (enquiry, viewing, offer) to analyse conversion funnels and drop-off.
4. Test a damped-trend or ETS model and compare MAPE to the current one.
