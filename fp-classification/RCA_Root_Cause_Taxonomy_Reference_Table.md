**ROOT-CAUSE TAXONOMY REFERENCE TABLE**

Confirmed False Positive Root Cause Classification Initiative — Phase 1 working reference

**Status: DRAFT — illustrative starting point for Phase 1 taxonomy validation, not final**

This table is the working reference for classifying confirmed false positive cases against the MECE root-cause taxonomy defined in the project plan (§3.2). Each confirmed case should be tagged with one PRIMARY category and sub-ID; a secondary tag may be added where causation is genuinely mixed (see Category 6.3), but the primary tag is what drives coverage/Pareto reporting, so it should reflect the single best-supported cause. Use Category 7 (Unclassified) rather than forcing a low-confidence case into the nearest plausible category — an honest unclassified residual is more useful than an inflated classification rate.

## **How to use this table**

* Tag each confirmed case with the most specific applicable sub-ID (e.g. 1.2, not just 1).

* Use the “Primary detection method” column to route cases to the right analysis strand: categories 1, 3, and 4 are largely findable through the structured statistical toolkit (subgroup discovery, decision-tree surrogate, stratified analysis); categories 2, 5, and 6 depend much more on case-note quality and manual review capacity.

* This category and sub-category list is a starting point, not final — it is expected to be revised, merged, or expanded during Phase 1 stakeholder validation as real case volume is reviewed against it.

* Categories are not weighted or pre-ranked by expected prevalence — that ranking is precisely what the systematic discovery and coverage reporting phases are designed to produce, not something to assume up front.

| Category | Sub-ID | Sub-category | Description | Example | Primary detection method | Typical evidence source |
| :---- | ----- | :---- | :---- | :---- | :---- | :---- |
| **1\. Algorithmic-LogicFailures** | **1.1** | **Score inflation / deterministic rule blind spots** | Threshold cleared via structurally weak evidence (e.g. Absent-field baseline scoring) rather than genuine matching signal. | Two records clear the merge threshold mainly because several fields are Absent, not because the present fields strongly agree. | Subgroup discovery; decision-tree surrogate | Structured match-log features |
|  | **1.2** | **Static reference data drift** | A name-equivalence, suffix-mapping, or format-validation table no longer reflects the current population being matched. | A common-suffix collision (e.g. shared morpheme across genuinely different names) scored as a strong match. | Stratified analysis by naming pattern; targeted feature audit | Structured features \+ manual case review |
|  | **1.3** | **Threshold miscalibration** | A global score cutoff has not been re-validated against current match volume or population composition. | Cutoff set years ago never revisited despite population/demographic shift. | Stratified analysis; decision-tree surrogate | Structured match-log features |
|  | **1.4** | **Field-interaction blind spots** | Rules cannot discount two fields' combined evidence appropriately when their co-occurrence is itself the confound. | Shared address treated as corroborating rather than confounding in a generational-household (Jr/Sr) case. | Subgroup discovery; association rule mining | Structured match-log features |
| **2\. Human andOperational Overrides** | **2.1** | **Manual review misjudgement** | A reviewer approves an incorrect merge despite available disambiguating information. | Reviewer overlooks a DOB conflict because the name and address both matched. | Stratification by reviewer/queue; manual coding | Case notes; review-queue logs |
|  | **2.2** | **Override / exception misuse** | A manual bypass of a Hard-Block or review-queue outcome. | An exception process used to force a merge the system had flagged for review. | Stratification by override flag; manual coding | Case notes; override/exception logs |
|  | **2.3** | **Reviewer inconsistency** | Variance in how different reviewers or teams apply the same rules, not attributable to the algorithm. | Two reviewers reach different outcomes on structurally similar cases. | Stratification by reviewer/team; manual coding | Case notes; review-queue logs |
| **3\. Data Quality andInput Noise** | **3.1** | **Source data entry errors** | Transcription, OCR, or formatting errors introduced at the point of capture. | A digit transposition in a driver licence number causes a false conflict. | Stratified analysis by intake channel | Source system audit; case notes |
|  | **3.2** | **Incomplete source fields at enquiry time** | An upstream data capture gap, not a matching-engine defect. | Address not captured at enquiry, forcing reliance on weaker fields. | Stratified analysis by record/enquiry type | Source system audit |
|  | **3.3** | **Conflicting updates across channels** | The same individual's file updated inconsistently across different intake channels. | A phone-channel update and an online-channel update leave the file internally inconsistent. | Stratified analysis by channel; data lineage review | Source system audit |
| **4\. Data Pipeline /ETL Causes** | **4.1** | **Join / key mapping defects** | Incorrect entity linkage introduced during extract, transform, or load. | A batch job join error attaches one entity's field to another's record. | Stratified analysis by batch/date | Pipeline logs; data engineering review |
|  | **4.2** | **Batch processing anomalies** | Errors concentrated in specific ingestion windows rather than spread evenly. | A spike in confirmed FPs traced to a specific nightly batch run. | Stratified analysis by batch/date | Pipeline logs |
|  | **4.3** | **Schema drift / silent field mis-mapping** | An upstream system or schema change not reflected downstream. | A source field renamed upstream silently maps to the wrong target field. | Stratified analysis by source system/version | Pipeline logs; data engineering review |
| **5\. Identity Fraud** | **5.1** | **Stolen / synthetic identity applications** | Fraudulent use of a genuine identity's core attributes. | Name, DOB, and driver licence all exact, but address absent or inconsistent — a stolen-identity signature. | Case-note mining; manual review | Case notes; fraud/velocity signals if available |
|  | **5.2** | **Application velocity / fraud-ring patterns** | Multiple enquiries sharing attributes in ways indicative of coordinated fraud. | Several enquiries in a short window sharing an address or contact channel. | Case-note mining; stratified analysis by timing | Case notes; fraud/velocity signals if available |
| **6\. Label / ProcessNoise** | **6.1** | **Investigator error** | The corrections-team finding itself is incorrect. | A confirmed-FP finding later shown to be a genuine match on further review. | Second-reviewer QA sampling | QA review sample |
|  | **6.2** | **Dispute-reason ambiguity** | A dispute upheld for reasons unrelated to identity-matching accuracy. | Consumer objects to a correct merge for a privacy/relationship reason, not an identity error. | Case-note mining; manual coding | Case notes; dispute reason codes |
|  | **6.3** | **Genuinely mixed causation** | A case with multiple plausible contributing causes that cannot be cleanly separated. | Both a static-data gap and a reviewer misjudgement plausibly contributed. | Manual review | Case notes; manual coding |
| **7\. Unclassified(mandatory)** | **7.0** | **Insufficient confidence to assign any category above** | Reportable as a specific, tracked percentage — not absorbed into the nearest plausible category. | Case notes too sparse and no structured pattern reaches confirmation threshold. | N/A — residual by definition | N/A |

## **Notes**

* “Primary detection method” indicates where a pattern is MOST LIKELY to first surface, not the only method capable of finding it — confirmation of any candidate pattern still requires manual case review (Phase 4\) before it is accepted as a classification category.

* “Example” rows are illustrative only, to aid tagging consistency — they are not a claim that this specific scenario has been confirmed at any particular prevalence in your data.