from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

FIGURES.mkdir(parents=True, exist_ok=True)


def plot_phase():

    df = pd.read_csv(
        TABLES / "ocr_by_phase.csv"
    )

    df = (
        df[
            ~df["suppressed"]
        ]
        .copy()
    )

    labels = [
        f"{phase}\n(n={n})"
        for phase, n in zip(
            df["phase_norm"],
            df["n_resolved"]
        )
    ]

    plt.figure(figsize=(10, 6))

    plt.bar(
        labels,
        df["ocr"]
    )

    plt.ylim(0, 1)

    plt.title(
        "Operational Completion Rate by Phase"
    )

    plt.xlabel("Phase")
    plt.ylabel("OCR")

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_by_phase.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def plot_technology():

    df = pd.read_csv(
        TABLES / "ocr_by_technology.csv"
    )

    df = (
        df[
            (~df["suppressed"])
            &
            (df["first_specific_technology"] != "Unknown")
        ]
        .copy()
    )

    df = (
        df
        .sort_values(
            "n_resolved",
            ascending=False
        )
        .head(10)
    )

    labels = [
        f"{tech} (n={n})"
        for tech, n in zip(
            df["first_specific_technology"],
            df["n_resolved"]
        )
    ]

    plt.figure(figsize=(12, 6))

    plt.barh(
        labels,
        df["ocr"]
    )

    plt.xlim(0, 1)

    plt.title(
        "Operational Completion Rate by Technology"
    )

    plt.xlabel("OCR")
    plt.ylabel("Technology")

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_by_technology.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def plot_targets():

    df = pd.read_csv(
        TABLES / "ocr_by_target.csv"
    )

    df = (
        df[
            ~df["suppressed"]
        ]
        .copy()
    )

    df = (
        df
        .sort_values(
            "n_resolved",
            ascending=False
        )
        .head(15)
    )

    labels = [
        f"{target} (n={n})"
        for target, n in zip(
            df["target_abbreviation"],
            df["n_resolved"]
        )
    ]

    plt.figure(figsize=(12, 8))

    plt.barh(
        labels,
        df["ocr"]
    )

    plt.xlim(0, 1)

    plt.title(
        "Operational Completion Rate by Target"
    )

    plt.xlabel("OCR")
    plt.ylabel("Target")

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_by_target.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def plot_indication():

    df = pd.read_csv(
        TABLES / "ocr_by_indication.csv"
    )

    df = (
        df[
            ~df["suppressed"]
        ]
        .copy()
    )

    df = (
        df
        .sort_values(
            "n_resolved",
            ascending=False
        )
        .head(15)
    )

    labels = [
        f"{ind} (n={n})"
        for ind, n in zip(
            df["indication"],
            df["n_resolved"]
        )
    ]

    plt.figure(figsize=(14, 8))

    plt.barh(
        labels,
        df["ocr"]
    )

    plt.xlim(0, 1)

    plt.title(
        "Operational Completion Rate by Indication"
    )

    plt.xlabel("OCR")
    plt.ylabel("Indication")

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_by_indication.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def plot_combination():

    df = pd.read_csv(
        TABLES / "ocr_by_combination.csv"
    )

    df["therapy_type"] = (
        df["is_combination_therapy"]
        .map(
            {
                True: "Combination Therapy",
                False: "Single Agent"
            }
        )
    )

    labels = [
        f"{therapy}\n(n={n})"
        for therapy, n in zip(
            df["therapy_type"],
            df["n_resolved"]
        )
    ]

    plt.figure(figsize=(6, 5))

    plt.bar(
        labels,
        df["ocr"]
    )

    plt.ylim(0, 1)

    plt.title(
        "Operational Completion Rate by Therapy Type"
    )

    plt.ylabel("OCR")

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_by_combination.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def plot_sensitivity():

    df = pd.read_csv(
        TABLES / "ocr_sensitivity.csv"
    )

    plt.figure(figsize=(7, 5))

    plt.bar(
        df["scenario"],
        df["ocr"]
    )

    plt.ylim(0, 1)

    plt.title(
        "OCR Sensitivity Analysis"
    )

    plt.ylabel("OCR")

    plt.xticks(rotation=15)

    plt.tight_layout()

    plt.savefig(
        FIGURES / "ocr_sensitivity.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


def main():

    plot_phase()
    plot_technology()
    plot_targets()
    plot_indication()
    plot_combination()
    plot_sensitivity()

    print(
        "All visualizations generated successfully."
    )


if __name__ == "__main__":
    main()
