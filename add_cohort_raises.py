"""Augment nypa_data.json with same-cohort YoY raise statistics.

Reads NYPA_Master_Dataset.csv and the existing nypa_data.json, computes a new
"cohort_raises" key for each Y -> Y+1 transition, and writes the JSON back
with all other keys preserved.

PL-072: Each transition also carries by_site / by_group / by_dept slice
breakdowns so view_org's Realized Raise card can react to the active filter
without any runtime computation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV_PATH = HERE / "NYPA_Master_Dataset.csv"
JSON_PATH = HERE / "nypa_data.json"

MIN_SLICE_N = 5  # drop slices smaller than this — keeps JSON tight and avoids noisy bars


def compute_slice_stats(bs1: pd.Series, bs2: pd.Series) -> dict | None:
    """Compute the all_cohort + raise_recipients pair for one slice's aligned salary series.

    Returns None when the slice has fewer than MIN_SLICE_N valid rows so callers can
    drop the slice entirely.
    """
    valid = (bs1 > 0) & bs2.notna()
    bs1 = bs1[valid]
    bs2 = bs2[valid]
    n = len(bs1)
    if n < MIN_SLICE_N:
        return None

    raises_dollar = bs2 - bs1
    raises_pct = raises_dollar / bs1 * 100
    recipients_mask = raises_dollar > 0
    rec_pct = raises_pct[recipients_mask]
    rec_dollar = raises_dollar[recipients_mask]

    return {
        "all_cohort": {
            "n": int(n),
            "mean_pct": round(float(raises_pct.mean()), 2),
            "median_pct": round(float(raises_pct.median()), 2),
            "mean_dollar": int(round(raises_dollar.mean())),
            "median_dollar": int(round(raises_dollar.median())),
        },
        "raise_recipients": {
            "n": int(recipients_mask.sum()),
            "pct_of_cohort": round(float(recipients_mask.sum() / n * 100), 1),
            "mean_pct": round(float(rec_pct.mean()), 2) if len(rec_pct) > 0 else 0,
            "median_pct": round(float(rec_pct.median()), 2) if len(rec_pct) > 0 else 0,
            "mean_dollar": int(round(rec_dollar.mean())) if len(rec_dollar) > 0 else 0,
            "median_dollar": int(round(rec_dollar.median())) if len(rec_dollar) > 0 else 0,
        },
    }


def compute_cohort_raises(
    df: pd.DataFrame,
    all_years: list[int],
    name_to_site: dict[str, str],
    sites: list[str],
    groups: list[str],
    top_depts: list[str],
) -> dict:
    """For each year transition (Y -> Y+1), compute org-wide raise stats plus
    by_site / by_group / by_dept slice stats for the same cohort.

    Site is a person-level attribute (set in 2026 org snapshot, doesn't vary by year);
    Group and Department are taken from the year_to row.
    """
    result: dict = {}
    for i in range(len(all_years) - 1):
        y1, y2 = all_years[i], all_years[i + 1]
        df_y1 = df[df["Year"] == y1]
        df_y2 = df[df["Year"] == y2]
        bs1_all = df_y1.set_index("Full Name")["Base Annualized Salary"]
        bs2_all = df_y2.set_index("Full Name")["Base Annualized Salary"]

        common = bs1_all.index.intersection(bs2_all.index)
        if len(common) == 0:
            continue

        bs1 = bs1_all.loc[common]
        bs2 = bs2_all.loc[common]

        org_stats = compute_slice_stats(bs1, bs2)
        if org_stats is None:
            continue

        # P25/P75 uses the same valid mask compute_slice_stats applies.
        valid = (bs1 > 0) & bs2.notna()
        raises_pct_org = (bs2[valid] - bs1[valid]) / bs1[valid] * 100

        entry: dict = {
            "year_from": int(y1),
            "year_to": int(y2),
            **org_stats,  # all_cohort + raise_recipients top-level (existing schema)
            "org_p25_pct": round(float(np.percentile(raises_pct_org, 25)), 2),
            "org_p75_pct": round(float(np.percentile(raises_pct_org, 75)), 2),
            "by_site": {},
            "by_group": {},
            "by_dept": {},
        }

        for site in sites:
            site_members = {n for n, s in name_to_site.items() if s == site}
            slice_idx = common.intersection(site_members)
            if len(slice_idx) == 0:
                continue
            slice_stats = compute_slice_stats(bs1.loc[slice_idx], bs2.loc[slice_idx])
            if slice_stats is not None:
                entry["by_site"][site] = slice_stats

        for group in groups:
            grp_names = set(df_y2.loc[df_y2["Group"] == group, "Full Name"])
            slice_idx = common.intersection(grp_names)
            if len(slice_idx) == 0:
                continue
            slice_stats = compute_slice_stats(bs1.loc[slice_idx], bs2.loc[slice_idx])
            if slice_stats is not None:
                entry["by_group"][group] = slice_stats

        for dept in top_depts:
            dept_names = set(df_y2.loc[df_y2["Department"] == dept, "Full Name"])
            slice_idx = common.intersection(dept_names)
            if len(slice_idx) == 0:
                continue
            slice_stats = compute_slice_stats(bs1.loc[slice_idx], bs2.loc[slice_idx])
            if slice_stats is not None:
                entry["by_dept"][dept] = slice_stats

        result[f"{y1}_{y2}"] = entry

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

    name_to_site = {
        name: (rec.get("site") or "").strip()
        for name, rec in data["records"].items()
        if (rec.get("site") or "").strip()
    }

    sites = data.get("sites", [])
    groups = data.get("groups", [])
    top_depts = data.get("top_depts", [])

    data["cohort_raises"] = compute_cohort_raises(
        nypa_df, all_years, name_to_site, sites, groups, top_depts
    )

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=True)

    n_pairs = len(data["cohort_raises"])
    if n_pairs:
        avg_sites = sum(len(v["by_site"]) for v in data["cohort_raises"].values()) / n_pairs
        avg_groups = sum(len(v["by_group"]) for v in data["cohort_raises"].values()) / n_pairs
        avg_depts = sum(len(v["by_dept"]) for v in data["cohort_raises"].values()) / n_pairs
        print(f"Wrote cohort_raises with {n_pairs} transitions to {JSON_PATH}")
        print(
            f"  Avg slices kept per transition: {avg_sites:.1f} sites, "
            f"{avg_groups:.1f} groups, {avg_depts:.1f} top depts"
        )
    else:
        print(f"Wrote cohort_raises (empty) to {JSON_PATH}")


if __name__ == "__main__":
    main()
