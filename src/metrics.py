from pathlib import Path

import pandas as pd

from src.config import NON_SPECIFIC_TARGETS


ROOT = Path(__file__).resolve().parent.parent

PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"

TABLES.mkdir(parents=True, exist_ok=True)


def load_data():

    dim_trial = pd.read_parquet(
        PROCESSED / "dim_trial.parquet"
    )

    bridge_target = pd.read_parquet(
        PROCESSED / "bridge_trial_target.parquet"
    )

    bridge_drug = pd.read_parquet(
        PROCESSED / "bridge_trial_drug.parquet"
    )

    bridge_indication = pd.read_parquet(
        PROCESSED / "bridge_trial_indication.parquet"
    )

    return (
        dim_trial,
        bridge_target,
        bridge_drug,
        bridge_indication
    )


def calculate_ocr(df):

    resolved = df[df["in_D2"]]

    completed = (
        resolved["recruitment_status"]
        == "COMPLETED"
    ).sum()

    return round(
        completed / len(resolved),
        3
    )


def sensitivity_analysis(df):

    completed = (
        df["recruitment_status"]
        == "COMPLETED"
    ).sum()

    terminated = (
        df["recruitment_status"]
        == "TERMINATED"
    ).sum()

    withdrawn = (
        df["recruitment_status"]
        == "WITHDRAWN"
    ).sum()

    unknown = (
        df["recruitment_status"]
        == "UNKNOWN"
    ).sum()

    resolved = (
        completed
        + terminated
        + withdrawn
    )

    return pd.DataFrame(
        {
            "scenario": [
                "UNKNOWN_EXCLUDED",
                "UNKNOWN_FAILURE",
                "UNKNOWN_SUCCESS",
            ],
            "ocr": [
                round(
                    completed / resolved,
                    3
                ),
                round(
                    completed /
                    (resolved + unknown),
                    3
                ),
                round(
                    (completed + unknown)
                    /
                    (resolved + unknown),
                    3
                ),
            ],
        }
    )


def ocr_by_group(
    df,
    group_col,
    min_n=10
):

    resolved = (
        df[df["in_D2"]]
        .copy()
    )

    resolved["completed"] = (
        resolved["recruitment_status"]
        == "COMPLETED"
    )

    results = (
        resolved
        .groupby(group_col)
        .agg(
            n_resolved=(
                "completed",
                "size"
            ),
            n_completed=(
                "completed",
                "sum"
            ),
        )
        .reset_index()
    )

    results["ocr"] = (
        results["n_completed"]
        /
        results["n_resolved"]
    ).round(3)

    results["small_sample"] = (
        results["n_resolved"]
        < min_n
    )

    results["suppressed"] = (
        results["n_resolved"]
        < min_n
    )

    return (
        results
        .sort_values(
            ["n_resolved", "ocr"],
            ascending=[False, False]
        )
        .reset_index(drop=True)
    )


def ocr_by_target(
    dim_trial,
    bridge_target,
    min_n=8
):

    target_df = (
        bridge_target
        .merge(
            dim_trial[
                [
                    "ID-datalake",
                    "recruitment_status",
                    "in_D2",
                ]
            ],
            left_on="trial_id",
            right_on="ID-datalake",
            how="left",
        )
    )

    target_df = (
        target_df[
            target_df["in_D2"]
        ]
        .copy()
    )

    target_df = (
        target_df[
            ~target_df[
                "target_abbreviation"
            ].isin(
                NON_SPECIFIC_TARGETS
            )
        ]
        .copy()
    )

    target_df["completed"] = (
        target_df["recruitment_status"]
        == "COMPLETED"
    )

    results = (
        target_df
        .groupby(
            "target_abbreviation"
        )
        .agg(
            n_resolved=(
                "completed",
                "size"
            ),
            n_completed=(
                "completed",
                "sum"
            ),
        )
        .reset_index()
    )

    results["ocr"] = (
        results["n_completed"]
        /
        results["n_resolved"]
    ).round(3)

    results["small_sample"] = (
        results["n_resolved"]
        < min_n
    )

    results["suppressed"] = (
        results["n_resolved"]
        < min_n
    )

    return (
        results
        .sort_values(
            ["n_resolved", "ocr"],
            ascending=[False, False]
        )
        .reset_index(drop=True)
    )


def ocr_by_indication(
    dim_trial,
    bridge_indication,
    min_n=10
):

    indication_df = (
        bridge_indication
        .merge(
            dim_trial[
                [
                    "ID-datalake",
                    "recruitment_status",
                    "in_D2"
                ]
            ],
            left_on="trial_id",
            right_on="ID-datalake",
            how="left"
        )
    )

    indication_df = (
        indication_df[
            indication_df["in_D2"]
        ]
        .copy()
    )

    indication_df["completed"] = (
        indication_df["recruitment_status"]
        == "COMPLETED"
    )

    results = (
        indication_df
        .groupby("indication")
        .agg(
            n_resolved=("completed", "size"),
            n_completed=("completed", "sum")
        )
        .reset_index()
    )

    results["ocr"] = (
        results["n_completed"]
        /
        results["n_resolved"]
    ).round(3)

    results["small_sample"] = (
        results["n_resolved"]
        < min_n
    )

    results["suppressed"] = (
        results["n_resolved"]
        < min_n
    )

    return (
        results
        .sort_values(
            ["n_resolved", "ocr"],
            ascending=[False, False]
        )
        .reset_index(drop=True)
    )


def main():

    (
        dim_trial,
        bridge_target,
        bridge_drug,
        bridge_indication
    ) = load_data()

    pd.DataFrame(
        {
            "metric": ["OCR"],
            "value": [
                calculate_ocr(
                    dim_trial
                )
            ],
        }
    ).to_csv(
        TABLES / "ocr_summary.csv",
        index=False,
    )

    sensitivity_analysis(
        dim_trial
    ).to_csv(
        TABLES / "ocr_sensitivity.csv",
        index=False,
    )

    ocr_by_group(
        dim_trial,
        "phase_norm",
        min_n=10,
    ).to_csv(
        TABLES / "ocr_by_phase.csv",
        index=False,
    )

    ocr_by_group(
        dim_trial,
        "first_specific_technology",
        min_n=10,
    ).to_csv(
        TABLES / "ocr_by_technology.csv",
        index=False,
    )

    ocr_by_group(
        dim_trial,
        "is_combination_therapy",
        min_n=1,
    ).to_csv(
        TABLES / "ocr_by_combination.csv",
        index=False,
    )

    ocr_by_target(
        dim_trial,
        bridge_target,
        min_n=8,
    ).to_csv(
        TABLES / "ocr_by_target.csv",
        index=False,
    )

    ocr_by_indication(
        dim_trial,
        bridge_indication,
        min_n=10,
    ).to_csv(
        TABLES / "ocr_by_indication.csv",
        index=False,
    )

    print(
        "All Part 2 metrics generated successfully."
    )


if __name__ == "__main__":
    main()
