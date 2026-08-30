# 1. Executive Summary

Confirmed false positive matches — credit files that were incorrectly commingled or matched at enquiry time and file maintenance (merge or separate) time — represent both a direct consumer harm (privacy breach under Part IIIA of the Privacy Act 1988 and the CR Code) and a source of AFCA dispute and remediation cost. To date, root cause analysis of confirmed false positives has been conducted opportunistically: individual patterns are noticed during review and investigated in isolation, without a systematic view of how much of the total confirmed false positive population any single identified pattern actually explains.

This project establishes a systematic, exhaustive alternative: classify 100% of recorded confirmed false positive cases against a defined root-cause taxonomy, using a combination of structured statistical discovery methods and manual/qualitative review, so that remediation effort is prioritised by evidence of actual impact rather than by whichever pattern was most recently or most visibly discovered.

The output is not a fix in itself: it is a complete, evidenced map of why confirmed false positives occur, ranked by prevalence, together with concrete recommendations for the entity resolution rules, static reference data, and surrounding processes that would address each identified cause.

# 2. Problem Definition

Entity resolution at enquiry and file-maintenance time relies on a deterministic, rules-based point mechanic: fixed per-field scoring (Exact/Near/Different/Absent) summed against a static threshold. This architecture has three compounding, structural weaknesses that together explain why confirmed false positives continue to occur despite an established matching framework.

## 2.1 Outdated matching rules

The scoring thresholds and field-comparison logic reflect assumptions made at the time the system was designed and have not been systematically revisited against current match volumes, current population naming/demographic composition, or current confirmed-error evidence. Individual rules that were reasonable in isolation at design time have not been re-evaluated against how they behave in combination with other fields at scale, or against the population the system now matches against.

## 2.2 Infrequent maintenance of existing logic and static reference data

Components the matching engine depends on — common-name equivalence/mapping tables, phonetic or transliteration variant lists, jurisdictional format rules for identifiers such as driver licence numbers — are static reference data with no defined review cadence or ownership. As Australia's population composition and naming diversity shifts, static tables built at a point in time drift out of alignment with the population being matched, silently degrading match quality in ways that are only discovered reactively, through disputes, rather than proactively.

## 2.3 Inherent limitations of a deterministic algorithm

Independent of maintenance cadence, a deterministic point-mechanic has structural limitations a probabilistic or learned approach does not: it cannot natively account for how common or rare a given field value is in the population (treating a shared common name identically to a shared rare name); it cannot capture interaction effects between fields without those interactions being explicitly hand-coded as new rules; and it cannot adapt without a manual rule change and release cycle. Some fraction of confirmed false positives may therefore not be resolvable through rule tuning alone, and may instead require a fundamentally different, non-deterministic matching approach rather than further rule tuning.

## 2.4 Current state

100% of confirmed false positive cases are recorded (sourced from corrections-team investigation of consumer disputes, and increasingly from proactive audit sampling). However, only a small, non-representative subset of these cases has an identified, evidenced root cause. The remainder have not been systematically analysed, meaning the organisation cannot currently state with confidence what the dominant drivers of confirmed false positives actually are, or whether remediation effort to date has been directed at the highest-impact causes.

## 2.5 Context: Current System Status and Planned Migration

The current entity resolution system is a long-standing, deterministic build, and the organisation has an impending migration to a modern replacement matching system (the extent to which the replacement is probabilistic is not yet confirmed and should not be assumed). That context does not replace the causes described above and introduces two further dimensions this project needs to account for.

-   Reduced investment in the current system over recent years is better understood as a deliberate, arguably reasonable-at-the-time resourcing decision given the planned migration, rather than oversight.
    
-   The migration deadline creates a shrinking window for this analysis, not an open-ended one: institutional knowledge of why specific rules and thresholds exist and subject-matter expert availability are likely to erode faster as the current system approaches decommissioning.
    

# 3. Goals and Objectives

## 3.1 Primary goal

Primary goal: Identify and classify 100% of recorded confirmed false positive cases against a defined, evidenced root-cause taxonomy.

## 3.2 Supporting objectives

-   Define a mutually exclusive, collectively exhaustive (MECE) root-cause taxonomy covering algorithmic-logic failures (including static-data maintenance causes), human and operational overrides, data quality and input noise, data pipeline/ETL causes, identity fraud, and label/process noise. This category list is a starting point, not exhaustive, and will be finalised and expanded as needed during Phase 1 taxonomy validation.
    
-   Apply systematic statistical discovery methods (subgroup discovery, decision-tree surrogate analysis, association rule mining, stratified significance testing) across the full confirmed false positive population, not only cases matching pre-existing hypotheses.
    
-   Quantify, for every identified root cause, the proportion of the total confirmed false positive population it explains — producing a ranked, evidence-based Pareto view rather than an anecdotal one.
    
-   Translate each confirmed root cause into a concrete, actionable recommendation — for example a rule change, a static data maintenance process, a data pipeline fix, or a routing/process change — noting that the specific recommendation types will depend on what the analysis finds and are not limited to this list.
    
-   Establish an ongoing classification process so that newly confirmed false positive cases (from both disputes and the proactive audit sampling program) are classified as they arrive, rather than requiring another retrospective exercise.
    

# 4. Scope

## 4.1 In scope

-   The full population of confirmed false positive cases recorded to date (label_source = CONFIRMED_INVESTIGATION and CONFIRMED_AUDIT).
    
-   Root-cause taxonomy design and validation.
    
-   Systematic and manual root-cause classification of every case in scope.
    
-   Quantified coverage/Pareto reporting of root causes.
    
-   Remediation recommendations for entity resolution matching rules, static reference data maintenance, and related data/process gaps.
    

## 4.2 Out of scope

-   Implementation of remediation recommendations (tracked as a follow-on workstream once this initiative delivers its recommendations).
    
-   False negative / file fragmentation analysis (a related but distinct problem, tracked separately).
    
-   Expansion of the proactive audit sampling program's overall volume or cadence, which is governed as its own initiative; this project consumes its output as one of several confirmed-label sources.
    

# 5. Approach and Methodology

The approach is deliberately structured to avoid the failure mode of the current state: stopping analysis as soon as one plausible root cause is found. Six phases combine automated, systematic discovery with targeted qualitative review, and close with a specific reconciliation step to confirm 100% coverage.

### Phase 1 — Taxonomy and framework definition

Define the MECE root-cause taxonomy (including a mandatory “unclassified” category) and the tagging schema each confirmed case will be scored against. Validate the taxonomy with corrections-team, data engineering, and compliance stakeholders.

### Phase 2 — Case data preparation

Consolidate the full confirmed false positive population into a single analysis-ready dataset. Where corrections-team investigation notes exist, prepare them for text mining; where a structured taxonomy tag does not already exist, establish a manual coding sample.

### Phase 3 — Systematic discovery

Apply the automated statistical discovery toolkit — subgroup discovery, decision-tree surrogate analysis, association rule mining, and stratified error-rate analysis with multiple-testing correction — across the full confirmed population to algorithmically surface candidate root-cause segments, including ones not previously hypothesised. This is a deliberately scoped subset of the available root-cause methods, not the exhaustive set: it covers structured/categorical features only. Case-note text mining (prepared in Phase 2) and any other qualitative or unstructured-data methods are executed as a distinct, complementary strand within Phases 3–4, since some root causes (e.g. fraud indicators, investigator commentary) may not be captured in structured fields at all.

### Phase 4 — Confirmation and classification

Each candidate segment from Phase 3 is reviewed against a sample of underlying cases to confirm the statistical pattern reflects a genuine causal mechanism, not a spurious correlation. Confirmed patterns are used to classify the matching population of cases; a targeted manual review pass addresses cases not resolved by any confirmed pattern.

### Phase 5 — Coverage reconciliation

Measure classified coverage against the 100% target. Where a material unclassified residual remains, iterate Phases 3–4 with refined features or additional qualitative input (e.g. deeper case-note mining) until the residual is reduced to a documented, justified minimum.

### Phase 6 — Recommendations and handoff

Translate each confirmed, quantified root cause into a specific recommendation — for example a rule change, static data maintenance process, pipeline fix, or process/routing change (illustrative, not exhaustive) — prioritised by the Pareto coverage each cause represents, and hand off to the appropriate owning team for implementation.

## 5.7 Audit Sampling Methodology

Confirmed false positive cases sourced purely from consumer disputes are inherently biased: a consumer only disputes a match that was actually wrong, so the confirmed population is not representative of the much larger unconfirmed population (matches that were never disputed). The true root-cause mix in that unconfirmed population could differ materially from what dispute-driven cases alone would suggest. A proactive audit sampling program addresses this directly by generating unbiased confirmed labels from the unconfirmed population, and its output is a first-class input to this project, not a footnote.

-   Candidate pool: cases drawn from the unconfirmed population — matches that were never disputed and have not already been audited.
    
-   Stratified by operational risk tier: audit review effort is allocated across the tiers a match can be routed to, weighted toward the tier where an undetected error would be most consequential (the tier that bypasses human review entirely), with a smaller share directed to tiers that already receive some form of human review.
    
-   Two sampling modes, used for different purposes: uniform random sampling draws candidates at random within a tier and produces an unbiased estimate of that tier's true error rate — this is the mode this project relies on for defensible root-cause prevalence figures. Risk-weighted sampling instead concentrates review effort near the boundary between tiers, where a wrong decision is most likely and most consequential; this is useful for finding additional errors but is not representative, and its output cannot be used to estimate prevalence.
    
-   Deduplication: a running audit log records every case ever sampled, so the same case is never selected for review twice across successive audit rounds.
    
-   Outcome and labelling: each audited case reviewed by the corrections team is confirmed as either a genuine match or a false positive, and is recorded against a label source that identifies it as coming from proactive audit rather than a consumer dispute. This distinction lets this project's classification and coverage reporting separate dispute-biased evidence from unbiased evidence explicitly, rather than treating all confirmed cases as equivalent.
    
-   Feeding into this project: audit-confirmed false positives are added to the classification population on the same basis as dispute-confirmed cases (Phase 2). Audit-confirmed genuine matches are equally valuable, since they are close to the only source of confirmed-correct evidence in operationally sensitive segments, which dispute-driven data essentially never provides.
    
-   Current maturity: this program is still building volume. Where audit-sourced evidence for a given segment is currently too sparse to be statistically meaningful, that limitation is carried into this project's coverage reporting (Phase 5) rather than treated as resolved.
    

# 6. Indicative Timeline (Draft — Pending Discussion)

The durations below are draft placeholders only. They have not yet been discussed or sized with the delivery team and must be reviewed and agreed before this plan is finalised; they assume dedicated analyst time and should be calendared against actual resourcing and confirmed-case volume once Phase 1 is complete. Phases 3–5 are expected to iterate rather than run strictly sequentially.

Phase
Key activities
Duration (TBC)

1. Taxonomy & framework

Define taxonomy; stakeholder validation

TBC — draft: 2 weeks

2. Case data preparation

Consolidate confirmed FP population; prepare case notes; manual coding sample

TBC — draft: 2–3 weeks

3. Systematic discovery

Run subgroup discovery, decision tree, association rules, stratified analysis

TBC — draft: 2 weeks

4. Confirmation & classification

Validate candidate patterns; classify full population; manual review of residual

TBC — draft: 3–4 weeks

5. Coverage reconciliation

Measure coverage; iterate on unclassified residual

TBC — draft: 1–2 weeks (iterative)

6. Recommendations & handoff

Draft and present remediation recommendations; handoff to owning teams

TBC — draft: 2 weeks

  

# 7. Expected Outcomes and Deliverables

-   A validated, documented root-cause taxonomy for confirmed false positive matches.
    
-   100% of recorded confirmed false positive cases classified against that taxonomy, including a quantified and justified “unclassified” residual (target: minimised, not necessarily zero).
    
-   A ranked, evidence-based root-cause coverage report (“what fraction of confirmed false positives does each cause explain”).
    
-   A remediation recommendation report covering matching rule changes, static reference data maintenance ownership and cadence, data pipeline fixes, and process/routing changes.
    
-   An updated feature engineering and rules backlog for the entity resolution system, prioritised by the Pareto coverage evidence.
    
-   An operationalised classification process so future confirmed cases are tagged on an ongoing basis rather than requiring another retrospective project.
    

# 8. Key Risks

Risk

Likelihood

Impact

Mitigation

Corrections-team investigation notes are unstructured or insufficiently detailed to support text-mining-based root cause attribution.

Medium

High

Establish a structured manual coding sample early (Phase 2) as a fallback; use it to train a scalable classifier rather than depending on notes alone.

A material fraction of confirmed cases remains genuinely unclassifiable (e.g. ambiguous investigation outcomes, cases with multiple plausible causes).

High

Medium

Treat “unclassified” as a legitimate, reportable outcome with a defined justification standard, rather than forcing every case into a category; report residual size transparently rather than overstating coverage.

Statistical false discovery from testing many segments/dimensions produces spurious “root causes” that do not hold up on closer review.

Medium

Medium

Multiple-testing correction is applied to all stratified tests; every candidate pattern is confirmed against a manual case sample before being accepted as a classification category (Phase 4).

Corrections-team capacity constraints limit availability for manual coding and confirmation review.

Medium

Medium

Scope the manual coding sample to the minimum size needed to train a scalable classifier; sequence confirmation reviews to align with existing case review workload where possible.

Root causes identified implicate static reference data (e.g. name equivalence tables) with no current owner or maintenance process, stalling remediation after the cause is known.

High

Medium

Explicitly recommend ownership and a review cadence for each affected static data asset as part of the Phase 6 deliverable, not only the technical fix.

Some confirmed causes are structurally unresolvable by rule changes alone, given the deterministic algorithm's inherent limitations.

Medium

Medium

Recommendations explicitly flag cause categories that require an architectural change, rather than forcing a rules-only fix and understating the true remediation cost.

Handling of case-level data (names, identifiers) during analysis creates privacy or access-control exposure.

Low

High

Analysis is conducted on de-identified/pseudonymised extracts consistent with existing Data Analysis sub-group handling standards; access scoped to the project team.

Institutional knowledge, SME availability, and raw case-level data needed for root cause analysis erode as the legacy system approaches decommissioning under the planned migration to a modern probabilistic system.

High

High

Prioritise and timebox knowledge and data capture early (Phases 2–3); interview retained SMEs before reassignment; ensure raw case-level data and logs are archived ahead of any legacy system decommissioning step.

Reduced organisational incentive to fully fund root cause analysis on a system already regarded as being replaced.

Medium

High

Secure explicit executive sponsorship framing this project's output as failure-mode evidence for the new system's training data, not only remediation of the outgoing system; report progress against the 100% classification target regularly to sustain visibility and support.

  

# 9. Constraints and Limitations

-   No confirmed outcome label exists for the large majority of historical matches (the undisputed, unaudited population). Root cause classification in this project is therefore necessarily scoped to the confirmed subset; it cannot directly measure root causes within cases that were never disputed or audited.
    
-   Confirmed cases sourced from disputes carry an inherent selection bias toward cases a consumer noticed and chose to report; the proactive audit sampling program partially addresses this but has its own, separate volume constraints.
    
-   Statistical confidence for low-volume segments (e.g. specific states, specific naming conventions, specific match types) will be inherently limited by case counts, independent of methodology quality.
    
-   The deterministic, rules-based architecture of the current entity resolution engine constrains what a “matching rule fix” can achieve; some identified root causes may only be fully addressed by a broader system or architectural change, which sits outside this project's direct delivery scope.
    
-   Static reference data maintenance ownership is not currently defined; this project can recommend ownership and cadence but cannot itself establish new operational ownership without sponsorship from the accountable business area.
    
-   Data pipeline or ETL defects identified during root cause analysis may require Data Engineering resourcing that sits outside this project's direct control and will need to be raised and prioritised through existing engineering channels.
    

# 10. Success Metrics

Metric

Target

Confirmed false positive cases classified against the root-cause taxonomy

100% (with a documented, justified unclassified residual where applicable)

Proportion of total confirmed false positives explained by the top 5 identified root causes

Reported and tracked; used to prioritise remediation, not a fixed target

Root-cause candidate patterns confirmed against manual case review before acceptance

100% of patterns used for classification

Remediation recommendations delivered with an identified owning team

100% of confirmed, in-scope root causes

Ongoing classification of newly confirmed cases

Operational process in place at project close, not a one-off exercise

  

# 11. Regulatory Context

This initiative directly supports the organisation's obligations under Part IIIA of the Privacy Act 1988 and the Credit Reporting Code, both of which treat incorrect commingling of consumer credit files as a reportable privacy matter. A complete, evidenced understanding of why confirmed false positives occur strengthens the organisation's position with AFCA on systemic-issue reporting and with OAIC on demonstrating active, evidence-led remediation of a known risk, rather than reactive, case-by-case correction.
