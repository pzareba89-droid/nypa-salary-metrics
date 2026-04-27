"""PL-033 Step 3 validation harness - runs all 6 analyses on Piotr Zareba.

Stubs out Streamlit so app.py can be imported in plain Python, then calls each
analysis and prints a summary report. This file is intentionally NOT in the
git tracker - it's a one-shot validation script.
"""
from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path

# Force UTF-8 on Windows consoles so box-drawing chars don't crash cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- Stub Streamlit so `import app` doesn't error outside a Streamlit run ----
_st = types.ModuleType("streamlit")


def _passthrough_decorator(*args, **kwargs):
    if args and callable(args[0]) and not kwargs:
        return args[0]
    def deco(fn):
        return fn
    return deco


def _noop(*args, **kwargs):
    return None


_st.cache_data = _passthrough_decorator
_st.dialog = _passthrough_decorator
_st.set_page_config = _noop
_st.markdown = _noop
_st.write = _noop
_st.title = _noop
_st.header = _noop
_st.subheader = _noop
_st.sidebar = types.SimpleNamespace(__getattr__=lambda *a, **k: _noop)
sys.modules["streamlit"] = _st

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import app  # noqa: E402

PERSON = "Piotr Zareba"


def _fmt_val(v, max_chars=80):
    if isinstance(v, float):
        if abs(v) > 1000 and v == int(v):
            return f"{int(v):,}"
        if abs(v) >= 100:
            return f"{v:,.1f}"
        return f"{v:.3f}"
    if isinstance(v, list):
        if len(v) > 5:
            return f"[{len(v)} items]"
        return "[" + ", ".join(_fmt_val(x, 20) for x in v) + "]"
    if isinstance(v, dict):
        return f"{{...{len(v)} keys}}"
    s = str(v)
    if len(s) > max_chars:
        s = s[: max_chars - 1] + "…"
    return s


KEY_DETAIL_FIELDS = {
    "peer_position": [
        "n_peers", "person_salary", "peer_median", "peer_p75",
        "person_percentile", "gap_to_median", "peers_above", "peers_below",
    ],
    "yoy_raise_pattern": [
        "n_transitions", "count_beat", "count_tied", "count_below",
        "avg_gap_when_below", "worst_gap_year", "worst_gap_pct_pts",
        "best_gap_year", "best_gap_pct_pts", "tie_tolerance_pct_pts",
    ],
    "cumulative_gap": [
        "starting_year", "starting_salary", "actual_salary",
        "counter_factual_salary", "dollar_gap", "pct_gap", "compounding_lost",
    ],
    "peer_growth": [
        "person_total_growth_pct", "person_cagr", "growth_percentile",
        "cagr_percentile", "peer_median_total_growth", "peer_median_cagr",
        "peer_p75_total_growth", "n_peers_with_growth",
    ],
    "title_stripped": [
        "person_site", "person_avg_raise_pct", "site_cohort_avg_pct",
        "white_plains_cohort_avg_pct", "org_cohort_avg_pct",
        "gap_person_vs_site_cohort", "gap_site_vs_wp", "gap_site_vs_org",
        "n_site_employees",
    ],
    "specific_ask": [
        "current_salary", "target_p50", "target_p75", "target_minimum",
        "pct_increase_p50", "pct_increase_p75", "pct_increase_min",
        "above_p50", "above_p75", "above_min",
        "site_raise_rate_pct", "market_raise_rate_pct",
        "forward_looking_dollar_5yr", "forward_looking_dollar_5yr_at_market",
        "forward_looking_5yr_gap", "n_peers",
    ],
}


def _cohort_label(analysis_id: str) -> str:
    if analysis_id in {"peer_position", "peer_growth", "specific_ask"}:
        return "MARKET"
    if analysis_id in {"yoy_raise_pattern", "cumulative_gap"}:
        return "ORG (cohort_raises)"
    if analysis_id == "title_stripped":
        return "STRUCTURAL (site x role_type)"
    return "?"


def main() -> None:
    data = json.loads((HERE / "nypa_data.json").read_text(encoding="utf-8"))
    records = data["records"]
    person_record = records[PERSON]
    peer_groups = app.resolve_peer_group(PERSON, person_record, records)

    print("=" * 90)
    print(f"PL-033 STEP 3 VALIDATION — Person: {PERSON}")
    print(f"  Latest base: ${person_record['base'][-1]:,} ({person_record['years'][-1]})")
    print(f"  Latest title: {person_record['titles'][-1]}")
    print(f"  Site: {person_record.get('site')}")
    print(f"  Role type (resolver): {peer_groups['person_role_type']}")
    print(f"  LOCAL cohort:  {peer_groups['local']['level']} (n={peer_groups['local']['n']})")
    print(f"  MARKET cohort: {peer_groups['market']['level']} (n={peer_groups['market']['n']})")
    print("=" * 90)

    funcs = [
        app.analyze_peer_position,
        app.analyze_yoy_raise_pattern,
        app.analyze_cumulative_gap,
        app.analyze_peer_growth,
        app.analyze_title_stripped,
        app.analyze_specific_ask,
    ]

    results = []
    for f in funcs:
        result = f(PERSON, person_record, records, peer_groups, data)
        results.append(result)

    for r in results:
        aid = r["id"]
        print()
        print("─" * 90)
        print(f"### {aid.upper()}    [cohort: {_cohort_label(aid)}]")
        print("─" * 90)
        print("HEADLINE:")
        print(f"  {r['headline']}")
        print()
        print("KEY DETAILS:")
        for k in KEY_DETAIL_FIELDS.get(aid, list(r["details"].keys())[:6]):
            v = r["details"].get(k, "<MISSING>")
            print(f"  {k:<35s}  {_fmt_val(v)}")
        print()
        print("CREDIBILITY INPUTS:")
        ci = r["credibility_inputs"]
        print(f"  n_peers                              {ci['n_peers']}")
        print(f"  dollar_impact                        ${ci['dollar_impact']:,.0f}")
        print(f"  extremity                            {ci['extremity']:.3f}")
        print(f"  narrative_corroboration_tag          {ci['narrative_corroboration_tag']}")
        print()
        print(f"DATA SOURCE: {r['data_source']}")

    print()
    print("=" * 90)
    print("CORROBORATION TAG SUMMARY (cross-analysis)")
    print("=" * 90)
    tag_groups: dict[str, list[str]] = {}
    for r in results:
        t = r["credibility_inputs"]["narrative_corroboration_tag"]
        tag_groups.setdefault(t, []).append(r["id"])
    for t, ids in sorted(tag_groups.items(), key=lambda kv: -len(kv[1])):
        print(f"  {t:<32s}  {ids}")

    print()
    print("=" * 90)
    print("ANALYSIS-2 PER-TRANSITION TABLE (sanity check)")
    print("=" * 90)
    yoy_r = next(r for r in results if r["id"] == "yoy_raise_pattern")
    print(f"  {'transition':<14s}  {'person%':>9s}  {'org_med%':>9s}  {'p25%':>7s}  {'p75%':>7s}  {'gap pp':>8s}  outcome")
    for t in yoy_r["details"]["per_transition"]:
        print(
            f"  {t['year_label']:<14s}  "
            f"{t['person_raise_pct']:>9.2f}  {t['org_median_pct']:>9.2f}  "
            f"{t['org_p25_pct']:>7.2f}  {t['org_p75_pct']:>7.2f}  "
            f"{t['gap_pct_pts']:>+8.2f}  {t['outcome']}"
        )

    print()
    print("=" * 90)
    print("ANALYSIS-3 YEAR-BY-YEAR TRAJECTORY (sanity check)")
    print("=" * 90)
    cg = next(r for r in results if r["id"] == "cumulative_gap")["details"]
    print(f"  {'year':<6s}  {'actual':>12s}  {'cf':>12s}  {'gap':>12s}")
    for yr, a, cf, g in zip(cg["years"], cg["yearly_actual"],
                            cg["yearly_counter_factual"], cg["yearly_gaps"]):
        print(f"  {yr:<6d}  ${a:>10,.0f}  ${cf:>10,.0f}  ${g:>+10,.0f}")


if __name__ == "__main__":
    main()
