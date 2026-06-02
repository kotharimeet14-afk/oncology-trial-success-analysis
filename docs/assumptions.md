# Assumptions and Analytical Decisions

This document records the assumptions and methodological decisions used throughout the analysis.

---

## 1. Operational Completion Rate (OCR) Is Not Therapeutic Success

The source dataset does not contain:

* Primary endpoint results
* Efficacy outcomes
* Regulatory approvals
* Survival outcomes
* Biomarker response data

As a result, true clinical success cannot be measured directly.

The primary metric used in this analysis is therefore an **Operational Completion Rate (OCR)**, which measures whether a trial progressed to protocol-defined completion.

A completed trial should not be interpreted as a clinically successful therapy.

---

## 2. Success Definition

The primary outcome variable is defined as:

### Success

* COMPLETED

### Failure

* TERMINATED
* WITHDRAWN

These statuses represent trials that either completed according to protocol or stopped prematurely.

---

## 3. Treatment of Ongoing Trials

The following statuses are considered right-censored observations:

* RECRUITING
* ACTIVE_NOT_RECRUITING
* NOT_YET_RECRUITING
* ENROLLING_BY_INVITATION
* SUSPENDED

These trials have not yet reached a final outcome and are therefore excluded from the primary OCR denominator.

---

## 4. Treatment of UNKNOWN Status

Trials labelled UNKNOWN present outcome uncertainty.

Three sensitivity scenarios were evaluated:

### Scenario A (Primary Analysis)

UNKNOWN excluded from denominator.

### Scenario B

UNKNOWN treated as failure.

### Scenario C

UNKNOWN treated as success.

This produces an OCR range that reflects uncertainty introduced by missing outcome information.

---

## 5. Phase Standardization

Phase values were standardized into a controlled vocabulary:

* EARLY_PHASE1
* PHASE1
* PHASE1/PHASE2
* PHASE2
* PHASE2/PHASE3
* PHASE3
* PHASE4
* UNCLASSIFIED

Hybrid phases were preserved rather than collapsed.

This retains information regarding transitional development programs.

---

## 6. Multi-Valued Fields

Several fields contained multiple entities within a single cell:

* indications
* interventions_drugs
* target_abbreviations

These fields were normalized into bridge tables.

Each value was treated as an independent relationship to the trial.

---

## 7. Target Attribution

A trial targeting multiple molecular targets contributes to each relevant target stratum.

Example:

A trial targeting both PD-1 and VEGFR contributes to:

* PD-1 analyses
* VEGFR analyses

This is intentional and reflects the biological design of multi-target therapies.

Consequently, target-level counts should not be interpreted as mutually exclusive populations.

---

## 8. Combination Therapy Definition

A trial is classified as a combination therapy when more than one investigational drug is present after parsing the intervention field.

### Single Agent

1 drug

### Combination Therapy

2 or more drugs

Supportive care and non-pharmacological interventions are excluded where identifiable.

---

## 9. Checkpoint Inhibitor Flag

A trial is flagged as involving checkpoint inhibition when at least one target includes:

* PD-1
* PD-L1
* CTLA-4
* LAG-3
* TIM-3
* TIGIT

This feature was engineered to support future immuno-oncology analyses.

---

## 10. Small-Strata Suppression

Very small cohorts produce unstable estimates.

A stratum is flagged as a small sample when:

### Phase and Technology Analyses

n_resolved < 10

### Target Analyses

n_resolved < 8

Suppressed strata are retained in output tables but should be interpreted cautiously.

---

## 11. Date Handling

Date fields were converted to standardized datetime formats.

Derived variables include:

* start_year
* trial_duration_days

Duration calculations were performed only when both start and completion dates were available.

---

## 12. Missing Data

Missing values were not imputed.

The analysis prioritizes transparency over synthetic completion of records.

Where information was unavailable:

* values remain missing
* completeness statistics are reported explicitly

---

## 13. Technology Classification

Technology analyses use the first standardized technology label available in the source data.

Examples include:

* Small Molecule
* Monoclonal Antibody
* Colony-Stimulating Factor

Technology categories are treated as provided by the source dataset and were not externally reclassified.

---

## 14. Scope of Inference

The results presented here should be interpreted as characteristics of the provided oncology trial dataset.

The analysis does not attempt to estimate:

* Regulatory approval probability
* Drug market success
* Clinical benefit
* Real-world effectiveness

The objective is to provide a reproducible operational assessment of trial progression and completion.
