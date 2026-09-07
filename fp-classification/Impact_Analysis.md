  
**IMPACT ANALYSIS**

**Score-Inflation Vulnerability and Naming-Pattern Concentration in Confirmed False Positive Matches**

# **1\. Executive Summary**

Two findings from the false positive root cause review generated leadership interest and are analysed in detail here:

* An absent-field scoring mechanic that can award enough “free” evidence points to clear the match threshold without genuine corroborating data, when DOB, driver licence, or middle name is missing from either side of a comparison.

* A concentration of confirmed errors among two specific naming conventions — Punjabi/Sikh names sharing a common suffix morpheme (e.g. \-deep, \-preet, \-jeet), and Vietnamese names with multiple shared tokens (e.g. Van, Thi, Anh) — which together account for approximately 70% of the corrections cohort reviewed to date.

These two findings are related, not independent: the absent-field mechanic is a plausible contributing MECHANISM that can let a naming-pattern collision clear the match threshold in the first place. Section 5 sets out the specific interaction analysis needed to confirm how much overlap exists.

The absent-field scoring value is a deliberate design choice, not a bug, and changing the underlying score itself would be a major overhaul of the matching logic — not a small patch. Section 6 sets out why that distinction matters for scoping a decision, along with several other factors (interim risk, a possible regulatory notification obligation, and the planned system migration) that bear directly on what leadership should decide now versus what can wait for fuller quantification.

**DATA NEEDED:** This document quantifies impact using the “bad cohort” (confirmed false positives) vs “good cohort” (confirmed correct matches) framework set out in §2, and a population baseline where relevant. Specific figures are not yet populated pending access described in §8 — the one confirmed figure available at time of writing is the \~70% corrections-cohort concentration already reported to leadership. Presenting precise-looking numbers without that access would overstate the current state of evidence; this draft is structured so the real figures can be inserted directly once available, without changing the analysis framework.

# **2\. How to Read This Analysis**

Two deliberate framing choices shape every number in this document, and are worth stating explicitly before the findings themselves, since both affect how confidently a figure can be acted on.

## **2.1 Bad cohort vs good cohort**

* “Bad cohort” \= confirmed false positives — cases the corrections team has actually confirmed as incorrect matches, from either consumer disputes or proactive audit sampling.

* “Good cohort” \= confirmed correct matches — cases actually confirmed as correct, overwhelmingly sourced from proactive audit sampling rather than disputes (nobody disputes a match that was actually right, so disputes alone cannot populate this cohort).

* A pattern's presence in the bad cohort only becomes meaningful once compared against its presence in the good cohort. A naming pattern that appears in 70% of errors but ALSO appears in 65% of correct matches is barely elevated; the same 70% against a 10% good-cohort rate is a serious signal.

## **2.2 Why a baseline population denominator is required**

Overrepresentation in the corrections cohort is only evidence of disparate impact relative to how common that group is in the population being matched overall. Without that baseline, a 70% figure cannot be read as “high” or “normal” — it is simply a proportion of a cohort whose expected composition is unknown. Obtaining this baseline is treated as a required input in §8, not an optional refinement.

## **2.3 Lift, not just prevalence**

Where possible, findings below are expressed as LIFT — the error rate for a specific condition divided by the baseline error rate for the whole population — rather than raw counts or shares alone. This is the same logic already built into the root cause analysis toolkit (root\_cause\_analysis.py) and is what distinguishes a genuine risk driver from a pattern that is simply common.

# **3\. Scenario 1: Absent-Field Score Inflation**

## **3.1 Problem definition**

The match engine's point mechanic awards a fixed neutral score (3 out of 9 points) whenever a field is Absent, rather than contributing zero information. This is defensible for a single field in isolation — it avoids unfairly penalising a record simply because a field was never captured. The vulnerability emerges in combination: when DOB, driver licence, AND/OR middle name are absent across several fields at once, the candidate can accumulate enough total score to clear the match threshold on scoring mechanics alone, without the corresponding genuine evidence a fully-populated comparison would require.

Concrete example: a candidate with Name \= Exact, DOB \= Absent, Driver Licence \= Absent, Address \= Near can clear the candidate threshold even though only one of four fields carries real corroborating evidence — the other two contributed “free” points, and the fourth contributed partial evidence.

**IMPORTANT CONTEXT:** The 3-point Absent-field baseline is a deliberate design choice, not an oversight or bug — it exists specifically to avoid unfairly penalising a record when a field was genuinely never captured. Changing that value directly would touch the core scoring formula the entire matching engine relies on, requiring full re-validation and threshold recalibration well beyond these two scenarios — in practice, a major overhaul of the matching logic, not a small patch. A narrower, ADDITIVE fix (e.g. a minimum-evidence gate layered on top of existing scoring, discussed in §6.1) does not require changing this value and could be materially faster to deliver — see §6 before scoping a remediation decision on this scenario.

## **3.2 Quantified impact**

Bad cohort vs good cohort, for the specific condition “two or more core fields Absent, with total score in the range that would not clear threshold without the Absent-field baseline”:

| Cohort / Metric | n | % of cohort | Notes |
| :---- | :---- | :---- | :---- |
| Bad cohort (confirmed FP) exhibiting this condition | ***DATA NEEDED*** | ***DATA NEEDED*** | ***DATA NEEDED*** |
| Good cohort (confirmed correct) exhibiting this condition | ***DATA NEEDED*** | ***DATA NEEDED*** | ***DATA NEEDED*** |
| Lift (bad cohort rate ÷ good cohort rate) | ***DATA NEEDED*** | — | — |
| Overall confirmed-FP rate (baseline, all causes) | ***DATA NEEDED*** | — | — |

This table is directly computable from root\_cause\_analysis.py's subgroup discovery output (the absent\_count / total\_score\_band interaction is already a first-class feature in that toolkit) once run against the full confirmed population — see §9.

## **3.3 Why this matters**

* Direct consumer harm mechanism: this is the specific pathway by which two genuinely different people can be merged with the LEAST genuine evidence, not the most — the opposite of what a reviewer would assume from a passing score.

* It is a structural, rule-level cause, not a data-quality or one-off error — meaning every future case meeting this condition carries the same elevated risk until the rule changes, regardless of how many past cases have already been remediated individually.

## **3.4 Recommended next steps**

* Quantify precisely using root\_cause\_analysis.py against the full confirmed population (bad and good cohorts) — ready to run once data access is confirmed.

* Evaluate a minimum-evidence floor: require at least N non-Absent core fields before a candidate is eligible for Auto-Merge, independent of total score.

* Evaluate differential Absent-field scoring by field — DOB/DL absence may warrant a lower baseline than a field that is absent for structural reasons (e.g. no driver licence exists for that demographic segment) rather than data-capture failure.

* Re-run threshold calibration (as already built in train\_entity\_match\_model.py's optimize\_thresholds) once the de-inflated feature set is validated against real confirmed volume.

# **4\. Scenario 2: Naming-Pattern Concentration**

## **4.1 Problem definition**

Two distinct naming-convention patterns were identified as disproportionately associated with confirmed matching errors:

* Punjabi/Sikh naming pattern: many distinct given names share a common suffix morpheme (-jeet/-jit, \-deep, \-preet, \-meet, \-neet, etc.). Generic string-similarity matching (Jaro-Winkler) scores two DIFFERENT names sharing only the suffix as highly similar, because most of the string is identical, even though the distinguishing root (e.g. ‘Har-’ vs ‘Man-’) is completely different.

* Vietnamese/Southeast Asian naming pattern: a large share of the population shares common given/middle-name tokens (Van, Thi, Anh, Minh, etc.) across a multi-part name structure. Two different people can share 2 of 3 name tokens purely because those tokens are extremely common, not because the names are actually the same.

Methodology validation (name\_match\_bias\_test.py, run against synthetic hard-negative test cases constructed specifically to isolate this mechanism): a naive Jaro-Winkler approach incorrectly scored different-person pairs as a strong match 72–100% of the time for these two patterns specifically. A frequency-weighted correction (down-weighting common suffixes/tokens, requiring closer-to-exact agreement on short high-information tokens) reduced this to 3–29% on the same test cases. These figures confirm the MECHANISM is real and a fix is technically viable — they are not production prevalence figures and should not be cited as such.

## **4.2 What we know so far**

**IMPORTANT CONTEXT:** The corrections cohort figure currently available is: these two naming-pattern groups together represent approximately 70% of the corrections cohort reviewed. Per §2.2, this cannot yet be interpreted as disparate impact without the population baseline share of these two groups. It is also explicitly noted that not all errors within this 70% are attributable to the name-matching vulnerability specifically — some fraction will trace to other root causes (see the Root Cause Taxonomy reference table, categories 2–6) despite the individual also having one of these naming patterns.

## **4.3 Quantified impact**

| Metric | n | % | Notes |
| :---- | :---- | :---- | :---- |
| Punjabi-pattern share of bad cohort (confirmed FP) | ***DATA NEEDED*** | ***DATA NEEDED*** | — |
| Vietnamese-pattern share of bad cohort (confirmed FP) | ***DATA NEEDED*** | ***DATA NEEDED*** | — |
| Combined share of bad cohort | ***DATA NEEDED*** | \~70% | Figure as reported to leadership |
| Combined share of good cohort (confirmed correct) | ***DATA NEEDED*** | ***DATA NEEDED*** | Needed for lift calc |
| Combined share of overall applicant/match population (baseline) | ***DATA NEEDED*** | ***DATA NEEDED*** | Needed for disparate-impact read |
| Lift: bad-cohort rate ÷ baseline population rate | ***DATA NEEDED*** | — | The number that actually answers “is this disproportionate” |
| Of the \~70%, share attributable to confirmed name-matching root cause specifically (vs other taxonomy categories) | ***DATA NEEDED*** | ***DATA NEEDED*** | Requires RCA classification (Phase 4\) to be far enough along |

## **4.4 Why this matters**

* If confirmed as disproportionate against the population baseline, this is a fair-treatment / anti-discrimination exposure in addition to the direct privacy-breach exposure common to all confirmed false positives — recommend specific legal/compliance review of this scenario given that added dimension, separate from the general RCA governance already in place.

* The mechanism (generic string similarity blind to population-level name-token frequency) is structural, not incidental — it would be expected to reproduce in any naming convention with similarly common shared components, not only the two identified so far.

## **4.5 Recommended next steps**

* Obtain the population baseline (Punjabi/Vietnamese-pattern share of overall applicant or match volume) — the single highest-priority missing input for interpreting this finding correctly.

* Complete root cause classification (per the RCA taxonomy) on the corrections cohort specifically for these two naming patterns, to separate name-matching-attributable cases from coincidental co-occurrence with other root causes.

* Progress the frequency-weighted / suffix-root-decomposition matching correction (validated in principle in name\_match\_bias\_test.py) toward a production-ready change, calibrated against real name-token frequency data rather than the illustrative synthetic corpus used for initial validation.

* Extend the same systematic method (real name-token frequency analysis) to check for analogous patterns in other naming conventions, rather than treating Punjabi and Vietnamese patterns as the complete list.

* Stratify the proactive audit sampling program specifically by naming pattern, to build a statistically defensible, unbiased estimate of the true error rate for these groups (current 70% is drawn from the dispute-biased corrections cohort, not a random sample — see the audit sampling methodology already established for this program).

# **5\. Cross-Cutting Interaction Between the Two Scenarios**

These two findings plausibly compound rather than operate independently. A naming-pattern collision (Scenario 2\) that would otherwise score too low to clear the match threshold could be pushed over that threshold specifically BECAUSE of Absent-field free points (Scenario 1\) on DOB, driver licence, or address — the exact “double-blind” combination already identified as a structural risk pattern in the entity matching feature work.

**RECOMMENDED NEXT STEP:** Compute what fraction of confirmed false positives exhibiting the Punjabi/Vietnamese naming pattern ALSO exhibit two or more Absent core fields. This is directly answerable via root\_cause\_analysis.py's association rule mining once note-derived naming-pattern flags (see prepare\_case\_notes.py / production\_name\_bias\_audit.py) are joined into the confirmed population. A high overlap would mean the two scenarios are substantially the SAME underlying problem viewed from two angles, with direct implications for remediation sequencing (fixing the interaction may resolve more of the 70% than fixing name-matching alone).

# **6\. Additional Considerations Before Deciding Next Steps**

The findings above answer “what is happening.” This section covers what leadership additionally needs to scope a decision on what to do about it — none of it changes the findings, but each point changes what a reasonable next step looks like.

## **6.1 Remediation is not a binary choice**

“Fix Scenario 1” covers options at very different cost and speed. Worth separating explicitly before scoping any decision:

* Tier A (additive, fastest): a minimum-evidence gate layered ON TOP of existing scoring — e.g. require at least N non-Absent core fields before Auto-Merge eligibility, regardless of total score. Does not change the Absent-field value itself, so does not require re-validating the existing scoring formula. Compensating manual-review routing for high-Absent-count or flagged-naming-pattern candidates falls in this tier too.

* Tier B (moderate): differential Absent-field scoring by field (e.g. DOB/DL absence scored differently from address absence), and production rollout of the frequency-weighted name-matching correction. Touches specific parts of the scoring logic but not the whole architecture.

* Tier C (major overhaul): redesigning the point-mechanic/scoring architecture itself, including changing the core Absent-field value. This is the only tier that requires full re-validation and threshold recalibration across the whole matching engine, not just these two scenarios — and is the tier your comment specifically flags.

These tiers are not mutually exclusive — Tier A is a reasonable near-term step regardless of what's later decided on Tier B/C.

## **6.2 Interim risk while a fix is pending**

Whichever tier is chosen, there will be a gap between now and delivery. Worth an explicit decision on whether a Tier A control (mandatory manual review for high-risk candidates) should be enabled immediately as a compensating control, independent of the timeline for any deeper fix.

## **6.3 Possible regulatory notification obligation — time-sensitive, separate from remediation timing**

**URGENT — TIME-SENSITIVE:** Confirmed, systemic incorrect disclosure of one consumer's credit information to another may meet the threshold for assessment under the Privacy Act's Notifiable Data Breaches scheme, which carries its own assessment and notification timeline once an organisation is aware of a likely eligible data breach. This is flagged here as a question for urgent legal/compliance assessment — not an assertion that the threshold is met — and should not wait for full quantification of §3–§4, since any notification clock would run independently of the remediation timeline.

## **6.4 The false-negative tradeoff**

Tightening Absent-field handling to reduce false positives can increase file fragmentation — the false negative harm this program also exists to prevent (responsible lending risk under ASIC obligations). Any proposed fix, at any tier, should be evaluated against its effect on both error types, not false positive reduction alone.

## **6.5 Known scope is very likely a floor, not a ceiling**

The two identified naming patterns were found by manual review, not by an exhaustive, systematic scan. The same mechanism (generic string similarity blind to population-level name-token frequency) would be expected to reproduce in other naming conventions not yet examined. Sizing a decision only against the currently known 70% risks under-scoping the eventual investment needed.

## **6.6 Interaction with the planned system migration**

Given the already-reduced investment in the current matching system ahead of its planned replacement, leadership needs to explicitly weigh whether Tier C investment is justified on a system being retired, or whether Tier A/B interim controls are the appropriate scope for its remaining lifespan — with the underlying architectural fix addressed once, in the migration, rather than built twice.

## **6.7 What is actually being asked of leadership right now**

Recommended framing for this decision point, rather than leaving it as an open-ended technical task list:

* Approve urgent legal/compliance assessment of the notification question in §6.3 — low cost, time-sensitive, should proceed immediately regardless of the rest of this list.

* Approve Tier A interim controls as immediate risk mitigation while quantification and Tier B/C scoping continue.

* Approve continued data-access work (§8) to complete the bad/good cohort quantification and obtain the population baseline.

* Defer a Tier B vs Tier C investment decision until quantification, the population baseline, and the migration timeline are all in hand — deciding this now would be premature on current evidence.

# **7\. Consolidated Recommended Next Steps**

Ordered by what unblocks the most other work, not strictly by scenario:

* 1\. Obtain the population baseline denominator (naming-pattern share of overall applicant/match volume) — required to correctly interpret Scenario 2 and avoid over- or under-stating a fair-treatment issue.

* 2\. Run root\_cause\_analysis.py and the bad/good cohort quantification in §3.2 and §4.3 against the full confirmed population, once data access is in place (see §8).

* 3\. Run the Scenario 1 × Scenario 2 interaction analysis (§5) to determine remediation sequencing.

* 4\. Route Scenario 2 for legal/compliance review given its fair-treatment dimension, in parallel with — not blocked by — the technical quantification work.

* 5\. Progress both technical fixes (minimum-evidence floor for Scenario 1; frequency-weighted matching for Scenario 2\) toward production readiness, calibrated against real data once available.

* 6\. Stratify ongoing audit sampling by both conditions (Absent-field pattern; naming pattern) to build unbiased prevalence estimates going forward rather than relying on dispute-biased cohort figures.

# **8\. Data Needed to Complete This Analysis**

* Full confirmed false positive population (dispute- and audit-sourced)

* Full confirmed correct-match population (predominantly audit-sourced) — needed to populate every “good cohort” row in this document; without it, only bad-cohort prevalence can be computed, not lift.

* Population baseline: share of overall applicant/match volume that is Punjabi-pattern and Vietnamese-pattern named, independent of match outcome.

* Root cause classification status/output for the corrections cohort (per the RCA taxonomy) — needed to state what share of the 70% is specifically attributable to the naming-pattern vulnerability.

* Confirmation of which fields (case description / outcome notes) are available and in what volume, to support the note-derived naming-pattern and Absent-field-interaction flags referenced in §5.