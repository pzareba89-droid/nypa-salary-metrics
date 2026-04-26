"""Augment nypa_data.json with same-cohort YoY raise statistics.

Reads NYPA_Master_Dataset.csv and the existing nypa_data.json, computes a new
"cohort_raises" key for each Y -> Y+1 transition, and writes the JSON back
with all other keys preserved.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV_PATH = HERE / "NYPA_Master_Dataset.csv"
JSON_PATH = HERE / "nypa_data.json"


def compute_cohort_raises(df: pd.DataFrame, all_years: list[int]) -> dict:
    """For each year transition (Y -> Y+1), compute raise statistics for
    employees present in BOTH years.
    """
    result: dict = {}
    for i in range(len(all_years) - 1):
        y1, y2 = all_years[i], all_years[i + 1]
        df1 = df[df["Year"] == y1].set_index("Full Name")["Base Annualized Salary"]
        df2 = df[df["Year"] == y2].set_index("Full Name")["Base Annualized Salary"]

        # Same-cohort: people present in both years
        common = df1.index.intersection(df2.index)
        if len(common) == 0:
            continue

        bs1 = df1.loc[common]
        bs2 = df2.loc[common]

        # Filter to valid base salaries (non-zero, non-null)
        valid = (bs1 > 0) & bs2.notna()
        bs1 = bs1[valid]
        bs2 = bs2[valid]

        if len(bs1) == 0:
            continue

        raises_dollar = bs2 - bs1
        raises_pct = (raises_dollar / bs1 * 100)

        recipients_mask = raises_dollar > 0
        rec_pct = raises_pct[recipients_mask]
        rec_dollar = raises_dollar[recipients_mask]

        key = f"{y1}_{y2}"
        result[key] = {
            "year_from": int(y1),
            "year_to": int(y2),
            "all_cohort": {
                "n": int(len(bs1)),
                "mean_pct": round(float(raises_pct.mean()), 2),
                "median_pct": round(float(raises_pct.median()), 2),
                "mean_dollar": int(round(raises_dollar.mean())),
                "median_dollar": int(round(raises_dollar.median())),
            },
            "raise_recipients": {
                "n": int(recipients_mask.sum()),
                "pct_of_cohort": round(float(recipients_mask.sum() / len(bs1) * 100), 1),
                "mean_pct": round(float(rec_pct.mean()), 2) if len(rec_pct) > 0 else 0,
                "median_pct": round(float(rec_pct.median()), 2) if len(rec_pct) > 0 else 0,
                "mean_dollar": int(round(rec_dollar.mean())) if len(rec_dollar) > 0 else 0,
                "median_dollar": int(round(rec_dollar.median())) if len(rec_dollar) > 0 else 0,
            },
            "org_p25_pct": round(float(np.percentile(raises_pct, 25)), 2),
            "org_p75_pct": round(float(np.percentile(raises_pct, 75)), 2),
        }
    return result


def main() -> None:
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    df = pd.read_csv(CSV_PATH, low_memory=False)
    # Restrict to NYPA employees with a Full Name (matches what the rest of the JSON covers).
    nypa_df = df[df["Authority Name"].str.contains("Power Authority", na=False)].copy()
    nypa_df = nypa_df.dropna(subset=["Full Name"])
    # ~0.3% of (Year, Full Name) pairs are distinct people sharing a name.
    # Drop both rows — picking one (keep="last") would silently invent fictitious
    # raises across years (e.g., John Smith #1's 2022 base vs. John Smith #2's 2023 base).
    nypa_df = nypa_df.drop_duplicates(subset=["Year", "Full Name"], keep=False)

    all_years = sorted(int(y) for y in data["all_years"])
    data["cohort_raises"] = compute_cohort_raises(nypa_df, all_years)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=True)

    print(f"Wrote cohort_raises with {len(data['cohort_raises'])} transitions to {JSON_PATH}")


if __name__ == "__main__":
    main()
