# Analytical Schema Design

## Trial Table

One row per trial.

Fields:

- trial_id
- nct_id
- phase
- recruitment_status
- enrollment
- dates
- derived features

---

## Trial Indication Bridge

One row per indication per trial.

Columns:

- trial_id
- indication

---

## Trial Drug Bridge

One row per drug per trial.

Columns:

- trial_id
- drug_id
- technology

---

## Trial Target Bridge

One row per target per trial.

Columns:

- trial_id
- target

---

## Derived Fields

- phase_norm
- outcome_category
- duration_days
- n_drugs
- is_combination_therapy
- has_checkpoint_inhibitor
