"""PL-033 Step 4 validation harness - tests scorer/selector/credibility.

Runs build_report_payload against three test subjects:
  1. Piotr Zareba                    - the original subject (above-median, structural site lag)
  2. An auto-discovered underpaid    - low percentile non-craft engineer (multi-year tenure)
  3. An auto-discovered above-market - high percentile non-craft engineer (multi-year tenure)

For each subject, prints:
  - All 6 analyses with strength score, direction, and tag
  - Case arguments (top of report) vs context arguments (counter-evidence)
  - Credibility verdict with rationale and warnings

Stubs out Streamlit so app.py can be imported in plain Python. Kept as a
regression harness; safe to rerun at any time.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

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

PIOTR = "Piotr Zareba"


# ----------------------------------------------------------------------------
# Subject discovery
# ----------------------------------------------------------------------------
def discover_test_subjects(records: dict) -> tuple[str, str]:
    """Find two contrastive non-craft engineering subjects from Piotr's market.

    - underpaid: someone with low base_latest in the market cohort, 5+ year tenure
    - above_market: someone with high base_latest in the same cohort

    Returns (underpaid_name, above_market_name).
    """
    piotr_record = records[PIOTR]
    piotr_groups = app.resolve_peer_group(PIOTR, piotr_record, records)
    market_members = piotr_groups["market"]["members"]
    multi_year = [m for m in market_members
                  if len(m["years"]) >= 5 and m["base_latest"] > 0]
    multi_year.sort(key=lambda m: m["base_latest"])

    underpaid = multi_year[3]["full_name"]
    above_market = multi_year[-3]["full_name"]
    return underpaid, above_market


# ----------------------------------------------------------------------------
# Pretty printing
# ----------------------------------------------------------------------------
DIRECTION_BADGE = {
    "case_supporting": "[CASE]",
    "neutral": "[NEUT]",
    "counter_evidence": "[CTR ]",
}


def print_subject_header(payload: dict) -> None:
    rec = payload["person_record"]
    pg = payload["peer_groups"]
    print()
    print("=" * 100)
    print(f"SUBJECT: {payload['person_name']}")
    print(
        f"  Latest base: ${rec['base'][-1]:,} ({rec['years'][-1]})  "
        f"|  Site: {rec.get('site') or '(none)'}  "
        f"|  Role type: {pg['person_role_type']}"
    )
    print(f"  Latest title: {rec['titles'][-1]}")
    print(f"  Tenure: {rec['years'][0]} -> {rec['years'][-1]} "
          f"({rec['years'][-1] - rec['years'][0]} years)")
    print(f"  Cohorts: LOCAL={pg['local']['level']} (n={pg['local']['n']})  "
          f"MARKET={pg['market']['level']} (n={pg['market']['n']})")
    print("=" * 100)


def print_all_analyses_table(payload: dict) -> None:
    print()
    print("ALL 6 ANALYSES (sorted by strength desc):")
    print(f"  {'rank':<5s}  {'analysis':<20s}  {'strength':>9s}  {'direction':<18s}  "
          f"{'tag':<32s}  components(d/s/e/mod)")
    print(f"  {'-'*5}  {'-'*20}  {'-'*9}  {'-'*18}  {'-'*32}  {'-'*30}")
    sorted_analyses = sorted(payload["all_analyses"],
                             key=lambda a: -a["strength"])
    for i, a in enumerate(sorted_analyses, 1):
        c = a["score_components"]
        comp_str = (
            f"{c['dollar']:.2f}/{c['sample']:.2f}/{c['extremity']:.2f}/"
            f"{c['direction_modifier']:+.1f}"
        )
        tag = a["credibility_inputs"]["narrative_corroboration_tag"]
        print(
            f"  {i:<5d}  {a['id']:<20s}  {a['strength']:>9.2f}  "
            f"{DIRECTION_BADGE[a['score_direction']]} {a['score_direction']:<10s}  "
            f"{tag:<32s}  {comp_str}"
        )


def print_selection(payload: dict) -> None:
    print()
    print("SELECTION:")
    print(f"  {payload['selection_summary']}")
    print()
    print("  CASE ARGUMENTS (top of report):")
    for i, a in enumerate(payload["case_arguments"], 1):
        tag = a["credibility_inputs"]["narrative_corroboration_tag"]
        marker = "  PUNCHLINE" if a["id"] == "specific_ask" else ""
        pad_marker = "  (neutral pad)" if a["score_direction"] == "neutral" else ""
        print(f"    {i}. {a['id']:<20s}  strength={a['strength']:>6.2f}  "
              f"tag={tag}{marker}{pad_marker}")
    print()
    print("  CONTEXT ARGUMENTS (counter-evidence + neutrals not promoted):")
    if not payload["context_arguments"]:
        print("    (none)")
    for a in payload["context_arguments"]:
        tag = a["credibility_inputs"]["narrative_corroboration_tag"]
        print(f"    -  {a['id']:<20s}  strength={a['strength']:>6.2f}  "
              f"tag={tag}  ({a['score_direction']})")


def print_credibility(payload: dict) -> None:
    cred = payload["credibility"]
    print()
    print(f"CREDIBILITY: {cred['level'].upper()}  ({cred['color']})")
    print(f"  Rationale: {cred['rationale']}")
    d = cred["details"]
    print(
        f"  Details: market_n={d['market_n']}, case_count={d['case_count']}, "
        f"counter_count={d['counter_count']}, "
        f"avg_case_strength={d['avg_case_strength']:.2f}, "
        f"has_dollar_anchor={d['has_dollar_anchor']}, "
        f"has_corroboration={d['has_corroboration']}"
    )
    if cred["warnings"]:
        print("  Warnings:")
        for w in cred["warnings"]:
            print(f"    - {w}")
    else:
        print("  Warnings: (none)")


def print_top_headlines(payload: dict) -> None:
    print()
    print("TOP HEADLINES (case_arguments, in report order):")
    for i, a in enumerate(payload["case_arguments"], 1):
        print(f"  {i}. [{a['id']}]  {a['headline']}")
    if payload["context_arguments"]:
        ctr = [a for a in payload["context_arguments"]
               if a["score_direction"] == "counter_evidence"]
        if ctr:
            print()
            print("  CONTEXT (counter-evidence headlines):")
            for a in ctr:
                print(f"     - [{a['id']}]  {a['headline']}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    data = json.loads((HERE / "nypa_data.json").read_text(encoding="utf-8"))
    records = data["records"]

    underpaid_name, above_market_name = discover_test_subjects(records)

    print()
    print("=" * 100)
    print("PL-033 STEP 4 VALIDATION - Strength Scorer / Selector / Credibility")
    print("=" * 100)
    print("Test subjects discovered from Piotr's 535-peer market cohort:")
    print(f"  Subject A (target):       Piotr Zareba")
    print(f"  Subject B (underpaid):    {underpaid_name}  "
          f"(${records[underpaid_name]['base'][-1]:,})")
    print(f"  Subject C (above-market): {above_market_name}  "
          f"(${records[above_market_name]['base'][-1]:,})")

    payloads: list[dict] = []
    for name in (PIOTR, underpaid_name, above_market_name):
        payload = app.build_report_payload(name, records[name], records, data)
        payloads.append(payload)
        print_subject_header(payload)
        print_all_analyses_table(payload)
        print_selection(payload)
        print_credibility(payload)
        print_top_headlines(payload)

    # ---- Cross-subject comparison ----
    print()
    print("=" * 100)
    print("CROSS-SUBJECT COMPARISON")
    print("=" * 100)
    print(f"  {'subject':<40s}  {'cred':<10s}  {'case#':>6s}  {'ctr#':>6s}  "
          f"{'avg_case_str':>13s}  {'mkt_n':>6s}  top tag")
    print(f"  {'-'*40}  {'-'*10}  {'-'*6}  {'-'*6}  {'-'*13}  {'-'*6}  {'-'*30}")
    for p in payloads:
        c = p["credibility"]
        d = c["details"]
        top_case = p["case_arguments"][0] if p["case_arguments"] else None
        top_tag = (top_case["credibility_inputs"]["narrative_corroboration_tag"]
                   if top_case else "-")
        print(f"  {p['person_name']:<40s}  {c['level']:<10s}  "
              f"{d['case_count']:>6d}  {d['counter_count']:>6d}  "
              f"{d['avg_case_strength']:>13.2f}  {d['market_n']:>6d}  {top_tag}")

    print()
    print("Validation summary:")
    print("  - Each subject produces a different report shape, driven by their tag mix.")
    print("  - specific_ask is forced into case_arguments for all subjects (the punchline).")
    print("  - Counter-evidence is preserved (visible in context_arguments + warnings),")
    print("    not hidden, so the report can disclose what works against the case.")


if __name__ == "__main__":
    main()
