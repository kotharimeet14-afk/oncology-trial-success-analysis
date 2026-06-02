"""
config.py
=========
Central configuration for the oncology trials analysis pipeline.
All paths, thresholds, and domain constants live here.
Changing a value here propagates automatically to every downstream module.
"""

from pathlib import Path

# ── Repository root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# ── I/O paths ────────────────────────────────────────────────────────────────
RAW_DATA_PATH     = ROOT / "data" / "raw" / "SampleDateExtract.xlsx"
OUTPUTS_TABLES    = ROOT / "outputs" / "tables"
OUTPUTS_FIGURES   = ROOT / "outputs" / "figures"

# ── Recruitment status groupings ─────────────────────────────────────────────
RESOLVED_STATUSES = frozenset({"COMPLETED", "TERMINATED", "WITHDRAWN"})
CENSORED_STATUSES = frozenset({
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION", "SUSPENDED",
})
# UNKNOWN is implicitly everything else

# ── Phase ordering (for sorted chart axes) ───────────────────────────────────
PHASE_ORDER = {
    "EARLY_PHASE1":   0,
    "PHASE1":         1,
    "PHASE1/PHASE2":  2,
    "PHASE2":         3,
    "PHASE2/PHASE3":  4,
    "PHASE3":         5,
    "PHASE4":         6,
    "UNCLASSIFIED":   7,
}

# ── Mojibake repair map (UTF-8 stored as Latin-1) ────────────────────────────
MOJIBAKE_MAP: dict[str, str] = {
    "Î±": "α",
    "Î²": "β",
    "Î³": "γ",
    "Î´": "δ",
    "Î¼": "μ",
    "Îº": "κ",
    "Î¶": "ζ",
    "Îµ": "ε",
}

# ── Checkpoint inhibitor molecular targets ───────────────────────────────────
CHECKPOINT_TARGETS = frozenset({
    "PD-1", "PD-L1", "CTLA-4", "CTLA4",
    "LAG-3", "TIM-3", "TIGIT",
})

# ── Non-pharmacological intervention keywords ────────────────────────────────
NON_PHARMA_KEYWORDS = frozenset([
    "radiation", "surgery", "surgical", "imaging", "biopsy",
    "specimen", "procedure", "magnetic", "computed", "tomography",
    "ultrasound", "questionnaire", "resection", "irradiation",
    "positron", "emission", "conventional", "hypofractionated",
    "stereotactic", "intensity-modulated", "bone marrow", "placebo",
])

# ── Non-specific molecular target descriptors (excluded from target analysis) ─
# These are mechanism-class labels, not discrete molecular targets.
NON_SPECIFIC_TARGETS = frozenset({
    "DNA", "Tubulin", "Proteasome", "RNA", "Microtubule",
    "Cell Wall", "mTOR", "HDAC",   # HDAC is sometimes specific; flag separately
})

# ── Success metric parameters ────────────────────────────────────────────────
# Minimum resolved-trial count below which a stratum's OCR is suppressed
# in summary tables (replaced with NaN and flagged).
SUPPRESS_BELOW_N_RESOLVED: int = 10

# Minimum resolved-trial count for target-level strata (lower threshold
# because we expect many small target groups).
SUPPRESS_BELOW_N_TARGET: int = 8

# Wilson CI confidence level
CI_ALPHA: float = 0.05   # → 95 % confidence interval

# ── Metric metadata stamped on every output CSV ──────────────────────────────
METRIC_TYPE_NOTE = (
    "OPERATIONAL COMPLETION RATE — measures whether a trial ran to protocol "
    "completion. Does NOT measure therapeutic efficacy, primary endpoint "
    "achievement, or clinical benefit. Completed trial ≠ successful drug."
)

# ── Visualisation palette ────────────────────────────────────────────────────
# Consistent hex colours used across all figures.
COLOR_COMPLETED   = "#2A7ABF"   # blue
COLOR_TERMINATED  = "#C94F3A"   # red
COLOR_WITHDRAWN   = "#E09B3D"   # amber
COLOR_CENSORED    = "#888888"   # grey
COLOR_UNKNOWN     = "#B0B0B0"   # light grey
COLOR_CI          = "#2A7ABF"   # matches bar colour
COLOR_SUPPRESSED  = "#DDDDDD"

FIGURE_DPI: int  = 150
FIGURE_STYLE     = "seaborn-v0_8-whitegrid"
