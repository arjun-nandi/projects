# Hackathon Scripts by Stage (v3)

Companion to `hackathon_build_plan.md`. Scripts are grouped by milestone (M0 to M5) and tagged with the owning stream (A lead, B platform and app, C bureau and geospatial, D hazard and modelling).

## Quick actions by stage (start here)

Each stage has three parts: **Do** (the actions), **Check** (sanity checks on the outputs, with the expected result), and **Test** (assumptions we are relying on, with what to do if they fail). Detailed scripts for each item are in the sections below. Do not move to the next stage until the Check items pass.

### M0: Kickoff and foundations (Days 1-2)

**Do**
- [ ] Send the governance request (A)
- [ ] Run the address mapping checks first (B)
- [ ] Build `team.base` with `sa2`, band ranks and derived peril features (B)
- [ ] Build the 1% dev sample (B)
- [ ] Run the diagnostics: distributions, stress by band, `n_high_plus` breakdown, tail percentiles (D)
- [ ] Generate mock data and start the app skeleton (B)

**Check (expected result)**
- [ ] `base` row count equals the source (16.29M), and `malid` is unique
- [ ] No NULL rank in any peril column (a NULL means an unmapped band label)
- [ ] `base.sa2` is populated for more than 99% of rows, and `peril_signature` is empty only where `n_high_plus` is 0
- [ ] `ins_stress` has min 0, max 99, median about 17 and p90 about 67, matching what you were told
- [ ] The dev sample is about 1% of rows (roughly 163k)
- [ ] `address_map` has one row per `malid`, no NULL `sa2`, and 9-character SA2 codes
- [ ] Distinct SA2 codes number roughly 2,400 to 2,500
- [ ] Mapping coverage of the hazard table is above 99%, and `gnaf_pid` agrees between the two sources

**Test (assumptions)**
- [ ] **Band order is right.** Median stress should rise with band for each peril. If "Medium" scores lower than "Moderate", the order is probably wrong, so confirm with the provider before continuing.
- [ ] **Stress is right-skewed.** Median far below p90, with no odd spike at 0 or 99. If there is a spike, investigate how it was capped or filled.
- [ ] **Multi-peril matters.** Share of top-decile stress should rise with `n_high_plus`. Note the result, since it decides how much weight the multi-peril story gets.
- [ ] **Governance.** Written answer received, or escalated, before any bureau data is touched.

```sql
-- Band order test: p50 stress should rise with rank (run per peril)
SELECT fl_r, fl_score, COUNT(*) n, APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)] AS p50
FROM `proj.team.base` GROUP BY 1, 2 ORDER BY 1;
```

### M1: Data foundations (Days 2-4)

**Do**
- [ ] Download the ASGS 2021 SA2 shapefile, simplify it and save `sa2_simplified.geojson` (B)
- [ ] Build `malid_geo` (small lookup from `base`) (B)
- [ ] Train the BQML residual model, then build `base_scored` and `area_hazard` (D)
- [ ] Build `cfn_malid` and `mortgage_month` from the bureau tables (C)

**Check (expected result)**
- [ ] GeoJSON "in data but not on map" count is a handful, not hundreds
- [ ] `malid_geo` has one row per `malid`, with coverage above 99%
- [ ] `base_scored` row count equals `base`, and the mean residual is close to 0
- [ ] `area_hazard` has about 2,400 rows, and `SUM(n_addr)` equals the `base` row count (minus unmatched)
- [ ] `cfn_malid` has one row per credit file
- [ ] `mortgage_month` has no duplicate account-months, and at most 24 months per account
- [ ] Account counts by `month_end` are stable (no month more than about 5% different from its neighbours), with the latest month not partial

**Test (assumptions)**
- [ ] **SA2 edition is 2021.** Codes in the mapping table match the ABS file. A mismatch shows up as hundreds of unmatched codes.
- [ ] **Model is a decomposition, not a discovery.** R-squared will be high because `ins_stress` is built from the peril scores. Record it and note it for the limitations slide. If the fit is low, `ins_stress` is driven mostly by non-hazard inputs, which strengthens the mismatch story.
- [ ] **Rank-based vs band-based model.** The two models should give similar residuals. If they differ materially, use the band-dummy version.
- [ ] **RHI scale is understood.** The distribution should be dominated by the "current" value and decline smoothly. Confirm what each code means before choosing the 30+ and 90+ cut-offs.
- [ ] **Primary-holder rule is reasonable.** Check how many accounts have more than one credit file, to see how much the rule matters.
- [ ] **Address currency.** Share of credit files with a current (open-ended) address. If low, the "current address" rule is weak.

```sql
-- Residual mean should be near 0; spread tells you how much stress is unexplained by hazard
SELECT AVG(residual) AS mean_resid, STDDEV(residual) AS sd_resid,
       APPROX_QUANTILES(residual, 100)[OFFSET(5)] AS p5,
       APPROX_QUANTILES(residual, 100)[OFFSET(95)] AS p95
FROM `proj.team.base_scored`;

-- Monthly stability of the panel (look for a dip in the latest month)
SELECT month_end, COUNT(*) AS acct_months
FROM `proj.team.mortgage_month` GROUP BY 1 ORDER BY 1;
```

### M2: Core analysis and Gate G1 (Days 4-6)

**Do**
- [ ] Build `area_outcomes` and `area_defaults` with small-cell suppression (C)
- [ ] Build `area_summary` with quadrants (D)
- [ ] Run the Gate G1 query (D)
- [ ] Export `area_summary.parquet` and wire the app to real data (B)

**Check (expected result)**
- [ ] No published cell has fewer than 20 accounts (`cells_below_20` is 0)
- [ ] At least 90% of mortgage account-months reach an SA2 (join coverage)
- [ ] `area_summary` has one row per SA2, and the Parquet row count matches
- [ ] Arrears rates are plausible: a low single-digit percentage nationally, with no area at 0% across the board or above about 15%
- [ ] Hardship rate is lower than the arrears rate in nearly every area
- [ ] No quadrant is empty or holds more than about 80% of areas (if so, retune the cut-offs)
- [ ] The map draws every area, with no-data areas in grey, and the tooltip shows text

**Test (assumptions)**
- [ ] **Gate G1: the lens predicts observed distress.** High-stress, low-hazard areas should show clearly higher arrears and hardship than low-stress, low-hazard areas. If rates are flat across quadrants, pivot the lead to tail risk and blind spots.
- [ ] **Stress, not just hazard, explains distress.** Arrears should rise with `mean_stress` within the low-hazard group.
- [ ] **Small areas are not noise.** Plot arrears rate against account count; the spread should narrow as accounts rise (funnel shape). If the smallest areas dominate the extremes, apply a minimum size or smoothing before ranking.
- [ ] **Suppression is not biasing results.** Compare the characteristics of suppressed areas (hazard, stress) with published ones. Rural areas may be over-suppressed, so mention it if so.
- [ ] **Quadrant cut-offs are not driving the result.** Re-run the Gate G1 query with two or three alternative thresholds. The conclusion should hold.

### M3: Validation and scenarios (Days 6-8)

**Do**
- [ ] Build `area_scenarios` for the shock levels (D)
- [ ] Run the validation regressions (D)
- [ ] Run hotspot analysis on the residual (C)
- [ ] Use cases: build `tier_history`, the back-test, the migration matrix, the hardship queue and the origination check (D, C, B)
- [ ] Optional: event study for one disaster (C)
- [ ] Add the shock slider, distress chart and priority list to the app (B)

**Check (expected result)**
- [ ] At shock 0, the scenario table equals `area_summary` exactly
- [ ] The number of high-stress areas rises monotonically with the shock level
- [ ] Regression coefficients have the expected sign (higher stress or residual, higher arrears) and converge without warnings
- [ ] Hotspot results are not all "significant" or all "not significant", and clusters look geographically coherent on the map
- [ ] Back-test features are all measured on or before the snapshot date; outcomes come only after it
- [ ] Tier counts reconcile to the snapshot, and the hardship queue never exceeds capacity
- [ ] Event study (if run): pre-event lines for affected and comparison areas run roughly in parallel

**Test (assumptions)**
- [ ] **Residual adds information beyond hazard.** Compare AIC of "hazard only" against "hazard + residual". If there is no improvement, say so, and lead with the observed-versus-modelled blind spots instead.
- [ ] **Result survives controls.** The residual coefficient should stay in the same direction after adding state (and SEIFA when available). If it vanishes, the pattern may reflect regional economics, not hidden vulnerability.
- [ ] **Hardship tells the same story as arrears.** Run the same model on `hardship_rate`. Divergence is worth explaining.
- [ ] **Scenario logic is defensible.** The shock affects high-hazard areas harder. Check that the result is not dominated by the arbitrary factor of 2, by re-running at 1 and 3.
- [ ] **Tier adds information beyond exposure alone.** Compare the back-test capture share of the tier with a hazard-only ranking; if it is no better, say so.
- [ ] **Tier survives a second snapshot date.** Repeat the back-test on an earlier snapshot; the Priority lift should hold.
- [ ] **Origination shock is monotonic.** A higher shock never improves a borrower's margin.
- [ ] **Event study has enough history.** At least 6 pre-event months must exist within the RHI window, and the comparison group must be similar on stress and hazard.

### M4: App complete and property lookup (Days 7-9)

**Do**
- [ ] Build `address_lookup` from the mapping table (B)
- [ ] Build national percentiles and the demo-address table, export `demo_properties.parquet` (B, D)
- [ ] Wire up live search and the demo-address mode (B)
- [ ] Governance review of everything the app shows (A)

**Check (expected result)**
- [ ] Spot-check 20 addresses: score bands, stress and residual in the app match a direct query on the table
- [ ] Postcode search returns results for postcodes with leading zeros (for example 0800)
- [ ] Live lookup returns in about 2 seconds or less, and falls back cleanly to demo mode if BigQuery is unreachable
- [ ] The percentile shown for an address is consistent with the national quantiles table
- [ ] No bureau field (arrears, hardship, default, account or credit file id) appears on the property view
- [ ] Each demo address is a team or consenting colleague address

**Test (assumptions)**
- [ ] **Address text is searchable.** Try 10 realistic searches (units, ranges like 12-14, abbreviations). Note the failures and keep the demo to formats that work.
- [ ] **One location is not one household.** Check how many `malid`s share the same coordinates (apartment blocks), and be ready to explain it.
- [ ] **Hazard is location-based only.** Confirm the wording on the property view says so.
- [ ] **Search results cannot be enumerated.** A blank or one-letter query returns nothing, and results are capped at 10.

### M5: Freeze and final checks (Days 9-11)

**Do**
- [ ] Feature freeze on Day 9 (A)
- [ ] Re-run all headline queries from scratch and record the query ID beside each slide number (C, D)
- [ ] Run the reconciliation checks (C, D)
- [ ] Complete the demo hardening checklist and record the backup video (B)
- [ ] Finalise the limitations log (A)

**Check (expected result)**
- [ ] Every number on a slide matches a re-run query, within rounding
- [ ] Row counts reconcile across `src`, `base`, `base_scored`, `malid_geo` and `area_hazard`
- [ ] Key uniqueness holds (`malid`, `sa2`) and suppression holds (no cell below the threshold)
- [ ] The app runs end to end offline on the presentation machine, after one warm-up run
- [ ] A second person has reviewed every headline number and its query

**Test (assumptions)**
- [ ] **Headline claim is supported.** The sentence on the title slide ("hazard-only views miss X% of distressed areas") is backed by an actual query, and the percentage is computed the way it is described.
- [ ] **Story matches the data.** If Gate G1 or the residual test came out weak, the narrative has been changed to match, not left as originally planned.
- [ ] **Limitations are honest.** The seven items in the limitations log are on a slide, including circularity and area-level inference.
- [ ] **Questions are rehearsed.** The team can answer: how are the bands defined, why is the model circular and what does the residual mean, how are small areas handled, and why is this permitted use of bureau data?

---

## What changed in v3

- **`team.base` redesigned.** It now carries `sa2` (from the address mapping), cleaned band labels, ranks, `dominant_peril`, `n_high_plus`, `n_severe_plus` and `peril_signature`. It is clustered on `sa2, gnaf_pid`, and holds no model outputs, thresholds or labels.
- **Build order swapped.** The address mapping checks now run before `base`, because `base` joins to the mapping.
- **`malid_geo` is now a small lookup built from `base`** (used by the bureau joins), and `area_hazard` reads `sa2` straight from `base_scored`.
- **`base_scored` adds** `sa2`, `dominant_peril` and `peril_signature`.

## What changed in v2

- **No spatial join.** The existing address mapping table (`malid`, `gnaf_pid`, address, postcode, SA2) replaces the point-in-polygon join and the G-NAF load.
- **Boundaries are map-only.** ABS 2021 SA2 boundaries are downloaded, simplified and saved as `sa2_simplified.geojson` (kept in GCS and on the presentation machine). They are not loaded into BigQuery.
- **Names and state come from the GeoJSON**, not from `area_summary`.
- **Left merge in the app**, so suppressed or no-data areas draw in grey instead of vanishing.
- **BOOL arithmetic fix** retained: BigQuery cannot add BOOLs, so conditions are cast with `CAST(cond AS INT64)`.

## Conventions and placeholders (edit before running)

| Placeholder | Meaning |
|---|---|
| `proj.src.hazard` | Source hazard table (16.29M rows) |
| `proj.team.*` | Team working dataset (all derived tables) |
| `proj.ref.address_map` | Existing mapping: `malid, gnaf_pid, full_address, postcode, sa2` (**adapt column names**) |
| `proj.bureau.account`, `rhi_monthly`, `fha_monthly`, `defaults`, `address` | Bureau tables. **Column names below are assumed; adapt to your schema** |

**Assumptions to confirm**
- Band order is Negligible < Low < Moderate < Medium < High < Severe < Catastrophic.
- RHI scale: the thresholds used below (`>=1` any arrears, `>=2` 30+, `>=4` 90+) are placeholders. Check the real scale.
- Small-cell suppression threshold is 20 accounts (confirm with privacy).
- SA2 codes are **ASGS 2021**, stored as **9-digit strings** everywhere (mapping table, `area_summary`, GeoJSON).
- Bureau data stays in the approved environment; only area-level, suppressed aggregates leave it.

---

## M0: Kickoff and foundations (Days 1-2)

### A. Governance request (message template)

```
Subject: Hackathon: request to use CCR data in a restricted analysis

We are building a hackathon analysis combining catastrophe hazard scores with
area-level credit outcomes (RHI arrears, FHA hardship, defaults). Please confirm:
1. Is this use permitted for the hackathon, and under what conditions?
2. Which environment must the data stay in (project / region / access group)?
3. What output controls apply (minimum cell size, suppression, review before presenting)?
4. Can the property lookup in the demo show hazard data only, with bureau metrics at SA2 level?
Outputs will be aggregated to SA2, small cells suppressed, with no account or
individual-level data in the app or slides.
```

### B. Check the address mapping table (run this before building `base`)

```sql
-- 1. One row and one SA2 per malid (duplicates would inflate every area count)
SELECT COUNT(*) AS rows_, COUNT(DISTINCT malid) AS distinct_malid,
       COUNT(DISTINCT gnaf_pid) AS distinct_gnaf,
       COUNTIF(sa2 IS NULL) AS null_sa2
FROM `proj.ref.address_map`;

-- 2. SA2 code format: expect 9 characters, and roughly 2,400 to 2,500 distinct 2021 SA2s
SELECT LENGTH(CAST(sa2 AS STRING)) AS code_len, COUNT(*) n, COUNT(DISTINCT sa2) AS distinct_sa2
FROM `proj.ref.address_map` GROUP BY 1 ORDER BY 1;

-- 3. Coverage of the hazard table
SELECT COUNT(*) AS hazard_rows,
       COUNTIF(m.malid IS NOT NULL) AS matched,
       COUNTIF(m.malid IS NOT NULL) / COUNT(*) AS coverage
FROM `proj.src.hazard` b
LEFT JOIN `proj.ref.address_map` m USING (malid);        -- aim above 99%

-- 4. gnaf_pid agrees between the hazard data and the mapping
SELECT COUNT(*) AS n, COUNTIF(a.gnaf_pid = b.gnaf_pid) AS agree
FROM `proj.src.hazard` b JOIN `proj.ref.address_map` a USING (malid);
```

The first query matters most: if `address_map` has more than one row per `malid`, the join in `base` will duplicate rows, so fix that first.

### B. Base table (`team.base`)

One row per `malid`. It holds facts and values derived deterministically from the source row, and nothing that depends on a model, a threshold or the bureau data.

| Group | Columns |
|---|---|
| Keys | `malid`, `gnaf_pid` |
| Geography | `sa2` (9-char string), `latitude`, `longitude` |
| Raw bands (cleaned) | `bf_score`, `cy_score`, `eq_score`, `fl_score`, `sc_score` |
| Ranks (0 to 6) | `bf_r`, `cy_r`, `eq_r`, `fl_r`, `sc_r` |
| Derived | `max_peril_r`, `dominant_peril`, `n_high_plus`, `n_severe_plus`, `peril_signature` |
| Stress | `ins_stress` |

Kept out on purpose: address text (lives in `address_lookup`), a GEOGRAPHY point, model outputs (`base_scored`), and quadrant or tier labels (area-level, and cut-offs are not fixed until diagnostics are done).

```sql
CREATE TEMP FUNCTION rank_band(s STRING) AS (
  CASE UPPER(TRIM(s))
    WHEN 'NEGLIGIBLE'   THEN 0
    WHEN 'LOW'          THEN 1
    WHEN 'MODERATE'     THEN 2
    WHEN 'MEDIUM'       THEN 3
    WHEN 'HIGH'         THEN 4
    WHEN 'SEVERE'       THEN 5
    WHEN 'CATASTROPHIC' THEN 6
  END
);

CREATE OR REPLACE TABLE `proj.team.base`
CLUSTER BY sa2, gnaf_pid
OPTIONS (description = 'One row per malid: hazard bands, ranks, derived peril features, stress, SA2') AS
WITH r AS (
  SELECT
    h.malid, h.gnaf_pid,
    LPAD(CAST(m.sa2 AS STRING), 9, '0') AS sa2,
    h.latitude, h.longitude, h.ins_stress,
    INITCAP(TRIM(h.bf_score)) AS bf_score, INITCAP(TRIM(h.cy_score)) AS cy_score,
    INITCAP(TRIM(h.eq_score)) AS eq_score, INITCAP(TRIM(h.fl_score)) AS fl_score,
    INITCAP(TRIM(h.sc_score)) AS sc_score,
    rank_band(h.bf_score) AS bf_r, rank_band(h.cy_score) AS cy_r,
    rank_band(h.eq_score) AS eq_r, rank_band(h.fl_score) AS fl_r,
    rank_band(h.sc_score) AS sc_r
  FROM `proj.src.hazard` h
  LEFT JOIN `proj.ref.address_map` m USING (malid)     -- LEFT: keep unmatched rows (sa2 is NULL)
)
SELECT
  *,
  GREATEST(bf_r, cy_r, eq_r, fl_r, sc_r) AS max_peril_r,
  -- ties resolve in a fixed order: flood, bushfire, storm, cyclone, earthquake (state this if shown)
  CASE GREATEST(bf_r, cy_r, eq_r, fl_r, sc_r)
    WHEN fl_r THEN 'Flood' WHEN bf_r THEN 'Bushfire' WHEN sc_r THEN 'Storm'
    WHEN cy_r THEN 'Cyclone' ELSE 'Earthquake' END AS dominant_peril,
  CAST(bf_r >= 4 AS INT64) + CAST(cy_r >= 4 AS INT64) + CAST(eq_r >= 4 AS INT64)
    + CAST(fl_r >= 4 AS INT64) + CAST(sc_r >= 4 AS INT64) AS n_high_plus,
  CAST(bf_r >= 5 AS INT64) + CAST(cy_r >= 5 AS INT64) + CAST(eq_r >= 5 AS INT64)
    + CAST(fl_r >= 5 AS INT64) + CAST(sc_r >= 5 AS INT64) AS n_severe_plus,
  -- e.g. 'BF|FL' = bushfire and flood both at High or worse; empty string if none
  ARRAY_TO_STRING(ARRAY(
    SELECT p FROM UNNEST([
      IF(bf_r >= 4, 'BF', NULL), IF(cy_r >= 4, 'CY', NULL), IF(eq_r >= 4, 'EQ', NULL),
      IF(fl_r >= 4, 'FL', NULL), IF(sc_r >= 4, 'SC', NULL)]) AS p WHERE p IS NOT NULL), '|') AS peril_signature
FROM r;
```

Design notes: clustering (not partitioning) suits a table of roughly 1 to 2 GB; labels are trimmed and title-cased so the band-dummy model never sees "high" and "High" as different values; the LEFT JOIN keeps unmatched rows so coverage can be measured instead of rows silently disappearing.

### B. 1% dev sample

```sql
CREATE OR REPLACE TABLE `proj.team.base_sample` AS
SELECT * FROM `proj.team.base`
WHERE MOD(ABS(FARM_FINGERPRINT(CAST(malid AS STRING))), 100) = 0;
```

### B. Quality checks on `base`

```sql
-- 1. Structure, keys and ranges (expect n = d_malid = source rows; the rest near 0)
SELECT
  COUNT(*) AS n, COUNT(DISTINCT malid) AS d_malid, COUNT(DISTINCT gnaf_pid) AS d_gnaf,
  COUNTIF(sa2 IS NULL) AS null_sa2,
  COUNTIF(bf_r IS NULL OR cy_r IS NULL OR eq_r IS NULL OR fl_r IS NULL OR sc_r IS NULL) AS null_rank,
  COUNTIF(ins_stress IS NULL) AS null_stress,
  COUNTIF(ins_stress NOT BETWEEN 0 AND 99) AS stress_out_of_range,
  COUNTIF(n_high_plus > 0 AND peril_signature = '') AS signature_mismatch,
  (SELECT COUNT(*) FROM `proj.src.hazard`) AS source_rows
FROM `proj.team.base`;

-- 2. Distinct labels actually present (check spelling, casing, whitespace)
SELECT 'bf' AS peril, bf_score AS label, COUNT(*) n FROM `proj.src.hazard` GROUP BY 1, 2
UNION ALL SELECT 'cy', cy_score, COUNT(*) FROM `proj.src.hazard` GROUP BY 1, 2
UNION ALL SELECT 'eq', eq_score, COUNT(*) FROM `proj.src.hazard` GROUP BY 1, 2
UNION ALL SELECT 'fl', fl_score, COUNT(*) FROM `proj.src.hazard` GROUP BY 1, 2
UNION ALL SELECT 'sc', sc_score, COUNT(*) FROM `proj.src.hazard` GROUP BY 1, 2
ORDER BY 1, 2;
```

### D. Diagnostics

```sql
-- Stress distribution (101 values: min, p1 ... p99, max)
SELECT APPROX_QUANTILES(ins_stress, 100) AS q FROM `proj.team.base`;

-- Stress by band, per peril (shows which perils actually move stress)
SELECT 'bf' AS peril, bf_score AS band, bf_r AS rnk, COUNT(*) n,
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)] p50,
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(90)] p90
FROM `proj.team.base` GROUP BY 1, 2, 3
UNION ALL
SELECT 'cy', cy_score, cy_r, COUNT(*), APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)],
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(90)] FROM `proj.team.base` GROUP BY 1, 2, 3
UNION ALL
SELECT 'eq', eq_score, eq_r, COUNT(*), APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)],
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(90)] FROM `proj.team.base` GROUP BY 1, 2, 3
UNION ALL
SELECT 'fl', fl_score, fl_r, COUNT(*), APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)],
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(90)] FROM `proj.team.base` GROUP BY 1, 2, 3
UNION ALL
SELECT 'sc', sc_score, sc_r, COUNT(*), APPROX_QUANTILES(ins_stress, 100)[OFFSET(50)],
  APPROX_QUANTILES(ins_stress, 100)[OFFSET(90)] FROM `proj.team.base` GROUP BY 1, 2, 3
ORDER BY peril, rnk;

-- Multi-peril concentration: does top-decile stress rise with peril count?
SELECT n_high_plus, COUNT(*) n,
  AVG(ins_stress) AS avg_stress,
  COUNTIF(ins_stress >= 67) / COUNT(*) AS share_top10_stress
FROM `proj.team.base`
GROUP BY n_high_plus ORDER BY n_high_plus;

-- Correlations on the dev sample (Pearson on ranks; percent rank of stress gives a Spearman proxy)
WITH s AS (
  SELECT *, PERCENT_RANK() OVER (ORDER BY ins_stress) AS stress_pr
  FROM `proj.team.base_sample`
)
SELECT
  CORR(bf_r, stress_pr) AS bf, CORR(cy_r, stress_pr) AS cy, CORR(eq_r, stress_pr) AS eq,
  CORR(fl_r, stress_pr) AS fl, CORR(sc_r, stress_pr) AS sc, CORR(n_high_plus, stress_pr) AS n_high
FROM s;

-- Tail of stress (needed for tier thresholds)
SELECT
  APPROX_QUANTILES(ins_stress, 1000)[OFFSET(750)] AS p75,
  APPROX_QUANTILES(ins_stress, 1000)[OFFSET(900)] AS p90,
  APPROX_QUANTILES(ins_stress, 1000)[OFFSET(950)] AS p95,
  APPROX_QUANTILES(ins_stress, 1000)[OFFSET(990)] AS p99
FROM `proj.team.base`;
```

### B. Mock data for the app (so the engineer is never blocked)

`mock_data.py` generates a fake `area_summary.parquet` (data only) and a gridded `sa2_simplified.geojson` (geometry, name and state), with the same schema as the real files.

```python
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import box

rng = np.random.default_rng(42)
nx, ny = 40, 30
x0, x1, y0, y1 = 113, 154, -39, -11
dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
states = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]

rows, geo_rows, geoms = [], [], []
for i in range(nx):
    for j in range(ny):
        sa2 = f"{100000000 + i * 100 + j}"                     # 9-digit string, like real codes
        hz = float(rng.beta(1.5, 4))
        stress = float(np.clip(rng.gamma(2, 10) + 20 * hz, 0, 99))
        accts = int(rng.integers(50, 3000))
        arrears = float(np.clip(0.01 + 0.0006 * stress + rng.normal(0, 0.01), 0, 0.3))
        rows.append(dict(
            sa2=sa2, n_addr=int(rng.integers(500, 20000)), mean_stress=stress,
            p90_stress=min(99.0, stress * 1.8), share_high_hazard=hz, share_multi_peril=hz * 0.4,
            mean_residual=float(rng.normal(0, 8)), n_accts=accts,
            arrears_rate=arrears, arrears30_rate=arrears * 0.6, arrears90_rate=arrears * 0.25,
            hardship_rate=float(arrears * 0.3),
        ))
        geo_rows.append(dict(sa2=sa2, sa2_name=f"Area {sa2}", state=str(rng.choice(states))))
        geoms.append(box(x0 + i * dx, y0 + j * dy, x0 + (i + 1) * dx, y0 + (j + 1) * dy))

pd.DataFrame(rows).to_parquet("area_summary.parquet", index=False)
gpd.GeoDataFrame(geo_rows, geometry=geoms, crs="EPSG:4326").to_file("sa2_simplified.geojson", driver="GeoJSON")
print("mock files written")
```

---

## M1: Data foundations (Days 2-4)

### B. Download and prepare SA2 boundaries (map only)

1. Download the **ASGS 2021 SA2, GDA2020 shapefile** from the ABS (digital boundary files, ASGS Edition 3). Typical file name: `SA2_2021_AUST_GDA2020.shp` (plus its `.dbf`, `.shx`, `.prj` companions).
2. Confirm that the edition matches the SA2 codes in your mapping table.
3. Run `prepare_boundaries.py`:

```python
import geopandas as gpd, pandas as pd

STATE_ABBR = {
    "New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD", "South Australia": "SA",
    "Western Australia": "WA", "Tasmania": "TAS", "Northern Territory": "NT",
    "Australian Capital Territory": "ACT", "Other Territories": "OT",
}

b = gpd.read_file("SA2_2021_AUST_GDA2020.shp")
b = b.rename(columns={"SA2_CODE21": "sa2", "SA2_NAME21": "sa2_name", "STE_NAME21": "state_name"})
b["sa2"] = b["sa2"].astype(str).str.zfill(9)                   # keep codes as 9-digit strings
b["state"] = b["state_name"].map(STATE_ABBR).fillna(b["state_name"])
b = b[b.geometry.notna() & ~b.geometry.is_empty]               # drops non-geographic SA2s
b = b.to_crs(4326)                                             # web maps need lat/long
b["geometry"] = b.geometry.simplify(0.001, preserve_topology=True)   # raise to 0.005 if the map lags

b[["sa2", "sa2_name", "state", "geometry"]].to_file("sa2_simplified.geojson", driver="GeoJSON")
print(len(b), "areas written")

# Join check against the codes actually in your data (export distinct SA2s from address_map first)
codes = pd.read_csv("sa2_codes_in_data.csv", dtype=str)["sa2"].str.zfill(9)
print("in data but not on map:", len(set(codes) - set(b.sa2)))
print("on map but not in data:", len(set(b.sa2) - set(codes)))
```

Export the code list with:

```sql
SELECT DISTINCT LPAD(CAST(sa2 AS STRING), 9, '0') AS sa2 FROM `proj.ref.address_map`;
```

A handful of "in data but not on map" codes is normal (for example "no usual address" or "migratory" SA2s). Hundreds means an edition mismatch.

4. Upload the file to the team bucket and keep a copy on the presentation machine:

```bash
gsutil cp sa2_simplified.geojson gs://YOUR_BUCKET/sa2_simplified.geojson
```

### B. `malid_geo` (small malid-to-SA2 lookup, built from `base`)

The bureau joins (`area_outcomes`, `area_defaults`) use this narrow table so they never scan the full `base`.

```sql
CREATE OR REPLACE TABLE `proj.team.malid_geo`
CLUSTER BY malid AS
SELECT malid, sa2
FROM `proj.team.base`
WHERE sa2 IS NOT NULL;

-- Must be equal (one SA2 per malid)
SELECT COUNT(*) AS rows_, COUNT(DISTINCT malid) AS distinct_malid FROM `proj.team.malid_geo`;
```

### D. Residual model (BQML)

```sql
-- Model 1: linear regression on band ranks (pragmatic, easy to explain)
CREATE OR REPLACE MODEL `proj.team.stress_vs_hazard`
OPTIONS (model_type = 'LINEAR_REG', input_label_cols = ['ins_stress']) AS
SELECT ins_stress, bf_r, cy_r, eq_r, fl_r, sc_r, n_high_plus
FROM `proj.team.base`
WHERE MOD(ABS(FARM_FINGERPRINT(CAST(malid AS STRING))), 10) = 0;   -- 10% training sample

SELECT * FROM ML.EVALUATE(MODEL `proj.team.stress_vs_hazard`);

-- Model 2 (compare): bands as categories (BQML one-hot encodes STRING inputs automatically)
CREATE OR REPLACE MODEL `proj.team.stress_vs_hazard_bands`
OPTIONS (model_type = 'LINEAR_REG', input_label_cols = ['ins_stress']) AS
SELECT ins_stress, bf_score, cy_score, eq_score, fl_score, sc_score
FROM `proj.team.base`
WHERE MOD(ABS(FARM_FINGERPRINT(CAST(malid AS STRING))), 10) = 0;

SELECT * FROM ML.EVALUATE(MODEL `proj.team.stress_vs_hazard_bands`);

-- Optional Model 3: boosted tree to capture interactions
-- CREATE OR REPLACE MODEL `proj.team.stress_vs_hazard_bt`
-- OPTIONS (model_type = 'BOOSTED_TREE_REGRESSOR', input_label_cols = ['ins_stress'], max_iterations = 50) AS
-- SELECT ins_stress, bf_score, cy_score, eq_score, fl_score, sc_score
-- FROM `proj.team.base` WHERE MOD(ABS(FARM_FINGERPRINT(CAST(malid AS STRING))), 10) = 0;
```

Caution: `ins_stress` is partly built from these peril scores, so a strong fit is expected by construction. Present this as decomposition (what is left over), not prediction.

### D. Score every address (`team.base_scored`)

```sql
CREATE OR REPLACE TABLE `proj.team.base_scored`
CLUSTER BY gnaf_pid AS
SELECT
  malid, gnaf_pid, sa2, latitude, longitude, ins_stress,
  bf_score, cy_score, eq_score, fl_score, sc_score,
  bf_r, cy_r, eq_r, fl_r, sc_r, max_peril_r, dominant_peril, peril_signature,
  n_high_plus, n_severe_plus,
  predicted_ins_stress,
  ins_stress - predicted_ins_stress AS residual
FROM ML.PREDICT(
  MODEL `proj.team.stress_vs_hazard`,
  (SELECT * FROM `proj.team.base`)
);
```

### D. `area_hazard` (hazard, stress and residual by SA2)

```sql
CREATE OR REPLACE TABLE `proj.team.area_hazard` AS
SELECT
  b.sa2,
  COUNT(*) AS n_addr,
  AVG(b.ins_stress) AS mean_stress,
  APPROX_QUANTILES(b.ins_stress, 100)[OFFSET(90)] AS p90_stress,
  AVG(CAST(b.max_peril_r >= 4 AS INT64)) AS share_high_hazard,
  AVG(CAST(b.n_high_plus >= 2 AS INT64)) AS share_multi_peril,
  AVG(b.residual) AS mean_residual
FROM `proj.team.base_scored` b
WHERE b.sa2 IS NOT NULL
GROUP BY b.sa2;
```

### C. `cfn_malid` (one address per credit file)

Columns assumed: `cfn, malid, addr_start_date, addr_end_date`.

```sql
CREATE OR REPLACE TABLE `proj.team.cfn_malid`
CLUSTER BY cfn AS
SELECT cfn, malid
FROM `proj.bureau.address`
WHERE malid IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY cfn
  ORDER BY (addr_end_date IS NULL) DESC, addr_start_date DESC   -- current address first
) = 1;

-- Must be equal
SELECT COUNT(*) AS rows_, COUNT(DISTINCT cfn) AS distinct_cfn FROM `proj.team.cfn_malid`;
```

Because bureau addresses already carry `malid`, this joins to the same `malid_geo`, so hazard and bureau outputs share one geography.

### C. `mortgage_month` (account-month panel, mortgages only)

Columns assumed: `account_id, primary_cfn, account_type, owner_occupier_flag` on `account`; `account_id, month_end, rhi_value` on `rhi_monthly`; `account_id, month_end, fha_flag` on `fha_monthly`.

```sql
CREATE OR REPLACE TABLE `proj.team.mortgage_month`
CLUSTER BY cfn AS
SELECT
  a.account_id,
  a.primary_cfn AS cfn,                       -- primary holder only avoids joint-account double counting
  r.month_end,
  r.rhi_value,
  COALESCE(f.fha_flag, 0) AS fha_flag
FROM `proj.bureau.account` a
JOIN `proj.bureau.rhi_monthly` r USING (account_id)
LEFT JOIN `proj.bureau.fha_monthly` f USING (account_id, month_end)
WHERE a.account_type = 'MORTGAGE'
  -- AND a.owner_occupier_flag = TRUE         -- enable if available
  AND r.month_end >= DATE_SUB(CURRENT_DATE(), INTERVAL 24 MONTH);

-- Must be equal (no duplicated account-months)
SELECT COUNT(*) AS rows_, COUNT(DISTINCT CONCAT(account_id, CAST(month_end AS STRING))) AS uniq
FROM `proj.team.mortgage_month`;
```

---

## M2: Core analysis and Gate G1 (Days 4-6)

### C. `area_outcomes` (area x month, suppressed)

```sql
CREATE OR REPLACE TABLE `proj.team.area_outcomes` AS
SELECT
  g.sa2, m.month_end,
  COUNT(*)                        AS n_accts,
  COUNTIF(m.rhi_value >= 1)       AS n_past_due,
  COUNTIF(m.rhi_value >= 2)       AS n_30p,        -- map to your RHI scale
  COUNTIF(m.rhi_value >= 4)       AS n_90p,        -- map to your RHI scale
  SUM(m.fha_flag)                 AS n_hardship
FROM `proj.team.mortgage_month` m
JOIN `proj.team.cfn_malid` c USING (cfn)
JOIN `proj.team.malid_geo` g USING (malid)
GROUP BY g.sa2, m.month_end
HAVING COUNT(*) >= 20;                              -- small-cell suppression

-- Join coverage: share of mortgage account-months that reach an SA2 (aim above 90%)
SELECT
  (SELECT COUNT(*) FROM `proj.team.mortgage_month`) AS acct_months,
  (SELECT SUM(n_accts) FROM `proj.team.area_outcomes`) AS acct_months_in_areas;
```

### C. `area_defaults` (listed defaults, last 12 months)

Columns assumed on `defaults`: `cfn, listed_date`.

```sql
CREATE OR REPLACE TABLE `proj.team.area_defaults` AS
SELECT
  g.sa2,
  COUNT(DISTINCT d.cfn) AS n_cfn_with_default
FROM `proj.bureau.defaults` d
JOIN `proj.team.cfn_malid` c USING (cfn)
JOIN `proj.team.malid_geo` g USING (malid)
WHERE d.listed_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY g.sa2
HAVING COUNT(DISTINCT d.cfn) >= 5;                  -- suppress small counts
```

Defaults are typically across all credit products, so describe them as broader financial distress, not mortgage default.

### D. `area_summary` (one row per SA2; data only, names and state come from the GeoJSON)

```sql
DECLARE hazard_cut FLOAT64 DEFAULT 0.30;   -- tune after viewing distributions
DECLARE stress_cut FLOAT64 DEFAULT 30.0;   -- tune after viewing distributions

CREATE OR REPLACE TABLE `proj.team.area_summary` AS
WITH latest AS (SELECT MAX(month_end) AS m FROM `proj.team.area_outcomes`),
o AS (
  SELECT sa2,
         SUM(n_accts)    AS accts_3m,
         SUM(n_past_due) AS pd_3m,
         SUM(n_30p)      AS d30_3m,
         SUM(n_90p)      AS d90_3m,
         SUM(n_hardship) AS hd_3m
  FROM `proj.team.area_outcomes`
  WHERE month_end > DATE_SUB((SELECT m FROM latest), INTERVAL 3 MONTH)
  GROUP BY sa2
)
SELECT
  h.sa2, h.n_addr, h.mean_stress, h.p90_stress, h.share_high_hazard, h.share_multi_peril,
  h.mean_residual,
  o.accts_3m AS n_accts,
  SAFE_DIVIDE(o.pd_3m,  o.accts_3m) AS arrears_rate,
  SAFE_DIVIDE(o.d30_3m, o.accts_3m) AS arrears30_rate,
  SAFE_DIVIDE(o.d90_3m, o.accts_3m) AS arrears90_rate,
  SAFE_DIVIDE(o.hd_3m,  o.accts_3m) AS hardship_rate,
  h.share_high_hazard >= hazard_cut AS hazard_high,
  h.mean_stress >= stress_cut       AS stress_high,
  CONCAT(IF(h.share_high_hazard >= hazard_cut, 'High hazard', 'Low hazard'), ' / ',
         IF(h.mean_stress >= stress_cut,       'High stress', 'Low stress')) AS quadrant
FROM `proj.team.area_hazard` h
LEFT JOIN o USING (sa2);
```

Add SEIFA and defaults by joining on `sa2` once those tables exist.

### D. Gate G1 query (does the lens predict observed distress?)

```sql
SELECT quadrant,
  COUNT(*) AS n_areas,
  SUM(n_accts) AS accts,
  SAFE_DIVIDE(SUM(arrears_rate * n_accts),  SUM(n_accts)) AS arrears_rate,
  SAFE_DIVIDE(SUM(hardship_rate * n_accts), SUM(n_accts)) AS hardship_rate
FROM `proj.team.area_summary`
WHERE n_accts IS NOT NULL
GROUP BY quadrant
ORDER BY quadrant;
```

**Decision rule:** if the high-stress, low-hazard quadrant shows meaningfully higher arrears and hardship than low-stress, low-hazard, continue with the mismatch story. If the rates are flat across quadrants, pivot the lead to tail risk and blind spots.

### B. Export for the app

```bash
bq extract --destination_format=PARQUET \
  proj:team.area_summary gs://YOUR_BUCKET/area_summary.parquet
gsutil cp gs://YOUR_BUCKET/area_summary.parquet ./area_summary.parquet
gsutil cp gs://YOUR_BUCKET/sa2_simplified.geojson ./sa2_simplified.geojson
```

Or from Python:

```python
from google.cloud import bigquery
df = bigquery.Client().query("SELECT * FROM `proj.team.area_summary`").to_dataframe()
df["sa2"] = df["sa2"].astype(str).str.zfill(9)
df.to_parquet("area_summary.parquet", index=False)
```

---

## M3: Validation and scenarios (Days 6-8)

### D. Premium-shock scenarios (precomputed)

```sql
-- Illustrative assumption: shock hits high-hazard areas harder.
-- Label as illustrative on the slide and in the app.
CREATE OR REPLACE TABLE `proj.team.area_scenarios` AS
SELECT s.*, shock,
  LEAST(99, s.mean_stress * (1 + (shock / 100) * s.share_high_hazard * 2)) AS stress_adj
FROM `proj.team.area_summary` s, UNNEST([0, 10, 20, 30]) AS shock;

-- How many areas and accounts cross the high-stress line under each shock?
SELECT shock,
  COUNTIF(stress_adj >= 30) AS areas_high_stress,
  SUM(IF(stress_adj >= 30, n_accts, 0)) AS accts_in_high_stress_areas
FROM `proj.team.area_scenarios`
GROUP BY shock ORDER BY shock;
```

### D. Validation: does the residual explain observed distress? (`validation.py`)

```python
import numpy as np, pandas as pd, geopandas as gpd
import statsmodels.api as sm
import statsmodels.formula.api as smf

df = pd.read_parquet("area_summary.parquet").dropna(subset=["arrears_rate", "n_accts"])
geo = gpd.read_file("sa2_simplified.geojson")[["sa2", "state"]]
df = df.merge(geo, on="sa2", how="left")
# df = df.merge(seifa, on="sa2")  # add SEIFA decile when available

for c in ["share_high_hazard", "mean_stress", "mean_residual"]:
    df[c + "_z"] = (df[c] - df[c].mean()) / df[c].std()

def fit(formula, outcome):
    return smf.glm(
        formula.replace("OUT", outcome), data=df,
        family=sm.families.Binomial(), var_weights=df["n_accts"]
    ).fit(cov_type="HC1")

controls = "C(state)"                                 # + " + seifa_decile" when available
m_hazard = fit(f"OUT ~ share_high_hazard_z + {controls}", "arrears_rate")
m_stress = fit(f"OUT ~ share_high_hazard_z + mean_stress_z + {controls}", "arrears_rate")
m_resid  = fit(f"OUT ~ share_high_hazard_z + mean_residual_z + {controls}", "arrears_rate")

for name, m in [("hazard only", m_hazard), ("hazard + stress", m_stress), ("hazard + residual", m_resid)]:
    print(f"\n=== {name} === AIC {m.aic:.1f}")
    print(m.summary2().tables[1].loc[lambda t: ~t.index.str.startswith("C(state)")])

# Repeat for hardship_rate. If the residual adds explanatory power beyond hazard, the
# 'hidden vulnerability' quadrant is real. Compare AIC and the residual coefficient.
```

### C. Hotspots (Gi* on the residual) (`hotspots.py`)

```python
import geopandas as gpd, pandas as pd
from libpysal import weights
from esda.getisord import G_Local

df = pd.read_parquet("area_summary.parquet")
geo = gpd.read_file("sa2_simplified.geojson")[["sa2", "geometry"]]
gdf = geo.merge(df, on="sa2").dropna(subset=["mean_residual"]).reset_index(drop=True)

w = weights.Queen.from_dataframe(gdf, use_index=False)
if w.islands:                                          # islands break contiguity weights
    w = weights.KNN.from_dataframe(gdf, k=6)
w.transform = "R"

g = G_Local(gdf["mean_residual"].values, w, transform="R", star=True, permutations=999, seed=42)
gdf["gi_z"] = g.Zs
gdf["gi_p"] = g.p_sim
gdf["hotspot"] = pd.cut(gdf["gi_z"], [-99, -1.96, 1.96, 99], labels=["cold", "not sig", "hot"])
print(gdf["hotspot"].value_counts())
gdf[["sa2", "gi_z", "gi_p", "hotspot"]].to_parquet("hotspots.parquet", index=False)
```

Merge `hotspots.parquet` into the app as an optional map layer. Describe it as clustering of unexplained stress, not causation.

### C. Optional event study (flood or fire)

Prepare `team.event_areas(sa2, affected BOOL, event_month DATE)`. Affected areas come from LGA disaster declarations or event footprints; build the comparison group from unaffected areas in the same state with similar `mean_stress` and SEIFA.

```sql
WITH p AS (
  SELECT
    e.affected,
    DATE_DIFF(o.month_end, e.event_month, MONTH) AS rel_month,
    SUM(o.n_accts) AS accts, SUM(o.n_past_due) AS pd, SUM(o.n_hardship) AS hd
  FROM `proj.team.area_outcomes` o
  JOIN `proj.team.event_areas` e USING (sa2)
  GROUP BY e.affected, rel_month
  HAVING rel_month BETWEEN -12 AND 12
)
SELECT affected, rel_month,
  SAFE_DIVIDE(pd, accts) AS arrears_rate,
  SAFE_DIVIDE(hd, accts) AS hardship_rate
FROM p ORDER BY affected, rel_month;
```

Chart both lines with `rel_month` on the x axis. A simple difference-in-differences:

```sql
WITH base AS (
  SELECT affected, IF(rel_month < 0, 'pre', 'post') AS period,
         SAFE_DIVIDE(SUM(hd), SUM(accts)) AS hardship_rate
  FROM (
    SELECT e.affected, DATE_DIFF(o.month_end, e.event_month, MONTH) AS rel_month,
           o.n_accts AS accts, o.n_hardship AS hd
    FROM `proj.team.area_outcomes` o JOIN `proj.team.event_areas` e USING (sa2)
  )
  WHERE rel_month BETWEEN -12 AND 12
  GROUP BY affected, period
)
SELECT
  (MAX(IF(affected AND period = 'post', hardship_rate, NULL)) - MAX(IF(affected AND period = 'pre', hardship_rate, NULL)))
  - (MAX(IF(NOT affected AND period = 'post', hardship_rate, NULL)) - MAX(IF(NOT affected AND period = 'pre', hardship_rate, NULL)))
  AS diff_in_diff
FROM base;
```

Check that you have enough pre-event months within the 24-month RHI window, since history length limits which events are usable.

---

## M3b: Use-case builds (tier, back-test, migration, queue, origination check)

Run after step 12 of the cheat sheet. Assumes a `proj.bureau.judgments(cfn, judgment_date)` table, which needs confirming. Scripts that use `DECLARE` must run as a single BigQuery script.

### D. `tier_history` (monthly snapshot; run once per month, and once per shock level)

First run: replace `INSERT INTO` with `CREATE OR REPLACE TABLE ... AS`. Later runs keep `INSERT INTO` with the same column order.

```sql
-- Parameters: change per run
DECLARE t0 DATE DEFAULT DATE '2026-06-30';   -- snapshot month-end
DECLARE shock_pct FLOAT64 DEFAULT 0;         -- 0 for base; 10, 20, 30 for sensitivity
DECLARE stress_cut FLOAT64 DEFAULT 30.0;     -- match area_summary

INSERT INTO `proj.team.tier_history`
WITH strain AS (
  SELECT m.cfn,
    MAX(IF(m.month_end = t0, m.rhi_value, NULL)) AS rhi_t0,
    MAX(IF(m.month_end BETWEEN DATE_SUB(t0, INTERVAL 2 MONTH) AND t0,
           CAST(m.rhi_value >= 2 AS INT64), 0)) AS arrears30_3m,
    MAX(IF(m.month_end BETWEEN DATE_SUB(t0, INTERVAL 11 MONTH) AND t0,
           m.fha_flag, 0)) AS hardship_12m
  FROM `proj.team.mortgage_month` m
  WHERE m.month_end BETWEEN DATE_SUB(t0, INTERVAL 11 MONTH) AND t0
  GROUP BY m.cfn
),
events AS (
  SELECT cfn,
    MAX(CAST(listed_date BETWEEN DATE_SUB(t0, INTERVAL 11 MONTH) AND t0 AS INT64)) AS default_12m
  FROM `proj.bureau.defaults` GROUP BY cfn
),
judg AS (
  SELECT cfn,
    MAX(CAST(judgment_date BETWEEN DATE_SUB(t0, INTERVAL 11 MONTH) AND t0 AS INT64)) AS judgment_12m
  FROM `proj.bureau.judgments` GROUP BY cfn
),
exp AS (
  SELECT c.cfn, c.malid, b.n_high_plus, b.dominant_peril,
    LEAST(99, b.ins_stress * (1 + shock_pct / 100 * CAST(b.max_peril_r >= 4 AS INT64) * 2)) AS stress_shock
  FROM `proj.team.cfn_malid` c
  JOIN `proj.team.base` b USING (malid)
),
flags AS (
  SELECT s.cfn, e.malid, e.dominant_peril,
    (COALESCE(e.n_high_plus, 0) >= 1 OR COALESCE(e.stress_shock, 0) >= stress_cut) AS exposed,
    s.rhi_t0, s.arrears30_3m, s.hardship_12m,
    COALESCE(ev.default_12m, 0) AS default_12m,
    COALESCE(j.judgment_12m, 0) AS judgment_12m,
    COALESCE(s.arrears30_3m, 0) + COALESCE(s.hardship_12m, 0)
      + COALESCE(ev.default_12m, 0) + COALESCE(j.judgment_12m, 0) AS strain
  FROM strain s
  LEFT JOIN exp e USING (cfn)
  LEFT JOIN events ev USING (cfn)
  LEFT JOIN judg j USING (cfn)
)
SELECT t0 AS snapshot_month, shock_pct, cfn, malid,
  CASE
    WHEN exposed AND strain >= 2 THEN 'Priority'
    WHEN (exposed AND strain = 1) OR (NOT exposed AND strain >= 2) THEN 'Act'
    WHEN exposed OR strain = 1 THEN 'Watch'
    ELSE 'Low'
  END AS tier,
  strain, exposed, rhi_t0, arrears30_3m, hardship_12m, default_12m, judgment_12m,
  ARRAY_TO_STRING([
    IF(exposed, CONCAT('exposed: ', COALESCE(dominant_peril, 'hazard')), NULL),
    IF(arrears30_3m = 1, '30+ days late in last 3 months', NULL),
    IF(hardship_12m = 1, 'hardship in last 12 months', NULL),
    IF(default_12m = 1, 'default in last 12 months', NULL),
    IF(judgment_12m = 1, 'judgment in last 12 months', NULL)
  ], '; ') AS drivers
FROM flags;
```

### D. Back-test: forward 12 months by tier

Pick a snapshot at least 12 months before the latest month in `mortgage_month`. The denominator is every customer in the tier. The numerators count only new events, meaning hardship or 30+ arrears that were not already present at the snapshot.

```sql
DECLARE t0 DATE DEFAULT DATE '2025-06-30';
WITH snap AS (
  SELECT * FROM `proj.team.tier_history` WHERE snapshot_month = t0 AND shock_pct = 0
),
fwd AS (
  SELECT cfn,
    MAX(IF(fha_flag = 1, 1, 0)) AS hardship_fwd,
    MAX(IF(rhi_value >= 2, 1, 0)) AS arrears30_fwd
  FROM `proj.team.mortgage_month`
  WHERE month_end > t0 AND month_end <= DATE_ADD(t0, INTERVAL 12 MONTH)
  GROUP BY cfn
),
by_tier AS (
  SELECT s.tier, COUNT(*) AS n,
    SUM(CAST(COALESCE(f.hardship_fwd, 0) = 1 AND s.hardship_12m = 0 AS INT64)) AS new_hardship,
    SUM(CAST(COALESCE(f.arrears30_fwd, 0) = 1 AND s.arrears30_3m = 0 AS INT64)) AS new_arrears30
  FROM snap s LEFT JOIN fwd f USING (cfn)
  GROUP BY s.tier
)
SELECT tier, n,
  SAFE_DIVIDE(new_hardship, n) AS hardship_rate,
  SAFE_DIVIDE(new_arrears30, n) AS arrears30_rate,
  SAFE_DIVIDE(new_hardship, SUM(new_hardship) OVER ()) AS share_of_hardship_cases
FROM by_tier
ORDER BY CASE tier WHEN 'Priority' THEN 1 WHEN 'Act' THEN 2 WHEN 'Watch' THEN 3 ELSE 4 END;
```

### D. Migration matrix (monitoring)

```sql
SELECT a.tier AS from_tier, b.tier AS to_tier, COUNT(*) AS n
FROM `proj.team.tier_history` a
JOIN `proj.team.tier_history` b USING (cfn)
WHERE a.snapshot_month = DATE '2026-05-31' AND b.snapshot_month = DATE '2026-06-30'
  AND a.shock_pct = 0 AND b.shock_pct = 0
GROUP BY 1, 2 ORDER BY 1, 2;
```

### D. Shock sensitivity (monitoring and origination)

Run `tier_history` at shock 10, 20 and 30, then compare with the base counts.

```sql
SELECT shock_pct, tier, COUNT(*) AS n
FROM `proj.team.tier_history`
WHERE snapshot_month = DATE '2026-06-30'
GROUP BY 1, 2 ORDER BY 1, 2;
```

### C and D. Hardship queue (capped, split by path)

```sql
DECLARE cap_per_path INT64 DEFAULT 500;      -- weekly outreach capacity per path
CREATE OR REPLACE TABLE `proj.team.hardship_queue` AS
WITH ranked AS (
  SELECT *,
    CASE tier WHEN 'Priority' THEN 1 WHEN 'Act' THEN 2 END AS tier_rank,
    IF(COALESCE(rhi_t0, 0) >= 1, 'collections', 'early_care') AS path
  FROM `proj.team.tier_history`
  WHERE snapshot_month = DATE '2026-06-30' AND shock_pct = 0 AND tier IN ('Priority', 'Act')
)
SELECT cfn, tier, path, drivers,
  ROW_NUMBER() OVER (PARTITION BY path ORDER BY tier_rank, strain DESC, COALESCE(rhi_t0, 0) DESC) AS queue_pos
FROM ranked
QUALIFY queue_pos <= cap_per_path;
```

### B. Origination serviceability check (Python, illustrative)

All inputs are user-entered or assumed. This is an affordability illustration, not a credit decision. Thresholds per tier are policy, set by credit risk.

```python
def serviceability_margin(annual_income, monthly_repayment, base_premium, shock_pct, living_costs):
    """Share of income left after repayments, insurance and living costs."""
    if annual_income <= 0:
        raise ValueError("income must be positive")
    repay = 12 * monthly_repayment
    before = annual_income - repay - base_premium - living_costs
    after = annual_income - repay - base_premium * (1 + shock_pct / 100) - living_costs
    return {"margin_before": before / annual_income,
            "margin_after": after / annual_income,
            "change": (after - before) / annual_income}

# Checks
assert abs(serviceability_margin(120_000, 2_500, 2_400, 0, 30_000)["change"]) < 1e-12
a = serviceability_margin(120_000, 2_500, 2_400, 30, 30_000)
b = serviceability_margin(120_000, 2_500, 2_400, 60, 30_000)
assert a["margin_after"] > b["margin_after"]          # higher shock never improves margin
# Hand check: before 0.48; after a 30% premium rise (2,400 to 3,120) is 0.474, a change of -0.006
print(round(a["margin_before"], 4), round(a["margin_after"], 4))
```

## M4: App complete and property lookup (Days 7-9)

### B. `address_lookup` (from the existing mapping, replaces the G-NAF build)

```sql
CREATE OR REPLACE TABLE `proj.team.address_lookup`
CLUSTER BY postcode AS
SELECT
  gnaf_pid,
  UPPER(full_address) AS full_address,
  LPAD(CAST(postcode AS STRING), 4, '0') AS postcode,     -- keeps NT postcodes like 0800
  LPAD(CAST(sa2 AS STRING), 9, '0') AS sa2
FROM `proj.ref.address_map`;
```

If there is no usable postcode column, extract it from the address text: `REGEXP_EXTRACT(full_address, r'(\d{4})\s*$')`.

### B. National percentiles for the property view

```sql
CREATE OR REPLACE TABLE `proj.team.national_quantiles` AS
SELECT 'ALL' AS scope, APPROX_QUANTILES(ins_stress, 100) AS q FROM `proj.team.base`;
```

### B. Property lookup query (parameterised)

```sql
SELECT b.gnaf_pid, b.latitude, b.longitude, b.ins_stress, b.predicted_ins_stress, b.residual,
       b.bf_score, b.cy_score, b.eq_score, b.fl_score, b.sc_score,
       b.n_high_plus, b.max_peril_r
FROM `proj.team.base_scored` b
WHERE b.gnaf_pid = @pid;
```

Because `base_scored` is clustered on `gnaf_pid`, each lookup scans a tiny slice.

### B. Demo-address fallback (precompute 10 to 20 addresses)

```sql
CREATE OR REPLACE TABLE `proj.team.demo_properties` AS
SELECT l.full_address, l.sa2, b.*
FROM `proj.team.base_scored` b
JOIN `proj.team.address_lookup` l USING (gnaf_pid)
WHERE l.full_address IN (
  -- list your team's or consenting colleagues' addresses here, spelled exactly as in address_lookup
  '1 EXAMPLE ST, MELBOURNE VIC 3000'
);
```

Export it to `demo_properties.parquet` so the app works even if BigQuery is slow or unreachable.

### B. `requirements.txt`

```
streamlit
pandas
numpy
pyarrow
geopandas
pydeck
google-cloud-bigquery
db-dtypes
statsmodels
libpysal
esda
```

### B. `app.py` (map, scenario, validation chart, priority list and property lookup)

```python
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st

st.set_page_config(layout="wide", page_title="Hazard vs Vulnerability")

# ---------- data ----------
@st.cache_data
def load_areas():
    df = pd.read_parquet("area_summary.parquet")
    df["sa2"] = df["sa2"].astype(str).str.zfill(9)
    geo = gpd.read_file("sa2_simplified.geojson")                 # sa2, sa2_name, state, geometry
    geo["sa2"] = geo["sa2"].astype(str).str.zfill(9)
    return geo.merge(df, on="sa2", how="left")                    # left merge: no-data areas stay on the map

gdf = load_areas()
PERIL_ORDER = ["Negligible", "Low", "Moderate", "Medium", "High", "Severe", "Catastrophic"]

tab_map, tab_prop = st.tabs(["Area view", "Property lookup"])

# ---------- AREA VIEW ----------
with tab_map:
    st.sidebar.header("Area filters")
    states = st.sidebar.multiselect("State", sorted(gdf.state.dropna().unique()),
                                    default=list(gdf.state.dropna().unique()))
    shock = st.sidebar.slider("Premium shock (%, illustrative)", 0, 50, 0, 5)
    stress_cut = st.sidebar.slider("High-stress threshold", 10, 80, 30)
    hazard_cut = st.sidebar.slider("High-hazard share threshold", 0.05, 0.8, 0.30)

    d = gdf[gdf.state.isin(states)].copy()
    d["stress_adj"] = (d.mean_stress * (1 + (shock / 100) * d.share_high_hazard * 2)).clip(upper=99)
    has_data = d.mean_stress.notna()
    hz = d.share_high_hazard >= hazard_cut
    hs = d.stress_adj >= stress_cut
    d["quadrant"] = np.select(
        [~has_data, hz & hs, ~hz & hs, hz & ~hs],
        ["No data", "High hazard / High stress", "Low hazard / High stress", "High hazard / Low stress"],
        default="Low hazard / Low stress")

    colors = {
        "High hazard / High stress": [200, 30, 30, 170],
        "Low hazard / High stress":  [240, 150, 20, 170],   # hidden vulnerability
        "High hazard / Low stress":  [60, 120, 200, 170],
        "Low hazard / Low stress":   [170, 170, 170, 90],
        "No data":                   [235, 235, 235, 60],
    }
    d["fill"] = d.quadrant.map(colors)
    for c in ["stress_adj", "arrears_rate", "hardship_rate"]:
        d[c] = d[c].round(4)

    c1, c2, c3 = st.columns(3)
    c1.metric("Areas in view", f"{len(d):,}")
    c2.metric("High hazard + high stress", int((d.quadrant == "High hazard / High stress").sum()))
    c3.metric("Hidden vulnerability areas", int((d.quadrant == "Low hazard / High stress").sum()))

    layer = pdk.Layer("GeoJsonLayer", data=json.loads(d.to_json()),        # to_json turns NaN into null
                      get_fill_color="properties.fill",
                      get_line_color=[80, 80, 80], line_width_min_pixels=0.3, pickable=True)
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=-28, longitude=134, zoom=3.3),
        # if the tooltip shows blank text, use {properties.sa2_name} style field names instead
        tooltip={"text": "{sa2_name}\n{quadrant}\nStress: {stress_adj}\nArrears rate: {arrears_rate}"}))

    st.subheader("Observed distress by quadrant (bureau, area level)")
    v = d.dropna(subset=["n_accts"])
    g = (v.groupby("quadrant")
           .apply(lambda x: pd.Series({
               "arrears_rate":  (x.arrears_rate * x.n_accts).sum() / x.n_accts.sum(),
               "hardship_rate": (x.hardship_rate * x.n_accts).sum() / x.n_accts.sum()}))
           .reset_index())
    st.bar_chart(g.set_index("quadrant"))

    st.subheader("Priority areas: low hazard, high stress, highest arrears")
    top = v[v.quadrant == "Low hazard / High stress"].sort_values("arrears_rate", ascending=False)
    st.dataframe(top[["sa2_name", "state", "stress_adj", "arrears_rate", "hardship_rate", "n_accts"]].head(20))
    st.caption("Shock logic is an illustrative assumption, not a calibrated model. Grey areas have no published data.")

# ---------- PROPERTY LOOKUP (hazard and stress only; no bureau data) ----------
def bq_client():
    from google.cloud import bigquery
    return bigquery.Client()

@st.cache_data(ttl=3600)
def search_addresses(postcode: str, text: str):
    from google.cloud import bigquery
    q = """SELECT gnaf_pid, full_address FROM `proj.team.address_lookup`
           WHERE postcode = @pc AND full_address LIKE @txt LIMIT 10"""
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("pc", "STRING", postcode),
        bigquery.ScalarQueryParameter("txt", "STRING", f"%{text.upper()}%")])
    return bq_client().query(q, job_config=cfg).to_dataframe()

@st.cache_data(ttl=3600)
def get_property(pid: str):
    from google.cloud import bigquery
    q = """SELECT b.gnaf_pid, b.latitude, b.longitude, b.ins_stress, b.predicted_ins_stress, b.residual,
                  b.bf_score, b.cy_score, b.eq_score, b.fl_score, b.sc_score, b.n_high_plus, b.max_peril_r
           FROM `proj.team.base_scored` b WHERE b.gnaf_pid = @pid"""
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("pid", "STRING", pid)])
    return bq_client().query(q, job_config=cfg).to_dataframe().iloc[0]

def show_property(p):
    c1, c2, c3 = st.columns(3)
    c1.metric("Insurance stress", f"{p.ins_stress:.0f}")
    c2.metric("Perils at High or worse", int(p.n_high_plus))
    c3.metric("Stress beyond hazard", f"{p.residual:+.0f}")
    perils = {"Bushfire": p.bf_score, "Cyclone": p.cy_score, "Earthquake": p.eq_score,
              "Flood": p.fl_score, "Storm": p.sc_score}
    st.dataframe(pd.DataFrame({"Peril": list(perils.keys()), "Band": list(perils.values()),
                               "Level (1-7)": [PERIL_ORDER.index(b) + 1 if b in PERIL_ORDER else 0 for b in perils.values()]}
                              ).set_index("Peril"))
    st.map(pd.DataFrame({"lat": [p.latitude], "lon": [p.longitude]}))

with tab_prop:
    st.write("Hazard and stress for a single location. Bureau credit data is never shown at property level.")
    mode = st.radio("Mode", ["Demo addresses (fast, safe)", "Live search"], horizontal=True)
    if mode.startswith("Demo"):
        demo = pd.read_parquet("demo_properties.parquet")
        choice = st.selectbox("Choose an address", demo.full_address)
        show_property(demo[demo.full_address == choice].iloc[0])
    else:
        pc = st.text_input("Postcode", max_chars=4)
        txt = st.text_input("Street address (for example 12 Smith St)")
        if pc and txt:
            try:
                cands = search_addresses(pc, txt)
                if cands.empty:
                    st.warning("No match. Try a shorter street name.")
                else:
                    choice = st.selectbox("Select an address", cands.full_address)
                    pid = cands.loc[cands.full_address == choice, "gnaf_pid"].iloc[0]
                    show_property(get_property(pid))
            except Exception as e:
                st.error(f"Live lookup unavailable ({e}). Switch to demo addresses.")
```

Run it:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Optional borrower affordability panel (user-entered inputs only, no bureau data):

```python
with st.expander("Illustrative affordability check"):
    income = st.number_input("Annual household income ($)", 0, 1_000_000, 120_000, 5_000)
    repay = st.number_input("Monthly mortgage repayment ($)", 0, 20_000, 3_000, 100)
    prem  = st.number_input("Annual home insurance premium ($)", 0, 50_000, 2_500, 100)
    shock_p = st.slider("Premium increase (%)", 0, 100, 30)
    new_prem = prem * (1 + shock_p / 100)
    st.metric("Housing cost / income (before)", f"{(repay * 12 + prem) / max(income, 1):.1%}")
    st.metric("Housing cost / income (after)",  f"{(repay * 12 + new_prem) / max(income, 1):.1%}")
```

---

## M5: Freeze and final checks (Days 9-11)

### C and D. Reconciliation checks (run from scratch before the deck is final)

```sql
-- 1. Row counts reconcile across the chain
SELECT
  (SELECT COUNT(*) FROM `proj.src.hazard`)           AS src_rows,
  (SELECT COUNT(*) FROM `proj.team.base`)            AS base_rows,
  (SELECT COUNT(*) FROM `proj.team.base_scored`)     AS scored_rows,
  (SELECT COUNT(*) FROM `proj.team.malid_geo`)       AS geo_rows,
  (SELECT SUM(n_addr) FROM `proj.team.area_hazard`)  AS area_rows;

-- 2. Uniqueness of keys
SELECT COUNT(*) AS n, COUNT(DISTINCT malid) AS d_malid FROM `proj.team.base_scored`;
SELECT COUNT(*) AS n, COUNT(DISTINCT sa2)   AS d_sa2   FROM `proj.team.area_summary`;

-- 3. Suppression honoured: no published cell under the threshold
SELECT COUNT(*) AS cells_below_20 FROM `proj.team.area_outcomes` WHERE n_accts < 20;   -- must be 0

-- 4. Headline numbers for the deck (record the query ID next to each slide number)
SELECT
  COUNT(*) AS areas,
  SUM(n_addr) AS addresses,
  COUNTIF(quadrant = 'Low hazard / High stress') AS hidden_vulnerability_areas,
  SUM(IF(quadrant = 'Low hazard / High stress', n_accts, 0)) AS mortgage_accts_in_hidden_areas,
  SUM(IF(quadrant = 'Low hazard / High stress', n_accts, 0)) / SUM(n_accts) AS share_of_accts
FROM `proj.team.area_summary`;

-- 5. Peril signature table (multi-peril story, supporting slide)
SELECT bf_score, cy_score, eq_score, fl_score, sc_score, COUNT(*) AS n,
       AVG(ins_stress) AS avg_stress
FROM `proj.team.base`
WHERE n_high_plus >= 2
GROUP BY 1, 2, 3, 4, 5 ORDER BY n DESC LIMIT 20;
```

### B. Demo hardening checklist

```
[ ] app runs offline from local Parquet and GeoJSON (BigQuery only for live search)
[ ] sa2_simplified.geojson and area_summary.parquet copied to the presentation machine
[ ] "in data but not on map" SA2 count is a handful, not hundreds
[ ] demo_properties.parquet loaded and 10+ addresses pre-tested
[ ] all st.cache_data calls warmed by one full run before presenting
[ ] browser zoom and projector colours checked on the presentation machine
[ ] backup screen recording of the full 5-minute path saved locally
[ ] no bureau rows, account ids or credit file numbers anywhere in the app files
[ ] premium shock labelled illustrative in the UI and on the slide
```

### A. Limitations log (paste into the deck appendix)

```
1. ins_stress is partly built from the peril scores, so model fit is by construction; we present the residual as a decomposition.
2. Bureau outcomes are area-level and cover credit-active mortgage holders only (ecological fallacy and selection bias).
3. The address link reflects where the borrower lives, which may differ from the mortgaged property.
4. Band thresholds are provider-defined and not independently validated.
5. The premium shock is a simple illustrative assumption, not a calibrated pricing model.
6. Defaults cover all credit products, so they reflect broader financial distress.
7. Results should support early intervention and portfolio monitoring, not blanket exclusion.
```

---

## Run order cheat sheet

| Order | Script | Owner |
|---|---|---|
| 1 | Governance message | A |
| 2 | Address mapping checks | B |
| 3 | `team.base`, `base_sample`, quality checks | B |
| 4 | Diagnostics | D |
| 5 | Download and simplify boundaries; `mock_data.py` and app skeleton | B |
| 6 | `malid_geo` (lookup from `base`) | B |
| 7 | BQML model, `base_scored`, `area_hazard` | D |
| 8 | `cfn_malid`, `mortgage_month` | C |
| 9 | `area_outcomes`, `area_defaults` | C |
| 10 | `area_summary`, Gate G1 query | D |
| 11 | Export, wire app to real data | B |
| 12 | Scenarios, validation, hotspots, event study | D, C |
| 12b | Use-case builds: tier history, back-test, migration, queue, origination check | D, C, B |
| 13 | `address_lookup`, property lookup, demo fallback | B |
| 14 | Reconciliation checks, hardening, limitations log | All |
