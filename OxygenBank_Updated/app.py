"""Oxygen Bank - Streamlit dashboard.
Run:
    streamlit run app.py
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config as C
import data_gen
import ledger
import model
import recommender
import simulator




# ------------------------------------------------------------------
# Location / BAU assessment
# ------------------------------------------------------------------
def assess_location(data: dict) -> dict:
    """Assess the proposed development as BAU and identify mitigation needs.

    This is a transparent prototype decision model. It is not a regulatory,
    structural, geotechnical, environmental or public-health approval.
    """
    before = model.calculate_live_metrics(data, apply_proposed=False)
    bau = model.calculate_live_metrics(data, apply_proposed=True)
    rec = model.recommendations(data, bau)

    def delta(after, before):
        return after - before

    return {
        "before": before,
        "bau": bau,
        "bau_score": bau["eco_score"],
        "bau_status": bau["status"],
        "bau_pillars": {k: v["score"] for k, v in bau["pillars"].items()},
        "recommendation": rec,
        "impact": {
            "score_change": delta(bau["eco_score"], before["eco_score"]),
            "built_change_m2": bau["impact"]["built_after_m2"] - data.get("current_built_m2", 0),
            "green_change_m2": bau["impact"]["green_after_m2"] - data.get("green_cover_m2", 0),
            "water_gap_m3": bau["impact"]["water_gap_m3"],
            "emissions_change_t": (bau["impact"]["emissions_t"] - before["impact"]["emissions_t"]),
        },
        "details": bau["impact"],
        "live_metrics": bau,
    }


def _score_bar(title, values):
    st.subheader(title)
    for label, value in values.items():
        st.progress(int(max(0, min(100, value))), text=f"{label}: {value:.0f}/100")


def show_about_page():
    """Aesthetic About page for Oxygen Bank / OXYNAUTS."""
    st.markdown("""
    <style>
    .about-hero {
        padding: 34px 38px;
        border-radius: 24px;
        border: 1px solid rgba(86, 196, 104, 0.28);
        background: radial-gradient(circle at 90% 10%, rgba(57,168,74,.16), transparent 32%),
                    linear-gradient(135deg, rgba(18,48,29,.96), rgba(10,27,17,.96));
        box-shadow: 0 18px 45px rgba(0,0,0,.22);
        margin-bottom: 28px;
    }
    .about-kicker { color:#73d27d; font-size:14px; font-weight:800; letter-spacing:2px; margin-bottom:8px; }
    .about-title { color:#f4fff5; font-size:42px; font-weight:800; line-height:1.05; margin:0 0 12px; }
    .about-subtitle { color:#c8dfcc; font-size:17px; line-height:1.6; max-width:900px; margin:0; }
    .about-section-title { color:#eaffec; font-size:25px; font-weight:750; margin:26px 0 14px; }
    .about-card {
        background:linear-gradient(145deg, rgba(22,52,31,.92), rgba(12,31,19,.92));
        border:1px solid rgba(91,196,103,.22); border-radius:18px; padding:22px;
        min-height:145px; box-shadow:0 10px 28px rgba(0,0,0,.16);
    }
    .about-card h4 { color:#7cdb84; margin:0 0 10px; font-size:17px; }
    .about-card p { color:#c9dcca; line-height:1.55; margin:0; font-size:14px; }
    .flow-card {
        text-align:center; background:rgba(20,50,29,.72);
        border:1px solid rgba(91,196,103,.22); border-radius:16px;
        padding:17px 10px; color:#eaffec; font-weight:750;
    }
    .flow-num { color:#72d47d; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:5px; }
    .member-card {
        background:radial-gradient(circle at 100% 0%, rgba(84,200,95,.12), transparent 42%),
                   linear-gradient(145deg, rgba(22,52,31,.96), rgba(10,28,17,.96));
        border:1px solid rgba(91,196,103,.28); border-radius:20px; padding:24px 20px;
        min-height:150px; text-align:center; box-shadow:0 12px 30px rgba(0,0,0,.18);
    }
    .member-number {
        display:inline-block; width:34px; height:34px; line-height:34px; border-radius:50%;
        background:rgba(82,194,94,.15); border:1px solid rgba(110,220,119,.30);
        color:#79dc82; font-weight:800; margin-bottom:12px;
    }
    .member-name { color:#f2fff3; font-size:19px; font-weight:750; margin-bottom:6px; }
    .member-role { color:#9ebda4; font-size:12px; letter-spacing:.5px; }
    .quote-box {
        margin:26px 0; padding:24px 28px; border-left:4px solid #69d475;
        border-radius:0 18px 18px 0; background:linear-gradient(90deg, rgba(53,130,64,.20), rgba(18,45,25,.50));
        color:#e7f9e9; font-size:21px; font-weight:650; line-height:1.45;
    }
    .source-card { background:rgba(17,43,25,.80); border:1px solid rgba(91,196,103,.18); border-radius:16px; padding:18px; margin-bottom:12px; }
    .source-title { color:#79dc82; font-weight:750; margin-bottom:5px; }
    .source-text { color:#bfd5c3; font-size:14px; line-height:1.5; }
    .disclaimer { padding:20px 22px; border-radius:17px; background:rgba(73,61,20,.20); border:1px solid rgba(206,177,72,.25); color:#d9d0a5; line-height:1.55; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-hero">
        <div class="about-kicker">OXYNAUTS • OXYGEN BANK</div>
        <div class="about-title">🌱 About Oxygen Bank</div>
        <p class="about-subtitle">Oxygen Bank is a digital ecological decision-support platform that makes development environmentally accountable.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    cards = [
        ("01 · MEASURE", "Understand the existing ecological condition of an area using environmental and development indicators."),
        ("02 · PREDICT", "Estimate how proposed development can change ecological pressure, including carbon, water and green-cover conditions."),
        ("03 · RESTORE", "Identify practical interventions such as tree plantation, rainwater harvesting, solar integration and green infrastructure."),
    ]
    for col, (title, body) in zip((c1, c2, c3), cards):
        with col:
            st.markdown(f'<div class="about-card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="about-section-title">How Oxygen Bank works</div>', unsafe_allow_html=True)
    flow_cols = st.columns(5)
    for i, label in enumerate(["Measure", "Predict", "Restore", "Track", "Simulate"], 1):
        with flow_cols[i - 1]:
            st.markdown(f'<div class="flow-card"><div class="flow-num">STEP {i}</div>{label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="quote-box">“We don’t stop development. We make development environmentally accountable.”</div>', unsafe_allow_html=True)

    st.markdown('<div class="about-section-title">👥 Team — OXYNAUTS</div>', unsafe_allow_html=True)
    members = [("1", "Vivek Bhaskar"), ("2", "Rineeth Patro"), ("3", "Shagun Tripathi"), ("4", "Shradha Sharma")]
    member_cols = st.columns(4)
    for col, (number, name) in zip(member_cols, members):
        with col:
            st.markdown(
                f'<div class="member-card"><div class="member-number">{number}</div>'
                f'<div class="member-name">{name}</div><div class="member-role">OXYNAUTS</div></div>',
                unsafe_allow_html=True
            )

    st.markdown('<p style="text-align:center;color:#9ebda4;margin:18px 0 28px;">Team Oxynauts — Building technology for responsible and resilient development.</p>', unsafe_allow_html=True)

    st.markdown('<div class="about-section-title">📚 Model & Bibliography</div>', unsafe_allow_html=True)
    sources = [
        ("GHG Protocol — Corporate Standard", "Organisational greenhouse-gas accounting and reporting framework."),
        ("FAO — Urban & Peri-Urban Forestry", "Urban trees and green infrastructure, including cooling, carbon sequestration and water-related benefits."),
        ("MoEFCC — Green Credit Programme", "Government of India programme and tree-plantation-based Green Credit methodology notified in February 2024."),
        ("IPCC — Guidelines for National Greenhouse Gas Inventories", "Guidance used for greenhouse-gas emissions estimation."),
    ]
    for title, body in sources:
        st.markdown(f'<div class="source-card"><div class="source-title">{title}</div><div class="source-text">{body}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="about-section-title">⚠️ Disclaimer</div>', unsafe_allow_html=True)
    st.markdown('<div class="disclaimer">Eco-Balance is a prototype, model-based indicator developed for decision support. Its score, weights and thresholds are not presented as universal scientific standards.</div>', unsafe_allow_html=True)

def current_state():
    return ledger.replay(model.load_baseline(), ledger.get_transactions())


def gauge(score, status):
    """Create the Eco-Balance gauge."""
    if score >= C.HEALTHY_MIN:
        color = "#39a84a"
    elif score >= C.TRANSITION_MIN:
        color = "#f9c74f"
    else:
        color = "#e85d75"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={
                "font": {
                    "size": 56,
                    "color": "#f4f4f4",
                }
            },
            title={
                "text": f"<b>Eco-Balance Score · {status}</b>",
                "font": {
                    "size": 20,
                    "color": "#f2f2f2",
                },
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": "#e8e8e8",
                    "tickfont": {"color": "#eeeeee"},
                },
                "bar": {
                    "color": color,
                    "thickness": 0.30,
                },
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {
                        "range": [0, C.OVERDRAFT_BELOW],
                        "color": "#f3b5bd",
                    },
                    {
                        "range": [C.OVERDRAFT_BELOW, C.HEALTHY_MIN],
                        "color": "#fff2b8",
                    },
                    {
                        "range": [C.HEALTHY_MIN, 100],
                        "color": "#bfe0c4",
                    },
                ],
            },
        )
    )

    fig.update_layout(
        height=315,
        margin=dict(t=55, b=0, l=15, r=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"},
    )
    return fig


# ------------------------------------------------------------------
# Custom styling
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* ---------- Main application ---------- */
        .stApp {
            background:
                radial-gradient(circle at 75% 18%, rgba(25, 82, 55, 0.12), transparent 30%),
                #080b11;
            color: #f5f5f5;
        }

        /* Remove excess Streamlit top whitespace */
        .block-container {
            padding-top: 0.25rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #242731 0%, #1e2029 100%);
            min-width: 220px;
            max-width: 220px;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1.2rem;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label {
            color: #f5f5f5 !important;
        }

        section[data-testid="stSidebar"] .stRadio > label {
            font-size: 13px !important;
            font-weight: 500 !important;
        }

        /* ---------- Header banner ---------- */
        .header-wrapper {
            width: 100%;
            overflow: hidden;
            margin: -0.25rem 0 1.3rem 0;
            border-radius: 0 0 2px 2px;
        }

        .header-wrapper img {
            width: 100%;
            height: 184px;
            object-fit: cover;
            object-position: center top;
            display: block;
        }

        /* ---------- Dashboard title ---------- */
        .dashboard-title {
            font-size: 42px;
            line-height: 1.05;
            font-weight: 750;
            letter-spacing: -1.2px;
            color: #f5f5f5;
            margin: 0 0 18px 0;
        }

        /* ---------- Status message ---------- */
        .status-box {
            background: linear-gradient(90deg, #073e2a, #0b4c31);
            border: 1px solid rgba(91, 230, 133, 0.10);
            border-radius: 8px;
            padding: 14px 20px;
            color: #8ee8a7;
            font-size: 15px;
            margin-bottom: 28px;
        }

        /* ---------- Pillar bars ---------- */
        .pillar {
            margin: 13px 0 22px 0;
        }

        .pillar-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 17px;
            font-weight: 650;
            color: #f3f3f3;
            margin-bottom: 9px;
        }

        .pillar-icon {
            width: 31px;
            text-align: center;
            font-size: 27px;
        }

        .pillar-track {
            height: 14px;
            background: #292c35;
            border-radius: 9px;
            overflow: hidden;
            box-shadow: inset 0 1px 2px rgba(0,0,0,.35);
        }

        .pillar-fill {
            height: 100%;
            border-radius: 9px;
            background: linear-gradient(90deg, #1597ed, #1f91e4);
        }

        /* ---------- KPI cards ---------- */
        .kpi-card {
            min-height: 118px;
            border-radius: 11px;
            padding: 20px 25px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 18px rgba(0,0,0,0.20);
            display: flex;
            align-items: center;
            gap: 18px;
        }

        .kpi-green {
            background: linear-gradient(135deg, #073827, #0d2d25);
        }

        .kpi-blue {
            background: linear-gradient(135deg, #092b4b, #0b223b);
        }

        .kpi-brown {
            background: linear-gradient(135deg, #3d291b, #302219);
        }

        .kpi-green2 {
            background: linear-gradient(135deg, #083b2c, #0c3028);
        }

        .kpi-icon {
            font-size: 39px;
            min-width: 44px;
            text-align: center;
        }

        .kpi-label {
            color: #d5d9df;
            font-size: 16px;
            margin-bottom: 3px;
        }

        .kpi-value {
            color: #ffffff;
            font-size: 35px;
            line-height: 1;
            font-weight: 750;
        }

        /* ---------- About page ---------- */
        .about-hero {
            background: linear-gradient(135deg, #062e24 0%, #0b4b36 55%, #102d29 100%);
            border: 1px solid rgba(100, 220, 150, 0.16);
            border-radius: 16px;
            padding: 34px 38px;
            margin: 0 0 26px 0;
            box-shadow: 0 10px 35px rgba(0,0,0,0.25);
        }

        .about-hero-kicker {
            color: #8ee8a7;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }

        .about-hero h1 {
            color: #ffffff;
            font-size: 42px;
            margin: 0 0 10px 0;
        }

        .about-hero p {
            color: #d8f4e1;
            font-size: 18px;
            line-height: 1.6;
            max-width: 850px;
            margin-bottom: 22px;
        }

        .about-flow {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            color: #ffffff;
            font-size: 16px;
            font-weight: 700;
        }

        .about-flow span {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 999px;
            padding: 7px 13px;
        }

        .about-flow b {
            color: #70e39a;
        }

        .about-card {
            background: #10141b;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 22px 25px;
            line-height: 1.75;
            box-shadow: 0 5px 18px rgba(0,0,0,0.16);
        }

        .about-card p {
            color: #dfe5e8;
            margin: 0 0 12px 0;
        }

        .about-card p:last-child {
            margin-bottom: 0;
        }

        .about-quote {
            margin: 20px 0 28px 0;
            padding: 18px 24px;
            border-left: 4px solid #49d37b;
            background: linear-gradient(90deg, rgba(7,62,42,0.9), rgba(7,62,42,0.25));
            border-radius: 0 10px 10px 0;
            color: #a8efbc;
            font-size: 18px;
            font-style: italic;
        }

        .about-step {
            min-height: 190px;
            background: #10141b;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 18px;
        }

        .about-step-number {
            color: #58d989;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .about-step-title {
            color: #ffffff;
            font-size: 20px;
            font-weight: 750;
            margin: 8px 0;
        }

        .about-step-text {
            color: #bfc7ce;
            font-size: 14px;
            line-height: 1.55;
        }

        .team-card {
            min-height: 125px;
            background: linear-gradient(135deg, #0b3025, #101b1b);
            border: 1px solid rgba(100, 220, 150, 0.13);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }

        .team-icon {
            font-size: 28px;
        }

        .team-name {
            color: #ffffff;
            font-size: 17px;
            font-weight: 700;
            margin-top: 7px;
        }

        .team-role {
            color: #83dca0;
            font-size: 12px;
            margin-top: 3px;
            letter-spacing: 1px;
        }

        .team-tagline {
            margin-top: 18px;
            padding: 15px 18px;
            background: rgba(20, 83, 55, 0.35);
            border-radius: 10px;
            color: #bcebc9;
            text-align: center;
        }

        .about-disclaimer {
            background: rgba(126, 91, 18, 0.24);
            border: 1px solid rgba(249, 199, 79, 0.28);
            border-radius: 10px;
            padding: 18px 20px;
            color: #ffe8a1;
            line-height: 1.6;
        }

        .about-footer {
            text-align: center;
            margin-top: 35px;
            padding: 24px 10px 8px 10px;
            color: #7fe19b;
            font-weight: 800;
            letter-spacing: 2px;
        }

        .about-footer small {
            display: block;
            margin-top: 8px;
            color: #87939a;
            font-weight: 400;
            letter-spacing: 0.5px;
        }

        /* ---------- General Streamlit elements ---------- */
        div[data-testid="stMetric"] {
            background: #10141b;
            border-radius: 10px;
            padding: 12px;
        }

        .stButton > button {
            border-radius: 7px;
        }

        /* Make native Plotly background disappear */
        div[data-testid="stPlotlyChart"] {
            background: transparent !important;
        }

        /* Responsive adjustment */
        @media (max-width: 900px) {
            .dashboard-title {
                font-size: 32px;
            }

            .header-wrapper img {
                height: 130px;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
st.sidebar.markdown(
    """
    <div style="font-size:20px;font-weight:750;margin-bottom:18px;">
        🌳 Oxygen Bank
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("_goto"):
    st.session_state["nav_page"] = st.session_state.pop("_goto")

page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Inputs",
        "Live Eco Dashboard",
        "Tree Map",
        "Ledger",
        "Recommendations",
        "2050 Simulator",
        "🌱 About Oxygen Bank",
    ],
    key="nav_page",
)

state = current_state()
metrics = model.compute_metrics(state)


# ==================================================================
# DASHBOARD
# ==================================================================
if page == "Dashboard":

    # Header image created from the supplied reference design.
    header_file = Path(__file__).parent / "oxygen_bank_header.png"

    if header_file.exists():
        st.markdown('<div class="header-wrapper">', unsafe_allow_html=True)
        st.image(str(header_file), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Fallback if the header image has not been copied beside app.py.
        st.markdown(
            """
            <div style="
                height:184px;
                border-radius:0 0 4px 4px;
                background:linear-gradient(90deg,#073b36,#0b5a40,#12382f);
                display:flex;
                align-items:center;
                padding:0 45px;
                margin-bottom:22px;">
                <div>
                    <div style="font-size:42px;font-weight:800;color:white;">
                        🌿 Oxygen <span style="color:#49d37b;">Bank</span>
                    </div>
                    <div style="font-size:14px;letter-spacing:4px;color:#b7e8d0;">
                        CAMPUS ECO-BALANCE PLATFORM
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="dashboard-title">Campus Eco-Balance 🔗</div>',
        unsafe_allow_html=True,
    )

    # Status banner
    if metrics["status"] == "Ecological Stress":
        status_text = "⚠️ Campus is under ecological stress. Redesign or add mitigation."
        status_color = "#7d202b"
        text_color = "#ffd4d8"
    elif metrics["status"] in ("Transition", "High Pressure"):
        status_text = "⚠️ Campus is in a development pressure zone."
        status_color = "#594714"
        text_color = "#ffe8a1"
    else:
        status_text = "🍃  Campus ecological account is healthy."
        status_color = "#073e2a"
        text_color = "#8ee8a7"

    st.markdown(
        f"""
        <div class="status-box"
             style="background:{status_color};color:{text_color};">
            {status_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Gauge + pillars
    gauge_col, pillar_col = st.columns([1.03, 1.35], gap="large")

    with gauge_col:
        st.plotly_chart(
            gauge(metrics["eco_score"], metrics["status"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.markdown(
            '<div style="text-align:center;font-size:28px;margin-top:-25px;">🍃</div>',
            unsafe_allow_html=True,
        )

    with pillar_col:
        pillars = [
            ("🌿", "Carbon", "carbon"),
            ("💧", "Water", "water"),
            ("🌳", "Cooling / Green cover", "cooling"),
        ]

        for icon, label, key in pillars:
            score = float(metrics["pillars"][key]["score"])
            st.markdown(
                f"""
                <div class="pillar">
                    <div class="pillar-title">
                        <span class="pillar-icon">{icon}</span>
                        <span>{label} — {score:.0f}/100</span>
                    </div>
                    <div class="pillar-track">
                        <div class="pillar-fill" style="width:{max(0,min(100,score))}%;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # KPI cards
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    trees = int(state.tree_count)
    population = int(state.population)
    emissions = metrics["emissions_kg"] / 1000
    green_cover = metrics["green_cover_pct"]

    k1, k2, k3, k4 = st.columns(4, gap="medium")

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card kpi-green">
                <div class="kpi-icon">🌳</div>
                <div>
                    <div class="kpi-label">Trees</div>
                    <div class="kpi-value">{trees:,}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card kpi-blue">
                <div class="kpi-icon">👥</div>
                <div>
                    <div class="kpi-label">Population</div>
                    <div class="kpi-value">{population:,}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card kpi-brown">
                <div class="kpi-icon">☁️</div>
                <div>
                    <div class="kpi-label">Emissions (t CO₂/yr)</div>
                    <div class="kpi-value">{emissions:,.0f}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            f"""
            <div class="kpi-card kpi-green2">
                <div class="kpi-icon">🍃</div>
                <div>
                    <div class="kpi-label">Green cover</div>
                    <div class="kpi-value">{green_cover:.1f}%</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )




# ==================================================================
# INPUTS / LOCATION ASSESSMENT
# ==================================================================
elif page == "Inputs":
    st.title("Sustainable Development Planner")
    st.caption(
        "Enter the existing campus condition and the development you are planning. "
        "The model compares the current baseline with Business-as-Usual (BAU), "
        "then identifies what can be added or changed to make the development more balanced."
    )

    st.info(
        "The score is a prototype decision metric, not a universal scientific or regulatory "
        "standard. Missing/unknown environmental values are estimated transparently where possible; "
        "they are never treated as zero performance."
    )

    _li = st.session_state.get("live_inputs") or {}
    with st.form("location_inputs"):
        st.subheader("1. Site & proposed development")
        c1, c2, c3 = st.columns(3)
        with c1:
            total_area = st.number_input(
                "Total site area (m²)", min_value=1.0,
                value=float(_li.get("total_area_m2", 100000.0)), step=1000.0
            )
            current_built = st.number_input(
                "Existing built-up area (m²)", min_value=0.0,
                value=float(_li.get("current_built_m2", 45000.0)), step=1000.0
            )
        with c2:
            proposed_construction = st.number_input(
                "Proposed new construction (m²)", min_value=0.0,
                value=float(_li.get("proposed_construction_m2", 15000.0)), step=100.0
            )
            population = st.number_input(
                "Current population / users", min_value=0.0,
                value=float(_li.get("population", 10000.0)), step=100.0
            )
        with c3:
            additional_population = st.number_input(
                "Expected additional population / users", min_value=0.0,
                value=float(_li.get("additional_population", 1000.0)), step=100.0
            )
            green_removed = st.number_input(
                "Green area removed by construction (m²)", min_value=0.0,
                value=float(_li.get("green_area_removed_m2", 3000.0)), step=100.0
            )

        st.subheader("2. Existing green / cooling capacity")
        c1, c2 = st.columns(2)
        with c1:
            trees = st.number_input(
                "Existing trees", min_value=0.0,
                value=float(_li.get("trees", 1200.0)), step=10.0
            )
        with c2:
            green_cover = st.number_input(
                "Existing green-cover area (m²)", min_value=0.0,
                value=float(_li.get("green_cover_m2", 25000.0)), step=500.0
            )

        st.subheader("3. Water")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            current_water = st.number_input(
                "Current annual water consumption (m³/year)", min_value=0.0,
                value=float(_li.get("current_annual_water_m3", 100000.0)), step=1000.0
            )
        with c2:
            additional_water = st.number_input(
                "Additional annual water demand (m³/year)", min_value=0.0,
                value=float(_li.get("additional_water_demand_m3", 10000.0)), step=500.0
            )
        with c3:
            rainwater = st.number_input(
                "Annual rainwater harvested (m³/year)", min_value=0.0,
                value=float(_li.get("rainwater_harvested_m3", 20000.0)), step=500.0
            )
        with c4:
            reused_water = st.number_input(
                "Annual recycled/reused water (m³/year)", min_value=0.0,
                value=float(_li.get("reused_water_m3", 10000.0)), step=500.0
            )

        st.subheader("4. Energy & carbon")
        c1, c2, c3 = st.columns(3)
        with c1:
            electricity = st.number_input(
                "Annual electricity consumption (kWh/year)", min_value=0.0,
                value=float(_li.get("annual_electricity_kwh", 2000000.0)), step=50000.0
            )
        with c2:
            renewable = st.number_input(
                "Annual renewable electricity (kWh/year)", min_value=0.0,
                value=float(_li.get("annual_renewable_kwh", 500000.0)), step=25000.0
            )
        with c3:
            additional_electricity = st.number_input(
                "Additional electricity from new development (kWh/year)", min_value=0.0,
                value=float(_li.get("additional_electricity_kwh", 400000.0)), step=25000.0,
                help="If unknown, the model estimates it from proposed construction area."
            )

        submitted = st.form_submit_button(
            "🌱 Analyse Development & Find Sustainable Scenario",
            use_container_width=True
        )

    if submitted:
        input_data = {
            "total_area_m2": total_area,
            "current_built_m2": current_built,
            "proposed_construction_m2": proposed_construction,
            "population": population,
            "additional_population": additional_population,
            "trees": trees,
            "green_cover_m2": green_cover,
            "green_area_removed_m2": green_removed,
            "current_annual_water_m3": current_water,
            "additional_water_demand_m3": additional_water,
            "rainwater_harvested_m3": rainwater,
            "reused_water_m3": reused_water,
            "annual_electricity_kwh": electricity,
            "annual_renewable_kwh": renewable,
            "additional_electricity_kwh": additional_electricity,
        }
        assessment = assess_location(input_data)
        st.session_state["location_assessment"] = assessment
        st.session_state["live_inputs"] = input_data
        st.session_state["live_assessment"] = assessment
        st.session_state["live_timestamp"] = datetime.now()

    result = st.session_state.get("location_assessment")
    if result:
        before = result["before"]
        bau = result["bau"]
        impact = result["impact"]
        rec = result["recommendation"]

        st.divider()
        st.subheader("Development decision")

        k1, k2, k3 = st.columns(3)
        k1.metric("Current Eco-Balance", f"{before['eco_score']:.1f}/100")
        k2.metric("BAU after development", f"{bau['eco_score']:.1f}/100",
                  f"{impact['score_change']:+.1f} points")
        k3.metric("Primary pressure", rec["weakest_pillar"].title())

        if bau["status"] == "Balanced":
            st.success("🟢 **Balanced Development** — the proposed development remains within the prototype's balanced zone.")
        elif bau["status"] == "Transition":
            st.warning("🟡 **Transition Zone** — development is possible, but mitigation is recommended.")
        elif bau["status"] == "High Pressure":
            st.warning("🟠 **High Environmental Pressure** — redesign/mitigation is strongly recommended.")
        else:
            st.error("🔴 **Ecological Stress** — major mitigation or redesign is required.")

        st.markdown("### What changed because of the development?")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Built-up after", f"{bau['impact']['built_after_m2']:,.0f} m²")
        d2.metric("Green cover after", f"{bau['impact']['green_pct']:.1f}%")
        d3.metric("Water gap", f"{bau['impact']['water_gap_m3']:,.0f} m³/yr")
        d4.metric("Emissions", f"{bau['impact']['emissions_t']:,.1f} t CO₂e/yr")

        st.subheader("Why is the BAU score at this level?")
        _score_bar("BAU pillar performance", result["bau_pillars"])

        weakest = rec["weakest_pillar"]
        st.markdown(f"**Main issue: {weakest.title()}**")
        for reason in rec["explanation"]:
            st.markdown(f"- {reason}")

        st.subheader("Recommended interventions")
        if rec["plan"]:
            for item in rec["plan"]:
                st.markdown(
                    f"**{item['action']}**  \n"
                    f"Suggested magnitude: **{item['quantity']:,.0f} {item['unit']}**  \n"
                    f"Reason: {item['reason']}"
                )
        else:
            st.success("No major intervention is required by the current prototype thresholds.")

        st.subheader("Try a sustainable development scenario")
        st.caption("Change the intervention quantities below. The dashboard recalculates the expected post-mitigation Eco-Balance.")
        i1, i2, i3 = st.columns(3)
        with i1:
            extra_trees = st.number_input("Additional trees", min_value=0.0, value=0.0, step=50.0, key="inp_extra_trees")
            extra_green = st.number_input("Additional/restored green area (m²)", min_value=0.0, value=0.0, step=500.0, key="inp_extra_green")
        with i2:
            extra_rain = st.number_input("Additional rainwater supply (m³/year)", min_value=0.0, value=0.0, step=1000.0, key="inp_extra_rain")
            extra_reuse = st.number_input("Additional water reuse (m³/year)", min_value=0.0, value=0.0, step=1000.0, key="inp_extra_reuse")
        with i3:
            extra_renewable = st.number_input("Additional renewable electricity (kWh/year)", min_value=0.0, value=0.0, step=25000.0, key="inp_extra_renewable")
            extra_roof = st.number_input("Green roof area (m²)", min_value=0.0, value=0.0, step=500.0, key="inp_extra_roof")

        intervention = {
            "extra_trees": extra_trees,
            "extra_green_m2": extra_green,
            "extra_rainwater_m3": extra_rain,
            "extra_reuse_m3": extra_reuse,
            "extra_renewable_kwh": extra_renewable,
            "extra_green_roof_m2": extra_roof,
        }
        scenario = model.calculate_development_metrics(st.session_state["live_inputs"], intervention)
        improvement = scenario["eco_score"] - bau["eco_score"]

        s1, s2, s3 = st.columns(3)
        s1.metric("BAU", f"{bau['eco_score']:.1f}/100")
        s2.metric("Sustainable scenario", f"{scenario['eco_score']:.1f}/100", f"{improvement:+.1f}")
        s3.metric("Result", scenario["status"])

        if scenario["eco_score"] >= C.HEALTHY_MIN:
            st.success("🌱 This intervention set moves the project into the Balanced Development zone.")
        elif scenario["eco_score"] >= C.TRANSITION_MIN:
            st.warning("🟡 This improves the project, but additional mitigation is still recommended.")
        else:
            st.error("🔴 The selected interventions are not enough yet.")

        cmp = []
        labels = {"carbon": "Carbon", "water": "Water", "cooling": "Cooling / Green Cover"}
        for key in C.WEIGHTS:
            cmp.append({
                "Pillar": labels[key],
                "BAU": round(bau["pillars"][key]["score"], 1),
                "After interventions": round(scenario["pillars"][key]["score"], 1),
                "Change": round(scenario["pillars"][key]["score"] - bau["pillars"][key]["score"], 1),
            })
        st.dataframe(pd.DataFrame(cmp), hide_index=True, use_container_width=True)

        st.caption(
            "Decision bands: 75–100 Balanced Development · 60–75 Transition · "
            "40–60 High Environmental Pressure · 0–40 Ecological Stress. "
            "These are prototype decision bands, not universal regulatory thresholds."
        )

elif page == "Live Eco Dashboard":
    PILLAR_LABEL = {"carbon": "Carbon", "water": "Water", "cooling": "Cooling / Green Cover"}
    PILLAR_ICON = {"carbon": "☁️", "water": "💧", "cooling": "🌳"}

    st.markdown(
        "<h1 style='margin-bottom:0'>SUSTAINABLE DEVELOPMENT DASHBOARD</h1>"
        "<div style='opacity:.75'>Impact → pressure → intervention → improved development</div>",
        unsafe_allow_html=True,
    )

    live_inputs = st.session_state.get("live_inputs")
    if not live_inputs:
        st.info("Go to Inputs and enter your campus + proposed development data first.")
        if st.button("Go to Inputs"):
            st.session_state["_goto"] = "Inputs"
            st.rerun()
        st.stop()

    bau = model.calculate_live_metrics(live_inputs, apply_proposed=True)
    before = model.calculate_live_metrics(live_inputs, apply_proposed=False)
    rec = model.recommendations(live_inputs, bau)

    st.markdown(
        f"**Current:** {before['eco_score']:.1f}/100 → "
        f"**BAU development:** {bau['eco_score']:.1f}/100 · "
        f"**{bau['status']}**"
    )

    g, p = st.columns([1.2, 1])
    with g:
        st.plotly_chart(gauge(bau["eco_score"], bau["status"]), use_container_width=True)
    with p:
        st.subheader("Pillar scores")
        for key in C.WEIGHTS:
            value = bau["pillars"][key]["score"]
            st.progress(int(value), text=f"{PILLAR_ICON[key]} {PILLAR_LABEL[key]}: {value:.0f}/100")
        st.write(f"**Weakest pillar:** {PILLAR_LABEL[rec['weakest_pillar']]}")

    k = st.columns(4)
    k[0].metric("Built-up after", f"{bau['impact']['built_after_m2']:,.0f} m²")
    k[1].metric("Green cover", f"{bau['impact']['green_pct']:.1f}%")
    k[2].metric("Water gap", f"{bau['impact']['water_gap_m3']:,.0f} m³/yr")
    k[3].metric("Emissions", f"{bau['impact']['emissions_t']:,.1f} t CO₂e/yr")

    st.subheader("What is causing the pressure?")
    causes = []
    if bau["pillars"]["carbon"]["score"] < C.RECOMMENDATION_TRIGGER:
        causes.append(f"☁️ Carbon: {bau['impact']['carbon_intensity_kg_m2']:.1f} kg CO₂e/m²/year; renewable share {bau['impact']['renewable_share_pct']:.1f}%.")
    if bau["pillars"]["water"]["score"] < C.RECOMMENDATION_TRIGGER:
        causes.append(f"💧 Water: sustainable supply covers {bau['impact']['water_coverage_pct']:.1f}% of annual demand; gap {bau['impact']['water_gap_m3']:,.0f} m³/year.")
    if bau["pillars"]["cooling"]["score"] < C.RECOMMENDATION_TRIGGER:
        causes.append(f"🌳 Cooling: green cover is {bau['impact']['green_pct']:.1f}% and tree density is {bau['impact']['tree_density_per_ha']:.1f} trees/ha.")
    if causes:
        for c_ in causes:
            st.markdown(f"- {c_}")
    else:
        st.success("No major pressure detected by the prototype thresholds.")

    st.subheader("Recommended path")
    for action in rec["explanation"]:
        st.markdown(f"- {action}")

    st.subheader("BAU → Sustainable development simulator")
    st.caption("Adjust interventions and see whether the development can move into the balanced zone.")
    c1, c2, c3 = st.columns(3)
    with c1:
        extra_trees = st.number_input("Additional trees", 0.0, step=50.0, key="dash_extra_trees")
        extra_green = st.number_input("Restored/additional green area (m²)", 0.0, step=500.0, key="dash_extra_green")
    with c2:
        extra_rain = st.number_input("Additional rainwater supply (m³/year)", 0.0, step=1000.0, key="dash_extra_rain")
        extra_reuse = st.number_input("Additional water reuse (m³/year)", 0.0, step=1000.0, key="dash_extra_reuse")
    with c3:
        extra_renewable = st.number_input("Additional renewable electricity (kWh/year)", 0.0, step=25000.0, key="dash_extra_renewable")
        extra_roof = st.number_input("Green roof area (m²)", 0.0, step=500.0, key="dash_extra_roof")

    intervention = {
        "extra_trees": extra_trees,
        "extra_green_m2": extra_green,
        "extra_rainwater_m3": extra_rain,
        "extra_reuse_m3": extra_reuse,
        "extra_renewable_kwh": extra_renewable,
        "extra_green_roof_m2": extra_roof,
    }
    scenario = model.calculate_development_metrics(live_inputs, intervention)
    improvement = scenario["eco_score"] - bau["eco_score"]

    s1, s2, s3 = st.columns(3)
    s1.metric("BAU", f"{bau['eco_score']:.1f}/100")
    s2.metric("Sustainable scenario", f"{scenario['eco_score']:.1f}/100", f"{improvement:+.1f}")
    s3.metric("Final status", scenario["status"])

    rows = []
    for key in C.WEIGHTS:
        rows.append({
            "Pillar": PILLAR_LABEL[key],
            "BAU": round(bau["pillars"][key]["score"], 1),
            "After intervention": round(scenario["pillars"][key]["score"], 1),
            "Change": round(scenario["pillars"][key]["score"] - bau["pillars"][key]["score"], 1),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    if scenario["eco_score"] >= C.HEALTHY_MIN:
        st.success("🌱 **Balanced Development achieved.** The selected interventions bring the project into the prototype's balanced zone.")
    elif scenario["eco_score"] >= C.TRANSITION_MIN:
        st.warning("🟡 **Improved, but not yet balanced.** Add more mitigation or redesign the development.")
    else:
        st.error("🔴 **Still under high pressure.** The selected interventions are not enough.")

    st.caption(
        "Decision bands: 75–100 Balanced Development · 60–75 Transition · "
        "40–60 High Environmental Pressure · 0–40 Ecological Stress."
    )

elif page == "Tree Map":
    st.title("Tree Inventory")
    trees = pd.read_csv(C.TREES_CSV)
    st.map(trees, latitude="lat", longitude="lon", size=6)
    st.bar_chart(trees.species.value_counts())
    st.dataframe(trees.head(50), use_container_width=True)


# ==================================================================
# LEDGER
# ==================================================================
elif page == "Ledger":
    st.title("Transaction Ledger")

    kind = st.radio(
        "Type",
        ["Withdrawal", "Deposit"],
        horizontal=True,
    )

    options = C.WITHDRAWALS if kind == "Withdrawal" else C.DEPOSITS

    with st.form("txn"):
        cat = st.selectbox(
            "Category",
            list(options),
            format_func=lambda k: options[k]["label"],
        )

        qty = st.number_input(
            "Quantity",
            min_value=1.0,
            value=10.0,
            step=1.0,
        )

        note = st.text_input("Note (optional)")

        if st.form_submit_button("Record transaction"):
            ledger.add_transaction(
                kind.lower(),
                cat,
                qty,
                note,
            )
            st.rerun()

    st.caption(
        "Units: "
        + ", ".join(
            f"{v['label']} = {v['unit']}"
            for v in options.values()
        )
    )

    df = ledger.get_transactions()

    st.subheader("History")
    st.dataframe(df, use_container_width=True)

    if st.button("Reset ledger"):
        ledger.reset()
        st.rerun()


# ==================================================================
# RECOMMENDATIONS
# ==================================================================
elif page == "Recommendations":
    st.title("Deposit Recommender")
    st.write(
        "Finds the cheapest mix of deposits to reach your target score."
    )

    target = st.slider(
        "Target Eco-Balance Score",
        40,
        100,
        70,
    )

    max_trees = st.slider(
        "Max trees we can plant",
        0,
        5000,
        1500,
        step=50,
    )

    max_rain = st.slider(
        "Max rainwater catchment (m²)",
        0,
        100000,
        30000,
        step=1000,
    )


    if st.button("Calculate plan"):
        st.session_state["plan"] = recommender.recommend(
            state,
            target,
            max_trees,
            max_rain,
        )

    res = st.session_state.get("plan")

    if res:
        if not res["ok"]:
            st.error("No feasible plan with these limits.")

        elif not res["plan"]:
            st.success("No deposits needed — target already met.")

        else:
            st.dataframe(
                pd.DataFrame(res["plan"]),
                use_container_width=True,
            )

            st.metric(
                "Total cost (₹)",
                f"{res['total_cost']:,.0f}",
            )

            a, b = st.columns(2)

            a.metric(
                "Score before",
                f"{res['before']['eco_score']:.1f}",
            )

            b.metric(
                "Score after",
                f"{res['after']['eco_score']:.1f}",
                delta=f"{res['after']['eco_score'] - res['before']['eco_score']:.1f}",
            )

            if st.button("✅ Add plan to ledger as deposits"):
                for item in res["plan"]:
                    ledger.add_transaction(
                        "deposit",
                        item["category"],
                        item["quantity"],
                        "Recommended plan",
                    )

                st.session_state.pop("plan")
                st.rerun()


# ==================================================================
# 2050 SIMULATOR
# ==================================================================
elif page == "2050 Simulator":
    st.title("2050 Simulator")

    hist = pd.read_csv(C.POP_CSV)
    fitted = simulator.fit_growth_rate(
        hist.year,
        hist.population,
    )

    st.caption(
        f"Growth rate fitted from historical population: "
        f"{fitted * 100:.1f}%/year"
    )

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Growth")

        r = (
            st.slider(
                "Population growth rate (%/yr)",
                0.0,
                12.0,
                round(fitted * 100, 1),
                0.1,
            )
            / 100
        )

        cap = st.slider(
            "Max campus population",
            5000,
            50000,
            20000,
            step=1000,
        )

    with c2:
        st.subheader("Oxygen Bank policy (per year)")

        trees = st.slider(
            "Trees planted",
            0,
            500,
            150,
            step=10,
        )

        solar = st.slider(
            "Solar canopy (m²)",
            0,
            2000,
            300,
            step=50,
        )

        roof = st.slider(
            "Green roof (m²)",
            0,
            2000,
            200,
            step=50,
        )

        rain = st.slider(
            "Rainwater catchment (m²)",
            0,
            5000,
            800,
            step=100,
        )

    bau = simulator.simulate(
        state,
        r=r,
        capacity=cap,
    )

    plan = simulator.simulate(
        state,
        r=r,
        capacity=cap,
        trees_per_year=trees,
        solar_m2_per_year=solar,
        green_roof_m2_per_year=roof,
        rain_m2_per_year=rain,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=bau.year,
            y=bau.eco_score,
            name="Business as usual",
            line=dict(color="#e85d75", width=3),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plan.year,
            y=plan.eco_score,
            name="With Oxygen Bank",
            line=dict(color="#39a84a", width=3),
        )
    )

    fig.add_hline(
        y=C.OVERDRAFT_BELOW,
        line_dash="dash",
        annotation_text="Overdraft line",
    )

    fig.add_hline(
        y=C.HEALTHY_MIN,
        line_dash="dot",
        annotation_text="Healthy line",
    )

    fig.update_layout(
        yaxis=dict(
            range=[0, 100],
            title="Eco-Balance Score",
        ),
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ffffff"},
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    od = simulator.first_overdraft_year(bau)

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "BAU score in 2050",
        f"{bau.eco_score.iloc[-1]:.0f}",
    )

    m2.metric(
        "Plan score in 2050",
        f"{plan.eco_score.iloc[-1]:.0f}",
    )

    m3.metric(
        "Overdraft year (BAU)",
        od if od else "None",
    )

    st.metric(
        "Total plan cost by 2050 (₹)",
        f"{plan.cum_cost_inr.iloc[-1]:,.0f}",
    )

    st.dataframe(
        plan[
            plan.year.isin([2030, 2040, 2050])
        ].round(1),
        use_container_width=True,
    )

# ==================================================================
# ABOUT OXYGEN BANK
# ==================================================================
elif page == "🌱 About Oxygen Bank":
    show_about_page()

