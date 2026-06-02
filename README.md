# Oncology Trial Success Analysis

## Overview

This project analyses a raw extract of oncology clinical trial data and develops a reproducible pipeline for assessing trial outcomes using an operational definition of success.

The dataset was provided as a flat-file extract intended for data entry rather than analytical use. The objective was to:

1. Assess and document data quality.
2. Design a clean analytical schema.
3. Define a computable proxy for trial success.
4. Calculate stratified success rates across clinically relevant cohorts.
5. Document assumptions, limitations, and future data requirements.

---

## Repository Structure

```text
data/
├── raw/
└── processed/

docs/
├── assumptions.md
├── data_quality_summary.md
├── schema_design.md
└── part3_written_response.md

notebooks/
└── 01_data_profiling.ipynb

outputs/
├── figures/
└── tables/

src/
├── config.py
├── transform.py
├── metrics.py
└── visualize.py
```

---

## Part 1 — Data Quality Assessment

### Data Profiling

The raw dataset was ingested into pandas and profiled before transformation.

Quality checks included:

* Field completeness
* Missing value distribution
* Cardinality assessment
* Duplicate identifier detection
* Status standardisation
* Phase standardisation
* Date consistency checks
* Unicode/mojibake correction
* Multi-valued field identification

### Key Findings

| Metric                           | Result |
| -------------------------------- | ------ |
| Total trials                     | 1000   |
| Duplicate trial IDs              | 0      |
| Maximum field missingness        | ~5.2%  |
| Critical identifier completeness | 100%   |
| Recruitment status completeness  | 100%   |
| Technology completeness          | 100%   |
| Target completeness              | 100%   |

The dataset was generally high quality, with modest missingness concentrated in completion dates, enrollment information, and phase labels.

---

## Part 1 — Analytical Schema Design

### Analytical Model

The source file contains several many-to-many relationships that are not suitable for cohort-level analysis.

The final schema consists of:

### dim_trial

One row per clinical trial.

Contains:

* Trial identifiers
* Status information
* Phase
* Dates
* Enrollment
* Derived features

### bridge_trial_indication

One row per trial–indication relationship.

Allows:

* Indication-level aggregation
* Multi-indication trials

### bridge_trial_drug

One row per trial–drug relationship.

Allows:

* Combination therapy analysis
* Drug-level attribution

### bridge_trial_target

One row per trial–target relationship.

Allows:

* Molecular target analysis
* Multi-target therapies

---

## Derived Features

Several analytical variables were engineered:

| Feature                  | Description                   |
| ------------------------ | ----------------------------- |
| start_year               | Trial start year              |
| trial_duration_days      | Start-to-completion duration  |
| phase_norm               | Standardized phase            |
| outcome_category         | Status grouping               |
| is_combination_therapy   | >1 investigational drug       |
| has_checkpoint_inhibitor | PD-1 / PD-L1 / CTLA4 exposure |
| in_D2                    | Eligible for OCR analysis     |
| in_D3                    | Resolved + actual enrollment  |

---

## Part 2 — Success Metric Definition

### Operational Completion Rate (OCR)

The dataset does not contain efficacy outcomes, regulatory approvals, or endpoint achievement data.

Therefore, a proxy success metric was defined.

### Primary Metric

Operational Completion Rate (OCR)

OCR =

Completed Trials
/
(Completed + Terminated + Withdrawn)

Only resolved trials are included in the denominator.

### Included Statuses

Success:

* COMPLETED

Failure:

* TERMINATED
* WITHDRAWN

Excluded from primary estimate:

* RECRUITING
* ACTIVE_NOT_RECRUITING
* NOT_YET_RECRUITING
* ENROLLING_BY_INVITATION
* SUSPENDED
* UNKNOWN

---

## Important Caveat

OCR measures operational completion, not therapeutic success.

A completed trial may still fail its primary endpoint.

Likewise, a terminated trial may stop for strategic, financial, or operational reasons unrelated to efficacy.

OCR should therefore be interpreted as a development execution metric rather than a clinical efficacy metric.

---

## Key Results

### Overall OCR

73.5%

### OCR by Phase

| Phase   | OCR   |
| ------- | ----- |
| Phase 1 | 75.6% |
| Phase 2 | 70.1% |
| Phase 3 | 80.3% |
| Phase 4 | 87.5% |

Higher-phase studies generally demonstrated higher completion rates.

### Therapy Type

| Therapy Type        | OCR   |
| ------------------- | ----- |
| Single Agent        | 72.6% |
| Combination Therapy | 74.5% |

Combination therapies exhibited slightly higher operational completion rates.

### Target Analysis

Examples of target-level OCR:

| Target | OCR   |
| ------ | ----- |
| HER2   | 95.2% |
| TOP2   | 87.2% |
| TYMS   | 79.7% |
| PD-1   | 66.7% |
| RNR    | 63.4% |

### Sensitivity Analysis

Because 12.1% of trials carried UNKNOWN outcomes, OCR was recalculated under three assumptions:

| Scenario          | OCR   |
| ----------------- | ----- |
| Unknown Excluded  | 73.5% |
| Unknown = Failure | 61.5% |
| Unknown = Success | 77.9% |

The true value likely lies within this interval.

---

## Reproducibility

### Environment

Python 3.10+

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Execute Pipeline

Transform raw data:

```bash
python -m src.transform
```

Generate metrics:

```bash
python -m src.metrics
```

Generate figures:

```bash
python -m src.visualize
```

Outputs are written to:

```text
outputs/tables/
outputs/figures/
```

---

## Limitations

* No efficacy endpoints available
* No regulatory approval outcomes available
* No progression-free survival data
* No overall survival data
* No adverse event data
* Potential right-censoring among ongoing studies
* Multi-target attribution may inflate counts for common targets

---

## Future Enhancements

With richer clinical datasets, the schema could be extended to include:

* Trial arms
* Endpoint outcomes
* Regulatory decisions
* Biomarker subgroups
* Safety outcomes
* Survival metrics

This would enable transition from operational completion metrics toward clinically meaningful measures of therapeutic success.
