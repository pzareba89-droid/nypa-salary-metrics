"""NYPA Salary Analytics — Streamlit app.

Four views (Individual Profile, Comparison, Leaderboard, Org Snapshot) plus a
Home overview. All data (including site lookups) comes from the pre-computed
nypa_data.json.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Paths & constants
# ----------------------------------------------------------------------------
HERE = Path(__file__).parent
DATA_JSON = HERE / "nypa_data.json"

BLUE = "#185FA5"
LIGHT_BLUE = "#378ADD"
DARK_BLUE = "#042C53"
GREEN = "#0F6E56"
LIME = "#1D9E75"
AMBER = "#BA7517"
DARK_AMBER = "#854F0B"
PURPLE = "#534AB7"
LAVENDER = "#7F77DD"
CORAL = "#D85A30"
RUST = "#993C1D"
PINK = "#D4537E"
CMP_COLORS = [LIGHT_BLUE, LIME, CORAL, LAVENDER, AMBER, PINK]

TIER_STYLE = {
    "rocket": "background:#FAEEDA;color:#412402;",
    "strong": "background:#EAF3DE;color:#173404;",
    "solid": "background:#E6F1FB;color:#042C53;",
    "steady": "background:#F1EFE8;color:#2C2C2A;",
}

# ----------------------------------------------------------------------------
# Page configuration + CSS
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="NYPA Salary Metrics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    .block-container {{padding-top:1.2rem;padding-bottom:2rem;max-width:1500px;}}
    section[data-testid="stSidebar"] {{background:{DARK_BLUE};}}
    section[data-testid="stSidebar"] * {{color:#fff !important;}}
    section[data-testid="stSidebar"] .stRadio > label {{color:rgba(255,255,255,0.55) !important;font-size:10px !important;letter-spacing:.12em;text-transform:uppercase;}}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{padding:6px 4px;border-radius:6px;}}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{background:rgba(255,255,255,0.05);}}
    h1, h2, h3 {{color:#111;}}
    .page-sub {{color:#888;font-size:12px;margin-top:-6px;margin-bottom:18px;}}
    .metric-card {{background:#fff;border-radius:8px;padding:12px 14px;border-top:3px solid #eee;margin-bottom:8px;}}
    .metric-card.blue {{border-top-color:{LIGHT_BLUE};}}
    .metric-card.green {{border-top-color:{GREEN};}}
    .metric-card.amber {{border-top-color:{AMBER};}}
    .metric-card.purple {{border-top-color:{LAVENDER};}}
    .metric-card.teal {{border-top-color:{LIME};}}
    .metric-card.coral {{border-top-color:{CORAL};}}
    .metric-label {{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px;}}
    .metric-value {{font-size:20px;font-weight:500;color:#111;}}
    .metric-sub {{font-size:10px;color:#999;margin-top:2px;}}
    .metric-delta-up {{color:{GREEN};font-size:11px;font-weight:500;margin-top:2px;}}
    .metric-delta-dn {{color:#A32D2D;font-size:11px;font-weight:500;margin-top:2px;}}
    .metric-delta-flat {{color:#888;font-size:11px;font-weight:500;margin-top:2px;}}
    .pill {{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:18px;font-size:11px;font-weight:600;margin-right:4px;margin-bottom:4px;}}
    .badge {{display:inline-block;font-size:10px;padding:2px 7px;border-radius:10px;font-weight:600;margin:0 2px;}}
    .b-up {{background:#EAF3DE;color:#27500A;}}
    .b-dn {{background:#FCEBEB;color:#791F1F;}}
    .b-flat {{background:#F1EFE8;color:#5F5E5A;}}
    .b-title {{background:#E6F1FB;color:#0C447C;}}
    .b-ot {{background:#E1F5EE;color:#085041;}}
    .b-add {{background:#FAEEDA;color:#412402;}}
    .callout {{font-size:11px;padding:7px 11px;border-radius:8px;border-left:3px solid;background:#f5f5f3;margin-bottom:6px;}}
    .gap-panel {{background:#fff;border:2px solid {LIGHT_BLUE};border-radius:10px;padding:14px;margin-bottom:12px;}}
    .timeline-item {{display:flex;gap:12px;padding-bottom:12px;}}
    .timeline-dot {{width:11px;height:11px;border-radius:50%;border:2px solid;flex-shrink:0;margin-top:6px;}}
    .timeline-year {{font-size:9px;font-weight:700;color:#888;}}
    .timeline-title {{font-size:12px;font-weight:500;}}
    .timeline-dept {{font-size:10px;color:#888;margin-top:1px;}}
    .hero-banner {{display:flex;align-items:center;gap:14px;padding:14px;background:#fff;border-radius:10px;border:1px solid #e8e8e4;margin-bottom:14px;}}
    .hero-avatar {{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600;}}
    .hero-name {{font-size:19px;font-weight:500;}}
    .hero-sub {{font-size:12px;color:#888;margin-top:2px;}}
    .fullscreen-note {{font-size:10px;color:#888;margin-top:-8px;margin-bottom:6px;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Data loaders (cached)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading NYPA pre-computed analytics…")
def load_data() -> dict[str, Any]:
    with open(DATA_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_site(name: str, data: dict) -> str:
    """Resolve a person's site from the pre-computed JSON."""
    rec = data["records"].get(name, {})
    return (rec.get("site") or "").strip()


# ----------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------
def fmt_dollar(v, signed=False) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    v = round(v)
    a = f"${abs(int(v)):,}"
    if signed:
        return ("+" if v >= 0 else "-") + a
    return ("-" + a) if v < 0 else a


def fmt_pct(v, signed=False, decimals=1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if signed and v > 0:
        return f"+{v:.{decimals}f}%"
    return f"{v:.{decimals}f}%"


def fmt_ordinal(n) -> str:
    """Return n with English ordinal suffix: 1st, 2nd, 3rd, 4th, …, 21st, 22nd."""
    if n is None:
        return "—"
    n_int = int(round(float(n)))
    last_two = n_int % 100
    if 11 <= last_two <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n_int % 10, "th")
    return f"{n_int}{suffix}"


def rgba(hex6: str, alpha: float) -> str:
    """Convert '#RRGGBB' + alpha (0–1) to a Plotly-friendly rgba string."""
    h = hex6.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def avatar_color(name: str) -> str:
    c = ["#378ADD", "#1D9E75", "#D85A30", "#7F77DD", "#BA7517", "#D4537E", "#639922", "#888780"]
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) % len(c)
    return c[h]


def initials(name: str) -> str:
    parts = [p for p in name.strip().split(" ") if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:1].upper()


def metric_card(label, value, *, sub="", color="blue", delta=None, delta_dir=None):
    delta_html = ""
    if delta:
        cls = {"up": "metric-delta-up", "dn": "metric-delta-dn"}.get(delta_dir, "metric-delta-flat")
        delta_html = f'<div class="{cls}">{delta}</div>'
    st.markdown(
        f'<div class="metric-card {color}"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# Plotly layout helper
# ----------------------------------------------------------------------------
def apply_layout(fig: go.Figure, *, height: int = 320, show_legend: bool = False, y_dollars=True):
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=show_legend,
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
        font=dict(family="system-ui, -apple-system, sans-serif", size=11, color="#333"),
        hoverlabel=dict(font=dict(size=11)),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
    if y_dollars:
        fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10),
                         tickprefix="$", tickformat=",")
    else:
        fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.05)", tickfont=dict(size=10))
    return fig


def chart_card(title: str, fig: go.Figure, *, key: str, subtitle: str = "", height: int = 320):
    """Render a chart inside a card with a fullscreen/expand control.

    Plotly also provides a built-in modebar fullscreen icon for each chart.
    """
    col_title, col_btn = st.columns([10, 1])
    with col_title:
        st.markdown(
            f"<div style='font-size:11px;font-weight:600;color:#888;"
            f"text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;'>"
            f"{title}</div>"
            + (f"<div class='fullscreen-note'>{subtitle}</div>" if subtitle else ""),
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("⤢", key=f"fs-{key}", help="Open fullscreen"):
            st.session_state[f"_fs_{key}"] = {"title": title, "fig": fig}
    st.plotly_chart(fig, use_container_width=True, key=f"chart-{key}",
                    config={"displaylogo": False, "responsive": True})
    pending = st.session_state.pop(f"_fs_{key}", None)
    if pending:
        _show_fullscreen(pending["title"], pending["fig"], key)


@st.dialog("Chart", width="large")
def _fullscreen_dialog(title: str, fig: go.Figure):
    st.markdown(f"### {title}")
    fig2 = go.Figure(fig)
    fig2.update_layout(height=640)
    st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False})


def _show_fullscreen(title: str, fig: go.Figure, key: str):
    _fullscreen_dialog(title, fig)


# ============================================================================
# PL-033 Report Generator Helpers
# ============================================================================
# Tokens stripped when extracting title keywords (seniority/level markers).
_TITLE_STRIP_TOKENS = {
    "i", "ii", "iii", "iv", "v",
    "1", "2", "3", "4", "5",
    "senior", "sr", "sr.",
    "junior", "jr", "jr.",
    "lead", "principal",
    "associate", "assistant",
    "level", "trainee", "intern",
    "&",
}


def _title_keywords(title: str) -> set[str]:
    """Normalized keywords from a title, stripping seniority/level markers.

    Splits on whitespace, '/' and '-' so compounds like 'Civil/Structural Engineer'
    contribute both 'civil' and 'structural'. 'O&M' becomes 'o&m' (kept as-is).
    """
    if not title:
        return set()
    raw = title.lower().replace("/", " ").replace("-", " ")
    tokens = [t.strip(".,;:()[]") for t in raw.split()]
    return {t for t in tokens if t and t not in _TITLE_STRIP_TOKENS}


_CRAFT_MARKERS = {
    "apprentice", "journeyperson", "journeyman", "journeywoman",
    "foreman", "mechanic", "electrician", "operator",
    "welder", "machinist", "rigger", "laborer",
    "groundsperson", "groundskeeper",
    "lineperson", "linesman", "lineman",
    "trainee",
    "chief",
    "technician",
    "worker", "fabricator", "warehouseperson",
    "captain", "drafter", "attendant",
}

_NON_CRAFT_MARKERS = {
    "engineer", "manager", "director", "supervisor",
    "coordinator", "specialist", "analyst", "administrator",
    "officer", "counsel", "president", "vp", "svp",
    "pilot", "advisor",
}

_EXEC_CHIEF_PATTERNS = {
    "chief executive", "chief financial", "chief operating", "chief technology",
    "chief information", "chief compliance", "chief legal", "chief marketing",
    "chief human resources", "chief administrative", "chief medical",
    "chief security", "chief strategy", "chief risk", "chief data",
    "chief diversity", "chief of staff",
}

# Context tokens that, alongside 'senior' + 'technician', flip a title to non-craft
# (e.g. 'Senior Engineering Technician', 'Senior Production Technician').
_SENIOR_TECH_CONTEXT = {"engineering", "production", "environmental", "system", "project"}


def classify_role_type(title: str) -> str:
    """Classify a title as 'craft' (union/trades) or 'non_craft' (professional/managerial).

    Evaluation order (top to bottom, first match wins):
      1. Executive 'Chief X' patterns → non_craft (CFO, COO, Chief of Staff, etc.)
      2. CAD/CADD + Operator → non_craft (drafting/design role, not a trade)
      3. Reprographics in title → non_craft (office equipment, not a trade)
      4. Senior + Technician + (engineering/production/environmental/system/project)
         → non_craft (senior technical-professional, not a journey-level technician)
      5. 'Trades ' substring → craft (overrides 'specialist' precedence so
         'Trades Specialist Welder' is craft)
      6. 'Maintenance Assistant' substring → craft
      7. 'Service Repair Assistant' substring → craft
      8. 'License' + 'Operator' → non_craft (license operator track)
      9. Non-craft token markers (engineer, manager, advisor, …) → non_craft
     10. Craft token markers (journeyperson, mechanic, technician, worker, …) → craft
     11. Default → non_craft (the safer org-wide default)
    """
    if not title:
        return "non_craft"
    raw = title.lower().replace("/", " ").replace("-", " ").replace(",", " ")

    if any(p in raw for p in _EXEC_CHIEF_PATTERNS):
        return "non_craft"

    tokens = {tok.strip(".:;()[]") for tok in raw.split()}

    if ("cad" in tokens or "cadd" in tokens) and "operator" in tokens:
        return "non_craft"

    if "reprographics" in tokens:
        return "non_craft"

    if "senior" in tokens and "technician" in tokens and (tokens & _SENIOR_TECH_CONTEXT):
        return "non_craft"

    if "trades " in raw:
        return "craft"

    if "maintenance assistant" in raw:
        return "craft"

    if "service repair assistant" in raw:
        return "craft"

    if "license" in tokens and "operator" in tokens:
        return "non_craft"

    if tokens & _NON_CRAFT_MARKERS:
        return "non_craft"
    if "vice" in tokens and "president" in tokens:
        return "non_craft"

    if tokens & _CRAFT_MARKERS:
        return "craft"

    return "non_craft"


def is_engineering_record(rec: dict) -> bool:
    """True when a person's title history indicates the engineering family.

    Conservative: requires 'ENGINEER' or 'ENGRG' substring in any title across the
    record. False for empty title histories. Used by analyze_title_stripped to scope
    the structural site comparison to engineers when the subject is an engineer —
    empirically necessary because St. Lawrence engineers (7.30%) outpace White
    Plains engineers (6.35%), opposite of the non-craft aggregate pattern.
    """
    titles = rec.get("titles") or []
    return any("ENGINEER" in t.upper() or "ENGRG" in t.upper() for t in titles)


def _peer_member(name: str, rec: dict) -> dict:
    """Uniform peer-member dict built from a raw record."""
    yrs = rec["years"]
    li = len(yrs) - 1
    return {
        "full_name": name,
        "title_latest": rec["titles"][li],
        "site": (rec.get("site") or "").strip(),
        "group_latest": rec["groups"][li],
        "dept_latest": rec["depts"][li],
        "year_first": yrs[0],
        "year_latest": yrs[li],
        "base_first": rec["base"][0],
        "base_latest": rec["base"][li],
        "years": yrs,
        "base_series": rec["base"],
        "yoy": rec["yoy"],
        "titles": rec["titles"],
    }


def resolve_peer_group(person_name: str, person_record: dict, all_records: dict) -> dict:
    """Resolve TWO peer cohorts for a person plus their classified role type.

    LOCAL cohort — 'what HR sees':
      Same Group + Same Site + Same role_type (craft / non_craft).
      Cascade: n>=10 → 'Local'; n>=5 → 'Local (small)'; else fall back to
      Group+role_type org-wide (n>=15) → 'Local (org fallback)'; else low-confidence.

    MARKET cohort — 'what the market sets':
      Same role_type + at least one shared title keyword, SITE-BLIND, no Group filter
      (so e.g. 'Engineering Manager' in Managerial counts toward an engineer's market).
      Cascade: n>=30 → 'Market'; n>=10 → 'Market (smaller)'; else 'Market (low confidence)'.

    Both cohorts exclude the person themselves. Returns:
      {
        "local":  {level, n, members, filter_description},
        "market": {level, n, members, filter_description},
        "person_role_type": "craft" | "non_craft",
      }
    """
    yrs = person_record["years"]
    li = len(yrs) - 1
    person_group = person_record["groups"][li]
    person_site = (person_record.get("site") or "").strip()
    person_title = person_record["titles"][li]
    person_keywords = _title_keywords(person_title)
    person_role = classify_role_type(person_title)

    local_site_role: list[dict] = []
    local_group_role_org: list[dict] = []
    market_role_kw: list[dict] = []

    for name, rec in all_records.items():
        if name == person_name:
            continue
        if not rec.get("years") or not rec.get("groups") or not rec.get("titles"):
            continue
        rli = len(rec["years"]) - 1
        peer_title = rec["titles"][rli]
        peer_role = classify_role_type(peer_title)
        if peer_role != person_role:
            continue
        peer_group = rec["groups"][rli]
        peer_site = (rec.get("site") or "").strip()
        peer_kw = _title_keywords(peer_title)
        member = _peer_member(name, rec)
        if peer_group == person_group:
            local_group_role_org.append(member)
            if peer_site == person_site:
                local_site_role.append(member)
        if person_keywords and peer_kw and (person_keywords & peer_kw):
            market_role_kw.append(member)

    site_label = person_site or "no site assigned"
    role_label = "non-craft" if person_role == "non_craft" else "craft"

    # ---- Local cohort cascade ----
    n_ls = len(local_site_role)
    n_lo = len(local_group_role_org)
    if n_ls >= 10:
        local = {
            "level": "Local",
            "n": n_ls,
            "members": local_site_role,
            "filter_description": (
                f"{n_ls} {role_label} peers in {person_group} at {site_label}"
            ),
        }
    elif n_ls >= 5:
        local = {
            "level": "Local (small)",
            "n": n_ls,
            "members": local_site_role,
            "filter_description": (
                f"{n_ls} {role_label} peers in {person_group} at {site_label} "
                f"(small sample — interpret with caution)"
            ),
        }
    elif n_lo >= 15:
        local = {
            "level": "Local (org fallback)",
            "n": n_lo,
            "members": local_group_role_org,
            "filter_description": (
                f"{n_lo} {role_label} peers in {person_group} org-wide "
                f"(site-level cohort too small)"
            ),
        }
    else:
        local = {
            "level": "Local (low confidence)",
            "n": max(n_ls, n_lo),
            "members": local_site_role if n_ls >= n_lo else local_group_role_org,
            "filter_description": (
                f"Only {max(n_ls, n_lo)} {role_label} peers available in "
                f"{person_group} — local cohort unreliable"
            ),
        }

    # ---- Market cohort cascade ----
    n_m = len(market_role_kw)
    if n_m >= 30:
        market = {
            "level": "Market",
            "n": n_m,
            "members": market_role_kw,
            "filter_description": (
                f"{n_m} {role_label} peers across NYPA whose titles share keywords "
                f"with '{person_title}' (site-blind, all groups)"
            ),
        }
    elif n_m >= 10:
        market = {
            "level": "Market (smaller)",
            "n": n_m,
            "members": market_role_kw,
            "filter_description": (
                f"{n_m} {role_label} peers across NYPA with overlapping title keywords "
                f"(smaller-than-ideal sample)"
            ),
        }
    else:
        market = {
            "level": "Market (low confidence)",
            "n": n_m,
            "members": market_role_kw,
            "filter_description": (
                f"Only {n_m} {role_label} peers across NYPA share title keywords with "
                f"'{person_title}' — market cohort unreliable"
            ),
        }

    return {
        "local": local,
        "market": market,
        "person_role_type": person_role,
    }


def compute_site_role_raise_pattern(records: dict, sites: list[str] | None = None,
                                    role_types: tuple[str, ...] = ("craft", "non_craft"),
                                    family_filter=None) -> dict:
    """Pre-computed avg annual base raise % broken down by Site × role_type.

    Each person's role_type is classified from their LATEST title (a stable identity
    label) and applied to all their year-transition raises (record['yoy'][i] for i>=1).
    Empty-site records are bucketed under '(no site)'.

    `family_filter`: optional callable(record) -> bool. When provided, records where
    family_filter(rec) is False are excluded — used by analyze_title_stripped to scope
    the structural pattern to engineering-only (or any other family) when the subject
    warrants it. Default None preserves backward-compatible org-wide behavior.

    Returns a plot-ready dict:
      {
        "sites_ordered":   [site, ...] sorted by total transition count desc,
        "by_site":         {site: {"all_pct": float, "craft_pct": float|None,
                                   "non_craft_pct": float|None, "n_craft": int,
                                   "n_non_craft": int, "transitions_total": int}},
        "org_wide":        {"all_pct", "craft_pct", "non_craft_pct",
                            "n_craft", "n_non_craft", "transitions_total"},
      }
    """
    no_site_label = "(no site)"
    site_rows: dict[str, list[tuple[str, float]]] = {}
    site_employees: dict[tuple[str, str], set[str]] = {}
    org_rows: list[tuple[str, float]] = []
    org_employees: dict[str, set[str]] = {rt: set() for rt in role_types}

    for name, rec in records.items():
        yrs = rec.get("years") or []
        yoy = rec.get("yoy") or []
        titles = rec.get("titles") or []
        if not yrs or len(yrs) < 2 or not titles:
            continue
        if family_filter is not None and not family_filter(rec):
            continue
        role = classify_role_type(titles[-1])
        if role not in role_types:
            continue
        site = (rec.get("site") or "").strip() or no_site_label
        site_employees.setdefault((site, role), set()).add(name)
        org_employees[role].add(name)
        for i in range(1, len(yrs)):
            v = yoy[i]
            if v is None:
                continue
            site_rows.setdefault(site, []).append((role, float(v)))
            org_rows.append((role, float(v)))

    def _avg(vals: list[float]) -> float | None:
        return (sum(vals) / len(vals)) if vals else None

    by_site: dict[str, dict] = {}
    for site, rows in site_rows.items():
        all_v = [v for _, v in rows]
        c_v = [v for r, v in rows if r == "craft"]
        nc_v = [v for r, v in rows if r == "non_craft"]
        by_site[site] = {
            "all_pct": _avg(all_v),
            "craft_pct": _avg(c_v),
            "non_craft_pct": _avg(nc_v),
            "n_craft": len(site_employees.get((site, "craft"), set())),
            "n_non_craft": len(site_employees.get((site, "non_craft"), set())),
            "transitions_total": len(rows),
        }

    sites_ordered = sorted(by_site.keys(),
                           key=lambda s: -by_site[s]["transitions_total"])
    if sites:
        sites_ordered = [s for s in sites_ordered if s in set(sites) | {no_site_label}]

    all_v = [v for _, v in org_rows]
    c_v = [v for r, v in org_rows if r == "craft"]
    nc_v = [v for r, v in org_rows if r == "non_craft"]
    org_wide = {
        "all_pct": _avg(all_v),
        "craft_pct": _avg(c_v),
        "non_craft_pct": _avg(nc_v),
        "n_craft": len(org_employees.get("craft", set())),
        "n_non_craft": len(org_employees.get("non_craft", set())),
        "transitions_total": len(org_rows),
    }

    return {
        "sites_ordered": sites_ordered,
        "by_site": by_site,
        "org_wide": org_wide,
    }


def resolve_title_similar_peers(person_name: str, person_record: dict, all_records: dict) -> dict:
    """Same-Group peers whose latest title shares any keyword with the person's latest title.

    Returns the same dict shape as resolve_peer_group. Used by analyses that need a
    title-stripped (within-role) cohort even when the broader group is the chosen peer set.
    """
    yrs = person_record["years"]
    li = len(yrs) - 1
    person_group = person_record["groups"][li]
    person_title = person_record["titles"][li]
    person_keywords = _title_keywords(person_title)

    title_matched: list[dict] = []
    for name, rec in all_records.items():
        if name == person_name:
            continue
        if not rec.get("years") or not rec.get("groups") or not rec.get("titles"):
            continue
        rli = len(rec["years"]) - 1
        if rec["groups"][rli] != person_group:
            continue
        peer_kw = _title_keywords(rec["titles"][rli])
        if person_keywords and peer_kw and (person_keywords & peer_kw):
            title_matched.append(_peer_member(name, rec))

    n = len(title_matched)
    if n == 0:
        return {
            "level": "Title-similar (empty)",
            "n": 0,
            "members": [],
            "filter_description": (
                f"No same-group peers share keywords with title '{person_title}'"
            ),
        }
    return {
        "level": "Title-similar",
        "n": n,
        "members": title_matched,
        "filter_description": (
            f"{n} same-group peers with titles sharing keywords with '{person_title}'"
        ),
    }


# ============================================================================
# PL-033 Report Analyses
# ============================================================================
# Each analyze_X function shares the same signature and returns a standardized
# result dict (see PL-033 contract). All numeric fields are JSON-serializable;
# strength is left at 0.0 — credibility scoring happens in Step 4. No colleague
# names ever leave these analyses — only counts, medians, percentiles.

def _safe_stats(vals: list[float]) -> dict:
    """Mean/std/median/p25/p75 from a list of floats. None-tolerant.

    Percentiles use linear interpolation between the two nearest order
    statistics (matches numpy.percentile default).
    """
    vals = [v for v in vals if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "median": None, "p25": None, "p75": None}
    s = sorted(vals)
    m = sum(s) / n
    var = sum((v - m) ** 2 for v in s) / n
    sd = var ** 0.5

    def _pct(p: float) -> float:
        if n == 1:
            return s[0]
        idx = (n - 1) * p / 100.0
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return s[lo] + (s[hi] - s[lo]) * frac

    return {"n": n, "mean": m, "std": sd, "median": _pct(50), "p25": _pct(25), "p75": _pct(75)}


def _percentile_rank(sorted_vals: list[float], target: float) -> float:
    """Where does target rank in sorted_vals (0-100)? Ties get half-weight."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    below = sum(1 for v in sorted_vals if v < target)
    equal = sum(1 for v in sorted_vals if v == target)
    return round((below + 0.5 * equal) / n * 100, 1)


def analyze_peer_position(person_name, person_record, all_records, peer_groups, data) -> dict:
    """Where does this person sit in their MARKET peer group's salary distribution?"""
    market = peer_groups["market"]
    members = market["members"]
    yrs = person_record["years"]
    li = len(yrs) - 1
    person_salary = person_record["base"][li]
    person_year = yrs[li]

    peer_salaries = sorted([float(m["base_latest"]) for m in members
                            if m.get("base_latest")])
    stats = _safe_stats(peer_salaries)
    n = stats["n"]
    median = stats["median"] or 0.0
    p75 = stats["p75"] or 0.0
    pct = _percentile_rank(peer_salaries, person_salary)
    gap_to_median = (median - person_salary) if median else 0.0
    gap_to_p75 = (p75 - person_salary) if p75 else 0.0
    peers_above = sum(1 for v in peer_salaries if v > person_salary)
    peers_below = sum(1 for v in peer_salaries if v < person_salary)

    direction = "below" if gap_to_median > 0 else "above"
    headline = (
        f"Compared to {n} peers in your professional engineering cohort across NYPA, "
        f"your base salary is at the {fmt_ordinal(pct)} percentile. "
        f"Median peer earns ${median:,.0f}; you earn ${person_salary:,.0f}."
    )
    narrative = (
        f"Across the {n}-person market cohort sharing your role and title family, "
        f"{peers_above} earn more than you and {peers_below} earn less. "
        f"You sit ${abs(gap_to_median):,.0f} {direction} the peer median, "
        f"${abs(gap_to_p75):,.0f} {'below' if gap_to_p75 > 0 else 'above'} the P75."
    )

    z = ((person_salary - stats["mean"]) / stats["std"]) if stats["std"] else 0.0
    if pct < 45:
        tag = "underpaid_vs_market"
    elif pct > 55:
        tag = "overpaid_vs_market"
    else:
        tag = "at_market"

    return {
        "id": "peer_position",
        "headline": headline,
        "details": {
            "person_salary": person_salary,
            "person_year": person_year,
            "person_percentile": pct,
            "peer_median": median,
            "peer_p75": p75,
            "peer_mean": stats["mean"],
            "gap_to_median": gap_to_median,
            "gap_to_p75": gap_to_p75,
            "peers_above": peers_above,
            "peers_below": peers_below,
            "n_peers": n,
        },
        "narrative": narrative,
        "data_source": (
            f"Market cohort — {market['level']}, n={n}. "
            f"{market['filter_description']}. Latest year only ({person_year})."
        ),
        "chart_spec": {
            "type": "histogram",
            "data": {
                "peer_salaries": peer_salaries,
                "person_salary": person_salary,
                "person_label": person_name,
                "median": median,
                "p75": p75,
            },
            "title": f"Base salary distribution — market cohort ({person_year})",
            "subtitle": f"n={n} engineering peers across NYPA",
        },
        "credibility_inputs": {
            "n_peers": n,
            "dollar_impact": float(gap_to_median),
            "extremity": abs(z),
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


_YOY_TIE_TOL_PCT_PTS = 0.05  # treat |gap| <= 0.05 pp as a tie (covers float-rounded zeros)


def analyze_yoy_raise_pattern(person_name, person_record, all_records, peer_groups, data) -> dict:
    """How often has this person's annual raise beaten / tied / fallen below the org median?"""
    yrs = person_record["years"]
    yoy = person_record["yoy"]
    cohort_raises = data.get("cohort_raises", {})
    tol = _YOY_TIE_TOL_PCT_PTS

    per_transition: list[dict] = []
    for i in range(1, len(yrs)):
        person_pct = yoy[i]
        if person_pct is None:
            continue
        key = f"{yrs[i-1]}_{yrs[i]}"
        c = cohort_raises.get(key)
        if not c:
            continue
        org_med = c["all_cohort"]["median_pct"]
        gap = person_pct - org_med
        if gap > tol:
            outcome = "beat"
        elif gap < -tol:
            outcome = "below"
        else:
            outcome = "tied"
        per_transition.append({
            "year_transition": key,
            "year_label": f"{yrs[i-1]}→{str(yrs[i])[-2:]}",
            "person_raise_pct": person_pct,
            "org_median_pct": org_med,
            "org_p25_pct": c["org_p25_pct"],
            "org_p75_pct": c["org_p75_pct"],
            "outcome": outcome,
            "gap_pct_pts": gap,
        })

    n_trans = len(per_transition)
    beat = [t for t in per_transition if t["outcome"] == "beat"]
    tied = [t for t in per_transition if t["outcome"] == "tied"]
    below = [t for t in per_transition if t["outcome"] == "below"]
    n_beat = len(beat)
    n_tied = len(tied)
    n_below = len(below)
    avg_gap_below = (sum(t["gap_pct_pts"] for t in below) / n_below) if below else 0.0

    worst = min(below, key=lambda t: t["gap_pct_pts"]) if below else None
    best = max(per_transition, key=lambda t: t["gap_pct_pts"]) if per_transition else None
    worst_year = worst["year_label"] if worst else None
    worst_gap = worst["gap_pct_pts"] if worst else None
    best_year = best["year_label"] if best else None
    best_gap = best["gap_pct_pts"] if best else None

    headline = (
        f"In {n_trans} year transitions: beat the org median in {n_beat}, tied in {n_tied}, "
        f"fell below in {n_below}. "
        f"When below, average shortfall: {abs(avg_gap_below):.1f} percentage points."
    )

    if n_below > 0 and n_beat > 0:
        narrative = (
            f"Mixed pattern across {n_trans} transitions: above org median in {n_beat}, "
            f"matching it in {n_tied}, behind in {n_below} (avg shortfall "
            f"{abs(avg_gap_below):.1f} pp). Best: {best_year} ({best_gap:+.1f} pp); "
            f"worst: {worst_year} ({worst_gap:+.1f} pp)."
        )
    elif n_below > 0:
        narrative = (
            f"You met or fell short of the org median in {n_tied + n_below} of {n_trans} "
            f"transitions, with {n_below} clear shortfalls averaging "
            f"{abs(avg_gap_below):.1f} pp below. Worst: {worst_year} ({worst_gap:+.1f} pp)."
        )
    elif n_beat > 0:
        narrative = (
            f"You beat or matched the org median in every transition: {n_beat} above, "
            f"{n_tied} at parity. Best: {best_year} ({best_gap:+.1f} pp)."
        )
    else:
        narrative = (
            f"All {n_tied} transitions matched the org median exactly — no clear "
            f"out- or under-performance signal."
        )

    if n_beat >= 5:
        tag = "raises_outperforming"
    elif n_below >= 4:
        tag = "raises_below_norm"
    elif (n_beat + n_tied) >= 5:
        tag = "raises_at_norm"
    else:
        tag = "raises_mixed"

    return {
        "id": "yoy_raise_pattern",
        "headline": headline,
        "details": {
            "per_transition": per_transition,
            "n_transitions": n_trans,
            "count_beat": n_beat,
            "count_tied": n_tied,
            "count_below": n_below,
            "avg_gap_when_below": avg_gap_below,
            "worst_gap_year": worst_year,
            "worst_gap_pct_pts": worst_gap,
            "best_gap_year": best_year,
            "best_gap_pct_pts": best_gap,
            "tie_tolerance_pct_pts": tol,
        },
        "narrative": narrative,
        "data_source": (
            f"All-cohort YoY raise medians from cohort_raises table "
            f"(employees present in both years). {n_trans} transitions covered. "
            f"Tie tolerance: ±{tol:.2f} pp."
        ),
        "chart_spec": {
            "type": "line_band",
            "data": {
                "year_labels": [t["year_label"] for t in per_transition],
                "person_pcts": [t["person_raise_pct"] for t in per_transition],
                "org_median_pcts": [t["org_median_pct"] for t in per_transition],
                "org_p25_pcts": [t["org_p25_pct"] for t in per_transition],
                "org_p75_pcts": [t["org_p75_pct"] for t in per_transition],
                "outcomes": [t["outcome"] for t in per_transition],
            },
            "title": "Your annual raise vs NYPA P25–P75 band",
            "subtitle": "Line = your raise; shaded band = org-wide P25 to P75; dashed = org median",
        },
        "credibility_inputs": {
            "n_peers": n_trans,
            "dollar_impact": 0.0,
            "extremity": abs(avg_gap_below) if n_below else 0.0,
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


def analyze_cumulative_gap(person_name, person_record, all_records, peer_groups, data) -> dict:
    """Counter-factual: where would this person be if every raise matched the org median?"""
    yrs = person_record["years"]
    base = person_record["base"]
    cohort_raises = data.get("cohort_raises", {})

    starting_year = yrs[0]
    starting_salary = base[0]
    actual_salary = base[-1]
    latest_year = yrs[-1]

    counter_factual = [float(starting_salary)]
    actual_path = [float(starting_salary)]
    yearly_gaps = [0.0]
    cur_cf = float(starting_salary)
    for i in range(1, len(yrs)):
        c = cohort_raises.get(f"{yrs[i-1]}_{yrs[i]}")
        org_med = c["all_cohort"]["median_pct"] if c else 0.0
        cur_cf = cur_cf * (1 + org_med / 100.0)
        counter_factual.append(cur_cf)
        actual_path.append(float(base[i]))
        yearly_gaps.append(cur_cf - float(base[i]))

    counter_factual_salary = counter_factual[-1]
    dollar_gap = counter_factual_salary - actual_salary
    pct_gap = (dollar_gap / actual_salary * 100.0) if actual_salary else 0.0
    compounding_lost = sum(yearly_gaps)

    if dollar_gap > 0:
        narrative = (
            f"If your annual raises had matched the org median each year since "
            f"{starting_year}, your current base would be ${counter_factual_salary:,.0f} — "
            f"${dollar_gap:,.0f} ({pct_gap:.1f}%) above your actual ${actual_salary:,.0f}. "
            f"That gap compounds: roughly ${compounding_lost:,.0f} in cumulative annual income "
            f"never realized over the {latest_year - starting_year}-year window."
        )
    else:
        narrative = (
            f"If your annual raises had only matched the org median each year since "
            f"{starting_year}, your base would be ${counter_factual_salary:,.0f}. "
            f"Your actual ${actual_salary:,.0f} sits ${abs(dollar_gap):,.0f} "
            f"({abs(pct_gap):.1f}%) above the counter-factual."
        )

    headline = (
        f"If you had received the org median raise each year since {starting_year}, "
        f"your current base would be approximately ${counter_factual_salary:,.0f} "
        f"(actual: ${actual_salary:,.0f}). Cumulative gap: ${dollar_gap:,.0f}."
    )

    if dollar_gap > 0:
        tag = "underpaid_vs_market"
    elif dollar_gap < 0:
        tag = "overpaid_vs_market"
    else:
        tag = "at_market"

    return {
        "id": "cumulative_gap",
        "headline": headline,
        "details": {
            "starting_year": starting_year,
            "starting_salary": starting_salary,
            "latest_year": latest_year,
            "actual_salary": actual_salary,
            "counter_factual_salary": counter_factual_salary,
            "dollar_gap": dollar_gap,
            "pct_gap": pct_gap,
            "compounding_lost": compounding_lost,
            "yearly_actual": actual_path,
            "yearly_counter_factual": counter_factual,
            "yearly_gaps": yearly_gaps,
            "years": list(yrs),
        },
        "narrative": narrative,
        "data_source": (
            f"Counter-factual built by compounding the all-cohort median raise % from "
            f"cohort_raises, applied to {starting_year} starting base."
        ),
        "chart_spec": {
            "type": "dual_line",
            "data": {
                "years": list(yrs),
                "actual": actual_path,
                "counter_factual": counter_factual,
            },
            "title": "Actual vs counter-factual salary trajectory",
            "subtitle": (
                f"Counter-factual = {starting_year} base compounded by org median "
                f"raise each year"
            ),
        },
        "credibility_inputs": {
            "n_peers": 0,
            "dollar_impact": float(dollar_gap),
            "extremity": abs(pct_gap) / 5.0,
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


def analyze_peer_growth(person_name, person_record, all_records, peer_groups, data) -> dict:
    """Career growth (total + CAGR) vs MARKET peer cohort."""
    market = peer_groups["market"]
    members = market["members"]
    yrs = person_record["years"]
    base = person_record["base"]

    person_yrs_span = yrs[-1] - yrs[0]
    person_first = base[0]
    person_last = base[-1]
    person_total_growth_pct = ((person_last / person_first) - 1) * 100 if person_first else 0.0
    person_cagr = (
        ((person_last / person_first) ** (1.0 / person_yrs_span) - 1) * 100
        if person_first and person_yrs_span > 0 else 0.0
    )

    peer_growths: list[float] = []
    peer_cagrs: list[float] = []
    for m in members:
        bf = m.get("base_first")
        bl = m.get("base_latest")
        yf = m.get("year_first")
        yl = m.get("year_latest")
        if not bf or not bl or yf is None or yl is None:
            continue
        span = yl - yf
        if span <= 0 or bf <= 0:
            continue
        peer_growths.append((bl / bf - 1) * 100)
        peer_cagrs.append(((bl / bf) ** (1.0 / span) - 1) * 100)

    growth_stats = _safe_stats(peer_growths)
    cagr_stats = _safe_stats(peer_cagrs)
    growth_pct_rank = _percentile_rank(sorted(peer_growths), person_total_growth_pct)
    cagr_pct_rank = _percentile_rank(sorted(peer_cagrs), person_cagr)

    peer_med_growth = growth_stats["median"] or 0.0
    peer_p75_growth = growth_stats["p75"] or 0.0
    peer_med_cagr = cagr_stats["median"] or 0.0
    peer_p75_cagr = cagr_stats["p75"] or 0.0

    headline = (
        f"Your {person_total_growth_pct:.1f}% total career growth ({person_cagr:.2f}% CAGR) "
        f"ranks at the {fmt_ordinal(growth_pct_rank)} percentile vs peer engineers "
        f"(median peer: {peer_med_growth:.1f}% growth, {peer_med_cagr:.2f}% CAGR)."
    )

    direction = "trailing" if growth_pct_rank < 50 else "leading"
    narrative = (
        f"Over your {person_yrs_span}-year visible window you grew "
        f"{person_total_growth_pct:.1f}% — {direction} the {len(peer_growths)}-peer "
        f"market cohort whose median grew {peer_med_growth:.1f}% (P75 {peer_p75_growth:.1f}%). "
        f"On annualized terms you compound at {person_cagr:.2f}% vs peer median "
        f"{peer_med_cagr:.2f}%."
    )

    if growth_pct_rank < 45:
        tag = "growth_lagging"
    elif growth_pct_rank > 55:
        tag = "growth_leading"
    else:
        tag = "growth_at_norm"

    return {
        "id": "peer_growth",
        "headline": headline,
        "details": {
            "person_total_growth_pct": person_total_growth_pct,
            "person_cagr": person_cagr,
            "person_year_span": person_yrs_span,
            "growth_percentile": growth_pct_rank,
            "cagr_percentile": cagr_pct_rank,
            "peer_median_total_growth": peer_med_growth,
            "peer_p75_total_growth": peer_p75_growth,
            "peer_median_cagr": peer_med_cagr,
            "peer_p75_cagr": peer_p75_cagr,
            "n_peers_with_growth": len(peer_growths),
        },
        "narrative": narrative,
        "data_source": (
            f"Market cohort — {market['level']}. Compared total growth and CAGR against "
            f"{len(peer_growths)} peers' visible windows (own start/end years per peer)."
        ),
        "chart_spec": {
            "type": "bar_compare",
            "data": {
                "categories": ["Total growth %", "CAGR %"],
                "person_values": [person_total_growth_pct, person_cagr],
                "peer_median_values": [peer_med_growth, peer_med_cagr],
                "peer_p75_values": [peer_p75_growth, peer_p75_cagr],
            },
            "title": "Career growth vs peer market cohort",
            "subtitle": f"You vs peer median and P75 (n={len(peer_growths)})",
        },
        "credibility_inputs": {
            "n_peers": len(peer_growths),
            "dollar_impact": 0.0,
            "extremity": abs(growth_pct_rank - 50) / 50.0,
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


def analyze_title_stripped(person_name, person_record, all_records, peer_groups, data) -> dict:
    """Structural site/role-type comparison: where does this person fit in raise patterns?

    NOTE: This replaces the original within-role title-stripped analysis with the
    site x role_type structural comparison validated in PL-033 Step 2.
    """
    yrs = person_record["years"]
    yoy = person_record["yoy"]
    role = peer_groups.get("person_role_type", "non_craft")
    site = (person_record.get("site") or "").strip() or "(no site)"

    person_raises = [v for v in yoy[1:] if v is not None]
    person_avg_raise = (sum(person_raises) / len(person_raises)) if person_raises else 0.0

    # Engineering subjects get an engineering-only structural pattern. Empirically
    # the engineering site rates differ from the non-craft aggregate (St. Lawrence
    # engineers 7.30% > White Plains engineers 6.35%, opposite of the non-craft
    # picture) — so the comparison must filter to engineers when the subject is one.
    is_eng_subject = is_engineering_record(person_record)
    family_filter = is_engineering_record if is_eng_subject else None
    pattern = compute_site_role_raise_pattern(all_records, family_filter=family_filter)
    by_site = pattern["by_site"]
    org_wide = pattern["org_wide"]
    role_key = "non_craft_pct" if role == "non_craft" else "craft_pct"
    n_key = "n_non_craft" if role == "non_craft" else "n_craft"

    site_cohort_avg = by_site.get(site, {}).get(role_key)
    wp_cohort_avg = by_site.get("White Plains", {}).get(role_key)
    org_cohort_avg = org_wide.get(role_key)

    gap_person_vs_site = (
        (person_avg_raise - site_cohort_avg) if site_cohort_avg is not None else None
    )
    gap_site_vs_wp = (
        (site_cohort_avg - wp_cohort_avg)
        if site_cohort_avg is not None and wp_cohort_avg is not None
        else None
    )
    gap_site_vs_org = (
        (site_cohort_avg - org_cohort_avg)
        if site_cohort_avg is not None and org_cohort_avg is not None
        else None
    )

    if is_eng_subject:
        role_label = "engineering"
    elif role == "non_craft":
        role_label = "non-craft"
    else:
        role_label = "craft"

    if site_cohort_avg is not None and wp_cohort_avg is not None:
        # Same-sign gaps stack; opposite-sign gaps partially offset.
        same_direction = (gap_site_vs_wp * gap_person_vs_site) > 0
        connector_word = "another" if same_direction else "but"
        person_dir_word = "above" if gap_person_vs_site > 0 else "below"
        headline = (
            f"{site} {role_label} cohort averages {site_cohort_avg:.1f}% annual raises vs "
            f"White Plains' {wp_cohort_avg:.1f}% — a {gap_site_vs_wp:+.1f} pt site-level "
            f"gap. Within {site}, you average {person_avg_raise:.1f}% — {connector_word} "
            f"{abs(gap_person_vs_site):.1f} pts {person_dir_word} your local cohort."
        )
        if same_direction:
            closing = "The structural and personal gaps compound."
        else:
            closing = (
                "Your personal pattern runs opposite to the site-level gap, "
                "partially offsetting the structural disadvantage."
            )
        narrative = (
            f"First: your site's {role_label} cohort runs "
            f"{abs(gap_site_vs_wp):.1f} pp "
            f"{'below' if gap_site_vs_wp < 0 else 'above'} the White Plains HQ benchmark. "
            f"Second: within your site, your personal {person_avg_raise:.1f}% average is "
            f"{abs(gap_person_vs_site):.1f} pp "
            f"{'below' if gap_person_vs_site < 0 else 'above'} the local {role_label} cohort. "
            f"{closing}"
        )
    else:
        headline = (
            f"{site} {role_label} cohort raise pattern not directly comparable; "
            f"your {len(person_raises)}-year average raise is {person_avg_raise:.1f}%."
        )
        narrative = (
            f"Site-level structural data is incomplete for {site}/{role_label}. "
            f"Personal average raise: {person_avg_raise:.1f}% across "
            f"{len(person_raises)} transitions."
        )

    site_bars: list[dict] = []
    for s, row in by_site.items():
        v = row.get(role_key)
        if v is not None:
            site_bars.append({"site": s, "value": v, "n": row.get(n_key, 0)})
    site_bars.sort(key=lambda r: -r["value"])

    if gap_site_vs_wp is not None and gap_site_vs_wp < -0.3:
        tag = "site_lagging"
    elif gap_site_vs_wp is not None and gap_site_vs_wp > 0.3:
        tag = "site_leading"
    else:
        # For engineering subjects, the small-gap region is "site_competitive" rather
        # than the generic "site_neutral" — names the engineer-specific finding that
        # the site is roughly even with the HQ benchmark.
        tag = "site_competitive" if is_eng_subject else "site_neutral"

    return {
        "id": "title_stripped",
        "headline": headline,
        "details": {
            "person_site": site,
            "person_role_type": role,
            "person_avg_raise_pct": person_avg_raise,
            "site_cohort_avg_pct": site_cohort_avg,
            "white_plains_cohort_avg_pct": wp_cohort_avg,
            "org_cohort_avg_pct": org_cohort_avg,
            "gap_person_vs_site_cohort": gap_person_vs_site,
            "gap_site_vs_wp": gap_site_vs_wp,
            "gap_site_vs_org": gap_site_vs_org,
            "n_person_transitions": len(person_raises),
            "n_site_employees": by_site.get(site, {}).get(n_key, 0),
        },
        "narrative": narrative,
        "data_source": (
            f"compute_site_role_raise_pattern() over "
            f"{'engineering-family records only' if is_eng_subject else 'all NYPA records'}, "
            f"role_type={role}. "
            f"Person classified by latest title; site avg uses all transitions of all "
            f"role-typed employees at the site."
        ),
        "chart_spec": {
            "type": "horizontal_bar",
            "data": {
                "bars": site_bars,
                "person_site": site,
                "person_avg": person_avg_raise,
                "white_plains_value": wp_cohort_avg,
                "org_value": org_cohort_avg,
            },
            "title": f"Average annual raise by site — {role_label} cohort",
            "subtitle": "All NYPA sites; marker shows your personal average",
        },
        "credibility_inputs": {
            "n_peers": by_site.get(site, {}).get(n_key, 0),
            "dollar_impact": 0.0,
            "extremity": abs(gap_site_vs_wp) if gap_site_vs_wp is not None else 0.0,
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


def analyze_specific_ask(person_name, person_record, all_records, peer_groups, data) -> dict:
    """Translate the gap into concrete dollar/% targets (MARKET cohort).

    Honest framing: when the person already exceeds a benchmark, that benchmark
    is reported as 'already above by $X', not as a negative ask. The headline
    surfaces only positive (actionable) targets, plus a forward-looking 5-year
    projection at site vs market raise rates so the report can frame
    'maintenance' asks as well as 'correction' asks.
    """
    market = peer_groups["market"]
    members = market["members"]
    yrs = person_record["years"]
    li = len(yrs) - 1
    current_salary = person_record["base"][li]

    peer_salaries = sorted([float(m["base_latest"]) for m in members
                            if m.get("base_latest")])
    stats = _safe_stats(peer_salaries)
    target_p50 = stats["median"] or float(current_salary)
    target_p75 = stats["p75"] or float(current_salary)
    target_minimum = (current_salary + target_p50) / 2.0

    pct_inc_p50 = ((target_p50 - current_salary) / current_salary * 100.0) if current_salary else 0.0
    pct_inc_p75 = ((target_p75 - current_salary) / current_salary * 100.0) if current_salary else 0.0
    pct_inc_min = ((target_minimum - current_salary) / current_salary * 100.0) if current_salary else 0.0

    above_p50 = pct_inc_p50 < 0
    above_p75 = pct_inc_p75 < 0
    above_min = pct_inc_min < 0

    # ---- Forward-looking 5-year projections (site vs market raise rates) ----
    pattern = compute_site_role_raise_pattern(all_records)
    role = peer_groups.get("person_role_type", "non_craft")
    role_key = "non_craft_pct" if role == "non_craft" else "craft_pct"
    site = (person_record.get("site") or "").strip() or "(no site)"
    site_rate = pattern["by_site"].get(site, {}).get(role_key)
    market_rate = pattern["org_wide"].get(role_key)

    def _project(rate_pct):
        if rate_pct is None:
            return None
        return current_salary * ((1 + rate_pct / 100.0) ** 5)

    fwd_5yr_site = _project(site_rate)
    fwd_5yr_market = _project(market_rate)
    fwd_5yr_gap = (
        (fwd_5yr_market - fwd_5yr_site)
        if fwd_5yr_site is not None and fwd_5yr_market is not None
        else None
    )

    # ---- Headline: only mention positive (actionable) asks ----
    if not above_p50 and not above_p75 and not above_min:
        # All targets are above current — original underpayment framing
        headline = (
            f"To reach peer median: ${target_p50:,.0f} ({pct_inc_p50:+.1f}%). "
            f"To reach peer P75: ${target_p75:,.0f} ({pct_inc_p75:+.1f}%). "
            f"Minimum corrective ask: ${target_minimum:,.0f} ({pct_inc_min:+.1f}%)."
        )
    elif above_p50 and not above_p75:
        # P75 is the only positive target
        excess_med = current_salary - target_p50
        excess_min = current_salary - target_minimum
        headline = (
            f"To reach peer P75: ${target_p75:,.0f} ({pct_inc_p75:+.1f}%). "
            f"Already above peer median by ${excess_med:,.0f} and "
            f"${excess_min:,.0f} above the minimum corrective target."
        )
    else:
        # All benchmarks already exceeded — pivot to maintenance framing
        excess_med = current_salary - target_p50
        excess_p75 = current_salary - target_p75
        headline = (
            f"Currently above all peer benchmarks (peer median by "
            f"${excess_med:,.0f}, P75 by ${excess_p75:,.0f}). "
            f"Forward-looking ask: maintain or exceed current peer P75 position."
        )

    # ---- Alternative framings: each is honest about above-vs-below ----
    if above_p50:
        market_correction = (
            f"Currently above peer median by ${current_salary - target_p50:,.0f}"
        )
    else:
        market_correction = (
            f"Adjust to professional engineering peer median: "
            f"${target_p50:,.0f} ({pct_inc_p50:+.1f}%)"
        )

    if above_p75:
        peer_alignment = "Currently at top quartile or above"
    else:
        peer_alignment = (
            f"Align with top quartile of professional engineering peers: "
            f"${target_p75:,.0f} ({pct_inc_p75:+.1f}%)"
        )

    if above_p50 and above_p75 and above_min:
        retention_aligned = (
            "Maintain peer P75 alignment with sustained above-median raises"
        )
    elif above_min:
        retention_aligned = (
            f"Already above the minimum corrective target by "
            f"${current_salary - target_minimum:,.0f}"
        )
    else:
        retention_aligned = (
            f"Minimum correction toward peer median: "
            f"${target_minimum:,.0f} ({pct_inc_min:+.1f}%)"
        )

    framings = {
        "market_correction": market_correction,
        "peer_alignment": peer_alignment,
        "retention_aligned": retention_aligned,
    }

    # ---- Narrative ----
    if above_p50 and above_p75:
        narrative = (
            f"You sit above all three peer benchmarks. The forward-looking question "
            f"is rate-of-growth, not catch-up. At your site's average raise rate "
            f"({site_rate:.2f}% per year), in 5 years you'd reach "
            f"${fwd_5yr_site:,.0f}; at the org-wide non-craft rate "
            f"({market_rate:.2f}%), ${fwd_5yr_market:,.0f} — a "
            f"${fwd_5yr_gap:,.0f} compounding gap if site lag persists."
            if fwd_5yr_site and fwd_5yr_market else
            f"You sit above all three peer benchmarks. The forward-looking question "
            f"is rate-of-growth, not catch-up."
        )
    elif above_p50:
        narrative = (
            f"Above peer median by ${current_salary - target_p50:,.0f}, "
            f"but {abs(pct_inc_p75):.1f}% below P75. Reaching P75 is the only "
            f"actionable upward target from peer benchmarks. All targets derive "
            f"from the {stats['n']}-peer market cohort."
        )
    else:
        narrative = (
            f"Three framings of the same underlying gap. The minimum correction "
            f"({pct_inc_min:+.1f}%) splits the difference toward peer median; "
            f"reaching the peer median requires {pct_inc_p50:+.1f}%; reaching the P75 "
            f"quartile requires {pct_inc_p75:+.1f}%. All three derive from the "
            f"{stats['n']}-peer market cohort, not invented."
        )

    # ---- Tag ----
    if above_p50 and above_p75 and above_min:
        tag = "ask_maintenance"
    elif pct_inc_p75 > 1:
        tag = "ask_to_reach_p75"
    elif pct_inc_p50 > 1:
        tag = "ask_to_correct_underpayment"
    else:
        tag = "ask_marginal"

    return {
        "id": "specific_ask",
        "headline": headline,
        "details": {
            "current_salary": current_salary,
            "target_p50": target_p50,
            "target_p75": target_p75,
            "target_minimum": target_minimum,
            "pct_increase_p50": pct_inc_p50,
            "pct_increase_p75": pct_inc_p75,
            "pct_increase_min": pct_inc_min,
            "above_p50": above_p50,
            "above_p75": above_p75,
            "above_min": above_min,
            "alternative_framings": framings,
            "n_peers": stats["n"],
            "forward_looking_dollar_5yr": fwd_5yr_site,
            "forward_looking_dollar_5yr_at_market": fwd_5yr_market,
            "forward_looking_5yr_gap": fwd_5yr_gap,
            "site_raise_rate_pct": site_rate,
            "market_raise_rate_pct": market_rate,
        },
        "narrative": narrative,
        "data_source": (
            f"Market cohort — {market['level']}, n={stats['n']}. Targets derived "
            f"from peer median and P75 of latest base salaries. 5-year projections "
            f"compound at site/org non-craft raise rates from "
            f"compute_site_role_raise_pattern()."
        ),
        "chart_spec": {
            "type": "horizontal_bar",
            "data": {
                "labels": ["Current", "Min ask", "Peer median", "Peer P75"],
                "values": [current_salary, target_minimum, target_p50, target_p75],
                "deltas_pct": [0.0, pct_inc_min, pct_inc_p50, pct_inc_p75],
                "above_flags": [False, above_min, above_p50, above_p75],
            },
            "title": "Ask framings — current vs three target levels",
            "subtitle": "Bars labeled 'already above' if current exceeds the benchmark",
        },
        "credibility_inputs": {
            "n_peers": stats["n"],
            "dollar_impact": float(
                (target_p75 - current_salary) if above_p50 else (target_p50 - current_salary)
            ),
            "extremity": abs(pct_inc_p75 if above_p50 else pct_inc_p50) / 10.0,
            "narrative_corroboration_tag": tag,
        },
        "strength": 0.0,
    }


# ============================================================================
# PL-033 Strength Scorer + Selector + Credibility
# ============================================================================
# A good lawyer makes the strongest defensible case while honestly disclosing
# counter-evidence. These functions implement that for the report:
#   - score_argument_strength: numeric ranking of how compelling each finding is
#   - select_top_arguments: case-supporting findings → headline; counter → context
#   - compute_overall_credibility: honest "Strong / Moderate / Weak" verdict
#   - build_report_payload: orchestrator the UI calls

# Tag → direction. Tags not listed default to "neutral".
_CASE_SUPPORTING_TAGS = frozenset({
    "ask_to_reach_p75",
    "ask_to_correct_underpayment",
    "raises_below_norm",
    "site_lagging",
    "growth_lagging",
    "gap_widening",
    "underpaid_vs_market",
})

_NEUTRAL_TAGS = frozenset({
    "raises_at_norm",
    "raises_mixed",
    "growth_at_norm",
    "at_market",
    "site_neutral",
    "site_competitive",
    "ask_marginal",
})

_COUNTER_EVIDENCE_TAGS = frozenset({
    "overpaid_vs_market",
    "no_correction_needed",
    "ask_maintenance",
    "raises_outperforming",
    "growth_leading",
    "site_leading",
})

# Short, audience-facing label for each counter-evidence tag — used in the
# credibility "warnings" list so the report can name what works against the case
# without dumping the full headline.
_TAG_WARNING_TEMPLATES = {
    "overpaid_vs_market": "Currently above peer median",
    "ask_maintenance": "All peer benchmarks already exceeded",
    "raises_outperforming": "Raises consistently above org norm",
    "growth_leading": "Career growth leading peers",
    "site_leading": "Site raise pattern leads HQ benchmark",
    "no_correction_needed": "No correction needed by peer benchmarks",
}


def _tag_direction(tag: str) -> str:
    if tag in _CASE_SUPPORTING_TAGS:
        return "case_supporting"
    if tag in _COUNTER_EVIDENCE_TAGS:
        return "counter_evidence"
    return "neutral"


def score_argument_strength(analysis_result: dict, person_record: dict,
                            peer_groups: dict) -> dict:
    """Score how compelling a single analysis is.

    raw_score = (dollar_score + sample_score + extremity_score) * (1 + direction_modifier)

    where direction_modifier is +1 / 0 / -0.5 for case_supporting / neutral /
    counter_evidence — so case-supporting analyses score ~2x higher than the
    same-magnitude counter-evidence.
    """
    ci = analysis_result["credibility_inputs"]
    dollar_impact = abs(float(ci.get("dollar_impact", 0) or 0))
    n_peers = max(int(ci.get("n_peers", 0) or 0), 0)
    extremity = max(float(ci.get("extremity", 0) or 0), 0.0)
    tag = ci.get("narrative_corroboration_tag", "")

    dollar_score = min(math.log10(max(dollar_impact, 1.0)), 5.0)
    sample_score = min(math.log10(max(n_peers, 1)), 3.0)
    extremity_score = min(extremity, 3.0)

    direction = _tag_direction(tag)
    if direction == "case_supporting":
        modifier = 1.0
    elif direction == "counter_evidence":
        modifier = -0.5
    else:
        modifier = 0.0

    component_sum = dollar_score + sample_score + extremity_score
    raw_score = component_sum * (1.0 + modifier)

    return {
        "raw_score": raw_score,
        "components": {
            "dollar": dollar_score,
            "sample": sample_score,
            "extremity": extremity_score,
            "direction_modifier": modifier,
            "component_sum": component_sum,
        },
        "direction": direction,
    }


def select_top_arguments(scored_analyses: list[dict],
                         max_count: int = 5, min_count: int = 3) -> dict:
    """Pick case-supporting findings for the headline; route counter to context.

    Selection rules (priority order):
      1. ALWAYS include specific_ask (the punchline).
      2. Add top scored case-supporting analyses up to max_count total.
      3. If still below min_count, pad with neutrals (highest-strength first).
      4. Counter-evidence is never picked — it goes to context_arguments.

    Within both lists, ordering is by strength desc.
    """
    by_id = {a["id"]: a for a in scored_analyses}

    case_supp_sorted = sorted(
        (a for a in scored_analyses if a.get("score_direction") == "case_supporting"),
        key=lambda a: -a["strength"],
    )
    neutrals_sorted = sorted(
        (a for a in scored_analyses if a.get("score_direction") == "neutral"),
        key=lambda a: -a["strength"],
    )

    selected: list[dict] = []
    selected_ids: set[str] = set()

    if "specific_ask" in by_id:
        selected.append(by_id["specific_ask"])
        selected_ids.add("specific_ask")

    for a in case_supp_sorted:
        if len(selected) >= max_count:
            break
        if a["id"] not in selected_ids:
            selected.append(a)
            selected_ids.add(a["id"])

    if len(selected) < min_count:
        for a in neutrals_sorted:
            if len(selected) >= min_count:
                break
            if a["id"] not in selected_ids:
                selected.append(a)
                selected_ids.add(a["id"])

    case_arguments = sorted(selected, key=lambda a: -a["strength"])
    context_arguments = sorted(
        [a for a in scored_analyses if a["id"] not in selected_ids],
        key=lambda a: -a["strength"],
    )

    n_case_supp_in_top = sum(
        1 for a in case_arguments if a.get("score_direction") == "case_supporting"
    )
    n_padded = len(case_arguments) - n_case_supp_in_top
    n_context = len(context_arguments)

    summary_parts = [
        f"Selected {n_case_supp_in_top} case-supporting argument"
        f"{'s' if n_case_supp_in_top != 1 else ''}"
    ]
    if n_padded:
        summary_parts.append(
            f"{n_padded} neutral argument{'s' if n_padded != 1 else ''} "
            f"included as padding"
        )
    if n_context:
        summary_parts.append(
            f"{n_context} finding{'s' if n_context != 1 else ''} shown as context"
        )
    selection_summary = ". ".join(summary_parts) + "."

    return {
        "case_arguments": case_arguments,
        "context_arguments": context_arguments,
        "selection_summary": selection_summary,
    }


def compute_overall_credibility(top_arguments: list[dict], peer_groups: dict,
                                scored_analyses: list[dict]) -> dict:
    """Honest credibility verdict for the report header.

    Levels:
      STRONG   — market_n>=30 AND case_count>=3 AND has_dollar_anchor
                 AND avg_case_strength>4.0
      MODERATE — market_n>=15 AND case_count>=2
      WEAK     — anything below
    """
    market_n = peer_groups["market"]["n"] if peer_groups.get("market") else 0

    case_supp_all = [
        a for a in scored_analyses if a.get("score_direction") == "case_supporting"
    ]
    counter_all = [
        a for a in scored_analyses if a.get("score_direction") == "counter_evidence"
    ]
    case_count = len(case_supp_all)
    counter_count = len(counter_all)

    avg_case_strength = (
        sum(a["strength"] for a in case_supp_all) / len(case_supp_all)
        if case_supp_all else 0.0
    )

    has_dollar_anchor = any(
        abs(float(a["credibility_inputs"].get("dollar_impact", 0) or 0)) > 5000
        for a in case_supp_all
    )

    tag_counts: dict[str, int] = {}
    for a in case_supp_all:
        t = a["credibility_inputs"].get("narrative_corroboration_tag", "")
        tag_counts[t] = tag_counts.get(t, 0) + 1
    has_corroboration = any(c >= 2 for c in tag_counts.values())

    if (market_n >= 30 and case_count >= 3
            and has_dollar_anchor and avg_case_strength > 4.0):
        level, color = "strong", "green"
    elif market_n >= 15 and case_count >= 2:
        level, color = "moderate", "amber"
    else:
        level, color = "weak", "red"

    if level == "strong":
        parts = [
            f"{case_count} case-supporting findings backed by a "
            f"{market_n}-peer market cohort",
        ]
        if has_dollar_anchor:
            parts.append("a concrete dollar anchor")
        if has_corroboration:
            parts.append("multiple analyses corroborating the same signal")
        rationale = "Strong case: " + ", with ".join(parts) + "."
    elif level == "moderate":
        parts = [
            f"{case_count} case-supporting finding{'s' if case_count != 1 else ''} "
            f"from a {market_n}-peer market cohort"
        ]
        if counter_count > 0:
            parts.append(
                f"{counter_count} counter-evidence finding"
                f"{'s' if counter_count != 1 else ''} that should be acknowledged"
            )
        rationale = "Moderate case: " + "; ".join(parts) + "."
    else:
        parts = []
        if market_n < 15:
            parts.append(f"market cohort too small (n={market_n})")
        if case_count == 0:
            parts.append("no case-supporting findings")
        elif case_count < 2:
            parts.append("only 1 case-supporting finding")
        rationale = (
            "Weak case: " + "; ".join(parts) + "."
            if parts else "Weak case: insufficient signal."
        )

    warnings: list[str] = []
    for a in counter_all:
        tag = a["credibility_inputs"].get("narrative_corroboration_tag", "")
        short = _TAG_WARNING_TEMPLATES.get(tag, tag.replace("_", " "))
        warnings.append(f"Counter-evidence ({a['id']}): {short}")

    return {
        "level": level,
        "color": color,
        "rationale": rationale,
        "warnings": warnings,
        "details": {
            "market_n": market_n,
            "case_count": case_count,
            "counter_count": counter_count,
            "avg_case_strength": avg_case_strength,
            "has_dollar_anchor": has_dollar_anchor,
            "has_corroboration": has_corroboration,
        },
    }


def build_report_payload(person_name: str, person_record: dict,
                         all_records: dict, data: dict) -> dict:
    """Top-level orchestrator — runs the whole PL-033 pipeline for one person."""
    peer_groups = resolve_peer_group(person_name, person_record, all_records)
    structural = compute_site_role_raise_pattern(all_records)

    analyses = [
        analyze_peer_position(person_name, person_record, all_records, peer_groups, data),
        analyze_yoy_raise_pattern(person_name, person_record, all_records, peer_groups, data),
        analyze_cumulative_gap(person_name, person_record, all_records, peer_groups, data),
        analyze_peer_growth(person_name, person_record, all_records, peer_groups, data),
        analyze_title_stripped(person_name, person_record, all_records, peer_groups, data),
        analyze_specific_ask(person_name, person_record, all_records, peer_groups, data),
    ]

    for a in analyses:
        sr = score_argument_strength(a, person_record, peer_groups)
        a["strength"] = sr["raw_score"]
        a["score_direction"] = sr["direction"]
        a["score_components"] = sr["components"]

    selection = select_top_arguments(analyses)
    credibility = compute_overall_credibility(
        selection["case_arguments"], peer_groups, analyses,
    )

    return {
        "person_name": person_name,
        "person_record": person_record,
        "peer_groups": peer_groups,
        "structural_pattern": structural,
        "all_analyses": analyses,
        "case_arguments": selection["case_arguments"],
        "context_arguments": selection["context_arguments"],
        "selection_summary": selection["selection_summary"],
        "credibility": credibility,
        "generated_date": date.today().isoformat(),
    }


# ============================================================================
# PL-033 Report Renderers (chart_spec → plotly figure, payload → markdown)
# ============================================================================

def _figure_from_chart_spec(spec: dict) -> go.Figure:
    """Dispatch a chart_spec dict to a plotly figure based on spec['type']."""
    t = spec.get("type")
    d = spec.get("data", {})
    if t == "histogram":
        return _fig_histogram_with_marker(d)
    if t == "line_band":
        return _fig_line_with_band(d)
    if t == "dual_line":
        return _fig_dual_line(d)
    if t == "bar_compare":
        return _fig_bar_compare(d)
    if t == "horizontal_bar":
        return _fig_horizontal_bar(d)
    return go.Figure()


def _fig_histogram_with_marker(d: dict) -> go.Figure:
    """Histogram of peer_salaries with a vertical line at person_salary."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=d.get("peer_salaries", []),
        nbinsx=30,
        marker=dict(color=rgba(LIGHT_BLUE, 0.7), line=dict(color=BLUE, width=0.5)),
        hovertemplate="$%{x:,.0f}<br>%{y} peers<extra></extra>",
        name="Peers",
    ))
    person_x = d.get("person_salary")
    if person_x is not None:
        fig.add_vline(
            x=person_x, line=dict(color=CORAL, width=3),
            annotation_text=f"You: ${person_x:,.0f}",
            annotation_position="top right",
            annotation=dict(font=dict(color=CORAL, size=11)),
        )
    median = d.get("median")
    if median is not None:
        fig.add_vline(
            x=median, line=dict(color=GREEN, width=2, dash="dash"),
            annotation_text=f"Median: ${median:,.0f}",
            annotation_position="bottom left",
            annotation=dict(font=dict(color=GREEN, size=10)),
        )
    apply_layout(fig, height=320, show_legend=False, y_dollars=False)
    fig.update_xaxes(tickprefix="$", tickformat=",")
    return fig


def _fig_line_with_band(d: dict) -> go.Figure:
    """Person's raise line with org P25-P75 shaded band + dashed median line."""
    fig = go.Figure()
    x = d.get("year_labels", [])
    p25 = d.get("org_p25_pcts", [])
    p75 = d.get("org_p75_pcts", [])
    median = d.get("org_median_pcts", [])
    person = d.get("person_pcts", [])

    if x and p25 and p75:
        fig.add_trace(go.Scatter(
            x=x, y=p75, mode="lines", line=dict(color="rgba(0,0,0,0)"),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=x, y=p25, mode="lines", fill="tonexty",
            fillcolor=rgba(LIGHT_BLUE, 0.18),
            line=dict(color="rgba(0,0,0,0)"),
            name="Org P25–P75", showlegend=True,
            hovertemplate="<b>%{x}</b><br>P25: %{y:.2f}%<extra></extra>",
        ))
    if x and median:
        fig.add_trace(go.Scatter(
            x=x, y=median, mode="lines",
            line=dict(color=BLUE, width=1.5, dash="dash"),
            name="Org median",
            hovertemplate="<b>%{x}</b><br>Org median: %{y:.2f}%<extra></extra>",
        ))
    if x and person:
        fig.add_trace(go.Scatter(
            x=x, y=person, mode="lines+markers",
            line=dict(color=CORAL, width=2.5),
            marker=dict(size=8, color=CORAL),
            name="You",
            hovertemplate="<b>%{x}</b><br>You: %{y:.2f}%<extra></extra>",
        ))
    apply_layout(fig, height=320, show_legend=True, y_dollars=False)
    fig.update_yaxes(ticksuffix="%")
    return fig


def _fig_dual_line(d: dict) -> go.Figure:
    """Two salary trajectories: actual vs counter-factual."""
    fig = go.Figure()
    yrs = d.get("years", [])
    actual = d.get("actual", [])
    cf = d.get("counter_factual", [])
    if yrs and actual:
        fig.add_trace(go.Scatter(
            x=yrs, y=actual, mode="lines+markers",
            line=dict(color=CORAL, width=2.5),
            marker=dict(size=7, color=CORAL),
            name="Actual",
            hovertemplate="<b>%{x}</b><br>Actual: $%{y:,.0f}<extra></extra>",
        ))
    if yrs and cf:
        fig.add_trace(go.Scatter(
            x=yrs, y=cf, mode="lines+markers",
            line=dict(color=BLUE, width=2, dash="dash"),
            marker=dict(size=6, color=BLUE),
            name="If org-median raise each year",
            hovertemplate="<b>%{x}</b><br>Counter-factual: $%{y:,.0f}<extra></extra>",
        ))
    apply_layout(fig, height=320, show_legend=True, y_dollars=True)
    return fig


def _fig_bar_compare(d: dict) -> go.Figure:
    """Grouped bars: person vs peer median vs P75 across categories."""
    cats = d.get("categories", [])
    p_vals = d.get("person_values", [])
    med_vals = d.get("peer_median_values", [])
    p75_vals = d.get("peer_p75_values", [])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cats, y=p_vals, name="You",
        marker=dict(color=CORAL),
        text=[f"{v:.1f}%" for v in p_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>You: %{y:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=cats, y=med_vals, name="Peer median",
        marker=dict(color=BLUE),
        text=[f"{v:.1f}%" for v in med_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Peer median: %{y:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=cats, y=p75_vals, name="Peer P75",
        marker=dict(color=LAVENDER),
        text=[f"{v:.1f}%" for v in p75_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Peer P75: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(barmode="group")
    apply_layout(fig, height=320, show_legend=True, y_dollars=False)
    fig.update_yaxes(ticksuffix="%")
    return fig


def _fig_horizontal_bar(d: dict) -> go.Figure:
    """Two flavors:
      - Site comparison: bars=[{site,value,n}], plus person_avg marker
      - Ask framing: labels + values + above_flags (already-exceeded benchmarks)
    """
    if "bars" in d:
        rows = d.get("bars", [])
        sites = [r["site"] for r in rows]
        vals = [r["value"] for r in rows]
        ns = [r.get("n") for r in rows]
        person_site = d.get("person_site")
        colors = [CORAL if s == person_site else LIGHT_BLUE for s in sites]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=sites, x=vals, orientation="h",
            marker=dict(color=colors),
            text=[f"{v:.1f}% (n={n})" if n else f"{v:.1f}%"
                  for v, n in zip(vals, ns)],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Avg raise: %{x:.2f}%<extra></extra>",
            showlegend=False,
        ))
        person_avg = d.get("person_avg")
        if person_avg is not None:
            fig.add_vline(
                x=person_avg, line=dict(color=AMBER, width=2.5, dash="dash"),
                annotation_text=f"Your personal avg: {person_avg:.1f}%",
                annotation_position="top right",
                annotation=dict(font=dict(color=AMBER, size=11)),
            )
        wp_v = d.get("white_plains_value")
        if wp_v is not None and "White Plains" not in sites:
            fig.add_vline(
                x=wp_v, line=dict(color=GREEN, width=1.5, dash="dot"),
                annotation_text=f"WP HQ: {wp_v:.1f}%",
                annotation_position="bottom right",
                annotation=dict(font=dict(color=GREEN, size=10)),
            )
        apply_layout(fig, height=max(280, 28 * len(sites) + 80),
                     show_legend=False, y_dollars=False)
        fig.update_xaxes(ticksuffix="%")
        fig.update_yaxes(autorange="reversed")
        return fig

    labels = d.get("labels", [])
    values = d.get("values", [])
    deltas = d.get("deltas_pct", [])
    above = d.get("above_flags", [False] * len(labels))
    colors = []
    for i, lbl in enumerate(labels):
        if i == 0:
            colors.append(CORAL)  # Current
        elif above[i]:
            colors.append(rgba(GREEN, 0.55))  # already exceeded
        else:
            colors.append(BLUE)  # actionable target

    text_labels = []
    for i, (v, dlt) in enumerate(zip(values, deltas)):
        if i == 0:
            text_labels.append(f"${v:,.0f}")
        elif above[i]:
            text_labels.append(f"${v:,.0f} (already above)")
        else:
            text_labels.append(f"${v:,.0f} ({dlt:+.1f}%)")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=values, orientation="h",
        marker=dict(color=colors),
        text=text_labels,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
        showlegend=False,
    ))
    apply_layout(fig, height=max(240, 40 * len(labels) + 80),
                 show_legend=False, y_dollars=False)
    fig.update_xaxes(tickprefix="$", tickformat=",")
    fig.update_yaxes(autorange="reversed")
    return fig


def _build_executive_summary(payload: dict) -> str:
    """Synthesize a 1-paragraph executive summary from case + counter-evidence."""
    case = payload["case_arguments"]
    context = payload["context_arguments"]
    counter = [a for a in context if a.get("score_direction") == "counter_evidence"]

    ask = next((a for a in case if a["id"] == "specific_ask"), None)
    case_supp = [a for a in case if a.get("score_direction") == "case_supporting"
                 and a["id"] != "specific_ask"]

    parts: list[str] = []
    if ask:
        parts.append(ask["headline"])
    for a in case_supp[:2]:
        parts.append(a["headline"])

    if counter:
        n = len(counter)
        parts.append(
            f"Counter-evidence acknowledged: {n} finding{'s' if n != 1 else ''} "
            f"point{'s' if n == 1 else ''} the other way (see Context section)."
        )
    return " ".join(parts)


def _peer_composition_summary(peer_groups: dict) -> dict:
    """Anonymized counts for the personal-view peer composition section."""
    def _summarize(cohort: dict) -> dict:
        members = cohort.get("members", [])
        title_counts: dict[str, int] = {}
        site_counts: dict[str, int] = {}
        dept_counts: dict[str, int] = {}
        for m in members:
            t = m.get("title_latest") or "(unknown)"
            title_counts[t] = title_counts.get(t, 0) + 1
            s = m.get("site") or "(no site)"
            site_counts[s] = site_counts.get(s, 0) + 1
            d_ = m.get("dept_latest") or "(unknown)"
            dept_counts[d_] = dept_counts.get(d_, 0) + 1
        return {
            "level": cohort.get("level"),
            "n": cohort.get("n"),
            "filter_description": cohort.get("filter_description"),
            "titles": sorted(title_counts.items(), key=lambda kv: -kv[1]),
            "sites": sorted(site_counts.items(), key=lambda kv: -kv[1]),
            "departments": sorted(dept_counts.items(), key=lambda kv: -kv[1]),
        }
    return {
        "local": _summarize(peer_groups.get("local", {})),
        "market": _summarize(peer_groups.get("market", {})),
        "person_role_type": peer_groups.get("person_role_type"),
    }


def generate_report_markdown(payload: dict) -> str:
    """Generate the full report as Markdown text.

    Excludes peer composition (personal-view only). Charts replaced with text
    descriptions of underlying numbers.
    """
    rec = payload["person_record"]
    pg = payload["peer_groups"]
    cred = payload["credibility"]
    case = payload["case_arguments"]
    context = payload["context_arguments"]
    counter = [a for a in context if a.get("score_direction") == "counter_evidence"]
    name = payload["person_name"]
    today = payload["generated_date"]
    role_label = "non-craft" if pg["person_role_type"] == "non_craft" else "craft"

    lines: list[str] = []
    lines.append(f"# Compensation Analysis — {name}")
    lines.append("")
    lines.append("*Internal market analysis based on public NYPA payroll data "
                 "(data.ny.gov, 2017–2024).*")
    lines.append("")
    lines.append(f"**Generated:** {today}")
    lines.append("")
    lines.append(f"**Credibility:** **{cred['level'].upper()}** — {cred['rationale']}")
    if cred["warnings"]:
        lines.append("")
        lines.append("**Counter-evidence acknowledged:**")
        for w in cred["warnings"]:
            lines.append(f"- {w}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(_build_executive_summary(payload))
    lines.append("")

    # Subject snapshot
    lines.append("## Subject")
    lines.append("")
    lines.append(f"- **Latest base salary:** ${rec['base'][-1]:,} ({rec['years'][-1]})")
    lines.append(f"- **Site:** {rec.get('site') or '(none)'}")
    lines.append(f"- **Latest title:** {rec['titles'][-1]}")
    lines.append(f"- **Tenure visible:** {rec['years'][0]} → {rec['years'][-1]} "
                 f"({rec['years'][-1] - rec['years'][0]} years)")
    lines.append(f"- **Role classification:** {role_label}")
    lines.append("")

    # The case
    lines.append("## The Case")
    lines.append("")
    for a in case:
        lines.append(f"### {a['headline']}")
        lines.append("")
        lines.append(a["narrative"])
        lines.append("")
        lines.append(f"<sub>Source: {a['data_source']}</sub>")
        lines.append("")

    # Counter-evidence / context
    if counter:
        lines.append("## Context — Findings That Don't Strongly Support the Case")
        lines.append("")
        lines.append(
            "The following findings run counter to the case above and are disclosed "
            "for transparency."
        )
        lines.append("")
        for a in counter:
            lines.append(f"**{a['headline']}**")
            lines.append("")
            lines.append(a["narrative"])
            lines.append("")

    # Career documentation
    lines.append("## Career Documentation")
    lines.append("")
    lines.append("### Salary Trajectory")
    lines.append("")
    lines.append("| Year | Title | Group | Base | YoY % |")
    lines.append("|---|---|---|---:|---:|")
    for i, y in enumerate(rec["years"]):
        yoy_v = rec["yoy"][i]
        yoy_str = f"{yoy_v:.1f}%" if yoy_v is not None else "—"
        lines.append(
            f"| {y} | {rec['titles'][i]} | {rec['groups'][i]} | "
            f"${rec['base'][i]:,} | {yoy_str} |"
        )
    lines.append("")

    # The ask
    ask = next((a for a in case if a["id"] == "specific_ask"), None)
    if ask:
        det = ask["details"]
        lines.append("## The Ask")
        lines.append("")
        lines.append(ask["narrative"])
        lines.append("")
        lines.append("**Three framings:**")
        lines.append("")
        framings = det.get("alternative_framings", {})
        for k in ("market_correction", "peer_alignment", "retention_aligned"):
            if k in framings:
                lines.append(f"- **{k.replace('_', ' ').title()}:** {framings[k]}")
        lines.append("")
        site_rate = det.get("site_raise_rate_pct")
        market_rate = det.get("market_raise_rate_pct")
        f5_site = det.get("forward_looking_dollar_5yr")
        f5_mkt = det.get("forward_looking_dollar_5yr_at_market")
        f5_gap = det.get("forward_looking_5yr_gap")
        if f5_site is not None and f5_mkt is not None:
            lines.append("**Forward-looking 5-year projection:**")
            lines.append("")
            lines.append(f"- At your site's current raise rate "
                         f"({site_rate:.2f}% per year): **${f5_site:,.0f}**")
            lines.append(f"- At the org-wide non-craft raise rate "
                         f"({market_rate:.2f}% per year): **${f5_mkt:,.0f}**")
            lines.append(f"- Compounding gap if site lag persists: **${f5_gap:,.0f}**")
            lines.append("")

    # Methodology
    lines.append("## Methodology and Data Sources")
    lines.append("")
    lines.append("**Data source:** NYPA payroll records on data.ny.gov, "
                 "spanning 2017–2024. All figures are public information.")
    lines.append("")
    lines.append("**Peer cohorts:**")
    lines.append("")
    lines.append(f"- *Local cohort* — {pg['local']['filter_description']}")
    lines.append(f"- *Market cohort* — {pg['market']['filter_description']}")
    lines.append("")
    lines.append("**Calculation methodology:**")
    lines.append("")
    lines.append("- Annual raises measured as same-employee year-over-year base-salary change.")
    lines.append("- Org median / P25 / P75 computed across all employees present in both years "
                 "of each transition.")
    lines.append("- Counter-factual trajectory compounds the org-median raise from the "
                 "starting year forward.")
    lines.append("- Career growth measured as total % change and CAGR over each peer's "
                 "visible window (own start/end years per peer).")
    lines.append("- Site × role-type raise pattern uses the latest title to classify each "
                 "employee, then averages all their year transitions.")
    lines.append("- Argument strength scored from log-scaled dollar impact, sample size, and "
                 "statistical extremity, weighted by direction (case-supporting vs counter-evidence).")
    lines.append("")
    lines.append("**Limitations:**")
    lines.append("")
    lines.append("- Peer-cohort matching uses title-keyword overlap; subject-matter expertise "
                 "and project responsibility are not encoded.")
    lines.append("- Public payroll data does not include performance reviews, internal "
                 "promotions in flight, or planned increases.")
    lines.append("- Raise rates can be skewed by promotions and re-classifications.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Source: data.ny.gov · NYPA payroll records · "
                 f"Generated {today}*")
    lines.append("")
    return "\n".join(lines)


_CRED_PILL_STYLE = {
    "strong": f"background:#EAF3DE;color:#173404;border:1px solid {GREEN};",
    "moderate": f"background:#FAEEDA;color:#412402;border:1px solid {AMBER};",
    "weak": f"background:#FCEBEB;color:#791F1F;border:1px solid #C04848;",
}


def render_compensation_report(payload: dict) -> None:
    """Render the full PL-033 report inline. Streamlit-side only."""
    name = payload["person_name"]
    rec = payload["person_record"]
    pg = payload["peer_groups"]
    cred = payload["credibility"]
    today = payload["generated_date"]

    # ---- SECTION 1: Controls ----
    ctrl_left, ctrl_mid, ctrl_right = st.columns([2, 2, 3])
    with ctrl_left:
        show_peer_details = st.checkbox(
            "Show peer details",
            value=False,
            key=f"_pl033_peerdetail_{name}",
            help=(
                "Personal view — verify the algorithm picked the right peer group. "
                "Anonymized counts only. Not included in the markdown export."
            ),
        )
    with ctrl_mid:
        last_token = name.split()[-1].replace("'", "").replace(" ", "_")
        md_filename = f"compensation_analysis_{last_token}_{today}.md"
        md_text = generate_report_markdown(payload)
        st.download_button(
            "⬇  Download as Markdown",
            data=md_text,
            file_name=md_filename,
            mime="text/markdown",
            key=f"_pl033_dl_{name}",
            help="Excludes the personal-view peer composition section.",
        )
    with ctrl_right:
        pill_style = _CRED_PILL_STYLE.get(cred["level"], _CRED_PILL_STYLE["weak"])
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<span style='{pill_style};padding:4px 12px;border-radius:14px;"
            f"font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;'>"
            f"Credibility: {cred['level']}</span>"
            f"<span style='font-size:11px;color:#666;'>{cred['rationale']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ---- SECTION 2: Report Header ----
    st.markdown(f"# Compensation Analysis — {name}")
    st.markdown(
        "<div style='color:#888;font-size:12px;font-style:italic;margin-top:-8px;'>"
        "Internal market analysis based on public NYPA payroll data (data.ny.gov, 2017–2024)."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='color:#666;font-size:11px;margin-bottom:8px;'>"
        f"Generated: {today}</div>",
        unsafe_allow_html=True,
    )

    if cred["warnings"]:
        warnings_html = "<ul style='margin:4px 0 0 18px;padding:0;font-size:11px;color:#791F1F;'>"
        for w in cred["warnings"]:
            warnings_html += f"<li>{w}</li>"
        warnings_html += "</ul>"
        st.markdown(
            f"<div class='callout' style='border-left-color:#C04848;background:#FCEBEB;"
            f"color:#791F1F;'><b>Counter-evidence acknowledged:</b>{warnings_html}</div>",
            unsafe_allow_html=True,
        )

    # ---- SECTION 3: Executive Summary ----
    st.markdown("### Executive Summary")
    summary = _build_executive_summary(payload)
    st.markdown(
        f"<div class='callout' style='border-left-color:{BLUE};background:#F0F6FB;"
        f"color:#0C447C;font-size:12px;'>{summary}</div>",
        unsafe_allow_html=True,
    )

    # ---- SECTION 4: The Case ----
    st.markdown("### The Case")
    for i, a in enumerate(payload["case_arguments"]):
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:#111;margin-top:14px;"
            f"margin-bottom:6px;'>{i + 1}. {a['headline']}</div>",
            unsafe_allow_html=True,
        )
        spec = a.get("chart_spec") or {}
        if spec:
            fig = _figure_from_chart_spec(spec)
            chart_card(
                spec.get("title", ""),
                fig,
                key=f"pl033-case-{a['id']}-{name}",
                subtitle=spec.get("subtitle", ""),
            )
        st.markdown(
            f"<div style='font-size:12px;color:#333;line-height:1.55;margin-top:6px;'>"
            f"{a['narrative']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:10px;color:#999;margin-top:4px;margin-bottom:10px;'>"
            f"Source: {a['data_source']}</div>",
            unsafe_allow_html=True,
        )

    # ---- SECTION 5: Context / Counter-evidence ----
    counter = [c for c in payload["context_arguments"]
               if c.get("score_direction") == "counter_evidence"]
    if counter:
        st.markdown("### Context — Findings That Don't Strongly Support the Case")
        st.markdown(
            "<div style='font-size:11px;color:#666;font-style:italic;'>"
            "These findings run counter to the case above and are disclosed for transparency."
            "</div>",
            unsafe_allow_html=True,
        )
        for a in counter:
            st.markdown(
                f"<div style='border-left:2px solid #aaa;padding-left:10px;margin-top:10px;'>"
                f"<div style='font-size:12px;font-weight:600;color:#444;'>{a['headline']}</div>"
                f"<div style='font-size:11px;color:#555;margin-top:3px;line-height:1.5;'>"
                f"{a['narrative']}</div></div>",
                unsafe_allow_html=True,
            )

    # ---- SECTION 6: Career Documentation ----
    st.markdown("### Career Documentation")
    yrs = rec["years"]
    base = rec["base"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yrs, y=base, mode="lines+markers",
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=8, color=BLUE),
        name="Base salary",
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    apply_layout(fig, height=280, show_legend=False, y_dollars=True)
    chart_card("Salary trajectory", fig, key=f"pl033-traj-{name}",
               subtitle=f"{yrs[0]}–{yrs[-1]} base salary")
    title_rows = []
    for i, y in enumerate(yrs):
        yoy_v = rec["yoy"][i]
        title_rows.append({
            "Year": y,
            "Title": rec["titles"][i],
            "Group": rec["groups"][i],
            "Base": base[i],
            "YoY %": yoy_v,
        })
    df_titles = pd.DataFrame(title_rows)
    st.dataframe(
        df_titles,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Base": st.column_config.NumberColumn(format="$%d"),
            "YoY %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    # ---- SECTION 7: The Ask ----
    ask = next((a for a in payload["case_arguments"] if a["id"] == "specific_ask"), None)
    if ask:
        det = ask["details"]
        st.markdown("### The Ask")
        st.markdown(
            f"<div style='font-size:12px;color:#333;line-height:1.55;'>"
            f"{ask['narrative']}</div>",
            unsafe_allow_html=True,
        )
        framings = det.get("alternative_framings", {})
        framing_html = "<div style='margin-top:8px;'>"
        for k, label in (("market_correction", "Market correction"),
                         ("peer_alignment", "Peer alignment"),
                         ("retention_aligned", "Retention-aligned")):
            if k in framings:
                framing_html += (
                    f"<div style='padding:6px 0;border-bottom:1px solid #eee;font-size:12px;'>"
                    f"<span style='font-weight:600;color:#555;'>{label}:</span> "
                    f"<span style='color:#333;'>{framings[k]}</span></div>"
                )
        framing_html += "</div>"
        st.markdown(framing_html, unsafe_allow_html=True)

        f5_site = det.get("forward_looking_dollar_5yr")
        f5_mkt = det.get("forward_looking_dollar_5yr_at_market")
        f5_gap = det.get("forward_looking_5yr_gap")
        site_rate = det.get("site_raise_rate_pct")
        market_rate = det.get("market_raise_rate_pct")
        if f5_site is not None and f5_mkt is not None:
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card("5-yr at site rate", fmt_dollar(f5_site),
                            sub=f"{site_rate:.2f}%/yr", color="amber")
            with c2:
                metric_card("5-yr at org rate", fmt_dollar(f5_mkt),
                            sub=f"{market_rate:.2f}%/yr", color="green")
            with c3:
                metric_card("5-yr compounding gap", fmt_dollar(f5_gap, signed=True),
                            sub="if site lag persists", color="coral")

    # ---- SECTION 8: Methodology ----
    with st.expander("Methodology and Data Sources", expanded=False):
        st.markdown(
            "**Data source:** NYPA payroll records on data.ny.gov, spanning 2017–2024. "
            "All figures are public information."
        )
        st.markdown("**Peer cohorts:**")
        st.markdown(f"- *Local cohort* — {pg['local']['filter_description']}")
        st.markdown(f"- *Market cohort* — {pg['market']['filter_description']}")
        st.markdown("**Calculation methodology:**")
        st.markdown(
            "- Annual raises measured as same-employee year-over-year base-salary change.\n"
            "- Org median / P25 / P75 computed across all employees present in both years "
            "of each transition.\n"
            "- Counter-factual trajectory compounds the org-median raise from the starting "
            "year forward.\n"
            "- Career growth measured as total % change and CAGR over each peer's visible "
            "window (own start/end years per peer).\n"
            "- Site × role-type raise pattern uses the latest title to classify each "
            "employee, then averages all their year transitions.\n"
            "- Argument strength scored from log-scaled dollar impact, sample size, and "
            "statistical extremity, weighted by direction (case-supporting vs counter-evidence)."
        )
        st.markdown("**Limitations:**")
        st.markdown(
            "- Peer-cohort matching uses title-keyword overlap; subject-matter expertise and "
            "project responsibility are not encoded.\n"
            "- Public payroll data does not include performance reviews, internal promotions "
            "in flight, or planned increases.\n"
            "- Raise rates can be skewed by promotions and re-classifications."
        )

    # ---- SECTION 9: Peer Composition (only when toggle is ON) ----
    if show_peer_details:
        st.markdown("### Peer Group Composition — Personal View")
        st.markdown(
            "<div style='background:#FCEBEB;color:#791F1F;border-left:3px solid #C04848;"
            "padding:6px 10px;font-size:11px;border-radius:6px;margin-bottom:8px;'>"
            "<b>Personal view only:</b> this section is for verification and is "
            "<b>excluded</b> from the markdown export. Anonymized counts only — no names."
            "</div>",
            unsafe_allow_html=True,
        )
        composition = _peer_composition_summary(pg)
        for label, key in (("Local cohort", "local"), ("Market cohort", "market")):
            cohort = composition[key]
            st.markdown(f"#### {label}")
            st.markdown(
                f"<div style='font-size:12px;color:#444;'>"
                f"<b>{cohort['level']}</b> · n={cohort['n']}<br>"
                f"<i>{cohort['filter_description']}</i></div>",
                unsafe_allow_html=True,
            )
            t_col, s_col = st.columns(2)
            with t_col:
                st.markdown(
                    "<div style='font-size:11px;font-weight:600;color:#888;"
                    "text-transform:uppercase;letter-spacing:.05em;margin-top:8px;'>"
                    "Top titles</div>",
                    unsafe_allow_html=True,
                )
                top_titles = cohort["titles"][:8]
                if top_titles:
                    df_t = pd.DataFrame(top_titles, columns=["Title", "n"])
                    st.dataframe(df_t, hide_index=True, use_container_width=True)
            with s_col:
                st.markdown(
                    "<div style='font-size:11px;font-weight:600;color:#888;"
                    "text-transform:uppercase;letter-spacing:.05em;margin-top:8px;'>"
                    "Sites</div>",
                    unsafe_allow_html=True,
                )
                sites = cohort["sites"][:8]
                if sites:
                    df_s = pd.DataFrame(sites, columns=["Site", "n"])
                    st.dataframe(df_s, hide_index=True, use_container_width=True)


# ============================================================================
# VIEW: HOME
# ============================================================================
def view_home(data: dict):
    st.markdown("## NYPA Salary Metrics")
    st.markdown(
        "<div class='page-sub'>New York Power Authority · Canal Corporation · "
        "2017 to 2024 · 4,318 unique employees</div>",
        unsafe_allow_html=True,
    )

    os_ = data["org_stats"]
    s17, s24 = os_["2017"], os_["2024"]
    og = round((s24["median"] - s17["median"]) / s17["median"] * 100)
    hc26 = data.get("headcount_2026", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Current employees", f"{s24['count']:,}", sub="Active in 2024", color="blue",
                    delta=f"↑ +{s24['count'] - s17['count']} since 2017", delta_dir="up")
    with c2:
        metric_card("Unique individuals", "4,318", sub="All records 2017–2024", color="green",
                    delta="8 years of data", delta_dir="flat")
    with c3:
        metric_card("Median salary (2024)", fmt_dollar(s24["median"]), sub="Base annualized",
                    color="amber",
                    delta=f"↑ {fmt_dollar(s24['median'] - s17['median'])} since 2017",
                    delta_dir="up")
    with c4:
        metric_card("Org growth 2017→2024", f"{og}%", sub="Median salary", color="purple",
                    delta=f"{fmt_dollar(s17['median'])} → {fmt_dollar(s24['median'])}",
                    delta_dir="up")

    st.markdown("&nbsp;")
    col_a, col_b = st.columns(2)
    years = data["all_years"]
    counts = [os_[str(y)]["count"] for y in years]
    with col_a:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=counts, marker=dict(color=LIGHT_BLUE), text=counts,
                             textposition="outside", textfont=dict(size=10)))
        apply_layout(fig, height=260, y_dollars=False)
        chart_card("Headcount trend 2017–2024", fig, key="home-hc")

    with col_b:
        st.markdown(
            "<div style='font-size:11px;font-weight:600;color:#888;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;'>Key insights</div>",
            unsafe_allow_html=True,
        )
        insights = [
            ("↑", "#E1F5EE", GREEN,
             f"Median salary grew from {fmt_dollar(s17['median'])} to {fmt_dollar(s24['median'])} — "
             f"{og}% org-wide increase"),
            ("$", "#FAEEDA", DARK_AMBER,
             "Overtime is significant compensation at NYPA — many roles carry substantial OT earnings"),
            ("↑", "#E6F1FB", BLUE,
             f"Headcount grew from {s17['count']:,} to {s24['count']:,} — "
             f"net +{s24['count'] - s17['count']} employees over 8 years"),
            ("≡", "#EEEDFE", PURPLE,
             "Use the Leaderboard group/site filters to compare growth across divisions"),
        ]
        if hc26.get("total_2026"):
            insights.append((
                "26", "#FAEEDA", DARK_AMBER,
                f"2026 headcount: {hc26['total_2026']:,} total employees across 8 sites · "
                f"{hc26['new_hires']} new hires since 2024 (2025 data unavailable)",
            ))
        for icon, bg, fg, text in insights:
            st.markdown(
                f"<div style='display:flex;gap:9px;margin-bottom:8px;font-size:12px;color:#444;"
                f"line-height:1.5;'><div style='width:22px;height:22px;border-radius:5px;"
                f"background:{bg};color:{fg};display:flex;align-items:center;justify-content:center;"
                f"font-size:11px;font-weight:700;flex-shrink:0;'>{icon}</div>{text}</div>",
                unsafe_allow_html=True,
            )

    medians = [os_[str(y)]["median"] for y in years]
    means = [os_[str(y)]["mean"] for y in years]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=medians, name="Median",
        line=dict(color=BLUE, width=2),
        mode="lines+markers",
        hovertemplate="<b>%{x}</b><br>Median: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=means, name="Mean",
        line=dict(color=AMBER, width=2, dash="dash"),
        mode="lines+markers",
        fill="tonexty",
        fillcolor=rgba(AMBER, 0.10),
        hovertemplate="<b>%{x}</b><br>Mean: $%{y:,.0f}<extra></extra>",
    ))
    apply_layout(fig, height=300, show_legend=True, y_dollars=True)
    chart_card(
        "Mean vs median salary — 2017 to 2024", fig, key="home-mm-trend",
        subtitle=(
            "Gap between mean and median indicates how concentrated high earners are. "
            "A widening gap = top-end pay growing faster than typical."
        ),
    )


# ============================================================================
# VIEW: INDIVIDUAL PROFILE
# ============================================================================
def _company_avg_raise_pct(
    cohort_raises: dict,
    start_y: int,
    end_y: int,
    compare_filter: str,
    cut_key: str = "raise_recipients",
) -> float | None:
    # PL-077 (amend): arithmetic mean of <cut>.mean_pct across the
    # [start_y, end_y) transitions. PL-085: cut_key routes to either
    # "raise_recipients" (default, excludes $0/frozen) or "all_cohort"
    # (includes frozen). Default preserves PL-077 baseline behavior.
    # compare_filter empty -> org-wide; otherwise the by_site slice.
    pcts = []
    for y in range(start_y, end_y):
        slice_data = cohort_raises.get(f"{y}_{y + 1}")
        if not slice_data:
            continue
        if compare_filter:
            slice_data = slice_data.get("by_site", {}).get(compare_filter)
            if not slice_data:
                continue
        pcts.append(slice_data[cut_key]["mean_pct"])
    if not pcts:
        return None
    return sum(pcts) / len(pcts)


def _personal_avg_raise_pct(rec: dict, start_y: int, end_y: int) -> float | None:
    # PL-077 (amend): arithmetic mean of the person's yoy[i] for consecutive
    # year transitions in (start_y, end_y]. Apples-to-apples with the company-
    # side arithmetic mean above.
    rec_years = rec.get("years", [])
    yoys = []
    for y in range(start_y + 1, end_y + 1):
        if y not in rec_years:
            continue
        i = rec_years.index(y)
        if i == 0 or rec_years[i - 1] != y - 1:
            continue
        v = rec["yoy"][i]
        if v is not None:
            yoys.append(v)
    if not yoys:
        return None
    return sum(yoys) / len(yoys)


def view_individual(data: dict):
    st.markdown("## Individual profile")
    st.markdown(
        "<div class='page-sub'>Search any of 4,318 NYPA employees for their full career "
        "and compensation history</div>",
        unsafe_allow_html=True,
    )

    people = data["people"]
    years = data["all_years"]
    records = data["records"]
    org_stats = data["org_stats"]

    col_s, col_y1, col_y2, col_site = st.columns([4, 2, 2, 2])
    with col_s:
        person = st.selectbox(
            "Search employee",
            options=[""] + people,
            index=0,
            format_func=lambda x: "Type a name…" if x == "" else x,
            key="ind_person",
        )
    with col_y1:
        sy = st.selectbox("Start year", years, index=0, key="ind_sy")
    with col_y2:
        eye_default = len(years) - 1
        ey = st.selectbox("End year", years, index=eye_default, key="ind_ey")
    with col_site:
        site_opts = [""] + data.get("sites", [])
        site_filter = st.selectbox(
            "Site filter",
            options=site_opts,
            format_func=lambda x: "All sites" if x == "" else x,
            key="ind_site",
        )
    if ey < sy:
        st.warning("End year must be greater than or equal to start year.")
        return
    if not person:
        st.info("Search for an employee above to view their profile.")
        return
    rec = records.get(person)
    if not rec:
        st.warning("No record found.")
        return
    p_site = get_site(person, data)
    if site_filter and p_site != site_filter:
        st.warning(f"{person} is not in site '{site_filter}' (site: {p_site or 'unknown'}).")
        return

    ry = [y for y in years if sy <= y <= ey]
    rec_years = rec["years"]
    ir = [y for y in ry if y in rec_years]
    if not ir:
        st.info("No data in selected range.")
        return
    fy, ly = ir[0], ir[-1]
    fi, li = rec_years.index(fy), rec_years.index(ly)
    bs, be = rec["base"][fi], rec["base"][li]
    n_years = ly - fy
    tg = round((be - bs) / bs * 1000) / 10 if n_years > 0 and bs else None
    cagr = round((pow(be / bs, 1 / n_years) - 1) * 10000) / 100 if n_years > 0 and bs else None
    ot_vals = [rec["ot"][rec_years.index(y)] for y in ir if rec["ot"][rec_years.index(y)] > 0]
    avg_ot = round(sum(ot_vals) / len(ot_vals)) if ot_vals else None
    max_ot = max(ot_vals) if ot_vals else None

    ac = avatar_color(person)
    pct_latest = rec.get("pctile", [None] * len(rec_years))[li]
    gap_med = rec.get("gap_median", [None] * len(rec_years))[li]
    gap_mean = rec.get("gap_mean", [None] * len(rec_years))[li]
    site_pill = (f" · {p_site}" if p_site else "") + (f" · joined {fy}" if fy > sy else "") + (
        f" · last record {ly}" if ly < ey else ""
    )

    st.markdown(
        f'<div class="hero-banner"><div class="hero-avatar" '
        f'style="background:{ac}22;color:{ac};">{initials(person)}</div>'
        f'<div><div class="hero-name">{person}</div>'
        f'<div class="hero-sub">{rec["titles"][li]} · {rec["depts"][li]} · '
        f'{rec["groups"][li]}{site_pill}</div></div></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Start base", fmt_dollar(bs), sub=str(fy), color="blue")
    with c2:
        sub = f"{int(pct_latest)}th percentile" if pct_latest is not None else ""
        delta = fmt_dollar(gap_med, signed=True) + " vs org median" if gap_med is not None else ""
        dd = "up" if (gap_med or 0) >= 0 else "dn"
        metric_card(f"Current base ({ly})", fmt_dollar(be), sub=sub, color="blue", delta=delta, delta_dir=dd)
    with c3:
        metric_card("Total growth", fmt_pct(tg) if tg is not None else "—",
                    sub=f"{fy}–{ly}", color="green")
    with c4:
        metric_card("CAGR", fmt_pct(cagr) if cagr is not None else "—",
                    sub="compound annual", color="amber")
    with c5:
        sub = f"peak: {fmt_dollar(max_ot)}" if max_ot else "none on record"
        metric_card("Avg OT / yr", fmt_dollar(avg_ot or 0), sub=sub, color="teal")

    # PL-077 (amend): dedicated comparison-site selector for the company-avg
    # benchmark in c5 below + the YoY chart line. Decoupled from the page
    # Site filter, which keeps its original informational role ("warn if person
    # isn't in the selected site").
    # PL-085: adds a sibling "Cohort cut" radio mirroring Org Overview's
    # org_cohort_mode toggle. Drives metric card, chart line, and verdict block
    # in lockstep. Default "Raise recipients only" preserves PL-077/PL-084
    # baseline math.
    col_cmp, col_cut, _col_pad = st.columns([2, 2, 2])
    with col_cmp:
        compare_against = st.selectbox(
            "Compare against",
            options=[""] + data.get("sites", []),
            format_func=lambda x: "All sites (Company avg)" if x == "" else x,
            key="ind_compare_against",
        )
    with col_cut:
        cohort_mode = st.radio(
            "Cohort cut",
            ["All cohort (incl. frozen)", "Raise recipients only"],
            horizontal=True,
            index=1,
            key="ind_cohort_mode",
            help=(
                "All cohort: includes employees with $0 raises (frozen). "
                "Raise recipients only: excludes $0 raises. "
                "Same toggle as Org Overview."
            ),
        )
    cut_key = "all_cohort" if cohort_mode == "All cohort (incl. frozen)" else "raise_recipients"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        gm_org = be - gap_med if gap_med is not None else None
        metric_card(f"vs org median ({ly})", fmt_dollar(gap_med, signed=True) if gap_med is not None else "—",
                    sub=f"org median: {fmt_dollar(gm_org)}", color="blue",
                    delta="", delta_dir="up" if (gap_med or 0) >= 0 else "dn")
    with c2:
        gmn_org = be - gap_mean if gap_mean is not None else None
        metric_card(f"vs org mean ({ly})", fmt_dollar(gap_mean, signed=True) if gap_mean is not None else "—",
                    sub=f"org mean: {fmt_dollar(gmn_org)}", color="green",
                    delta="", delta_dir="up" if (gap_mean or 0) >= 0 else "dn")
    with c3:
        ly_stats = org_stats.get(str(ly))
        sub_text = (
            f"of {ly_stats['count']:,} employees" if ly_stats
            else "no org-wide data for this year"
        )
        metric_card(f"Org percentile ({ly})",
                    f"{int(pct_latest)}th" if pct_latest is not None else "—",
                    sub=sub_text, color="purple")
    with c4:
        start_pct = rec.get("pctile", [None])[0]
        delta_pct = None
        if start_pct is not None and pct_latest is not None:
            delta_pct = round(pct_latest - start_pct)
        metric_card("Percentile trend",
                    f"{'+' if (delta_pct or 0) >= 0 else ''}{delta_pct}pts" if delta_pct is not None else "—",
                    sub=f"since {fy}", color="amber")
    with c5:
        # PL-077 (amend): arithmetic mean of raise_recipients raises across
        # the selected year range, scoped by the Compare-against dropdown.
        # Apples-to-apples with the personal arithmetic mean over the same
        # year transitions.
        co_avg = _company_avg_raise_pct(
            data.get("cohort_raises", {}), fy, ly, compare_against, cut_key
        )
        you_avg = _personal_avg_raise_pct(rec, fy, ly)
        avg_card_label = (
            f"{compare_against} avg raise % ({fy}-{ly})" if compare_against
            else f"Company avg raise % ({fy}-{ly})"
        )
        if co_avg is None:
            metric_card(avg_card_label, "—",
                        sub="Insufficient cohort data", color="teal")
        elif you_avg is not None:
            delta_pp = you_avg - co_avg
            metric_card(
                avg_card_label, f"{co_avg:.2f}%",
                sub=f"vs your {you_avg:.2f}%", color="teal",
                delta=f"{delta_pp:+.2f}pp",
                delta_dir="up" if delta_pp >= 0 else "dn",
            )
        else:
            metric_card(avg_card_label, f"{co_avg:.2f}%",
                        sub="Personal avg n/a", color="teal")

    # Career callouts
    callouts = []
    best_jump = (None, -math.inf)
    for y in ir:
        i = rec_years.index(y)
        v = rec["yoy"][i] if i < len(rec["yoy"]) else None
        if v is not None and v > best_jump[1]:
            best_jump = (y, v)
    if best_jump[0] and best_jump[1] > 10:
        i = rec_years.index(best_jump[0])
        prev = rec["base"][i - 1] if i > 0 else 0
        callouts.append((
            "#3B6D11",
            f"Biggest jump: {best_jump[0]} — +{best_jump[1]}% "
            f"({fmt_dollar(rec['base'][i] - prev, signed=True)}) base increase",
        ))
    freezes = [
        y for y in ir if rec["yoy"][rec_years.index(y)] == 0
    ]
    if freezes:
        callouts.append(("#888", f"Salary freeze: {', '.join(str(y) for y in freezes)} — no base increase"))
    title_changes = [y for y in ir if (i := rec_years.index(y)) > 0 and rec["titles"][i] != rec["titles"][i - 1]]
    if title_changes:
        parts = []
        for y in title_changes:
            parts.append(f"{y} → {rec['titles'][rec_years.index(y)]}")
        callouts.append((BLUE, "Title change" + ("s" if len(title_changes) > 1 else "") + ": " + " · ".join(parts)))
    if max_ot and max_ot > 10000:
        callouts.append((GREEN, f"Peak overtime: {fmt_dollar(max_ot)} — significant OT earnings on record"))
    if callouts:
        for color, text in callouts:
            st.markdown(f"<div class='callout' style='border-color:{color};'>{text}</div>",
                        unsafe_allow_html=True)

    # Chart: salary history
    base_series = [rec["base"][rec_years.index(y)] if y in rec_years else None for y in ry]
    total_series = [rec["total"][rec_years.index(y)] if y in rec_years else None for y in ry]
    point_colors = [
        "#E24B4A" if (y in rec_years and rec_years.index(y) > 0
                      and rec["titles"][rec_years.index(y)] != rec["titles"][rec_years.index(y) - 1])
        else ac
        for y in ry
    ]

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ry, y=base_series, mode="lines+markers", name="Base",
            line=dict(color=ac, width=2.5), marker=dict(color=point_colors, size=8),
            connectgaps=False,
            hovertemplate="<b>%{x}</b><br>Base: $%{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=ry, y=total_series, mode="lines+markers", name="Total comp",
            line=dict(color=ac, width=1.5, dash="dash"),
            marker=dict(color=ac, size=5),
            connectgaps=False,
            hovertemplate="<b>%{x}</b><br>Total: $%{y:,.0f}<extra></extra>",
        ))
        apply_layout(fig, height=280, show_legend=True)
        chart_card("Salary history — base vs total comp (red dot = title change)", fig,
                   key="ind-line")

    with col_r:
        fig = go.Figure()
        bases = [rec["base"][rec_years.index(y)] if y in rec_years else 0 for y in ry]
        ots = [max(rec["ot"][rec_years.index(y)], 0) if y in rec_years else 0 for y in ry]
        adds_pos = [max(rec["add"][rec_years.index(y)], 0) if y in rec_years else 0 for y in ry]
        adds_neg = [min(rec["add"][rec_years.index(y)], 0) if y in rec_years else 0 for y in ry]
        fig.add_trace(go.Bar(x=ry, y=bases, name="Base", marker=dict(color=rgba(ac, 0.8))))
        fig.add_trace(go.Bar(x=ry, y=ots, name="Overtime", marker=dict(color=rgba(LIME, 0.67))))
        fig.add_trace(go.Bar(x=ry, y=adds_pos, name="Add. earnings", marker=dict(color=rgba(ac, 0.33))))
        fig.add_trace(go.Bar(x=ry, y=adds_neg, name="Adjustment", marker=dict(color="#F09595")))
        fig.update_layout(barmode="stack")
        apply_layout(fig, height=280, show_legend=True)
        chart_card("Compensation breakdown — base + OT + add. earnings", fig, key="ind-stack")

    # Percentile rank over time
    pcts = [rec["pctile"][rec_years.index(y)] if y in rec_years else None for y in ir]
    start_pct = pcts[0] if pcts else None
    end_pct = pcts[-1] if pcts else None

    fig = go.Figure()
    bands = [
        (0, 25, "rgba(231, 76, 60, 0.06)"),
        (25, 50, "rgba(241, 196, 15, 0.06)"),
        (50, 75, "rgba(46, 204, 113, 0.06)"),
        (75, 90, "rgba(52, 152, 219, 0.10)"),
        (90, 100, "rgba(155, 89, 182, 0.12)"),
    ]
    for y0, y1, color in bands:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, layer="below", line_width=0)

    fig.add_trace(go.Scatter(
        x=ir, y=pcts, mode="lines+markers",
        line=dict(color=ac, width=3),
        marker=dict(size=8),
        connectgaps=False,
        hovertemplate="<b>%{x}</b><br>Percentile: %{y}<extra></extra>",
    ))

    if start_pct is not None:
        fig.add_annotation(x=ir[0], y=start_pct, text=f"Start: {start_pct}",
                           showarrow=True, arrowhead=2, ay=-30)
    if end_pct is not None and len(ir) > 1:
        fig.add_annotation(x=ir[-1], y=end_pct, text=f"Now: {end_pct}",
                           showarrow=True, arrowhead=2, ay=-30)

    fig.update_yaxes(range=[0, 100], title="Percentile rank", tickformat="d")
    apply_layout(fig, height=320, show_legend=False, y_dollars=False)

    direction = ""
    if start_pct is not None and end_pct is not None:
        diff = end_pct - start_pct
        if abs(diff) <= 5:
            direction = "Flat — relative position roughly unchanged"
        elif diff > 5:
            direction = f"▲ Climbing — gained {diff} percentile points"
        else:
            direction = f"▼ Sliding — lost {abs(diff)} percentile points"

    chart_card("Percentile rank over time", fig, key="ind-pctile",
               subtitle=direction)

    col_l, col_r = st.columns(2)
    with col_l:
        yy = ry[1:]
        dollars = []
        pct = []
        for y in yy:
            if y in rec_years:
                idx = rec_years.index(y)
                prev_y = ry[ry.index(y) - 1]
                if idx > 0 and prev_y in rec_years:
                    dollars.append(rec["base"][idx] - rec["base"][idx - 1])
                    pct.append(rec["yoy"][idx])
                else:
                    dollars.append(None)
                    pct.append(None)
            else:
                dollars.append(None)
                pct.append(None)
        colors = []
        for i, y in enumerate(yy):
            if dollars[i] is None:
                colors.append("rgba(128,128,128,0.15)")
            elif y in rec_years and rec_years.index(y) > 0 and (
                rec["titles"][rec_years.index(y)] != rec["titles"][rec_years.index(y) - 1]
            ):
                colors.append(rgba("#E24B4A", 0.67))
            else:
                colors.append(rgba(ac, 0.73))
        # PL-077 (amend): personal bars show raise % (was $); single % axis.
        # PL-084: bar text labels match the bar height (% instead of $); $ moves
        # to hover via customdata so the dollar context is still discoverable.
        pct_labels = [f"{p:+.1f}%" if p is not None else "" for p in pct]
        bar_customdata = [[d if d is not None else 0] for d in dollars]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=yy, y=pct, name="You",
            marker=dict(color=colors),
            text=pct_labels, textposition="outside", textfont=dict(size=10),
            customdata=bar_customdata,
            hovertemplate=(
                "<b>%{x}</b><br>Raise: %{y:+.2f}%<br>"
                "$ change: $%{customdata[0]:,}<extra>You</extra>"
            ),
        ))
        # Company-avg overlay on the SAME % axis. PL-085: reads cut_key so the
        # line moves in lockstep with the metric card when the user toggles
        # between all_cohort and raise_recipients.
        chart_cohort_raises = data.get("cohort_raises", {})
        co_pcts = []
        for y in yy:
            slice_data = chart_cohort_raises.get(f"{y - 1}_{y}")
            if compare_against and slice_data:
                slice_data = slice_data.get("by_site", {}).get(compare_against)
            co_pcts.append(
                slice_data[cut_key]["mean_pct"] if slice_data else None
            )
        co_label = f"{compare_against} avg" if compare_against else "Company avg"
        # PL-084: line points show their % values inline (was hover-only) so
        # the comparison values are legible without hovering.
        co_text = [f"{v:.1f}%" if v is not None else "" for v in co_pcts]
        fig.add_trace(go.Scatter(
            x=yy, y=co_pcts, name=co_label,
            mode="lines+markers+text",
            text=co_text, textposition="bottom center",
            textfont=dict(size=9, color=AMBER),
            line=dict(color=AMBER, width=2, dash="dash"),
            marker=dict(color=AMBER, size=6),
            connectgaps=False,
            hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.2f}%<extra></extra>",
        ))
        apply_layout(fig, height=260, show_legend=True, y_dollars=False)
        fig.update_yaxes(title="Raise %", ticksuffix="%")
        chart_card("Year-over-year raise % — you vs benchmark", fig, key="ind-yoy")

        cohort_data = data.get("cohort_raises", {})
        ctx = None
        if cohort_data:
            for y_ctx in reversed(ir):
                idx_ = rec_years.index(y_ctx)
                if idx_ > 0 and rec_years[idx_ - 1] == y_ctx - 1 and (y_ctx - 1) in ir:
                    person_pct = rec["yoy"][idx_]
                    trans = cohort_data.get(f"{y_ctx - 1}_{y_ctx}")
                    if person_pct is not None and trans:
                        # PL-087: read cut_key so the verdict benchmark matches
                        # the chart's amber line (was hard-coded all_cohort,
                        # which mismatched the raise_recipients chart line).
                        ctx = (y_ctx, person_pct, trans[cut_key]["mean_pct"])
                        break
        if ctx:
            y_ctx, person_pct, org_pct = ctx
            diff = person_pct - org_pct
            if diff > 1:
                verdict, vc = f"Outperformed by {diff:.1f} points", GREEN
            elif diff < -1:
                verdict, vc = f"Underperformed by {abs(diff):.1f} points", "#A32D2D"
            else:
                verdict, vc = "Matched the typical raise", "#888"
            st.markdown(
                f"<div style='font-size:11px;color:#444;margin-top:-4px;margin-bottom:8px;"
                f"padding:7px 11px;background:#f5f5f3;border-left:3px solid {vc};border-radius:4px;'>"
                f"In <strong>{y_ctx}</strong>, this employee got a "
                f"<strong>{person_pct:+.2f}%</strong> raise vs. org average of "
                f"<strong>{org_pct:+.2f}%</strong>. <em>{verdict} that year.</em>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with col_r:
        st.markdown(
            "<div style='font-size:11px;font-weight:600;color:#888;"
            "text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;'>Career timeline</div>",
            unsafe_allow_html=True,
        )
        tl_html = "<div style='max-height:280px;overflow-y:auto;padding-right:4px;'>"
        for y in ir:
            i = rec_years.index(y)
            is_pr = i > 0 and rec["titles"][i] != rec["titles"][i - 1]
            yoy_v = rec["yoy"][i]
            ot = rec["ot"][i]
            add = rec["add"][i]
            dot_color = BLUE if is_pr else (ac if y == ly else "#ccc")
            badges = ""
            if is_pr:
                badges += "<span class='badge b-title'>title change</span>"
            if yoy_v is not None and yoy_v >= 15:
                badges += f"<span class='badge b-up'>+{yoy_v}%</span>"
            if yoy_v == 0:
                badges += "<span class='badge b-flat'>no raise</span>"
            if ot > 10000:
                badges += f"<span class='badge b-ot'>OT: {fmt_dollar(ot)}</span>"
            tl_html += (
                f"<div class='timeline-item'>"
                f"<div style='display:flex;flex-direction:column;align-items:center;width:36px;'>"
                f"<div class='timeline-year'>{y}</div>"
                f"<div class='timeline-dot' style='background:{dot_color};border-color:{dot_color};'></div>"
                f"</div>"
                f"<div style='flex:1;'>"
                f"<div class='timeline-title'>{rec['titles'][i]}{badges}</div>"
                f"<div class='timeline-dept'>{rec['depts'][i]} · {rec['groups'][i]}</div>"
                f"<div style='display:flex;gap:10px;margin-top:4px;font-size:11px;color:#666;'>"
                f"<span>Base: <strong>{fmt_dollar(rec['base'][i])}</strong></span>"
            )
            if yoy_v is not None and i > 0:
                tl_html += f"<span>YoY: <strong>{fmt_pct(yoy_v, signed=True)}</strong></span>"
            if ot > 0:
                tl_html += f"<span>OT: <strong>{fmt_dollar(ot)}</strong></span>"
            if add > 0:
                tl_html += f"<span>Add: <strong>{fmt_dollar(add, signed=True)}</strong></span>"
            tl_html += "</div></div></div>"
        tl_html += "</div>"
        st.markdown(tl_html, unsafe_allow_html=True)

    # Year-by-year table
    st.markdown("#### Year by year detail")
    rows = []
    pctiles = rec.get("pctile", [None] * len(rec_years))
    for y in ir:
        i = rec_years.index(y)
        pct_i = pctiles[i] if i < len(pctiles) else None
        rows.append({
            "Year": y,
            "Title": rec["titles"][i],
            "Group": rec["groups"][i],
            "Base": rec["base"][i],
            "YoY %": rec["yoy"][i],
            "Percentile": f"{int(pct_i)}%" if pct_i is not None else "—",
            "Overtime": rec["ot"][i],
            "Add. earnings": rec["add"][i],
            "Total comp": rec["total"][i],
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Base": st.column_config.NumberColumn(format="$%d"),
            "Overtime": st.column_config.NumberColumn(format="$%d"),
            "Add. earnings": st.column_config.NumberColumn(format="$%d"),
            "Total comp": st.column_config.NumberColumn(format="$%d"),
            "YoY %": st.column_config.NumberColumn(format="%.1f%%"),
            "Percentile": st.column_config.TextColumn(
                help="This employee's percentile rank within the full org for that year's base salary.",
            ),
        },
    )

    # --------------------------------------------------------------------
    # PL-033 Compensation Report (per-person, on demand)
    # --------------------------------------------------------------------
    st.markdown("---")
    show_key = f"_pl033_show_{person}"
    if not st.session_state.get(show_key, False):
        st.markdown(
            "<div style='font-size:11px;color:#888;margin-bottom:6px;'>"
            "Generate a manager-handover compensation report for this employee — "
            "case-first analysis with honest counter-evidence and a Markdown export."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("📋 Generate Compensation Report",
                     key=f"_pl033_gen_btn_{person}", type="primary"):
            st.session_state[show_key] = True
            st.rerun()
    else:
        with st.spinner("Generating compensation report…"):
            payload = build_report_payload(person, rec, records, data)
        render_compensation_report(payload)
        if st.button("Hide compensation report",
                     key=f"_pl033_hide_btn_{person}"):
            st.session_state[show_key] = False
            st.rerun()


# ============================================================================
# VIEW: COMPARISON
# ============================================================================
def cmp_status(rec, sy, ey):
    ry = list(range(sy, ey + 1))
    ir = [y for y in ry if y in rec["years"]]
    if not ir:
        return {"status": "absent"}
    fy, ly = ir[0], ir[-1]
    fi, li = rec["years"].index(fy), rec["years"].index(ly)
    bs, be = rec["base"][fi], rec["base"][li]
    status = "full"
    if fy > sy and ly < ey:
        status = "partial"
    elif fy > sy:
        status = "joined"
    elif ly < ey:
        status = "left"
    return {"status": status, "fy": fy, "ly": ly, "bs": bs, "be": be}


def cmp_metrics(rec, sy, ey):
    st_ = cmp_status(rec, sy, ey)
    if st_["status"] == "absent":
        return None
    bs, be, fy, ly = st_["bs"], st_["be"], st_["fy"], st_["ly"]
    n = ly - fy
    tg = round((be - bs) / bs * 1000) / 10 if n > 0 and bs else None
    ca = round((pow(be / bs, 1 / n) - 1) * 10000) / 100 if n > 0 and bs else None
    return {"tg": tg, "ca": ca, "fy": fy, "ly": ly, "bs": bs, "be": be, "status": st_["status"]}


def _comparison_to_profile(name: str) -> None:
    # on_click callback: redirect to Individual Profile for the clicked pill.
    # Setting widget keys from a callback is allowed because callbacks run
    # before any widget renders on the next script run. cmp_sel is left intact
    # so navigating back to Comparison restores the prior selection.
    st.session_state["_nav_redirect"] = "Individual profile"
    st.session_state["ind_person"] = name


def view_comparison(data: dict):
    st.markdown("## Comparison")
    st.markdown(
        "<div class='page-sub'>Add up to 6 employees to compare salary trajectories "
        "side by side</div>",
        unsafe_allow_html=True,
    )

    # PL-075: surface any cap warning parked by Find by Raise Window's multi-select
    # redirect. pop() so the warning fires once and clears.
    cap_warning = st.session_state.pop("_lbw_cap_warning", None)
    if cap_warning:
        st.warning(cap_warning)

    years = data["all_years"]
    records = data["records"]
    people = data["people"]

    if "cmp_sel" not in st.session_state:
        st.session_state.cmp_sel = []

    col_add, col_clear, col_sy, col_ey, col_overlay = st.columns([3, 1, 1, 1, 2])
    with col_add:
        new_person = st.selectbox(
            "Add employee",
            options=[""] + [p for p in people if p not in st.session_state.cmp_sel],
            format_func=lambda x: "Type a name to add…" if x == "" else x,
            key="cmp_add",
        )
        if new_person and new_person not in st.session_state.cmp_sel and len(st.session_state.cmp_sel) < 6:
            st.session_state.cmp_sel.append(new_person)
            st.rerun()
    with col_clear:
        st.markdown("&nbsp;")
        if st.button("Clear all", key="cmp_clear_btn"):
            st.session_state.cmp_sel = []
            st.rerun()
    with col_sy:
        sy = st.selectbox("Start", years, index=0, key="cmp_sy")
    with col_ey:
        ey = st.selectbox("End", years, index=len(years) - 1, key="cmp_ey")
    with col_overlay:
        overlay = st.radio("Earnings overlay", ["Off", "OT", "Add. earnings", "Both"],
                           horizontal=True, index=1, key="cmp_overlay")

    if ey < sy:
        st.warning("End year must be >= start year.")
        return

    selected = st.session_state.cmp_sel

    # Pill display + remove + open-profile
    if selected:
        cols = st.columns(len(selected) + 1)
        for i, name in enumerate(selected):
            color = CMP_COLORS[i % len(CMP_COLORS)]
            with cols[i]:
                if st.button(f"✕ {name}", key=f"rm-{i}", help="Remove"):
                    st.session_state.cmp_sel = [x for x in selected if x != name]
                    st.rerun()
                st.markdown(
                    f"<div style='height:4px;background:{color};border-radius:2px;"
                    f"margin-top:-10px;'></div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    "→ profile",
                    key=f"to-prof-{i}",
                    on_click=_comparison_to_profile,
                    args=(name,),
                    help="Open this person's Individual Profile",
                )
    if len(selected) < 1:
        st.info("Search and add 2–6 people above to compare.")
        return

    ry = [y for y in years if sy <= y <= ey]
    metrics = [cmp_metrics(records[n], sy, ey) for n in selected]

    # Summary cards
    valid = [m for m in metrics if m and m["tg"] is not None]
    avg_g = sum(m["tg"] for m in valid) / len(valid) if valid else None
    avg_c = sum(m["ca"] for m in valid) / len(valid) if valid else None
    if valid:
        top_m = max(valid, key=lambda m: m["tg"])
        top_name = selected[metrics.index(top_m)]
    else:
        top_m = None
        top_name = "—"
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Avg total growth", f"{avg_g:.1f}%" if avg_g is not None else "—",
                    sub=f"{sy}–{ey}", color="blue")
    with c2:
        metric_card("Avg CAGR", f"{avg_c:.1f}%" if avg_c is not None else "—",
                    sub="compound annual", color="green")
    with c3:
        metric_card("Top grower", top_name,
                    sub=(f"+{top_m['tg']}%" if top_m else ""), color="amber")

    # Absolute salary chart (full width) — toggleable between base and total comp
    cmp_chart1_mode = st.radio(
        "Show",
        ["Base salary only", "Total compensation"],
        horizontal=True,
        index=0,
        key="cmp_chart1_mode",
        help=(
            "Base salary: career growth metric. "
            "Total compensation: actual take-home including OT and additional earnings."
        ),
    )
    use_total = cmp_chart1_mode == "Total compensation"
    series_key = "total" if use_total else "base"
    fig = go.Figure()
    for i, name in enumerate(selected):
        rec = records[name]
        color = CMP_COLORS[i % len(CMP_COLORS)]
        st_ = cmp_status(rec, sy, ey)
        if st_["status"] == "absent":
            continue
        y_data = [rec[series_key][rec["years"].index(y)] if y in rec["years"] else None for y in ry]
        dash = "dash" if st_["status"] != "full" else "solid"
        fig.add_trace(go.Scatter(
            x=ry, y=y_data, mode="lines+markers", name=name,
            line=dict(color=color, width=2, dash=dash),
            marker=dict(size=6),
            connectgaps=False,
            hovertemplate=f"<b>{name}</b><br>%{{x}}: $%{{y:,.0f}}<extra></extra>",
        ))
    apply_layout(fig, height=320, show_legend=True, y_dollars=True)
    chart1_title = "Total compensation over time" if use_total else "Base salary over time"
    chart_card(chart1_title, fig, key="cmp-abs-base")

    # Indexed growth chart (always indexed, base-salary based)
    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure()
        for i, name in enumerate(selected):
            rec = records[name]
            color = CMP_COLORS[i % len(CMP_COLORS)]
            st_ = cmp_status(rec, sy, ey)
            if st_["status"] == "absent":
                continue
            sb = st_["bs"]
            y_data = []
            for y in ry:
                if y in rec["years"]:
                    b = rec["base"][rec["years"].index(y)]
                    y_data.append(round(b / sb * 1000) / 10 if sb else None)
                else:
                    y_data.append(None)
            dash = "dash" if st_["status"] != "full" else "solid"
            fig.add_trace(go.Scatter(
                x=ry, y=y_data, mode="lines+markers", name=name,
                line=dict(color=color, width=2, dash=dash),
                marker=dict(size=6),
                connectgaps=False,
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>",
            ))
        fig.update_yaxes(title="Index (start=100)", tickprefix="", tickformat=".0f")
        apply_layout(fig, height=320, show_legend=True, y_dollars=False)
        chart_card(
            "Indexed growth — start=100",
            fig,
            key="cmp-norm",
            subtitle="All base salaries normalized to 100 in starting year. For absolute amounts, see chart above.",
        )

    with col_r:
        fig = go.Figure()
        for i, name in enumerate(selected):
            rec = records[name]
            color = CMP_COLORS[i % len(CMP_COLORS)]
            m = metrics[i]
            if not m:
                continue
            fig.add_trace(go.Scatter(
                x=[m["fy"], m["ly"]], y=[m["bs"], m["be"]],
                mode="lines+markers+text",
                name=name,
                text=[None, f"{m['tg']:+.1f}%" if m["tg"] is not None else ""],
                textposition="middle right", textfont=dict(size=10, color=color),
                line=dict(color=color, width=3),
                marker=dict(size=10, color=color),
                hovertemplate=f"<b>{name}</b><br>%{{x}}: $%{{y:,.0f}}<extra></extra>",
            ))
        apply_layout(fig, height=320, show_legend=False)
        chart_card("Start → End salary slope", fig, key="cmp-slope")

    # YoY bar chart
    yy = ry[1:]
    fig = go.Figure()
    for i, name in enumerate(selected):
        rec = records[name]
        color = CMP_COLORS[i % len(CMP_COLORS)]
        dollars = []
        pcts = []
        for y in yy:
            if y in rec["years"]:
                idx = rec["years"].index(y)
                if idx > 0 and rec["years"][idx - 1] in ry:
                    dollars.append(rec["base"][idx] - rec["base"][idx - 1])
                    pcts.append(rec["yoy"][idx])
                    continue
            dollars.append(None)
            pcts.append(None)
        labels = [f"{p:+.1f}%" if p is not None else "" for p in pcts]
        fig.add_trace(go.Bar(
            x=yy, y=dollars, name=name,
            marker=dict(color=rgba(color, 0.73)),
            text=labels, textposition="outside", textfont=dict(size=9, color=color),
            hovertemplate=f"<b>{name}</b><br>%{{x}}: $%{{y:,.0f}}<extra></extra>",
        ))
    fig.update_layout(barmode="group")
    apply_layout(fig, height=300, show_legend=True)
    chart_card("Year-over-year $ change", fig, key="cmp-yoy")

    # PL-015d — Comparison group vs org P25–P75 raise reference band
    cohort_data = data.get("cohort_raises", {})
    if cohort_data and yy:
        x_labels, p25s, p75s, group_means = [], [], [], []
        for y_to in yy:
            y_from = y_to - 1
            c_band = cohort_data.get(f"{y_from}_{y_to}")
            if not c_band:
                continue
            x_labels.append(f"{y_from}→{str(y_to)[-2:]}")
            p25s.append(c_band["org_p25_pct"])
            p75s.append(c_band["org_p75_pct"])
            member_pcts = []
            for name in selected:
                rec_ = records[name]
                if y_from in rec_["years"] and y_to in rec_["years"]:
                    i_to = rec_["years"].index(y_to)
                    i_from = rec_["years"].index(y_from)
                    if i_to == i_from + 1:
                        yp = rec_["yoy"][i_to]
                        if yp is not None:
                            member_pcts.append(yp)
            group_means.append(sum(member_pcts) / len(member_pcts) if member_pcts else None)

        if x_labels:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_labels, y=p75s, name="Org P75",
                line=dict(color="rgba(55,138,221,0)"),
                mode="lines", showlegend=False,
                hovertemplate="<b>%{x}</b><br>Org P75: %{y:.2f}%<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=x_labels, y=p25s, name="Org P25–P75 band",
                line=dict(color="rgba(55,138,221,0)"),
                mode="lines", fill="tonexty",
                fillcolor=rgba(LIGHT_BLUE, 0.20),
                hovertemplate="<b>%{x}</b><br>Org P25: %{y:.2f}%<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=x_labels, y=group_means, name="Comparison group mean",
                line=dict(color=CORAL, width=2.5),
                mode="lines+markers",
                marker=dict(size=8),
                connectgaps=False,
                hovertemplate="<b>%{x}</b><br>Group mean: %{y:.2f}%<extra></extra>",
            ))
            apply_layout(fig, height=300, show_legend=True, y_dollars=False)
            fig.update_yaxes(title="YoY raise %", ticksuffix="%")
            chart_card(
                "Comparison group raise vs org middle 50%", fig, key="cmp-org-band",
                subtitle=(
                    "Shaded area = org P25–P75 raise range for each year transition. "
                    "Line = mean raise of selected comparison group members present in both years."
                ),
            )

    # Earnings overlay
    if overlay != "Off":
        show_ot = overlay in ("OT", "Both")
        show_add = overlay in ("Add. earnings", "Both")
        fig = go.Figure()
        for i, name in enumerate(selected):
            rec = records[name]
            color = CMP_COLORS[i % len(CMP_COLORS)]
            if show_ot:
                y_vals = [max(rec["ot"][rec["years"].index(y)], 0) if y in rec["years"] else 0 for y in ry]
                fig.add_trace(go.Bar(
                    x=ry, y=y_vals, name=f"{name} OT",
                    marker=dict(color=rgba(LIME, 0.33), line=dict(color=LIME, width=1)),
                    offsetgroup=name, legendgroup=name,
                ))
            if show_add:
                y_vals = [max(rec["add"][rec["years"].index(y)], 0) if y in rec["years"] else 0 for y in ry]
                fig.add_trace(go.Bar(
                    x=ry, y=y_vals, name=f"{name} Add",
                    marker=dict(color=rgba(color, 0.33), line=dict(color=color, width=1)),
                    offsetgroup=name, legendgroup=name,
                ))
        fig.update_layout(barmode="stack")
        apply_layout(fig, height=280, show_legend=True)
        chart_card(f"Earnings overlay — {overlay}", fig, key="cmp-earn")

    # Heatmap (YoY matrix)
    st.markdown("#### Year-over-year heatmap")
    hm_rows = []
    for i, name in enumerate(selected):
        rec = records[name]
        row = {"Employee": name}
        for y in ry:
            if y in rec["years"]:
                idx = rec["years"].index(y)
                if idx > 0 and rec["years"][idx - 1] in ry:
                    row[str(y)] = rec["yoy"][idx]
                else:
                    row[str(y)] = None
            else:
                row[str(y)] = None
        m = metrics[i]
        row["Growth %"] = m["tg"] if m else None
        row["CAGR %"] = m["ca"] if m else None
        hm_rows.append(row)
    hm = pd.DataFrame(hm_rows)

    def color_yoy(v):
        if v is None or pd.isna(v):
            return "background-color:#F1EFE8;color:#888;"
        if v >= 20:
            return "background-color:#27500A;color:#C0DD97;"
        if v >= 10:
            return "background-color:#3B6D11;color:#EAF3DE;"
        if v >= 5:
            return "background-color:#639922;color:#EAF3DE;"
        if v >= 2:
            return "background-color:#97C459;color:#173404;"
        if v > 0:
            return "background-color:#C0DD97;color:#173404;"
        if v == 0:
            return "background-color:#F1EFE8;color:#5F5E5A;"
        return "background-color:#F7C1C1;color:#791F1F;"

    year_cols = [str(y) for y in ry]
    styled = hm.style.map(color_yoy, subset=year_cols).format(
        {c: lambda v: "—" if v is None or pd.isna(v) else f"{v:.1f}%" for c in year_cols + ["Growth %", "CAGR %"]}
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Summary table
    st.markdown("#### Summary")
    summary_rows = []
    for i, name in enumerate(selected):
        rec = records[name]
        m = metrics[i]
        st_ = cmp_status(rec, sy, ey)
        fy_, ly_ = m["fy"] if m else "", m["ly"] if m else ""
        s_title = rec["titles"][rec["years"].index(fy_)] if m else "—"
        e_title = rec["titles"][rec["years"].index(ly_)] if m else "—"
        ot_vals = [rec["ot"][rec["years"].index(y)] for y in ry
                   if y in rec["years"] and rec["ot"][rec["years"].index(y)] > 0]
        avg_ot = round(sum(ot_vals) / len(ot_vals)) if ot_vals else None
        summary_rows.append({
            "Name": name,
            "Status": st_["status"],
            "Start title": s_title,
            "End title": e_title,
            "Start base": m["bs"] if m else None,
            "End base": m["be"] if m else None,
            "$ Growth": (m["be"] - m["bs"]) if m else None,
            "Growth %": m["tg"] if m else None,
            "CAGR %": m["ca"] if m else None,
            "Avg OT": avg_ot,
        })
    df = pd.DataFrame(summary_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Start base": st.column_config.NumberColumn(format="$%d"),
            "End base": st.column_config.NumberColumn(format="$%d"),
            "$ Growth": st.column_config.NumberColumn(format="$%d"),
            "Avg OT": st.column_config.NumberColumn(format="$%d"),
            "Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "CAGR %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


# ============================================================================
# VIEW: LEADERBOARD
# ============================================================================
@st.cache_data(show_spinner=False)
def lb_compute(sy: int, ey: int, _records_hash: int) -> list[dict]:
    """Compute ranked leaderboard for year range. _records_hash is a cache key."""
    data = load_data()
    records = data["records"]
    people = data["people"]
    org_stats = data["org_stats"]
    cohort_raises = data.get("cohort_raises", {})
    ry = [y for y in data["all_years"] if sy <= y <= ey]
    if str(ey) in org_stats:
        latest_bases_all = []
        for n in people:
            r = records[n]
            if ey in r["years"]:
                latest_bases_all.append(r["base"][r["years"].index(ey)])
        latest_bases_all.sort()
    else:
        latest_bases_all = []
    out = []
    for name in people:
        rec = records[name]
        ir = [y for y in ry if y in rec["years"]]
        if len(ir) < 2:
            continue
        fy, ly = ir[0], ir[-1]
        fi, li = rec["years"].index(fy), rec["years"].index(ly)
        bs, be = rec["base"][fi], rec["base"][li]
        n = ly - fy
        tg = round((be - bs) / bs * 1000) / 10 if n > 0 and bs else 0
        ca = round((pow(be / bs, 1 / n) - 1) * 10000) / 100 if n > 0 and bs else 0
        dg = round(be - bs)
        yv = [rec["yoy"][rec["years"].index(y)] for y in ir[1:] if rec["yoy"][rec["years"].index(y)] is not None]
        ac = None
        if len(yv) >= 3:
            mid = len(yv) // 2
            ac = round((sum(yv[mid:]) / (len(yv) - mid) - sum(yv[:mid]) / mid) * 10) / 10
        ot_vals = [rec["ot"][rec["years"].index(y)] for y in ir if rec["ot"][rec["years"].index(y)] > 0]
        avg_ot = round(sum(ot_vals) / len(ot_vals)) if ot_vals else 0
        by = max(yv) if yv else None
        byy = ir[1:][yv.index(by)] if by is not None else None
        pr = sum(1 for y in ir if (i := rec["years"].index(y)) > 0 and rec["titles"][i] != rec["titles"][i - 1])
        fr = sum(1 for y in ir if rec["yoy"][rec["years"].index(y)] == 0)
        sp = [rec["yoy"][rec["years"].index(y)] if y in rec["years"] else None for y in ir[1:]]
        tier = "steady"
        if tg >= 80 or ca >= 12:
            tier = "rocket"
        elif tg >= 40 or ca >= 7:
            tier = "strong"
        elif tg >= 20:
            tier = "solid"
        latest_base = be
        if latest_bases_all:
            pct = round(sum(1 for v in latest_bases_all if v < latest_base) / len(latest_bases_all) * 100)
        else:
            pct = None
        ly_stats = org_stats.get(str(ly))
        gap_med = round(latest_base - ly_stats["median"]) if ly_stats else None
        gap_mean = round(latest_base - ly_stats["mean"]) if ly_stats else None
        aar = 0
        for y_to in ir[1:]:
            i_to = rec["years"].index(y_to)
            if i_to > 0 and rec["years"][i_to - 1] == y_to - 1:
                py = rec["yoy"][i_to]
                trans = cohort_raises.get(f"{y_to - 1}_{y_to}")
                if py is not None and trans and py > trans["all_cohort"]["mean_pct"]:
                    aar += 1
        out.append({
            "name": name, "tg": tg, "ca": ca, "dg": dg, "ac": ac, "avgOT": avg_ot,
            "by": by, "byy": byy, "pr": pr, "fr": fr, "sp": sp,
            "bs": bs, "be": be, "fy": fy, "ly": ly, "partial": fy > sy or ly < ey,
            "tier": tier, "title": rec["titles"][li], "group": rec["groups"][li],
            "site": rec.get("site", ""), "pctile": pct, "gapMed": gap_med, "gapMean": gap_mean,
            "aar": aar,
        })
    return out


def _clear_raise_window_filters() -> None:
    # Streamlit forbids assigning to a widget's session_state key after the widget
    # has rendered in the current run, so the Clear button uses this as on_click.
    for k in ("lbw_year", "lbw_site", "lbw_grp", "lbw_dept", "lbw_min", "lbw_max"):
        if k in st.session_state:
            del st.session_state[k]


def view_leaderboard(data: dict):
    st.markdown("## Leaderboard")
    st.markdown(
        "<div class='page-sub'>Rank all 4,318 NYPA employees — click the Gap Analysis search "
        "for a gap panel</div>",
        unsafe_allow_html=True,
    )

    tab_top, tab_window = st.tabs(["Top Performers", "Find by Raise Window"])
    with tab_top:
        _view_leaderboard_top_performers(data)
    with tab_window:
        _view_leaderboard_raise_window(data)


def _view_leaderboard_top_performers(data: dict):
    years = data["all_years"]
    people = data["people"]
    records = data["records"]

    MODE_LABELS = {
        "growth": "Total growth %", "cagr": "CAGR", "dollar": "$ gained",
        "accel": "Acceleration", "ot": "Avg OT", "yoy": "Best year",
        "above_avg_raises": "Years above org avg",
    }
    CARD_LABELS = {
        "growth": "Top Total Grower",
        "cagr": "Best CAGR Performer",
        "dollar": "Top $ Earner Increase",
        "accel": "Most Accelerated",
        "ot": "Highest Avg OT",
        "yoy": "Biggest Single Jump",
        "above_avg_raises": "Most Consistent Outperformer",
    }
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
    with col1:
        mode = st.radio("Rank by", list(MODE_LABELS.keys()),
                        format_func=lambda m: MODE_LABELS[m],
                        horizontal=True, key="lb_mode")
    with col2:
        top_n = st.radio("Show", [10, 25, 50], horizontal=True, key="lb_n")
    with col3:
        group_f = st.selectbox("Group filter", [""] + data["groups"],
                                format_func=lambda x: "All groups" if x == "" else x, key="lb_grp")
    with col4:
        site_f = st.selectbox("Site filter", [""] + data.get("sites", []),
                              format_func=lambda x: "All sites" if x == "" else x, key="lb_site")
    with col5:
        sy = st.selectbox("Start", years, index=0, key="lb_sy")
    with col6:
        ey = st.selectbox("End", years, index=len(years) - 1, key="lb_ey")

    if ey < sy:
        st.warning("End year must be >= start year.")
        return

    ranked = lb_compute(sy, ey, 2)

    # Apply filters (group + site)
    if group_f:
        ranked = [d for d in ranked if d["group"] == group_f]
    if site_f:
        ranked = [d for d in ranked if d["site"] == site_f]

    def mode_val(d):
        if mode == "growth":
            return d["tg"]
        if mode == "cagr":
            return d["ca"]
        if mode == "dollar":
            return d["dg"]
        if mode == "accel":
            return d["ac"] if d["ac"] is not None else -999
        if mode == "ot":
            return d["avgOT"]
        if mode == "yoy":
            return d["by"] if d["by"] is not None else -999
        if mode == "above_avg_raises":
            return d.get("aar", 0)
        return 0

    ranked.sort(key=mode_val, reverse=True)
    for i, d in enumerate(ranked):
        d["rank"] = i + 1
    if not ranked:
        st.info("No employees match the filters.")
        return

    # Summary
    g = ranked[0]
    c = sorted(ranked, key=lambda x: x["ca"], reverse=True)[0]
    rockets = sum(1 for d in ranked if d["tier"] == "rocket")
    avg = sum(d["tg"] for d in ranked) / len(ranked)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Avg growth", f"{avg:.1f}%",
                    sub=f"{sy}–{ey}" + (f" · {group_f}" if group_f else "") + (f" · {site_f}" if site_f else ""),
                    color="blue")
    with c2:
        if mode == "growth":
            top_sub = f"{g['tg']}% total"
        elif mode == "cagr":
            top_sub = f"{g['ca']}% / yr"
        elif mode == "dollar":
            top_sub = f"{fmt_dollar(g['dg'])} gained"
        elif mode == "accel":
            top_sub = f"{g['ac']:+.1f} accel" if g['ac'] is not None else "—"
        elif mode == "ot":
            top_sub = f"{fmt_dollar(g['avgOT'])} avg OT"
        elif mode == "yoy":
            top_sub = f"{g['by']}% in {g['byy']}" if g['by'] is not None else "—"
        elif mode == "above_avg_raises":
            n_aar = g.get("aar", 0)
            top_sub = f"{n_aar} year{'s' if n_aar != 1 else ''} above org avg"
        else:
            top_sub = ""
        metric_card(CARD_LABELS[mode], g["name"], sub=top_sub, color="green")
    with c3:
        metric_card("Best CAGR", c["name"], sub=f"{c['ca']}% / yr", color="amber")
    with c4:
        rocket_pct = round(rockets / len(ranked) * 100) if ranked else 0
        metric_card("Rocket tier", f"{rockets} ({rocket_pct}%)",
                    sub=f"of {len(ranked):,} employees · ≥80% growth or ≥12% CAGR",
                    color="purple")

    # Gap analysis
    gap_name = st.selectbox(
        "Gap analysis — select any employee",
        options=[""] + [d["name"] for d in ranked],
        format_func=lambda x: "— none —" if x == "" else x,
        key="lb_gap",
    )

    if gap_name:
        sub = next((d for d in ranked if d["name"] == gap_name), None)
        if sub is not None:
            leader = ranked[0]
            sv = mode_val(sub)
            lv = mode_val(leader)
            total = len(ranked)
            pctile = round((1 - (sub["rank"] - 1) / total) * 100) if total > 1 else 100
            top3 = ranked[min(2, len(ranked) - 1)]
            gap_top3 = mode_val(top3) - sv
            bc_map = {"growth": BLUE, "cagr": GREEN, "dollar": DARK_AMBER, "accel": PURPLE,
                      "ot": GREEN, "yoy": RUST, "above_avg_raises": PINK}
            bc = bc_map[mode]
            rows = list(ranked[:3])
            if sub["rank"] > 3:
                rows.append(sub)
            max_v = max(abs(mode_val(d)) for d in rows) or 0.01
            bars_html = ""
            for d in rows:
                v = mode_val(d)
                is_subj = d["name"] == gap_name
                pct = max(0, round(abs(v) / max_v * 100))
                name_color = BLUE if is_subj else "#111"
                bars_html += (
                    f"<div style='display:grid;grid-template-columns:30px 160px 1fr 80px;"
                    f"gap:8px;align-items:center;margin-bottom:6px;padding:4px;"
                    f"{'background:#E6F1FB18;border-radius:6px;' if is_subj else ''}'>"
                    f"<div style='font-size:11px;font-weight:600;color:#888;text-align:center;'>#{d['rank']}</div>"
                    f"<div style='font-size:11px;color:{name_color};font-weight:{600 if is_subj else 500};"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{d['name']}</div>"
                    f"<div style='height:10px;background:#eee;border-radius:5px;overflow:hidden;'>"
                    f"<div style='height:100%;width:{pct}%;background:{bc};border-radius:5px;'></div></div>"
                    f"<div style='font-size:11px;font-weight:600;text-align:right;'>"
                    f"{fmt_dollar(v) if mode in ('dollar', 'ot') else f'{v:.1f}%' if v is not None else '—'}</div></div>"
                )
            st.markdown(
                f"<div class='gap-panel'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:10px;'>"
                f"<div><div style='font-size:14px;font-weight:600;'>{gap_name} — Gap analysis</div>"
                f"<div style='font-size:10px;color:#888;'>Rank #{sub['rank']} of {total} · "
                f"{pctile}th percentile by {MODE_LABELS[mode]}</div></div></div>"
                f"<div style='display:grid;grid-template-columns:110px 1fr;gap:14px;margin-bottom:12px;'>"
                f"<div style='background:#f5f5f3;border-radius:8px;padding:12px;text-align:center;'>"
                f"<div style='font-size:36px;font-weight:500;color:{BLUE};line-height:1;'>#{sub['rank']}</div>"
                f"<div style='font-size:10px;color:#888;margin-top:2px;'>of {total}</div>"
                f"<div style='font-size:10px;color:#888;margin-top:8px;'>Your {MODE_LABELS[mode]}</div>"
                f"<div style='font-size:18px;font-weight:600;color:#111;'>"
                f"{fmt_dollar(sv) if mode in ('dollar', 'ot') else f'{sv:.1f}%' if sv is not None else '—'}</div></div>"
                f"<div>{bars_html}</div></div>"
                f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;'>"
                f"<div style='background:#f5f5f3;border-radius:8px;padding:10px 12px;'>"
                f"<div style='font-size:10px;color:#888;'>Gap to leader</div>"
                f"<div style='font-size:12px;font-weight:600;'>"
                f"{fmt_dollar(lv - sv) if mode in ('dollar', 'ot') else f'{lv - sv:.1f} pts'}</div></div>"
                f"<div style='background:#f5f5f3;border-radius:8px;padding:10px 12px;'>"
                f"<div style='font-size:10px;color:#888;'>Gap to top 3</div>"
                f"<div style='font-size:12px;font-weight:600;'>"
                f"{fmt_dollar(gap_top3) if mode in ('dollar', 'ot') else f'{gap_top3:.1f} pts'}</div></div>"
                f"<div style='background:#f5f5f3;border-radius:8px;padding:10px 12px;'>"
                f"<div style='font-size:10px;color:#888;'>Tier</div>"
                f"<div style='font-size:12px;font-weight:600;'>{sub['tier']}</div></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            # PL-034 — Personal raise pattern vs org P25–P75 band
            cohort_data = data.get("cohort_raises", {})
            if cohort_data:
                ry_lb = [y for y in years if sy <= y <= ey]
                yy_lb = ry_lb[1:]
                rec_p = records.get(gap_name, {})
                p_years = rec_p.get("years", [])
                p_yoy = rec_p.get("yoy", [])
                x_labels, p25s, p75s, person_pcts = [], [], [], []
                for y_to in yy_lb:
                    y_from = y_to - 1
                    c_band = cohort_data.get(f"{y_from}_{y_to}")
                    if not c_band:
                        continue
                    x_labels.append(f"{y_from}→{str(y_to)[-2:]}")
                    p25s.append(c_band["org_p25_pct"])
                    p75s.append(c_band["org_p75_pct"])
                    if y_from in p_years and y_to in p_years:
                        i_to = p_years.index(y_to)
                        i_from = p_years.index(y_from)
                        if i_to == i_from + 1:
                            person_pcts.append(p_yoy[i_to])
                        else:
                            person_pcts.append(None)
                    else:
                        person_pcts.append(None)

                if x_labels:
                    p_color = avatar_color(gap_name)
                    fig_pat = go.Figure()
                    fig_pat.add_trace(go.Scatter(
                        x=x_labels, y=p75s, name="Org P75",
                        line=dict(color="rgba(55,138,221,0)"),
                        mode="lines", showlegend=False,
                        hovertemplate="<b>%{x}</b><br>Org P75: %{y:.2f}%<extra></extra>",
                    ))
                    fig_pat.add_trace(go.Scatter(
                        x=x_labels, y=p25s, name="Org P25–P75 band",
                        line=dict(color="rgba(55,138,221,0)"),
                        mode="lines", fill="tonexty",
                        fillcolor=rgba(LIGHT_BLUE, 0.20),
                        hovertemplate="<b>%{x}</b><br>Org P25: %{y:.2f}%<extra></extra>",
                    ))
                    pos_labels = []
                    for v, p25, p75 in zip(person_pcts, p25s, p75s):
                        if v is None:
                            pos_labels.append("—")
                        elif v > p75:
                            pos_labels.append("above middle 50%")
                        elif v < p25:
                            pos_labels.append("below middle 50%")
                        else:
                            pos_labels.append("inside middle 50%")
                    customdata = list(zip(p25s, p75s, pos_labels))
                    fig_pat.add_trace(go.Scatter(
                        x=x_labels, y=person_pcts, name=f"{gap_name} raise",
                        line=dict(color=p_color, width=2.5),
                        mode="lines+markers",
                        marker=dict(size=8),
                        connectgaps=False,
                        customdata=customdata,
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Raise: %{y:.2f}%<br>"
                            "Org P25: %{customdata[0]:.2f}%<br>"
                            "Org P75: %{customdata[1]:.2f}%<br>"
                            "Position: %{customdata[2]}<extra></extra>"
                        ),
                    ))
                    apply_layout(fig_pat, height=300, show_legend=True, y_dollars=False)
                    fig_pat.update_yaxes(title="YoY raise %", ticksuffix="%")
                    chart_card(
                        f"{gap_name} — raise pattern vs. org middle 50%",
                        fig_pat, key="lb-gap-raise-pattern",
                        subtitle=(
                            "Shaded area = org P25–P75 raise range. "
                            "Line = this person's actual YoY raise. "
                            "Above the band = above 75% of org. "
                            "Below the band = below 75% of org."
                        ),
                    )

    # Top N chart
    top = ranked[:top_n]
    col_l, col_r = st.columns(2)
    with col_l:
        mode_colors = {"growth": BLUE, "cagr": GREEN, "dollar": DARK_AMBER,
                       "accel": PURPLE, "ot": GREEN, "yoy": RUST,
                       "above_avg_raises": PINK}
        bar_col = mode_colors[mode]
        names = [d["name"] for d in top]
        values = [mode_val(d) for d in top]
        labels = [fmt_dollar(v) if mode in ("dollar", "ot") else (f"{v:.1f}%" if v is not None else "—")
                  for v in values]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=names[::-1], x=values[::-1], orientation="h",
            marker=dict(color=bar_col),
            text=labels[::-1], textposition="outside", textfont=dict(size=10),
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        ))
        apply_layout(fig, height=max(260, 22 * len(top)), y_dollars=False)
        fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.05)")
        chart_card(f"Top {top_n} by {CARD_LABELS[mode]}", fig, key="lb-bar")

    with col_r:
        all_vals = [mode_val(d) for d in ranked if mode_val(d) is not None]
        sorted_vals = sorted(all_vals)
        n = len(sorted_vals)
        outlier_count = 0
        subtitle = ""

        if n > 20:
            if mode == "accel":
                p5_idx = max(0, int(n * 0.05))
                p95_idx = min(n - 1, int(n * 0.95))
                x_min = sorted_vals[p5_idx]
                x_max = sorted_vals[p95_idx]
                outlier_count = sum(1 for v in all_vals if v < x_min or v > x_max)
                cap_label = "5th–95th percentile"
            else:
                p90_idx = min(n - 1, int(n * 0.90))
                x_min = min(sorted_vals)
                x_max = sorted_vals[p90_idx]
                outlier_count = sum(1 for v in all_vals if v > x_max)
                cap_label = "90th percentile"

            filtered_vals = [v for v in all_vals if x_min <= v <= x_max]

            if outlier_count > 0:
                subtitle = f"X-axis capped at {cap_label}. {outlier_count} outliers not shown."
        else:
            filtered_vals = all_vals
            x_min = min(sorted_vals) if sorted_vals else 0
            x_max = max(sorted_vals) if sorted_vals else 1

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=filtered_vals,
            nbinsx=50,
            marker=dict(color="rgba(55, 138, 221, 0.73)",
                        line=dict(color=LIGHT_BLUE, width=1)),
        ))
        fig.update_xaxes(range=[x_min, x_max])
        apply_layout(fig, height=max(260, 22 * len(top)), y_dollars=False)
        chart_card(f"Distribution of {CARD_LABELS[mode]} across all employees",
                   fig, key="lb-dist", subtitle=subtitle)

    # Full table
    st.markdown("#### Full leaderboard")
    st.caption("Click a row to open that person's Individual Profile.")
    table_rows = []
    for d in ranked:
        table_rows.append({
            "Rank": d["rank"],
            "Name": d["name"],
            "Title": d["title"],
            "Group": d["group"],
            "Site": d["site"],
            "Tier": d["tier"],
            "Growth %": d["tg"],
            "CAGR %": d["ca"],
            "$ gained": d["dg"],
            "Accel": d["ac"],
            "Avg OT": d["avgOT"],
            "Best year %": d["by"],
            "Best year": d["byy"],
            "Yrs > org avg": d.get("aar", 0),
            "Title changes": d["pr"],
            "Freezes": d["fr"],
        })
    df = pd.DataFrame(table_rows)
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "$ gained": st.column_config.NumberColumn(format="$%d"),
            "Avg OT": st.column_config.NumberColumn(format="$%d"),
            "Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "CAGR %": st.column_config.NumberColumn(format="%.1f%%"),
            "Accel": st.column_config.NumberColumn(
                format="%.1f",
                help=(
                    "Difference in average YoY raise % between the second half of the "
                    "selected range and the first half. Positive = speeding up, "
                    "negative = slowing down."
                ),
            ),
            "Best year %": st.column_config.NumberColumn(format="%.1f%%"),
            "Yrs > org avg": st.column_config.NumberColumn(
                format="%d",
                help=(
                    "Number of year transitions in the selected range where this "
                    "employee's YoY raise exceeded the org's same-cohort mean for "
                    "that transition."
                ),
            ),
            "Tier": st.column_config.TextColumn(
                help=(
                    "Rocket: ≥80% growth or ≥12% CAGR · "
                    "Strong: ≥40% growth or ≥7% CAGR · "
                    "Solid: ≥20% growth · "
                    "Steady: below"
                )
            ),
        },
        height=440,
        on_select="rerun",
        selection_mode="single-row",
        key="lb_table",
    )
    sel_rows = event.selection.rows
    if sel_rows and 0 <= sel_rows[0] < len(df):
        selected_name = df.iloc[sel_rows[0]]["Name"]
        st.session_state["_nav_redirect"] = "Individual profile"
        st.session_state["ind_person"] = selected_name
        # Clear the dataframe's stored selection so returning to this tab later
        # doesn't auto-fire the redirect on the same stale selection.
        if "lb_table" in st.session_state:
            del st.session_state["lb_table"]
        st.rerun()


def _view_leaderboard_raise_window(data: dict):
    years = data["all_years"]
    records = data["records"]

    year_pairs = [(years[i], years[i + 1]) for i in range(len(years) - 1)]

    col_y, col_s, col_g, col_d, col_min, col_max, col_clear = st.columns(
        [1.6, 1.2, 1.2, 1.6, 0.9, 0.9, 0.7]
    )
    with col_y:
        sel_pair = st.selectbox(
            "Year transition",
            year_pairs,
            index=len(year_pairs) - 1,
            format_func=lambda p: f"{p[0]} → {p[1]}",
            key="lbw_year",
        )
    with col_s:
        site_f = st.selectbox(
            "Site filter", [""] + data.get("sites", []),
            format_func=lambda x: "All sites" if x == "" else x, key="lbw_site",
        )
    with col_g:
        grp_f = st.selectbox(
            "Group filter", [""] + data["groups"],
            format_func=lambda x: "All groups" if x == "" else x, key="lbw_grp",
        )
    with col_d:
        dept_f = st.selectbox(
            "Dept filter", [""] + data["top_depts"],
            format_func=lambda x: "All departments" if x == "" else x, key="lbw_dept",
        )
    with col_min:
        min_pct = st.number_input(
            "Min raise %", value=0.0, step=0.1, format="%.1f", key="lbw_min",
        )
    with col_max:
        max_pct = st.number_input(
            "Max raise %", value=100.0, step=0.1, format="%.1f", key="lbw_max",
        )
    with col_clear:
        st.markdown("&nbsp;")
        st.button("Clear", key="lbw_clear", on_click=_clear_raise_window_filters)

    if max_pct < min_pct:
        st.warning("Max raise % must be greater than or equal to min raise %.")
        return

    y1, y2 = sel_pair

    eligible = 0
    rows = []
    for name, rec in records.items():
        rec_years = rec.get("years", [])
        if y1 not in rec_years or y2 not in rec_years:
            continue
        i1 = rec_years.index(y1)
        i2 = rec_years.index(y2)
        prev_base = rec["base"][i1]
        curr_base = rec["base"][i2]
        if not prev_base or prev_base <= 0 or not curr_base:
            continue
        if site_f and (rec.get("site") or "") != site_f:
            continue
        if grp_f and rec["groups"][i2] != grp_f:
            continue
        if dept_f and rec["depts"][i2] != dept_f:
            continue
        # Past all non-raise filters → counts toward the eligible denominator.
        eligible += 1
        raise_pct = (curr_base - prev_base) / prev_base * 100
        if raise_pct < min_pct or raise_pct > max_pct:
            continue
        title_changed = (
            (rec["titles"][i1] or "").strip().lower()
            != (rec["titles"][i2] or "").strip().lower()
        )
        rows.append({
            "Name": name,
            "Title": rec["titles"][i2],
            "Site": rec.get("site") or "—",
            "Group": rec["groups"][i2],
            "Dept": rec["depts"][i2],
            "Title changed": "Yes" if title_changed else "No",
            "Prev salary": prev_base,
            "New salary": curr_base,
            "Raise %": raise_pct,
        })

    rows.sort(key=lambda r: r["Raise %"], reverse=True)

    matched = len(rows)
    match_pct = (matched / eligible * 100) if eligible else 0.0
    filter_label = site_f or grp_f or dept_f
    where = f"at {filter_label}" if filter_label else "org-wide"

    if not rows:
        st.info(
            f"{matched:,} of {eligible:,} ({match_pct:.1f}%) match. "
            "Try widening the raise window or clearing site/group/dept filters."
        )
        return

    st.markdown(
        f"**{matched:,}** of {eligible:,} ({match_pct:.1f}%) {where} "
        f"had raises between {min_pct:.1f}% and {max_pct:.1f}% in {y1}→{y2}"
    )
    with_change = sum(1 for r in rows if r["Title changed"] == "Yes")
    without_change = matched - with_change
    pct_with = with_change / matched * 100
    pct_without = without_change / matched * 100
    st.markdown(
        f"Of those: **{with_change:,}** ({pct_with:.1f}%) had a title change "
        f"· {without_change:,} ({pct_without:.1f}%) did not"
    )
    st.caption(
        "Select rows below, then click 'View selected' to open profile or comparison."
    )

    df = pd.DataFrame(rows)
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Prev salary": st.column_config.NumberColumn(format="$%d"),
            "New salary": st.column_config.NumberColumn(format="$%d"),
            "Raise %": st.column_config.NumberColumn(format="%.2f%%"),
            "Title changed": st.column_config.TextColumn(
                help="Title differed between the year_from and year_to rows (case-insensitive).",
            ),
        },
        height=440,
        on_select="rerun",
        selection_mode="multi-row",
        key="lbw_table",
    )
    # on_select="rerun" stays so the count below updates live as boxes are
    # toggled. Routing only runs from the explicit "View selected" button so
    # selecting a single row doesn't immediately yank the user to a new view.
    sel_rows = list(event.selection.rows) if event and event.selection else []
    n_selected = len(sel_rows)
    if n_selected == 0:
        st.caption("Select 1 row to view profile, or 2-6 to compare.")
    else:
        col_count, col_btn = st.columns([3, 1])
        with col_count:
            destination = (
                "→ Individual Profile" if n_selected == 1
                else "→ Comparison view"
            )
            cap_note = " (capped at 6 by Raise %)" if n_selected > 6 else ""
            st.caption(f"**{n_selected}** selected · {destination}{cap_note}")
        with col_btn:
            if st.button("View selected", key="lbw_view_btn", type="primary"):
                selected_names = [
                    df.iloc[i]["Name"] for i in sel_rows
                    if 0 <= i < len(df)
                ]
                if len(selected_names) == 1:
                    # Single row → Individual Profile (PL-074 behavior preserved)
                    st.session_state["_nav_redirect"] = "Individual profile"
                    st.session_state["ind_person"] = selected_names[0]
                elif len(selected_names) >= 2:
                    # Multi-row → Comparison view, capped at 6 (rows are sorted
                    # by Raise % desc, so the cap takes the top performers).
                    capped = selected_names[:6]
                    st.session_state["_nav_redirect"] = "Comparison"
                    st.session_state["cmp_sel"] = capped
                    if len(selected_names) > 6:
                        st.session_state["_lbw_cap_warning"] = (
                            f"Selected {len(selected_names)} people; "
                            f"Comparison capped at 6 — showing top 6 by Raise %."
                        )
                # Clear the dataframe's stored selection so returning to this
                # tab later starts fresh.
                if "lbw_table" in st.session_state:
                    del st.session_state["lbw_table"]
                st.rerun()


# ============================================================================
# VIEW: ORG SNAPSHOT
# ============================================================================
def _clear_org_filters() -> None:
    # Streamlit forbids assigning to a widget's session_state key after the widget
    # has rendered in the current run, so the Clear button uses this as on_click.
    for k in ("org_site", "org_grp", "org_dept"):
        st.session_state[k] = ""


def view_org(data: dict):
    st.markdown("## Org snapshot")
    st.markdown(
        "<div class='page-sub'>Organization-wide salary distribution, trends, "
        "and department breakdowns</div>",
        unsafe_allow_html=True,
    )

    years = data["all_years"]
    os_ = data["org_stats"]

    col_yr, col_site, col_grp, col_dept, col_clear = st.columns([2, 1.5, 1.5, 2, 1])
    with col_yr:
        dist_year = st.selectbox("Distribution year", years, index=len(years) - 1, key="org_yr")
    with col_site:
        site_f = st.selectbox("Site filter", [""] + data.get("sites", []),
                              format_func=lambda x: "All sites" if x == "" else x, key="org_site")
    with col_grp:
        grp_f = st.selectbox("Group filter", [""] + data["groups"],
                             format_func=lambda x: "All groups" if x == "" else x, key="org_grp")
    with col_dept:
        dept_f = st.selectbox("Dept filter", [""] + data["top_depts"],
                              format_func=lambda x: "All departments" if x == "" else x, key="org_dept")
    with col_clear:
        st.markdown("&nbsp;")
        st.button("Clear", key="org_clear", on_click=_clear_org_filters)

    filter_label = site_f or grp_f or dept_f
    filter_stats = None
    if site_f:
        filter_stats = data["site_stats"].get(site_f)
    elif grp_f:
        filter_stats = data["group_stats"].get(grp_f)
    elif dept_f:
        filter_stats = data["dept_stats"].get(dept_f)

    if filter_label:
        cnt = filter_stats.get(str(dist_year), {}).get("count") if filter_stats else None
        st.markdown(
            f"<div style='padding:8px 12px;background:#E6F1FB;border:1px solid #B5D4F4;"
            f"border-radius:8px;margin-bottom:12px;font-size:12px;color:#0C447C;'>"
            f"Filtered to: <strong>{filter_label}</strong>"
            f"{' · ' + str(cnt) + ' employees in ' + str(dist_year) if cnt else ''}"
            f"</div>",
            unsafe_allow_html=True,
        )

    s17 = os_["2017"]
    s_dy = os_.get(str(dist_year), os_["2024"])
    og = round((s_dy["median"] - s17["median"]) / s17["median"] * 100)
    spread = round((s_dy["mean"] - s_dy["median"]) / s_dy["median"] * 100)
    f_dy = (filter_stats or {}).get(str(dist_year)) if filter_stats else None
    f_v = round((f_dy["median"] - s_dy["median"]) / s_dy["median"] * 100) if f_dy else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card(f"Org median ({dist_year})", fmt_dollar(s_dy["median"]),
                    sub="Full org", color="blue",
                    delta=f"↑ {og}% since 2017", delta_dir="up")
    with c2:
        metric_card(f"Org mean ({dist_year})", fmt_dollar(s_dy["mean"]),
                    sub=f"vs median {fmt_dollar(s_dy['median'])}", color="green",
                    delta=f"gap: {fmt_dollar(s_dy['mean'] - s_dy['median'], signed=True)}",
                    delta_dir="up" if s_dy["mean"] > s_dy["median"] else "flat")
    with c3:
        metric_card("Mean vs median gap", f"{spread}%",
                    sub=f"{dist_year} (higher = top-heavy)", color="amber")
    with c4:
        metric_card(f"Headcount ({dist_year})", f"{s_dy['count']:,}",
                    sub="Active employees", color="purple",
                    delta=f"vs 2017: {'+' if s_dy['count'] > s17['count'] else ''}{s_dy['count'] - s17['count']}",
                    delta_dir="up" if s_dy["count"] > s17["count"] else "dn")
    with c5:
        if f_dy:
            metric_card(f"{filter_label} median", fmt_dollar(f_dy["median"]),
                        sub=f"vs org {fmt_dollar(s_dy['median'])}", color="teal",
                        delta=f"{'↑' if f_v > 0 else '↓'} {abs(f_v)}% vs org",
                        delta_dir="up" if (f_v or 0) > 0 else "dn")
        else:
            p90 = s_dy.get("p90") or os_["2024"].get("p90")
            metric_card(f"P90 salary ({dist_year})", fmt_dollar(p90),
                        sub="Top 10% earn above", color="teal",
                        delta=f"{fmt_dollar((p90 or 0) - s17.get('p90', 0), signed=True)} since 2017",
                        delta_dir="up")
    with c6:
        prev_year = dist_year - 1
        yr_pair = data.get("cohort_raises", {}).get(f"{prev_year}_{dist_year}")
        # PL-072: pick the slice matching the active filter; mirrors the elif chain
        # used by the rest of view_org's filter handling (one filter at a time).
        filter_used = site_f or grp_f or dept_f
        realized = None
        if yr_pair:
            if site_f:
                realized = yr_pair.get("by_site", {}).get(site_f)
            elif grp_f:
                realized = yr_pair.get("by_group", {}).get(grp_f)
            elif dept_f:
                realized = yr_pair.get("by_dept", {}).get(dept_f)
            else:
                realized = yr_pair

        if realized and "all_cohort" in realized:
            ac_ = realized["all_cohort"]
            title = (
                f"Realized Raise — {filter_used} ({dist_year})"
                if filter_used else f"Realized Raise ({dist_year})"
            )
            metric_card(
                title,
                f"{ac_['mean_pct']:.2f}%",
                sub=(
                    f"n={ac_['n']:,} · median {ac_['median_pct']:.2f}% · "
                    f"{realized['raise_recipients']['pct_of_cohort']:.0f}% got raise"
                ),
                color="coral",
            )
        elif filter_used:
            metric_card(
                f"Realized Raise — {filter_used} ({dist_year})", "—",
                sub="Insufficient sample for this slice", color="coral",
            )
        else:
            metric_card(
                f"Realized Raise ({dist_year})", "—",
                sub="No prior year for comparison", color="coral",
            )

    # Realized YoY raise history (same-cohort)
    cohort_data = data.get("cohort_raises", {})
    if cohort_data:
        cohort_mode = st.radio(
            "Cohort cut",
            ["All cohort (incl. frozen)", "Raise recipients only"],
            horizontal=True,
            index=0,
            key="org_cohort_mode",
            help=(
                "All cohort: includes employees who got $0 raise (frozen). "
                "Raise recipients only: excludes $0 raises, shows what raises actually were. "
                "Gap between them = workforce that was frozen."
            ),
        )
        cut_key = "all_cohort" if cohort_mode == "All cohort (incl. frozen)" else "raise_recipients"
        transitions = sorted(cohort_data.keys())
        # PL-073: pick slice matching active filter for each transition; mirrors the
        # elif chain c6 uses so the chart and card stay in lockstep with the filter.
        chart_filter = site_f or grp_f or dept_f
        x_labels, means, medians, customdata = [], [], [], []
        for t in transitions:
            c_org = cohort_data[t]
            if site_f:
                c = c_org.get("by_site", {}).get(site_f)
            elif grp_f:
                c = c_org.get("by_group", {}).get(grp_f)
            elif dept_f:
                c = c_org.get("by_dept", {}).get(dept_f)
            else:
                c = c_org
            if not c:
                continue
            cut = c[cut_key]
            x_labels.append(f"{c_org['year_from']}→{str(c_org['year_to'])[-2:]}")
            means.append(cut["mean_pct"])
            medians.append(cut["median_pct"])
            customdata.append([
                cut["n"],
                cut["mean_dollar"],
                cut["median_dollar"],
                c["raise_recipients"]["pct_of_cohort"],
            ])
        if not x_labels:
            st.info(
                f"No raise history available for '{chart_filter}' across recorded years."
            )
        else:
            hover_tpl = (
                "<b>%{x}</b><br>%{y:.2f}%<br>"
                "n=%{customdata[0]:,}<br>"
                "mean $: $%{customdata[1]:,}<br>"
                "median $: $%{customdata[2]:,}<br>"
                "%{customdata[3]:.1f}% got a raise"
                "<extra>%{fullData.name}</extra>"
            )
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_labels, y=means, name="Mean %",
                marker=dict(color=BLUE),
                customdata=customdata,
                hovertemplate=hover_tpl,
            ))
            fig.add_trace(go.Bar(
                x=x_labels, y=medians, name="Median %",
                marker=dict(color=AMBER),
                customdata=customdata,
                hovertemplate=hover_tpl,
            ))
            fig.update_layout(barmode="group")
            apply_layout(fig, height=300, show_legend=True, y_dollars=False)
            fig.update_yaxes(title="YoY raise %", ticksuffix="%")
            cut_subtitle = (
                "All cohort — includes $0 raises (frozen employees pull means down)."
                if cut_key == "all_cohort" else
                "Raise recipients only — excludes frozen employees, shows the actual raise distribution."
            )
            chart_title = (
                f"Realized YoY Raise History — Same-Cohort — {chart_filter}"
                if chart_filter
                else "Realized YoY Raise History — Same-Cohort"
            )
            chart_card(chart_title, fig, key="org-cohort-raises", subtitle=cut_subtitle)

    # Distribution chart
    col_l, col_r = st.columns(2)
    with col_l:
        bkts = data["dist_by_year"].get(str(dist_year), [])
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[b["l"] for b in bkts], y=[b["c"] for b in bkts],
            marker=dict(color=rgba(LIGHT_BLUE, 0.33), line=dict(color=LIGHT_BLUE, width=1)),
            hovertemplate="%{x}<br>%{y:,} employees<extra></extra>",
        ))
        apply_layout(fig, height=300, y_dollars=False)
        fig.update_yaxes(title="Employees")
        chart_card(f"Salary distribution — {dist_year}", fig, key="org-dist")

    with col_r:
        fig = go.Figure()
        om = [os_[str(y)]["median"] for y in years]
        omn = [os_[str(y)]["mean"] for y in years]
        fig.add_trace(go.Scatter(x=years, y=om, mode="lines+markers", name="Org median",
                                  line=dict(color=BLUE, width=2.5), marker=dict(size=7)))
        fig.add_trace(go.Scatter(x=years, y=omn, mode="lines+markers", name="Org mean",
                                  line=dict(color=LIGHT_BLUE, width=1.5, dash="dash"),
                                  marker=dict(size=5)))
        if filter_stats:
            fm = [filter_stats.get(str(y), {}).get("median") for y in years]
            fig.add_trace(go.Scatter(x=years, y=fm, mode="lines+markers",
                                      name=f"{filter_label} median",
                                      line=dict(color=GREEN, width=2.5), marker=dict(size=7),
                                      connectgaps=True))
        apply_layout(fig, height=300, show_legend=True)
        chart_card("Median vs mean — 2017 to 2024", fig, key="org-trend")

    # Headcount + Percentile bands
    col_l, col_r = st.columns(2)
    with col_l:
        hcs = [os_[str(y)]["count"] for y in years]
        colors = [DARK_BLUE if y == 2024 else rgba(LIGHT_BLUE, 0.53) for y in years]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=hcs, marker=dict(color=colors),
                             text=[f"{v:,}" for v in hcs], textposition="outside",
                             textfont=dict(size=10)))
        min_y = round(min(hcs) * 0.95)
        fig.update_yaxes(range=[min_y, max(hcs) * 1.08])
        apply_layout(fig, height=260, y_dollars=False)
        chart_card("Headcount by year", fig, key="org-hc")

    with col_r:
        p25 = [os_[str(y)].get("p25") for y in years]
        p75 = [os_[str(y)].get("p75") for y in years]
        p90 = [os_[str(y)].get("p90") for y in years]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=p90, mode="lines+markers", name="P90",
                                  line=dict(color="#0C447C", width=2.5), marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=years, y=p75, mode="lines+markers", name="P75",
                                  line=dict(color=LIGHT_BLUE, width=2), marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=years, y=p25, mode="lines+markers", name="P25",
                                  line=dict(color="#85B7EB", width=1.5), marker=dict(size=6)))
        apply_layout(fig, height=260, show_legend=True)
        chart_card("Percentile bands — P25 / P75 / P90", fig, key="org-bands")

    # Group comparison chart
    st.markdown("#### Group comparison — median salary by group")
    fig = go.Figure()
    for i, grp in enumerate(data["groups"]):
        gs = data["group_stats"].get(grp, {})
        vals = [gs.get(str(y), {}).get("median") for y in years]
        fig.add_trace(go.Scatter(
            x=years, y=vals, mode="lines+markers", name=grp,
            line=dict(color=CMP_COLORS[i % len(CMP_COLORS)], width=2),
            marker=dict(size=6),
        ))
    apply_layout(fig, height=300, show_legend=True)
    chart_card("Group median — 2017 to 2024", fig, key="org-grp")

    # Dept growth table
    st.markdown("#### Department growth ranking — 2017 to 2024")
    dpg = data["dept_growth"]
    df = pd.DataFrame([
        {"#": i + 1, "Department": d["dept"], "2017 median": d["m17"],
         "2024 median": d["m24"], "Growth %": d["growth"], "Count": d["count"]}
        for i, d in enumerate(sorted(dpg, key=lambda x: x["growth"], reverse=True))
    ])
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "2017 median": st.column_config.NumberColumn(format="$%d"),
            "2024 median": st.column_config.NumberColumn(format="$%d"),
            "Growth %": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0,
                max_value=max(d["growth"] for d in dpg),
            ),
        },
        height=420,
    )


# ============================================================================
# Main app
# ============================================================================
def main():
    data = load_data()

    # Apply pending navigation redirects (e.g. row clicks on the Leaderboard
    # raise-window table) before the sidebar radio renders. Streamlit forbids
    # writing to a widget-bound key after the widget has rendered, so the
    # redirect target is parked on a non-widget key and consumed here.
    pending_nav = st.session_state.pop("_nav_redirect", None)
    if pending_nav:
        st.session_state["nav"] = pending_nav

    with st.sidebar:
        st.markdown(
            "<div style='padding:8px 4px 14px;border-bottom:1px solid rgba(255,255,255,0.08);"
            "margin-bottom:8px;'><div style='font-size:12px;font-weight:700;letter-spacing:.12em;"
            "text-transform:uppercase;'>NYPA Salary Metrics</div>"
            "<div style='font-size:10px;color:rgba(255,255,255,0.65);margin-top:3px;'>"
            "We all Contribute, We all Belong!</div></div>",
            unsafe_allow_html=True,
        )
        nav = st.radio(
            "Views",
            ["Home", "Individual profile", "Comparison", "Leaderboard", "Org snapshot"],
            label_visibility="collapsed",
            key="nav",
        )
        st.markdown(
            "<div style='margin-top:auto;padding-top:20px;border-top:1px solid rgba(255,255,255,0.08);"
            "font-size:9px;color:rgba(255,255,255,0.55);line-height:1.6;margin-top:40px;'>"
            "SeeThroughNY · data.ny.gov<br>Power Authority of NY<br>"
            "2017–2024 · 4,318 employees</div>",
            unsafe_allow_html=True,
        )

    if nav == "Home":
        view_home(data)
    elif nav == "Individual profile":
        view_individual(data)
    elif nav == "Comparison":
        view_comparison(data)
    elif nav == "Leaderboard":
        view_leaderboard(data)
    elif nav == "Org snapshot":
        view_org(data)


if __name__ == "__main__":
    main()
