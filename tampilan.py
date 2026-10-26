"""Gaya tampilan dashboard (CSS ringan, cocok untuk tema terang maupun gelap)."""
import streamlit as st

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1400px;}
h1 {font-weight: 700; letter-spacing: -0.5px;}
[data-testid="stMetric"] {
    background: rgba(128,128,128,0.08); border: 1px solid rgba(128,128,128,0.25);
    border-radius: 10px; padding: 12px 16px;
}
[data-testid="stMetricLabel"] p {font-size: 0.8rem; opacity: 0.75;}
.stTabs [data-baseweb="tab-list"] {gap: 4px; border-bottom: 1px solid rgba(128,128,128,0.25);}
.stTabs [data-baseweb="tab"] {padding: 10px 18px; font-weight: 600; border-radius: 8px 8px 0 0;}
.stTabs [aria-selected="true"] {background: rgba(41,98,255,0.12);}
[data-testid="stExpander"] {border: 1px solid rgba(128,128,128,0.25); border-radius: 10px;}
[data-testid="stDataFrame"] {border-radius: 10px;}
</style>
"""


def terapkan_gaya():
    st.markdown(CSS, unsafe_allow_html=True)
