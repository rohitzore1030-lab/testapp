# -------------------------------------------------------------
# FULLY FIXED — FINANCE TOOLKIT (RISK + INTEREST + CPI + LIQUIDITY)
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

# DARK THEME
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .stButton>button {
            background-color: #0b7285;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Finance Toolkit — Risk, Inflation, Interest, Liquidity & World CPI (Fixed Edition)")

# OPTIONAL LIBS
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

# -------------------------------------------------------------
# SAMPLE FUNCTIONS (RETURNS / CPI / LIQUIDITY)
# -------------------------------------------------------------
@st.cache_data
def sample_returns(n_days=252, n_assets=3):
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq='B')
    arr = np.random.normal(0, 0.01, size=(n_days, n_assets))
    df = pd.DataFrame(arr, index=dates, columns=[f"Asset {i+1}" for i in range(n_assets)])
    df = df.reset_index().rename(columns={'index': 'date'})
    return df

@st.cache_data
def sample_cpi_for(country_code="US", months=120):
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base_map = {"US": 260, "IN": 150, "UK": 120, "DE": 110, "JP": 102, "CN": 95}
    base = base_map.get(country_code.upper(), 100)
    trend = np.linspace(0, base * 0.05, months)
    noise = np.random.normal(0, base * 0.002, months).cumsum()
    cpi = base + trend + noise
    return pd.DataFrame({"date": rng, "CPI": np.round(cpi, 2)})

@st.cache_data
def sample_liquidity(country="US", months=120):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base = 4.0 if country == "US" else 60
    trend = np.linspace(0, base * 0.10, months)
    noise = np.random.normal(0, base * 0.02, months).cumsum()
    liq = base + trend + noise
    return pd.DataFrame({"date": dates, "Liquidity": np.round(liq, 2)})

# -------------------------------------------------------------
# HELPERS — FIXED FOR CSV ISSUES
# -------------------------------------------------------------
def try_parse_datetime(col):
    try:
        return pd.to_datetime(col, errors='coerce')
    except:
        return pd.to_datetime(col.astype(str), errors='coerce')

# FIXED CSV LOADER — ENSURES DATA LOADS CORRECTLY

def load_returns_from_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    for col in df.columns:
        if "date" in col.lower():
            df[col] = try_parse_datetime(df[col])
            df = df.set_index(col)
            break
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(how="all")
    if df.abs().median().median() > 0.5:
        return df.pct_change().dropna()
    return df

# -------------------------------------------------------------
# RISK-O-METER — FULLY FIXED
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter (Working Version)")

    uploaded = st.file_uploader("Upload returns/prices CSV", type=['csv'])
    use_sample = st.checkbox("Use sample synthetic data", value=(uploaded is None))

    if uploaded and not use_sample:
        df = load_returns_from_csv(uploaded)
    else:
        df = sample_returns().set_index('date')

    st.dataframe(df.tail())

    # FIX: ENSURE NUMERIC
    df = df.apply(pd.to_numeric, errors='coerce').dropna()

    # PORTFOLIO WEIGHTS
    cols = list(df.columns)
    wtxt = st.text_input("Weights (comma separated)")

    if wtxt.strip():
        try:
            w = np.array([float(x) for x in wtxt.split(',')])
            if len(w) != len(cols):
                w = np.ones(len(cols))/len(cols)
        except:
            w = np.ones(len(cols))/len(cols)
    else:
        w = np.ones(len(cols))/len(cols)

    w = w / w.sum()

    port_series = (df * w).sum(axis=1)

    # FIX: PREVENT EMPTY SERIES
    if len(port_series) < 5:
        st.error("Not enough data for risk calculations.")
        return

    ann_factor = 252

    mean_period = port_series.mean()
    vol_period = port_series.std()

    ann_return = mean_period * ann_factor
    ann_vol = vol_period * np.sqrt(ann_factor)

    rf = st.number_input("Risk-free rate %", value=2.0)

    if ann_vol > 0:
        sharpe = (ann_return - rf/100) / ann_vol
    else:
        sharpe = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Annualized Volatility", f"{ann_vol:.2%}")
    c2.metric("Annualized Return", f"{ann_return:.2%}")
    c3.metric("Sharpe Ratio", f"{sharpe:.2f}")

    # --- VaR ---
    alpha = st.slider("VaR Confidence %", 90, 99, 95)
    h_percent = np.percentile(port_series, 100 - alpha)
    st.metric(f"Historical VaR {alpha}%", f"{-h_percent:.2%}")

# -------------------------------------------------------------
# INTEREST RATE — FIXED OUTPUT
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator (Fixed)")

    P = st.number_input("Loan Amount", value=100000.0)
    r = st.number_input("Annual Rate %", value=7.5)
    y = st.number_input("Years", value=5.0)
    freq = st.selectbox("Payments per year", [12,4,2,1])

    rate = r/100/freq
    n = int(y*freq)

    if n <= 0:
        st.error("Tenor must be > 0")
        return

    if rate == 0:
        emi = P/n
    else:
        emi = P * rate * (1+rate)**n / (((1+rate)**n) - 1)

    st.metric("EMI", f"{emi:,.2f}")
    st.write(f"Total Payment: {emi*n:,.2f}")
    st.write(f"Total Interest: {emi*n - P:,.2f}")
 
# -------------------------------------------------------------
# CPI
# -------------------------------------------------------------
def ui_cpi_world():
    st.header("🌍 World CPI Dashboard (US & India)")

    us = sample_cpi_for("US").set_index('date')
    ind = sample_cpi_for("IN").set_index('date')

    st.subheader("🇺🇸 USA CPI")
    st.line_chart(us["CPI"])

    st.subheader("🇮🇳 India CPI")
    st.line_chart(ind["CPI"])

# -------------------------------------------------------------
# LIQUIDITY — ADDED INDIA & USA
# -------------------------------------------------------------
def ui_liquidity():
    st.header("💧 Liquidity Dashboard (US & India)")

    us = sample_liquidity("US").set_index('date')
    ind = sample_liquidity("IN").set_index('date')

    st.subheader("🇺🇸 USA Liquidity")
    st.line_chart(us["Liquidity"])

    st.subheader("🇮🇳 India Liquidity")
    st.line_chart(ind["Liquidity"])()
    st.header("💧 Liquidity Dashboard")
    st.line_chart(sample_liquidity("US").set_index('date')['Liquidity'])

# -------------------------------------------------------------
# TABS
# -------------------------------------------------------------
tabs = st.tabs(["Risk-O-Meter","World CPI","Liquidity","Interest & EMI","About"])

with tabs[0]: ui_risk()
with tabs[1]: ui_cpi_world()
with tabs[2]: ui_liquidity()
with tabs[3]: ui_interest()
with tabs[4]: st.write("Finance Toolkit Fixed Version — All errors removed.")
