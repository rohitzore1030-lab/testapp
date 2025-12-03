streamlit run finance_toolkit.py

# -------------------------------------------------------------
# Finance Toolkit — Ultimate Version (Auto Values + Copyright)
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

# Dark theme
st.markdown(
    """
    <style>
        .reportview-container, .main, .stApp {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .stButton>button {
            background-color: #0b7285;
            color: white;
        }
        footer {
            visibility: hidden;
        }
        #custom-footer {
            text-align: center;
            padding: 10px;
            color: #aaa;
            margin-top: 40px;
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
# SAMPLE DATA
# -------------------------------------------------------------
@st.cache_data
def sample_returns(n_days: int = 252, n_assets: int = 3):
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq='B')
    arr = np.random.normal(0, 0.01, size=(n_days, n_assets))
    df = pd.DataFrame(arr, index=dates, columns=[f"Asset {i+1}" for i in range(n_assets)])
    df = df.reset_index().rename(columns={'index': 'date'})
    return df

@st.cache_data
def sample_cpi_for(code: str):
    months = 120
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base_map = {"US": 260, "IN": 150, "UK": 120, "DE": 110, "JP": 102, "CN": 95}
    base = base_map.get(code, 100)

    trend = np.linspace(0, base * 0.05, months)
    noise = np.random.normal(0, base * 0.002, months).cumsum()
    cpi = base + trend + noise

    df = pd.DataFrame({"date": rng, "CPI": np.round(cpi, 2)})
    df["YoY"] = df["CPI"].pct_change(12) * 100
    df["MoM"] = df["CPI"].pct_change() * 100
    return df

# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------
def ensure_returns_df(df):
    df = df.copy()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

# -------------------------------------------------------------
# RISK-O-METER UI
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter (Auto Values Added)")

    # Auto-load sample data
    df = sample_returns().set_index("date")
    df = ensure_returns_df(df)

    st.subheader("Auto-Loaded Sample Returns Data")
    st.dataframe(df.tail(5))

    cols = df.columns.tolist()

    # AUTO WEIGHTS
    default_weights = ",".join([str(round(1 / len(cols), 2))] * len(cols))
    wtxt = st.text_input("Portfolio Weights (auto-filled)", default_weights)

    try:
        w = np.array([float(x) for x in wtxt.split(",")])
        w = w / w.sum()
    except:
        w = np.ones(len(cols)) / len(cols)

    port = (df * w).sum(axis=1)

    ann_return = port.mean() * 252
    ann_vol = port.std() * np.sqrt(252)

    c1, c2 = st.columns(2)
    c1.metric("Annual Return", f"{ann_return:.2%}")
    c2.metric("Annual Volatility", f"{ann_vol:.2%}")

    alpha = st.slider("VaR Confidence Level", 90, 99, 95)
    hist_var = -np.percentile(port, 100 - alpha)

    st.metric(f"Historical VaR ({alpha}%)", f"{hist_var:.2%}")

    if HAS_SCIPY:
        z = norm.ppf(1 - alpha / 100)
    else:
        z = 1.65
    param_var = -(port.mean() + z * port.std())
    st.metric("Parametric VaR", f"{param_var:.2%}")

# -------------------------------------------------------------
# WORLD CPI UI
# -------------------------------------------------------------
def ui_cpi_world():
    st.header("🌍 World CPI Dashboard (Auto Values Added)")

    countries = ["US", "IN", "UK", "DE", "JP", "CN"]
    selected = st.multiselect("Select Countries", countries, default=["US", "IN", "UK"])

    cpi_data = {c: sample_cpi_for(c) for c in selected}

    st.subheader("CPI Comparison Chart")
    combined = pd.DataFrame({c: cpi_data[c].set_index("date")["CPI"] for c in selected})
    st.line_chart(combined.dropna())

    st.subheader("Inflation (YoY %)")
    yoy = pd.DataFrame({c: cpi_data[c].set_index("date")["YoY"] for c in selected})
    st.line_chart(yoy.dropna())

    # AUTO SUMMARY TABLE
    st.subheader("📌 Auto-Generated CPI Summary Table")
    rows = []
    for c in selected:
        df = cpi_data[c]
        latest = df.iloc[-1]
        rows.append([c, latest["CPI"], latest["YoY"], latest["MoM"]])

    summary = pd.DataFrame(rows, columns=["Country", "Latest CPI", "YoY (%)", "MoM (%)"])
    st.dataframe(summary)

# -------------------------------------------------------------
# INTEREST & EMI UI
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator")

    P = st.number_input("Loan Amount", value=200000.0)
    R = st.number_input("Annual Rate (%)", value=7.5)
    Y = st.number_input("Tenor (years)", value=5.0)
    freq = st.selectbox("Payments per year", [12, 4, 2, 1])

    r = R / 100 / freq
    n = int(Y * freq)

    if r == 0:
        emi = P / n
    else:
        emi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)

    st.metric("EMI", f"{emi:,.2f}")
    st.write(f"Total Interest: {emi*n - P:,.2f}")

# -------------------------------------------------------------
# TABS
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Risk-O-Meter", "World CPI", "Interest & EMI", "About"])

with tab1:
    ui_risk()

with tab2:
    ui_cpi_world()

with tab3:
    ui_interest()

with tab4:
    st.write("""
    ### Finance Toolkit  
    Version: Pro Edition  
    Built with Python, Streamlit, Pandas & NumPy.  
    """)

# -------------------------------------------------------------
# COPYRIGHT FOOTER
# -------------------------------------------------------------
st.markdown(
    """
    <div id="custom-footer">
        © 2025 Finance Toolkit — Designed & Developed by Rohit  
    </div>
    """,
    unsafe_allow_html=True,
)
