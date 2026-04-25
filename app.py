"""NYPA Salary Analytics — Streamlit app.

Four views (Individual Profile, Comparison, Leaderboard, Org Snapshot) plus a
Home overview. All data (including site lookups) comes from the pre-computed
nypa_data.json.
"""
from __future__ import annotations

import json
import math
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


# ============================================================================
# VIEW: INDIVIDUAL PROFILE
# ============================================================================
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

    c1, c2, c3, c4 = st.columns(4)
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
        metric_card(f"Org percentile ({ly})",
                    f"{int(pct_latest)}th" if pct_latest is not None else "—",
                    sub=f"of {org_stats[str(ly)]['count']:,} employees", color="purple")
    with c4:
        start_pct = rec.get("pctile", [None])[0]
        delta_pct = None
        if start_pct is not None and pct_latest is not None:
            delta_pct = round(pct_latest - start_pct)
        metric_card("Percentile trend",
                    f"{'+' if (delta_pct or 0) >= 0 else ''}{delta_pct}pts" if delta_pct is not None else "—",
                    sub=f"since {fy}", color="amber")

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
        labels = [fmt_pct(p, signed=True) if p is not None else "" for p in pct]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=yy, y=dollars, marker=dict(color=colors),
            text=labels, textposition="outside", textfont=dict(size=10),
            hovertemplate="<b>%{x}</b><br>%{text}<br>%{y:$,.0f}<extra></extra>",
        ))
        apply_layout(fig, height=260)
        chart_card("Year-over-year change ($ and %)", fig, key="ind-yoy")

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


def view_comparison(data: dict):
    st.markdown("## Comparison")
    st.markdown(
        "<div class='page-sub'>Add up to 6 employees to compare salary trajectories "
        "side by side</div>",
        unsafe_allow_html=True,
    )

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

    # Pill display + remove
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

    # Indexed growth chart
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
                if y in rec["years"] and sb:
                    b = rec["base"][rec["years"].index(y)]
                    y_data.append(round(b / sb * 1000) / 10)
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
        chart_card("Indexed growth — start=100", fig, key="cmp-norm")

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
        out.append({
            "name": name, "tg": tg, "ca": ca, "dg": dg, "ac": ac, "avgOT": avg_ot,
            "by": by, "byy": byy, "pr": pr, "fr": fr, "sp": sp,
            "bs": bs, "be": be, "fy": fy, "ly": ly, "partial": fy > sy or ly < ey,
            "tier": tier, "title": rec["titles"][li], "group": rec["groups"][li],
            "site": rec.get("site", ""), "pctile": pct, "gapMed": gap_med, "gapMean": gap_mean,
        })
    return out


def view_leaderboard(data: dict):
    st.markdown("## Leaderboard")
    st.markdown(
        "<div class='page-sub'>Rank all 4,318 NYPA employees — click the Gap Analysis search "
        "for a gap panel</div>",
        unsafe_allow_html=True,
    )

    years = data["all_years"]
    people = data["people"]

    MODE_LABELS = {
        "growth": "Total growth %", "cagr": "CAGR", "dollar": "$ gained",
        "accel": "Acceleration", "ot": "Avg OT", "yoy": "Best year",
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

    ranked = lb_compute(sy, ey, 1)

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
        metric_card("Top grower", g["name"], sub=f"{g['tg']}% total", color="green")
    with c3:
        metric_card("Best CAGR", c["name"], sub=f"{c['ca']}% / yr", color="amber")
    with c4:
        metric_card("Rocket tier", f"{rockets}", sub=f"of {len(ranked)} employees", color="purple")

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
                      "ot": GREEN, "yoy": RUST}
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

    # Top N chart
    top = ranked[:top_n]
    col_l, col_r = st.columns(2)
    with col_l:
        mode_colors = {"growth": BLUE, "cagr": GREEN, "dollar": DARK_AMBER,
                       "accel": PURPLE, "ot": GREEN, "yoy": RUST}
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
        chart_card(f"Top {top_n} — {MODE_LABELS[mode]}", fig, key="lb-bar")

    with col_r:
        all_vals = [mode_val(d) for d in ranked if mode_val(d) is not None]
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=all_vals, nbinsx=30,
            marker=dict(color="rgba(55, 138, 221, 0.73)",
                        line=dict(color=LIGHT_BLUE, width=1)),
        ))
        apply_layout(fig, height=max(260, 22 * len(top)), y_dollars=False)
        chart_card("Growth distribution — all employees", fig, key="lb-dist")

    # Full table
    st.markdown("#### Full leaderboard")
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
            "Title changes": d["pr"],
            "Freezes": d["fr"],
        })
    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "$ gained": st.column_config.NumberColumn(format="$%d"),
            "Avg OT": st.column_config.NumberColumn(format="$%d"),
            "Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "CAGR %": st.column_config.NumberColumn(format="%.1f%%"),
            "Accel": st.column_config.NumberColumn(format="%.1f"),
            "Best year %": st.column_config.NumberColumn(format="%.1f%%"),
        },
        height=440,
    )


# ============================================================================
# VIEW: ORG SNAPSHOT
# ============================================================================
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
        if st.button("Clear", key="org_clear"):
            for k in ("org_site", "org_grp", "org_dept"):
                st.session_state[k] = ""
            st.rerun()

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

    c1, c2, c3, c4, c5 = st.columns(5)
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
