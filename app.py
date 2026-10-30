"""Launch with: streamlit run app.py."""
import logging

import streamlit as st

st.set_page_config(page_title="Vineyard AI Monitor", page_icon="🍇", layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from pages import about, analysis, evaluation, health_map, overview

st.markdown("""
<style>
.block-container {max-width: 1440px; padding-top: 2.2rem; padding-bottom: 3rem;}
h1, h2, h3 {letter-spacing: -.025em;}
h1 {font-size: 2.65rem !important;}
[data-testid="stSidebar"] {border-right: 1px solid #dbe4d7;}
[data-testid="stMetric"] {background: white; border: 1px solid #dce6d9; border-radius: 12px; padding: 18px 20px;}
[data-testid="stMetricLabel"] {color: #586d60;}
[data-testid="stMetricValue"] {font-size: 2.2rem; color:#174b34;}
[data-testid="stExpander"] {background: #fff; border-radius: 10px;}
.hero {background: #174b34; color:#fff; padding: 32px 36px; border-radius: 16px; margin-bottom: 24px;}
.hero h1 {color: #fff; margin: 6px 0 4px;}
.hero p {color: #d8e7d6; font-size: 1.08rem; max-width: 760px; margin-bottom: 0;}
.eyebrow {font-size: .73rem; letter-spacing: .16em; font-weight: 650; color: #bce2b8;}
.step {background:#fff; border:1px solid #dce6d9; border-radius:12px; padding:20px; min-height:142px;}
.step small {color:#25805b; font-weight:700; letter-spacing:.08em;}
.step h3 {font-size:1.1rem; margin-top:8px;}
.step p {color:#62756a; font-size:.88rem; margin-bottom:0;}
.brand {font-size:1.35rem; font-weight:750; color:#174b34; margin-bottom:0;}
.sidebar-note {font-size:.78rem; color:#637568; margin-top:28px; line-height:1.6;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">🍇 Vineyard AI</div>', unsafe_allow_html=True)
    st.caption("SEE THE CANOPY. FOCUS THE INSPECTION.")
    st.divider()
    page = st.radio("Workspace", ["Overview", "Vineyard Analysis", "Vineyard Health Map", "Evaluation", "About the Project"], key="workspace_page", label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="sidebar-note">RGB drone imagery → canopy analysis → inspection priorities.<br><br>CPU baseline · Runs locally<br>No account or external API required</div>', unsafe_allow_html=True)

routes = {"Overview": overview.render, "Vineyard Analysis": analysis.render, "Vineyard Health Map": health_map.render, "Evaluation": evaluation.render, "About the Project": about.render}
routes[page]()
