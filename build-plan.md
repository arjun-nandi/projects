# Hackathon Plan: Hazard vs Vulnerability

## 1. Summary

**Concept:** Physical hazard alone misses where borrowers are actually fragile. We combine three layers:

1. **Hazard**: five banded peril scores (bushfire, cyclone, earthquake, flood, storm)
2. **Modelled vulnerability**: `ins_stress` and its residual after removing the effect of hazard
3. **Observed distress**: RHI arrears, FHA hardship and defaults, aggregated at area level

The 2x2 of hazard against vulnerability is then validated against real bureau outcomes.

**Headline claim to prove:** "Hazard-only views miss X% of distressed mortgage areas. Hazard plus vulnerability finds them earlier."

**Why it works**
- 16.29M address-level rows already in BigQuery
- `malid` links bureau addresses straight to the hazard table (no geocoding)
- The bureau sees both sides (lender and insurer) of the risk

**Users**
- **Banks:** portfolio monitoring, proactive hardship outreach, stress testing, climate-adjusted affordability
- **Insurers:** affordability and lapse risk, underinsurance, accumulation, post-event customer care

**Demo:** national quadrant map, premium-shock slider, observed-distress chart, priority list, and a property lookup (hazard and stress only).

**Use cases (one tier engine, four views):** origination affordability check, portfolio monitoring, hardship and collections queue, and disaster response. The tier and its back-test are the must-haves; see section 4b for scope.

## 2. Key data facts

| Item | Detail |
|---|---|
| Rows | 16.29M, one per location id (`malid`) |
| Peril bands (ordinal) | Negligible < Low < Moderate < Medium < High < Severe < Catastrophic (confirm Moderate vs Medium order with provider) |
| `ins_stress` | Continuous, 0-99, median 17, p90 67 (right-skewed; use quantile tiers) |
| Bureau link | Account (RHI/FHA by month) to credit file number to address (`malid`) to hazard table |
| Platform | BigQuery |

## 3. Team streams

| Stream | Owner | Scope |
|---|---|---|
| **A. Lead and story** | PM | Governance, scope, data dictionary, narrative, deck, rehearsals |
| **B. Platform and app** | Engineer | Base tables, spatial joins, `area_summary`, Streamlit app, G-NAF lookup |
| **C. Bureau and geospatial** | Analyst 1 | Credit-file-to-address mapping, RHI/FHA/default aggregates, hotspot stats, event study |
| **D. Hazard and modelling** | Analyst 2 | Hazard and stress EDA, residual model, quadrants, scenario logic, validation stats |

**Rules for parallel work**
- **Day 1 contract:** agree the `area_summary` schema, table names, the shared `team` dataset and a shared repo. The engineer builds the app against a mock Parquet file from Day 2.
- **Critical path:** governance sign-off, then bureau access, then `area_outcomes`, then validation. Start the governance ask first thing on Day 1.
- **Daily rhythm:** 15-minute stand-up; each person shows something working at day's end.

## 4. Milestones

### M0: Kickoff and foundations (Days 1-2)

- **A:** Governance request (permitted use, environment, output controls, small-cell threshold). Confirm band order with the data provider. Write the one-sentence claim and judging scorecard. Publish the schema contract.
- **B:** Create `team` dataset and repo. Build `base` (band ranks, `max_peril_r`, `n_high_plus`), a 1% dev sample and a Parquet copy. Check for NULL ranks from unexpected labels.
- **C:** Get read access to account, RHI, FHA, default and address tables. Document schema, RHI scale and joint-account structure. Profile credit-file-to-address coverage.
- **D:** Run diagnostics: row and distinct counts, nulls, per-peril and stress distributions (p75/p95/p99), stress quantiles per band, Spearman correlations.
- **Exit:** governance answer received (or escalated), `base` built, schema contract signed off, diagnostics shared.

### M1: Data foundations (Days 2-4)

- **B:** Download and simplify the ABS 2021 SA2 boundaries (map only). Build `malid_geo` as a small lookup from `base`. Build `area_hazard`. Start the Streamlit skeleton on mock data.
- **C:** Build `cfn_malid` (one address per credit file) and `mortgage_month` (primary holder, mortgages only, 24 months). Run coverage checks (match rate, row-count invariance).
- **D:** Train the BQML residual model on a 10% sample; compare with band dummies. Materialise `base_scored`. Draft quadrant cut-offs from the distributions.
- **A:** Chase governance. Draft deck skeleton. Line up public data (SEIFA, Census, disaster declarations by LGA).
- **Exit:** `malid_geo`, `cfn_malid`, `mortgage_month`, `base_scored` exist and pass sanity checks.

### M2: Core analysis and Gate G1 (Days 4-6)

- **C:** Build `area_outcomes` (arrears 1+/30+/90+, hardship, with small-cell suppression) and the defaults table.
- **D:** Finalise quadrants. Build `area_summary` v1 and export it.
- **B:** Wire real `area_summary` into the app. Add quadrant map, tooltips and state filter.
- **A:** Review early results and run the gate.
- **Gate G1 (end of Day 5 or 6):** does the residual or quadrant relate to observed arrears and hardship?
  - **Yes:** continue.
  - **Weak or no:** pivot the lead to tail risk and blind spots; keep the 2x2 as supporting.
- **Exit:** clear lead story and a working map on real data.

### M3: Validation and scenarios (Days 6-8)

- **D:** Regress observed distress on hazard, stress and residual with controls (state, SEIFA). Quadrant outcome table with confidence intervals. Premium-shock scenario logic, precomputed for 3 shock levels.
- **C:** Hotspot stats (Gi* or local Moran's I) on SA2 residuals in Python. Optional event study (affected vs comparison areas, FHA and arrears before and after one known event).
- **B:** Add shock slider, observed-distress chart and priority list to the app. Build `address_lookup` from the address mapping table.
- **D (use cases):** build `tier_history`, run the 12-month back-test and the tier migration matrix (section 4b)
- **B (use cases):** add the hardship queue view and the origination serviceability panel, both on synthetic or consenting rows
- **A:** Pull out headline numbers; draft story slides and the bank and insurer use-case slides.
- **Exit:** every number on a slide traces to a table and query; scenario runs end to end.

### M4: App complete and property lookup (Days 7-9)

- **B:** Property lookup (postcode plus street search, live clustered query on `gnaf_pid`, peril bars, percentile, quadrant, residual). Build a 10-20 address demo dropdown as fallback. Test performance.
- **D:** Add national percentile quantiles. Spot-check property-level outputs on 20 addresses.
- **C:** Precompute SA2 context panel metrics (arrears and hardship comparison, small-cell suppressed).
- **A:** Governance review of what the app shows; confirm no bureau data at property level.
- **Exit:** full demo path runs on the presentation machine.

### M5: Freeze and story (Days 9-11)

- **Day 9, feature freeze:** no new features after this.
- **A:** Build the deck (problem, approach, three layers, findings, demo, bank and insurer value, limitations, next steps). Write the demo script with timings.
- **B:** Harden the app (caching, error handling, fixed demo state, packaging). Record a backup demo video.
- **C and D:** Final number validation (re-run headline queries from scratch), assumptions and limitations log, one-page methods appendix.
- **Exit:** deck v1, demo script, reconciled final numbers.

### M6: Rehearsal and buffer (Days 12-14)

- **Day 12:** full timed run, then a dry run in front of someone outside the team (ideally credit risk or product).
- **Day 13:** fix issues, tighten narrative, prepare Q&A (10 hardest likely questions with answers).
- **Day 14:** buffer, equipment check, final run on the presentation machine.

## 4b. Use-case tracks (origination, monitoring, hardship and collections)

All three use cases read from one shared engine: a monthly **tier snapshot** at customer level (`team.tier_history`). Build it once, then each use case is a view on it. Four people cannot build three full products in two weeks, so the scope is set explicitly below.

**Shared tier (starting rules; tune at Gate G1)**

| Element | Rule |
|---|---|
| Exposed | Any high-or-worse peril (`n_high_plus >= 1`), or stress after shock at or above 30 |
| Strain (0 to 4 flags) | 30+ days late in last 3 months; hardship in last 12 months; default in last 12 months; judgment in last 12 months |
| Priority | Exposed and strain 2 or more |
| Act | Exposed and strain 1, or not exposed and strain 2 or more |
| Watch | Exposed and strain 0, or not exposed and strain 1 |
| Low | Not exposed and strain 0 |

Each tier row stores its drivers as plain text, the snapshot date and the shock used.

**Scope for the two weeks**

| Use case | Must have (demo) | Should have | Narrate only |
|---|---|---|---|
| Shared tier and back-test | Monthly snapshot; 12-month back-test; capture share by tier | Repeat on a second snapshot date | Quarterly recalibration pipeline |
| Portfolio monitoring | Tier migration matrix; area watchlist; shock counts | Alert rules; drivers on the watchlist | Live alerts |
| Hardship and collections | Capped queue split into early care and collections, on synthetic rows | Driver text per case | Agent script library |
| Origination | Serviceability calculator with user-entered inputs | Address lookup returns the tier | Live API into the decision engine |

**Rule:** if the back-test is not finished by Day 9, present every use case as designed but unproven, and say so on the slide.

**Tasks by use case**

*Portfolio monitoring*
- **Do:** store each monthly snapshot (D); build the migration matrix (D); build the area watchlist with dominant peril (B); count tier shifts under 10, 20 and 30 percent shocks (D)
- **Check:** one row per customer per snapshot; tier counts sum to the customer total; migration row totals equal the prior month's tier counts; Priority share moves only a few points month to month unless there is a known event
- **Test:** customers who migrate up show more hardship and arrears afterwards than those who stay put or move down; the monthly repayment lag is stated on the slide

*Hardship and collections*
- **Do:** build the capped queue (C, D); split early care from collections using `rhi_t0` (D); attach drivers (D); show the queue on synthetic rows in the app (B)
- **Check:** queue never exceeds capacity; no customer appears twice; every queued customer has at least one driver; early care and collections do not overlap
- **Test:** Priority and Act customers show higher later hardship than Watch; contact rates by area stay within a reasonable band (fairness); queue position is not driven by loan size, which the tier does not use

*Origination*
- **Do:** build the serviceability calculator (B); build the address-to-tier lookup from `base_scored` (B); draft assessor wording (A); draft policy thresholds for each tier (A)
- **Check:** calculator matches a hand calculation on three worked examples; a zero shock leaves the margin unchanged; a higher shock never raises the margin
- **Test:** the exposure-only tier and the full tier put similar shares of loans in the top tier (if so, hazard drives the result, which is fine, but say so); count how many illustrative applications change action at a 30 percent shock

*Back-test (shared; owned by D with C)*
- **Do:** take a snapshot at least 12 months before the latest data; measure new hardship and new 30+ arrears in the following 12 months; report results and capture share by tier
- **Check:** every feature month is on or before the snapshot date; the outcome window starts after it; tier counts reconcile to the snapshot; Priority hardship rate is above Low
- **Test:** the result holds on a second snapshot date; a strain-only ranking is compared, so exposure must add something, or we say it does not

**Constraint:** `mortgage_month` holds 24 months, so only one or two valid snapshots exist. State this on the slide and treat the back-test as first evidence, not full validation.

## 5. Data build order

1. `base` (ranks, `max_peril_r`, `n_high_plus`)
2. `malid_geo` (malid to SA2)
3. `cfn_malid` (one address per credit file)
4. `mortgage_month` (primary holder, mortgages only)
5. `area_outcomes` and `area_hazard`
6. `base_scored` (BQML predictions and residuals)
7. `area_summary` (one row per SA2, exported to Parquet)
8. `address_lookup` (from the address mapping)
9. `tier_history`, back-test, migration matrix, hardship queue (section 4b)

**`area_summary` columns:** `sa2, sa2_name, state, n_addr, mean_stress, p90_stress, share_high_hazard, mean_residual, n_accts, arrears_rate, hardship_rate, quadrant`

## 6. Dependencies and mitigations

| Dependency | Risk | Mitigation |
|---|---|---|
| Governance for bureau data | Blocks stream C and validation | Ask on Day 1. Fallback: hazard-only story with SEIFA and Census as the vulnerability proxy |
| Address join into `base` | Duplicate rows if `address_map` has more than one row per `malid` | Run the mapping checks before building `base` |
| Bureau join quality | Silent double counting | Row-count invariance and coverage checks before analysis |
| `area_summary` schema changes | App rework | Freeze schema after Day 2; add columns only |
| Address mapping coverage | Property lookup gaps | Check coverage on the hazard table; keep the dropdown fallback |
| Judgments data access | Back-test and strain flag incomplete | Confirm early with the bureau data owner; if unavailable, drop judgments from strain and say so |
| Row-level use-case views | Governance blocks the queue and origination demo | Demo with synthetic or consenting rows only; production use needs model risk and compliance sign-off |

## 7. Cut list if behind (drop in this order)

1. Event study
2. Gi* hotspot statistics (use simple maps)
3. Live property lookup (use precomputed demo-address dropdown)
4. Live shock slider (use three precomputed scenarios)
5. Streamlit app (fall back to Looker Studio on `area_summary`)

**Never cut:** quadrant map, validation against observed distress, limitations slide, backup video, and the tier back-test.

For the use cases, cut the origination panel first, then the hardship queue. Keep the tier and its back-test, since every use case depends on them.

## 8. Guardrails

- Bureau data stays in the approved environment and only appears as area-level, small-cell-suppressed aggregates. Never at property or account level.
- Property lookup shows hazard and stress only; bureau outcomes appear only at SA2 level.
- Limit browsing and enumeration of addresses; use team or consenting colleagues' addresses for the demo.
- Row-level outputs (hardship queue, origination check) use synthetic or consenting records only during the hackathon. Real account-level use needs model risk and compliance approval.
- State limits plainly: circularity in `ins_stress`, area-level (not individual) inference, residence is not the security property, shock assumptions are illustrative, band thresholds are provider-defined.
- Position outputs as support and early intervention, not blanket exclusion (fairness and proxy-for-disadvantage risk).

## 9. Demo script (5 minutes)

1. National quadrant map
2. Click an area (hazard, stress, observed arrears)
3. Move the premium shock slider
4. Observed distress by quadrant (the validation)
5. Priority list
6. Property lookup with a demo address
7. Close on the bank and insurer value

## 10. Definition of done (per deliverable)

- Named owner
- Table or file in the shared location
- Reproducible query or script in the repo
- Second person has reviewed the numbers
