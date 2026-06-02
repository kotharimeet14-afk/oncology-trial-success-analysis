"""
transform.py
============
Full transformation pipeline: raw Excel → cleaned dim_trial + bridge tables.

Implements transformations T-01 through T-17 as documented in the
transformation specification. Each public function is a discrete,
testable step. The top-level ``run()`` function executes the full
pipeline and persists outputs to data/processed/.

Usage
-----
    from src.transform import run
    dim_trial, bridges = run()

    # or from the command line:
    python -m src.transform
"""

from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pandas as pd

# Allow running as a script from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    CENSORED_STATUSES,
    CHECKPOINT_TARGETS,
    MOJIBAKE_MAP,
    NON_PHARMA_KEYWORDS,
    PHASE_ORDER,
    RAW_DATA_PATH,
    RESOLVED_STATUSES,
)

# ─────────────────────────────────────────────────────────────────────────────
# T-01 / T-02  Ingestion & type coercion
# ─────────────────────────────────────────────────────────────────────────────

def ingest(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """
    T-01 / T-02: Load the raw Excel file, assert structural invariants,
    and coerce column dtypes.

    Raises
    ------
    AssertionError
        If the file violates uniqueness or null constraints on key columns.
    """
    df = pd.read_excel(path, engine="openpyxl")

    # ── T-01: Schema assertions ──────────────────────────────────────────────
    expected_cols = {
        "ID-datalake", "nct_id", "brief_title", "official_title",
        "phase", "recruitment_status", "start_date", "completion_date",
        "primary_completion_date", "enrollment", "enrollment_type",
        "indications", "interventions_drugs", "drugs_datalake",
        "main_technologies", "specific_technologies",
        "target_names", "target_abbreviations",
    }
    missing = expected_cols - set(df.columns)
    assert not missing, f"Missing expected columns: {missing}"

    assert df["ID-datalake"].nunique() == len(df), \
        "Duplicate ID-datalake values detected"
    assert df["nct_id"].nunique() == len(df), \
        "Duplicate nct_id values detected"
    assert df["ID-datalake"].isna().sum() == 0, \
        "Null values in surrogate key ID-datalake"
    assert df["nct_id"].isna().sum() == 0, \
        "Null values in nct_id"

    # ── T-02: Dtype coercion ─────────────────────────────────────────────────
    for col in ("start_date", "primary_completion_date", "completion_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-03  Unicode repair
# ─────────────────────────────────────────────────────────────────────────────

def repair_unicode(text: str) -> str:
    """
    Replace known UTF-8/Latin-1 mojibake sequences with correct Unicode.

    The source file encoded Greek letters (α β γ δ μ κ ζ ε) as Latin-1
    bytes while the consuming system interpreted them as CP-1252, producing
    two-character sequences such as 'Î±' for 'α'.  185 such sequences were
    found across target_abbreviations and target_names.
    """
    if not isinstance(text, str):
        return text
    for bad, good in MOJIBAKE_MAP.items():
        text = text.replace(bad, good)
    return text


def apply_unicode_repair(df: pd.DataFrame) -> pd.DataFrame:
    """T-03: Apply Unicode repair to both target columns in-place copy."""
    df = df.copy()
    for col in ("target_abbreviations", "target_names"):
        df[col] = df[col].apply(repair_unicode)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-04  Phase normalisation
# ─────────────────────────────────────────────────────────────────────────────

def normalise_phase(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-04: Add phase_norm and phase_order columns.

    Null phase values → 'UNCLASSIFIED'.
    Hybrid phases (PHASE1/PHASE2, PHASE2/PHASE3) are preserved as distinct
    strata — they represent adaptive seamless trial designs and contain
    biologically distinct populations from either parent phase.
    EARLY_PHASE1 is preserved as a distinct pre-Phase-1 category.
    """
    df = df.copy()
    df["phase_norm"]  = df["phase"].fillna("UNCLASSIFIED")
    df["phase_order"] = df["phase_norm"].map(PHASE_ORDER).fillna(99).astype(int)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-05  Outcome category
# ─────────────────────────────────────────────────────────────────────────────

def map_outcome_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-05: Derive outcome_category, is_resolved, is_censored from
    recruitment_status.

    outcome_category values
    -----------------------
    RESOLVED  — COMPLETED, TERMINATED, WITHDRAWN  (known terminal state)
    CENSORED  — RECRUITING, ACTIVE_NOT_RECRUITING, NOT_YET_RECRUITING,
                ENROLLING_BY_INVITATION, SUSPENDED  (time-censored)
    UNKNOWN   — status is explicitly UNKNOWN; cannot be classified
    """
    df = df.copy()

    def _map(status: str) -> str:
        if status in RESOLVED_STATUSES:
            return "RESOLVED"
        if status in CENSORED_STATUSES:
            return "CENSORED"
        return "UNKNOWN"

    df["outcome_category"] = df["recruitment_status"].map(_map)
    df["is_resolved"]      = df["outcome_category"] == "RESOLVED"
    df["is_censored"]      = df["outcome_category"] == "CENSORED"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-06  Enrollment type imputation
# ─────────────────────────────────────────────────────────────────────────────

def clean_enrollment_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-06: Impute null enrollment_type as 'HISTORICAL'.

    44 trials (all pre-2005 start dates) have null enrollment_type.
    Imputing 'HISTORICAL' signals that a count exists but the
    ACTUAL/ESTIMATED distinction was never captured at registration.
    is_enrollment_actual=True only for verified ACTUAL records.
    """
    df = df.copy()
    df["enrollment_type_clean"]  = df["enrollment_type"].fillna("HISTORICAL")
    df["is_enrollment_actual"]   = df["enrollment_type_clean"] == "ACTUAL"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-07  Date audit & derived durations
# ─────────────────────────────────────────────────────────────────────────────

def audit_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-07: Flag and correct the one known date inversion (NCT01680965),
    derive duration_days, and build a DQ bitmask.

    dq_flags bitmask
    ----------------
    bit 0 (1)  — date inversion corrected
    bit 1 (2)  — start_date is null
    bit 2 (4)  — completion_date (best available) is null
    """
    df = df.copy()

    # Identify the one inversion where primary > overall completion
    df["date_inverted_flag"] = (
        df["primary_completion_date"] > df["completion_date"]
    ).fillna(False)

    # Swap the inverted pair; raw values no longer needed for downstream work
    mask = df["date_inverted_flag"]
    tmp = df.loc[mask, "primary_completion_date"].copy()
    df.loc[mask, "primary_completion_date"] = df.loc[mask, "completion_date"]
    df.loc[mask, "completion_date"]         = tmp

    # Best-available completion anchor: prefer primary_completion_date
    df["completion_date_used"] = (
        df["primary_completion_date"].fillna(df["completion_date"])
    )

    df["duration_days"] = (
        (df["completion_date_used"] - df["start_date"]).dt.days
    )

    df["dq_flags"] = (
          df["date_inverted_flag"].astype(int) * 1
        + df["start_date"].isna().astype(int)  * 2
        + df["completion_date_used"].isna().astype(int) * 4
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-08 / T-09  List column parsing
# ─────────────────────────────────────────────────────────────────────────────

def _safe_parse_list(raw) -> list:
    """
    Parse a Python-literal-encoded list string.
    Returns an empty list on null, empty, or malformed input.
    """
    if not isinstance(raw, str) or raw.strip() in ("", "[]", "nan"):
        return []
    try:
        result = ast.literal_eval(raw)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def _dedup_list(items: list) -> list:
    """Deduplicate a list while preserving insertion order."""
    return list(dict.fromkeys(items))


LIST_COLUMNS = [
    "indications",
    "interventions_drugs",
    "drugs_datalake",
    "main_technologies",
    "specific_technologies",
    "target_names",
    "target_abbreviations",
]


def parse_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-08 / T-09: Parse all list-encoded string columns into Python lists.
    Deduplicate indications (122 trials had internal duplicates).
    Parsed columns stored with '_parsed' suffix.
    """
    df = df.copy()
    for col in LIST_COLUMNS:
        parsed = df[col].apply(_safe_parse_list)
        if col == "indications":
            # T-08: remove within-trial duplicate indication entries
            parsed = parsed.apply(_dedup_list)
        df[f"{col}_parsed"] = parsed
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-10  Non-pharmacological intervention flagging
# ─────────────────────────────────────────────────────────────────────────────

def _is_non_pharma(drug_name: str) -> bool:
    """Return True if drug_name matches a known non-pharmacological keyword."""
    name_lower = drug_name.lower()
    return any(kw in name_lower for kw in NON_PHARMA_KEYWORDS)


def flag_non_pharma(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-10: Split interventions_drugs_parsed into pharmacological and
    non-pharmacological components.  Adds:
      has_non_pharma_component  — bool
      n_non_pharma_items        — count of non-drug interventions
    """
    df = df.copy()

    def _split(drug_list: list) -> tuple[list, list]:
        pharma     = [d for d in drug_list if not _is_non_pharma(d)]
        non_pharma = [d for d in drug_list if     _is_non_pharma(d)]
        return pharma, non_pharma

    results = df["interventions_drugs_parsed"].apply(_split)
    df["interventions_pharma_only"] = results.apply(lambda x: x[0])
    df["non_pharma_items"]          = results.apply(lambda x: x[1])
    df["has_non_pharma_component"]  = df["non_pharma_items"].apply(bool)
    df["n_non_pharma_items"]        = df["non_pharma_items"].apply(len)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-16  Derived feature engineering
# ─────────────────────────────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-16: Compute analytically meaningful derived features.

    n_drugs
        Count of distinct pharmacological agents with datalake IDs.
        Based on drugs_datalake_parsed (NOT interventions_drugs_parsed)
        to exclude non-pharmacological items and unmapped agents.

    is_combination_therapy
        True when n_drugs > 1.  A trial with one drug plus radiation is
        NOT classified as combination therapy under this definition.

    has_checkpoint_inhibitor
        True when any target in the trial matches a known checkpoint
        inhibitor target (PD-1, PD-L1, CTLA-4, LAG-3, TIM-3, TIGIT).
        Derived from target_abbreviations_parsed after Unicode repair.

    first_specific_technology
        The specific technology of the first (index-0) drug in the
        trial.  Used as a trial-level technology label for stratification.
        Acknowledged limitation: multi-drug trials have multiple
        technologies; this captures the leading drug only.
    """
    df = df.copy()

    # Drug count and combination flag
    df["n_drugs"]               = df["drugs_datalake_parsed"].apply(len)
    df["is_combination_therapy"] = df["n_drugs"] > 1

    # Flat unique target list per trial (for checkpoint flag and target bridge)
    def _flatten_targets(nested: list) -> list:
        seen = set()
        flat = []
        for inner in nested:
            items = inner if isinstance(inner, list) else [inner]
            for t in items:
                if isinstance(t, str) and t and t not in seen:
                    seen.add(t)
                    flat.append(t)
        return flat

    df["all_targets_flat"] = df["target_abbreviations_parsed"].apply(_flatten_targets)
    df["n_unique_targets"] = df["all_targets_flat"].apply(len)

    df["has_checkpoint_inhibitor"] = df["all_targets_flat"].apply(
        lambda targets: any(t in CHECKPOINT_TARGETS for t in targets)
    )

    # First specific technology (trial-level label)
    def _first_spec_tech(nested: list) -> str:
        for inner in nested:
            if isinstance(inner, list) and inner:
                val = inner[0]
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return "Unknown"

    df["first_specific_technology"] = df["specific_technologies_parsed"].apply(
        _first_spec_tech
    )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# T-17  Denominator set membership flags
# ─────────────────────────────────────────────────────────────────────────────

def define_denominators(df: pd.DataFrame) -> pd.DataFrame:
    """
    T-17: Add pre-specified denominator membership flags.

    D1 — all 1,000 trials (used only in sensitivity analysis)
    D2 — resolved trials only: COMPLETED + TERMINATED + WITHDRAWN (n=616)
    D3 — resolved + enrollment_type=ACTUAL + enrollment > 0 (n=504)

    These are computed once here to prevent ad-hoc denominator changes
    after results are viewed (which would constitute p-hacking).
    """
    df = df.copy()
    df["in_D1"] = True
    df["in_D2"] = df["is_resolved"]
    df["in_D3"] = (
        df["is_resolved"]
        & df["is_enrollment_actual"]
        & (df["enrollment"].fillna(0) > 0)
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Bridge table construction
# ─────────────────────────────────────────────────────────────────────────────

def build_bridge_indication(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the trial ↔ indication bridge table.
    One row per unique indication per trial (duplicates removed in T-08).
    """
    records = [
        {"trial_id": row["ID-datalake"], "indication": ind}
        for _, row in df.iterrows()
        for ind in row["indications_parsed"]
    ]
    return pd.DataFrame(records).drop_duplicates()


def build_bridge_drug(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the trial ↔ drug bridge table.

    Uses drugs_datalake as the linking key.  drugs_datalake, main_technologies,
    specific_technologies, and target_abbreviations all share the same
    outer-list length (one entry per drug), confirmed by forensic audit.
    interventions_drugs does NOT share this alignment (365 mismatches).
    """
    records = []
    for _, row in df.iterrows():
        drug_ids   = row["drugs_datalake_parsed"]
        main_techs = row["main_technologies_parsed"]
        spec_techs = row["specific_technologies_parsed"]

        for i, drug_id in enumerate(drug_ids):
            main_t = (
                main_techs[i][0]
                if i < len(main_techs) and isinstance(main_techs[i], list) and main_techs[i]
                else None
            )
            spec_t = (
                spec_techs[i][0]
                if i < len(spec_techs) and isinstance(spec_techs[i], list) and spec_techs[i]
                else None
            )
            records.append({
                "trial_id":          row["ID-datalake"],
                "drug_id":           drug_id,
                "drug_position":     i,
                "main_technology":   main_t,
                "specific_technology": spec_t,
            })
    return pd.DataFrame(records)


def build_bridge_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the trial ↔ drug ↔ target bridge table.
    One row per drug per target per trial.
    Unicode repair (T-03) must be applied before calling this function.
    """
    records = []
    for _, row in df.iterrows():
        drug_ids = row["drugs_datalake_parsed"]
        targets  = row["target_abbreviations_parsed"]

        for i, drug_id in enumerate(drug_ids):
            drug_targets = (
                targets[i]
                if i < len(targets) and isinstance(targets[i], list)
                else []
            )
            for tgt in drug_targets:
                if isinstance(tgt, str) and tgt.strip():
                    records.append({
                        "trial_id":           row["ID-datalake"],
                        "drug_id":            drug_id,
                        "drug_position":      i,
                        "target_abbreviation": tgt.strip(),
                    })
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# Data quality report
# ─────────────────────────────────────────────────────────────────────────────

def build_dq_report(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a structured data quality report comparing raw and cleaned frames.
    Saved to outputs/tables/data_quality_report.csv by run().
    """
    rows = []
    for col in df_raw.columns:
        null_raw   = int(df_raw[col].isna().sum())
        null_clean = int(df_clean[col].isna().sum()) if col in df_clean.columns else null_raw
        rows.append({
            "column":          col,
            "dtype_raw":       str(df_raw[col].dtype),
            "null_count_raw":  null_raw,
            "null_pct_raw":    round(null_raw / len(df_raw) * 100, 2),
            "null_count_clean": null_clean,
            "unique_values":   int(df_raw[col].nunique(dropna=True)),
        })

    dq = pd.DataFrame(rows)

    # Annotate known issues
    issues = {
        "target_abbreviations": "Unicode corruption (185 chars, 8 patterns) — repaired in T-03",
        "target_names":         "Unicode corruption (17 chars, 2 patterns) — repaired in T-03",
        "phase":                "40 nulls (4.0%) → UNCLASSIFIED in phase_norm",
        "enrollment_type":      "44 nulls (4.4%) → HISTORICAL for pre-2005 trials",
        "enrollment":           "26 nulls (2.6%) including 20 COMPLETED trials",
        "completion_date":      "52 nulls (5.2%); 1 inversion vs primary_completion_date",
        "primary_completion_date": "51 nulls (5.1%)",
        "recruitment_status":   "121 UNKNOWN (12.1%) — unclassifiable as resolved or censored",
        "indications":          "122 trials (12.2%) contain within-list duplicate entries",
        "interventions_drugs":  "237 non-pharma items; 365 count mismatches vs drugs_datalake",
    }
    dq["known_issue"] = dq["column"].map(issues).fillna("")
    dq["severity"] = dq["column"].map({
        "target_abbreviations": "Critical",
        "recruitment_status":   "Critical",
        "phase":                "Major",
        "enrollment_type":      "Major",
        "enrollment":           "Major",
        "completion_date":      "Major",
        "indications":          "Major",
        "interventions_drugs":  "Major",
        "target_names":         "Major",
        "primary_completion_date": "Minor",
    }).fillna("None")
    return dq


# ─────────────────────────────────────────────────────────────────────────────
# Master pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run(
    path: Path = RAW_DATA_PATH,
    save_processed: bool = True,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Execute the full transformation pipeline T-01 → T-17.

    Returns
    -------
    dim_trial : pd.DataFrame
        Cleaned, enriched trial-level table (1,000 rows).
    bridges : dict
        Keys: 'indication', 'drug', 'target'
        Values: the corresponding bridge DataFrames.
    """
    from src.config import OUTPUTS_TABLES

    print("── T-01/02: Ingesting raw data …")
    df = ingest(path)

    print("── T-03: Unicode repair …")
    df = apply_unicode_repair(df)

    print("── T-04: Phase normalisation …")
    df = normalise_phase(df)

    print("── T-05: Outcome category mapping …")
    df = map_outcome_category(df)

    print("── T-06: Enrollment type clean …")
    df = clean_enrollment_type(df)

    print("── T-07: Date audit …")
    df = audit_dates(df)

    print("── T-08/09: List column parsing …")
    df = parse_list_columns(df)

    print("── T-10: Non-pharma flagging …")
    df = flag_non_pharma(df)

    print("── T-16: Feature engineering …")
    df = engineer_features(df)

    print("── T-17: Denominator flags …")
    df = define_denominators(df)

    # ── Build bridge tables ──────────────────────────────────────────────────
    print("── Building bridge tables …")
    bridge_indication = build_bridge_indication(df)
    bridge_drug       = build_bridge_drug(df)
    bridge_target     = build_bridge_target(df)

    # ── DQ report ────────────────────────────────────────────────────────────
    df_raw_reload = pd.read_excel(path, engine="openpyxl")
    dq_report = build_dq_report(df_raw_reload, df)

    if save_processed:
        processed_dir = path.parent.parent / "processed"
        processed_dir.mkdir(exist_ok=True)

        # Parquet requires list columns to be serialised back to strings
        # for broad compatibility; keep a clean subset for parquet output
        scalar_cols = [
            c for c in df.columns
            if not c.endswith("_parsed")
            and c not in ("all_targets_flat", "interventions_pharma_only",
                          "non_pharma_items")
        ]
        df[scalar_cols].to_parquet(
            processed_dir / "dim_trial.parquet", index=False
        )
        bridge_indication.to_parquet(
            processed_dir / "bridge_trial_indication.parquet", index=False
        )
        bridge_drug.to_parquet(
            processed_dir / "bridge_trial_drug.parquet", index=False
        )
        bridge_target.to_parquet(
            processed_dir / "bridge_trial_target.parquet", index=False
        )

        OUTPUTS_TABLES.mkdir(parents=True, exist_ok=True)
        dq_report.to_csv(OUTPUTS_TABLES / "data_quality_report.csv", index=False)
        print(f"   Saved processed data to {processed_dir}")

    print("── Transformation pipeline complete.")
    print(f"   dim_trial shape:       {df.shape}")
    print(f"   bridge_indication rows: {len(bridge_indication)}")
    print(f"   bridge_drug rows:       {len(bridge_drug)}")
    print(f"   bridge_target rows:     {len(bridge_target)}")
    print(f"   D2 (resolved):          {df['in_D2'].sum()}")
    print(f"   D3 (resolved+actual):   {df['in_D3'].sum()}")

    bridges = {
        "indication": bridge_indication,
        "drug":       bridge_drug,
        "target":     bridge_target,
    }
    return df, bridges


if __name__ == "__main__":
    run()
