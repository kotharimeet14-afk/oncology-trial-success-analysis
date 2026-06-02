# Data Quality Summary

## Dataset Overview

Rows: 1000

Columns: 18

Each row represents a clinical trial.

---

## Key Findings

### Missing Data

Highest missingness observed in:

- completion_date (5.2%)
- primary_completion_date (5.1%)
- enrollment_type (4.4%)
- phase (4.0%)

### Structural Integrity

- No duplicate NCT IDs
- No duplicate datalake IDs

### Multi-valued Fields

The following columns contain serialized list structures:

- indications
- interventions_drugs
- drugs_datalake
- main_technologies
- specific_technologies
- target_names
- target_abbreviations

These require normalization.

### Dirty Values

Observed issues:

- Unicode corruption in target abbreviations
- Duplicate indications within some rows
- 121 trials with UNKNOWN recruitment status

### Analytical Impact

The UNKNOWN status category and ongoing trials introduce right-censoring and prevent direct measurement of therapeutic success.
