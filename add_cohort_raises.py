"""Augment nypa_data.json with same-cohort YoY raise statistics.

Reads NYPA_Master_Dataset.csv and the existing nypa_data.json, computes a new
"cohort_raises" key for each Y -> Y+1 transition, and writes the JSON back
with all other keys preserved.

PL-072: Each transition also carries by_site / by_group / by_dept slice
breakdowns so view_org's Realized Raise card can react to the active filter
without any runtime computation.

PL-094: Each slice additionally emits title_change_* and merit_only_*
sub-buckets. A year-pair is a PROMOTION when the normalized title changed
AND the raise is >= PROMOTION_RAISE_THRESHOLD; everything else is MERIT.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV_PATH = HERE / "NYPA_Master_Dataset.csv"
JSON_PATH = HERE / "nypa_data.json"

MIN_SLICE_N = 5  # drop slices smaller than this — keeps JSON tight and avoids noisy bars

# PL-094: hybrid AND promotion-detection rule. A year-pair counts as a
# title-change/promotion only if the normalized title differs AND the raise
# clears this floor. 4.0% matches NYPA's stated merit-pool guidance; title
# changes with raises below it are dominated by data-cleanup noise
# (e.g. "P & C" -> "P C") and lateral moves rather than real promotions.
PROMOTION_RAISE_THRESHOLD = 4.0

_TITLE_PUNCT_RE = re.compile(r"[/\-,.]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_title(s) -> str:
    """Canonicalize a job title for cross-year equality comparison.

    Lowercases, replaces "&" with "and", strips the punctuation set the
    PL-094 audit found most responsible for spurious "title changes"
    (`/`, `-`, `,`, `.`), collapses whitespace. NaN/non-string returns "".
    """
    if not isinstance(s, str):
        return ""
    s = s.replace("&", "and")
    s = _TITLE_PUNCT_RE.sub(" ", s)
    s = s.lower()
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


def _bucket_stats(raises_dollar: pd.Series, raises_pct: pd.Series) -> dict:
    return {
        "n": int(len(raises_dollar)),
        "mean_pct": round(float(raises_pct.mean()), 2),
        "median_pct": round(float(raises_pct.median()), 2),
        "mean_dollar": int(round(raises_dollar.mean())),
        "median_dollar": int(round(raises_dollar.median())),
    }


def _recipients_stats(
    rec_dollar: pd.Series, rec_pct: pd.Series, denom_n: int
) -> dict:
    n_rec = int(len(rec_dollar))
    return {
        "n": n_rec,
        "pct_of_cohort": round(float(n_rec / denom_n * 100), 1) if denom_n > 0 else 0,
        "mean_pct": round(float(rec_pct.mean()), 2) if n_rec > 0 else 0,
        "median_pct": round(float(rec_pct.median()), 2) if n_rec > 0 else 0,
        "mean_dollar": int(round(rec_dollar.mean())) if n_rec > 0 else 0,
        "median_dollar": int(round(rec_dollar.median())) if n_rec > 0 else 0,
    }


def compute_slice_stats(
    bs1: pd.Series,
    bs2: pd.Series,
    t1: pd.Series,
    t2: pd.Series,
) -> dict | None:
    """Compute the all_cohort + raise_recipients pair (plus PL-094
    title_change_* and merit_only_* sub-buckets) for one slice's aligned
    salary series.

    Returns None when the slice has fewer than MIN_SLICE_N valid rows so
    callers can drop the slice entirely. Per-bucket MIN_SLICE_N also
    applies to the title-change / merit-only sub-buckets: if a sub-bucket
    falls below threshold its keys are omitted from the result.
    """
    valid = (bs1 > 0) & bs2.notna()
    bs1 = bs1[valid]
    bs2 = bs2[valid]
    t1 = t1[valid]
    t2 = t2[valid]
    n = len(bs1)
    if n < MIN_SLICE_N:
        return None

    raises_dollar = bs2 - bs1
    raises_pct = raises_dollar / bs1 * 100
    recipients_mask = raises_dollar > 0
    rec_pct = raises_pct[recipients_mask]
    rec_dollar = raises_dollar[recipients_mask]

    result: dict = {
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

    # PL-094: hybrid AND classifier. is_promotion := normalized title changed
    # AND raise >= 4.0%. Everything else is the merit bucket. n's of the two
    # sub-buckets sum to all_cohort n by construction.
    is_promotion = (
        t1.map(normalize_title) != t2.map(normalize_title)
    ) & (raises_pct >= PROMOTION_RAISE_THRESHOLD)

    tc_dollar = raises_dollar[is_promotion]
    tc_pct = raises_pct[is_promotion]
    mo_dollar = raises_dollar[~is_promotion]
    mo_pct = raises_pct[~is_promotion]

    tc_rec_mask = recipients_mask & is_promotion
    mo_rec_mask = recipients_mask & (~is_promotion)

    if len(tc_dollar) >= MIN_SLICE_N:
        result["title_change_all"] = _bucket_stats(tc_dollar, tc_pct)
        result["title_change_recipients"] = _recipients_stats(
            raises_dollar[tc_rec_mask], raises_pct[tc_rec_mask], int(len(tc_dollar))
        )

    if len(mo_dollar) >= MIN_SLICE_N:
        result["merit_only_all"] = _bucket_stats(mo_dollar, mo_pct)
        result["merit_only_recipients"] = _recipients_stats(
            raises_dollar[mo_rec_mask], raises_pct[mo_rec_mask], int(len(mo_dollar))
        )

    return result


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
        t1_all = df_y1.set_index("Full Name")["Title"]
        t2_all = df_y2.set_index("Full Name")["Title"]

        common = bs1_all.index.intersection(bs2_all.index)
        if len(common) == 0:
            continue

        bs1 = bs1_all.loc[common]
        bs2 = bs2_all.loc[common]
        t1 = t1_all.loc[common]
        t2 = t2_all.loc[common]

        org_stats = compute_slice_stats(bs1, bs2, t1, t2)
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
            slice_stats = compute_slice_stats(
                bs1.loc[slice_idx], bs2.loc[slice_idx],
                t1.loc[slice_idx], t2.loc[slice_idx],
            )
            if slice_stats is not None:
                entry["by_site"][site] = slice_stats

        for group in groups:
            grp_names = set(df_y2.loc[df_y2["Group"] == group, "Full Name"])
            slice_idx = common.intersection(grp_names)
            if len(slice_idx) == 0:
                continue
            slice_stats = compute_slice_stats(
                bs1.loc[slice_idx], bs2.loc[slice_idx],
                t1.loc[slice_idx], t2.loc[slice_idx],
            )
            if slice_stats is not None:
                entry["by_group"][group] = slice_stats

        for dept in top_depts:
            dept_names = set(df_y2.loc[df_y2["Department"] == dept, "Full Name"])
            slice_idx = common.intersection(dept_names)
            if len(slice_idx) == 0:
                continue
            slice_stats = compute_slice_stats(
                bs1.loc[slice_idx], bs2.loc[slice_idx],
                t1.loc[slice_idx], t2.loc[slice_idx],
            )
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
