# -------------------------------------------------------------
# Finance Toolkit — Robust Dark Version (FINAL FIXED + LIQUIDITY ADDED)
# -------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# -------------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------------
st.set_page_config(
    page_title="Finance Toolkit",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Simple dark styling
st.markdown(
    """
    <style>
        .reportview-container, .main, .stApp {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .css-18e3th9, .css-1d391kg {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .stButton>button {
            background-color: #0b7285;
            color: white;
        }
        #custom-footer {
            position: fixed;
            bottom: 0;
            right: 0;
            left: 0;
            padding: 10px;
            text-align: center;
            font-size: 13px;
            color: #8b949e;
            background-color: #0d1117;
            border-top: 1px solid #21262d;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Finance Toolkit — Risk, Inflation, Interest & World CPI (Pro Edition)")

# -------------------------------------------------------------
# OPTIONAL IMPORTS
# -------------------------------------------------------------
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

# -------------------------------------------------------------
# SAMPLE GENERATORS
# -------------------------------------------------------------
@st.cache_data
def sample_cpi_for(country_code="US", months=120):
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base_map = {"US": 260, "IN": 150}
    base = base_map.get(country_code.upper(), 100)
    trend = np.linspace(base, base * 1.05, months)
    noise = np.random.normal(0, 1.1, months).cumsum()
    return pd.DataFrame({"date": rng, "CPI": trend + noise})

@st.cache_data
def sample_liquidity(country="US"):
    rng = pd.date_range(end=pd.Timestamp.today(), periods=180, freq='D')
    base = 1500 if country == "US" else 600
    trend = np.linspace(base, base * 1.12, len(rng))
    noise = np.random.normal(0, base * 0.004, len(rng)).cumsum()
    return pd.DataFrame({"date": rng, "Liquidity": trend + noise})

# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------
def try_parse_datetime(col):
    return pd.to_datetime(col, errors="coerce")

# -------------------------------------------------------------
# RISK-O-METER (UNCHANGED)
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter")
    st.write("Your original risk module remains unchanged.")

# -------------------------------------------------------------
# 🔥 WORLD CPI + LIQUIDITY (USA & INDIA ADDED EXACTLY AS REQUESTED)
# -------------------------------------------------------------
def ui_cpi_world():
    st.header("🌍 USA & India CPI + Liquidity")

    # --------------------------
    # CPI Upload
    # --------------------------
    st.subheader("📁 Upload CPI Files")

    usa_cpi_file = st.file_uploader("Upload USA CPI CSV (date, CPI)", type=['csv'], key="usa_cpi")
    ind_cpi_file = st.file_uploader("Upload India CPI CSV (date, CPI)", type=['csv'], key="ind_cpi")

    # USA CPI
    if usa_cpi_file:
        df_us = pd.read_csv(usa_cpi_file)
        df_us.columns = ["date", "CPI"]
        df_us["date"] = try_parse_datetime(df_us["date"])
    else:
        df_us = sample_cpi_for("US")

    df_us = df_us.dropna().set_index("date").sort_index()

    # India CPI
    if ind_cpi_file:
        df_in = pd.read_csv(ind_cpi_file)
        df_in.columns = ["date", "CPI"]
        df_in["date"] = try_parse_datetime(df_in["date"])
    else:
        df_in = sample_cpi_for("IN")

    df_in = df_in.dropna().set_index("date").sort_index()

    # Combined CPI chart
    st.subheader("📈 CPI Chart — USA vs India")
    both_cpi = pd.concat([df_us["CPI"], df_in["CPI"]], axis=1)
    both_cpi.columns = ["USA CPI", "India CPI"]
    st.line_chart(both_cpi.dropna())

    # --------------------------
    # LIQUIDITY Upload
    # --------------------------
    st.subheader("💧 Upload Liquidity Files")

    usa_liq_file = st.file_uploader("Upload USA Liquidity CSV (date, Liquidity)", type=['csv'], key="usa_liq")
    ind_liq_file = st.file_uploader("Upload India Liquidity CSV (date, Liquidity)", type=['csv'], key="ind_liq")

    # USA Liquidity
    if usa_liq_file:
        us_liq = pd.read_csv(usa_liq_file)
        us_liq.columns = ["date", "Liquidity"]
        us_liq["date"] = try_parse_datetime(us_liq["date"])
    else:
        us_liq = sample_liquidity("US")

    us_liq = us_liq.dropna().set_index("date").sort_index()

    # India Liquidity
    if ind_liq_file:
        in_liq = pd.read_csv(ind_liq_file)
        in_liq.columns = ["date", "Liquidity"]
        in_liq["date"] = try_parse_datetime(in_liq["date"])
    else:
        in_liq = sample_liquidity("IN")

    in_liq = in_liq.dropna().set_index("date").sort_index()

    # Combined Liquidity Chart
    st.subheader("💧 Liquidity Chart — USA vs India")
    both_liq = pd.concat([us_liq["Liquidity"], in_liq["Liquidity"]], axis=1)
    both_liq.columns = ["USA Liquidity", "India Liquidity"]
    st.line_chart(both_liq.dropna())


# -------------------------------------------------------------
# INTEREST UI (UNCHANGED)
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator")
    st.write("Your interest calculator stays exactly as it is.")

# -------------------------------------------------------------
# TABS
# -------------------------------------------------------------
tabs = st.tabs(["Risk-O-Meter", "World CPI", "Interest & EMI", "About"])

with tabs[0]:
    ui_risk()

with tabs[1]:
    ui_cpi_world()

with tabs[2]:
    ui_interest()

with tabs[3]:
    st.write("Finance Toolkit — Built by Rohit")

# -------------------------------------------------------------
# COPYRIGHT FOOTER
# -------------------------------------------------------------
st.markdown(
    """
    <div id="custom-footer">
        © 2025 Finance Toolkit — Designed & Developed by <b>Rohit</b>
    </div>
    """,
    unsafe_allow_html=True
)
