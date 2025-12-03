# -------------------------------------------------------------
# Finance Toolkit — Enhanced Dark Version (FINAL)
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

# Custom Dark Theme Color
st.markdown("""
<style>
    body {
        background-color: #0d1117;
        color: #ffffff;
    }
    .stApp {
        background-color: #0d1117;
    }
    .css-18e3th9, .css-1d391kg {
        background-color: #0d1117;
        color: #fff;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Finance Toolkit — Risk, Inflation, Interest & CPI (Pro Edition)")

# -------------------------------------------------------------
# OPTIONAL IMPORTS (SAFE)
# -------------------------------------------------------------
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

try:
    from fredapi import Fred
    HAS_FRED = True
except:
    HAS_FRED = False

# -------------------------------------------------------------
# SAMPLE RETURN GENERATOR
# -------------------------------------------------------------
@st.cache_data
def sample_returns():
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B')
    df = pd.DataFrame(np.random.normal(0,0.01,(252,3)), index=dates,
                      columns=['Asset A', 'Asset B', 'Asset C']).reset_index()
    df.rename(columns={'index':'date'}, inplace=True)
    return df

@st.cache_data
def sample_cpi(country='US'):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='M')
    base = 260 if country=='US' else 150
    cpi = base + np.linspace(0, 5, len(dates)).cumsum()/10
    return pd.DataFrame({'date':dates, 'CPI':np.round(cpi,2)})

# -------------------------------------------------------------
# CLEANER
# -------------------------------------------------------------
def clean_returns(df):
    df = df.copy()
    try:
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
        df = df.set_index(df.columns[0])
    except:
        pass

    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    return df.dropna(axis=0, how='all')

# -------------------------------------------------------------
# RISK-O-METER UI
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter (Advanced)")

    st.info("Upload returns CSV or use sample data")

    f = st.file_uploader("Upload returns CSV", type=['csv'])
    if f:
        raw = pd.read_csv(f)
        df = clean_returns(raw)
    else:
        df = clean_returns(sample_returns())

    if df.empty:
        st.error("No numeric columns detected")
        return

    st.subheader("Data Preview")
    st.dataframe(df.tail())

    # ---------------------- Weights --------------------------
    wtxt = st.text_input("Weights (comma separated) — optional", "")
    n = df.shape[1]

    if wtxt.strip():
        try:
            w = np.array([float(x.strip()) for x in wtxt.split(',')])
            if len(w) != n:
                st.warning("Weight count mismatch — using equal weights.")
                w = np.ones(n)/n
        except:
            st.warning("Invalid format — using equal weights.")
            w = np.ones(n)/n
    else:
        w = np.ones(n)/n

    w = w / w.sum()

    # ---------------------- Port Stats -----------------------
    cov = df.cov().fillna(0) * 252
    port_var = float(w @ cov.values @ w.T)
    port_vol = np.sqrt(max(port_var, 0))

    # Sharpe ratio (assuming rf=2%)
    pres = (df * w).sum(axis=1)
    mu = pres.mean()*252
    sigma = pres.std()*np.sqrt(252)
    rf = 0.02
    sharpe = (mu - rf) / sigma if sigma > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Annualized Volatility", f"{port_vol:.2%}")
    col2.metric("Annualized Return (est.)", f"{mu:.2%}")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")

    # ------------------ Risk Classification ------------------
    st.subheader("Risk Classification")

    if port_vol < 0.08:
        st.success("🟢 Low Risk Portfolio")
    elif port_vol < 0.15:
        st.warning("🟡 Moderate Risk Portfolio")
    else:
        st.error("🔴 High Risk Portfolio")

    # ---------------------- VaR ------------------------------
    st.markdown("---")
    st.subheader("Value-at-Risk (VaR)")

    alpha = st.slider("Confidence Level (%)", 90, 99, 95)

    if len(pres) < 30:
        st.warning("Need at least 30 observations for VaR")
    else:
        hvar = -np.percentile(pres, 100 - alpha)
        st.metric(f"Historical VaR ({alpha}%)", f"{hvar:.2%}")

        if HAS_SCIPY:
            z = norm.ppf(1 - alpha/100)
            pvar = -(pres.mean() + z * pres.std())
            st.metric(f"Parametric VaR ({alpha}%)", f"{pvar:.2%}")
        else:
            st.info("Install scipy for parametric VaR")

    # Rolling volatility
    st.markdown("---")
    st.subheader("Rolling 30-Day Volatility")
    roll = pres.rolling(30).std() * np.sqrt(252)
    st.line_chart(roll)

# -------------------------------------------------------------
# CPI UI
# -------------------------------------------------------------
def ui_cpi():
    st.header("📉 Inflation & CPI Dashboard")

    st.sidebar.subheader("Optional FRED API")
    fred_key = st.sidebar.text_input("FRED API Key")

    st.subheader("US CPI Data")

    # ------------------- FETCH -------------------------------
    if fred_key.strip() and HAS_FRED:
        try:
            fred = Fred(api_key=fred_key)
            s = fred.get_series("CPIAUCSL")
            df = s.reset_index().rename(columns={'index':'date', 0:'CPI'})
            df['date'] = pd.to_datetime(df['date'])
            df['CPI'] = pd.to_numeric(df['CPI'], errors='coerce')
            st.success("Fetched CPI from FRED")
        except:
            st.error("FRED fetch failed — using sample data")
            df = sample_cpi("US")
    else:
        f = st.file_uploader("Upload CPI CSV", type=['csv'])
        if f:
            df = pd.read_csv(f)
            df.columns = ['date','CPI']
            df['date'] = pd.to_datetime(df['date'])
            df['CPI'] = pd.to_numeric(df['CPI'], errors='coerce')
        else:
            df = sample_cpi("US")

    df['YoY'] = df['CPI'].pct_change(12)*100
    df['MoM'] = df['CPI'].pct_change()*100

    st.dataframe(df.tail())

    st.subheader("CPI Trend")
    st.line_chart(df.set_index('date')['CPI'])

    st.subheader("YoY Inflation (%)")
    st.line_chart(df.set_index('date')['YoY'])

    st.subheader("MoM Inflation (%)")
    st.bar_chart(df.set_index('date')['MoM'])

    # Inflation calculator
    st.markdown("---")
    st.subheader("Inflation Calculator")
    o = st.number_input("Old CPI", value=100.0)
    n = st.number_input("New CPI", value=105.0)
    if st.button("Compute Inflation"):
        st.success(f"Inflation = {(n-o)/o*100:.2f}%")

# -------------------------------------------------------------
# INTEREST UI
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator")

    P = st.number_input("Loan Amount", value=100000.0)
    r = st.number_input("Annual Rate (%)", value=7.5)
    y = st.number_input("Years", value=5)
    freq = st.selectbox("Payments per year", [12,4,2,1])

    rate = r/100/freq
    n = int(y*freq)

    if n <= 0:
        st.error("Invalid term")
        return

    if rate == 0:
        emi = P/n
    else:
        emi = P*rate*(1+rate)**n / ((1+rate)**n - 1)

    st.metric("EMI", f"{emi:.2f}")
    st.write(f"Total Payment: {emi*n:.2f}")
    st.write(f"Total Interest: {emi*n - P:.2f}")

    # Amortization Table
    st.subheader("Amortization Schedule")
    balance = P
    rows = []

    for i in range(1, n+1):
        interest = balance*rate
        principal = emi - interest
        balance -= principal
        rows.append([i, emi, principal, interest, balance])

    df = pd.DataFrame(rows, columns=['Period','EMI','Principal','Interest','Balance'])
    st.dataframe(df.head(20))

    st.line_chart(df.set_index('Period')['Balance'])

# -------------------------------------------------------------
# APP TABS
# -------------------------------------------------------------
tabs = st.tabs(["Risk-O-Meter", "Inflation & CPI", "Interest", "About"])

with tabs[0]: ui_risk()
with tabs[1]: ui_cpi()
with tabs[2]: ui_interest()
with tabs[3]:
    st.header("ℹ About")
    st.write("""
    ### Finance Toolkit (Pro Edition)
    Built entirely with **Python + Streamlit**  
    No external data dependencies required.

    ### Recommended `requirements.txt`
    ```
    streamlit
    pandas
    numpy
    scipy       # optional
    fredapi     # optional
    ```

    ### Run Locally
    ```
    streamlit run streamlit_finance_app.py
    ```
    """)
