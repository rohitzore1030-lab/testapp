"""
Streamlit RBI Dashboard — ZERO-MATPLOTLIB VERSION
File: RBI_Dashboard.py

This version avoids matplotlib/plotly/scipy entirely so it will not fail due to missing plotting libraries.
Dependencies: streamlit, pandas, numpy

Run:
    pip install streamlit pandas numpy
    streamlit run RBI_Dashboard.py

Included features:
- Repo rate trend (st.line_chart)
- CPI & Core CPI
- Forex & Gold
- Banking health (bar chart)
- UPI payments
- Yield curve table
- VaR (historical percentile)
- Stress shock simulation
- CSV download buttons
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="RBI Dashboard (Light)", layout="wide")

# -------------------------------
# Data generators (offline-safe)
# -------------------------------
@st.cache_data
def fetch_repo_rate_history():
    dates = pd.date_range(end=datetime.today(), periods=60, freq='M')
    repo = np.clip(4 + np.sin(np.arange(len(dates)) / 6) * 1.5 + np.linspace(-0.5, 1.5, len(dates)), 3, 8)
    return pd.DataFrame({"date": dates, "repo_rate": np.round(repo, 2)})

@st.cache_data
def fetch_cpi_series():
    dates = pd.date_range(end=datetime.today(), periods=120, freq='M')
    cpi = 150 + np.cumsum(np.random.normal(0.3, 0.8, len(dates)))
    core = cpi - np.random.normal(3, 1, len(dates))
    return pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2), "Core_CPI": np.round(core, 2)})

@st.cache_data
def fetch_forex_reserves():
    dates = pd.date_range(end=datetime.today(), periods=36, freq='M')
    reserves = 400 + np.cumsum(np.random.normal(1, 2, len(dates)))
    gold = 35 + np.cumsum(np.random.normal(0.05, 0.2, len(dates)))
    return pd.DataFrame({"date": dates, "Forex_Reserves_USD_bn": np.round(reserves, 2), "Gold_tonnes": np.round(gold, 2)})

@st.cache_data
def fetch_banking_health():
    banks = ["SBI", "HDFC", "ICICI", "PNB", "AXIS", "BOB"]
    return pd.DataFrame({
        "Bank": banks,
        "Gross_NPA_pct": np.round(np.random.uniform(1, 10, 6), 2),
        "Net_NPA_pct": np.round(np.random.uniform(0.3, 6, 6), 2),
        "CAR_pct": np.round(np.random.uniform(10, 16, 6), 2),
        "Credit_Growth_pct": np.round(np.random.uniform(-5, 18, 6), 2)
    })

@st.cache_data
def fetch_upi_data():
    dates = pd.date_range(end=datetime.today(), periods=30, freq='D')
    txns = 400 + np.cumsum(np.random.normal(5, 10, len(dates)))
    value = 8 + np.cumsum(np.random.normal(0.1, 0.2, len(dates)))
    return pd.DataFrame({"date": dates, "Txn_Count_mn": np.round(txns, 2), "Txn_Value_bn": np.round(value, 2)})

@st.cache_data
def simulate_yield_curve():
    tenors = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    yields = [5.1, 5.2, 5.25, 5.4, 5.6, 6.0, 6.4, 6.6]
    return pd.DataFrame({"Tenor": tenors, "Yield_pct": yields})

# -------------------------------
# VAR calculation (historical)
# -------------------------------
def compute_var_historical(returns, confidence=0.99):
    if len(returns) < 10:
        return np.nan
    alpha = 1 - confidence
    var = -np.percentile(returns, alpha * 100)
    return var

# -------------------------------
# Sidebar controls
# -------------------------------
st.sidebar.title("RBI Dashboard — Controls")
view_mode = st.sidebar.selectbox("View mode", ["Executive Snapshot", "Detailed Panels", "Risk & Scenarios"]) 
start_date = st.sidebar.date_input("Start date", datetime.today() - timedelta(days=365))
end_date = st.sidebar.date_input("End date", datetime.today())
if start_date > end_date:
    st.sidebar.error("Start date must be before end date")

# toggles
show_forex = st.sidebar.checkbox("Show Forex", True)
show_inflation = st.sidebar.checkbox("Show Inflation", True)
show_banking = st.sidebar.checkbox("Show Banking", True)
show_payments = st.sidebar.checkbox("Show Payments", True)

# -------------------------------
# Load data
# -------------------------------
repo_df = fetch_repo_rate_history()
cpi_df = fetch_cpi_series()
forex_df = fetch_forex_reserves()
bank_df = fetch_banking_health()
upi_df = fetch_upi_data()
yield_df = simulate_yield_curve()

# apply date filters where relevant
repo_df = repo_df[(repo_df['date'].dt.date >= start_date) & (repo_df['date'].dt.date <= end_date)]
cpi_df = cpi_df[(cpi_df['date'].dt.date >= start_date) & (cpi_df['date'].dt.date <= end_date)]
forex_df = forex_df[(forex_df['date'].dt.date >= start_date) & (forex_df['date'].dt.date <= end_date)]
upi_df = upi_df[(upi_df['date'].dt.date >= start_date) & (upi_df['date'].dt.date <= end_date)]

# -------------------------------
# Header & KPIs
# -------------------------------
st.title("📊 RBI — Central Dashboard (Light)")
st.markdown("Offline-safe Streamlit RBI dashboard (no matplotlib/plotly required).")

k1, k2, k3, k4 = st.columns(4)
latest_repo = repo_df.iloc[-1]['repo_rate'] if not repo_df.empty else np.nan
k1.metric("Repo Rate (latest)", f"{latest_repo} %")
latest_cpi = cpi_df.iloc[-1]['CPI'] if not cpi_df.empty else np.nan
k2.metric("CPI (latest)", f"{latest_cpi}")
latest_res = forex_df.iloc[-1]['Forex_Reserves_USD_bn'] if not forex_df.empty else np.nan
k3.metric("Forex Reserves (USD bn)", f"{latest_res}")
latest_upi = upi_df.iloc[-1]['Txn_Value_bn'] if not upi_df.empty else np.nan
k4.metric("UPI txn value (bn)", f"{latest_upi}")

# -------------------------------
# Views
# -------------------------------
if view_mode == "Executive Snapshot":
    st.header("Executive Snapshot")
    left, right = st.columns([2,1])
    with left:
        st.subheader("Repo Rate History")
        st.line_chart(repo_df.set_index('date')['repo_rate'])

        if show_inflation:
            st.subheader("Inflation — CPI & Core CPI")
            st.line_chart(cpi_df.set_index('date')[['CPI', 'Core_CPI']])

    with right:
        st.subheader("Yield Curve (table)")
        st.table(yield_df)
        if show_forex:
            st.subheader("Forex Reserves (recent)")
            st.table(forex_df.tail(6).set_index('date'))

elif view_mode == "Detailed Panels":
    st.header("Detailed Panels")

    if show_inflation:
        st.subheader("Inflation Details")
        st.dataframe(cpi_df.reset_index(drop=True))

    if show_banking:
        st.subheader("Banking Health")
        st.dataframe(bank_df)
        st.bar_chart(bank_df.set_index('Bank')['Gross_NPA_pct'])

    if show_forex:
        st.subheader("Forex & Gold")
        st.line_chart(forex_df.set_index('date'))

    if show_payments:
        st.subheader("Digital Payments — UPI")
        st.line_chart(upi_df.set_index('date'))

    st.subheader("Yield Curve")
    st.table(yield_df)

elif view_mode == "Risk & Scenarios":
    st.header("Risk & Scenarios")
    st.write("Simple VaR calculator using historical simulation (synthetic returns). Replace with real portfolio returns for production.")

    tickers = st.text_input("Portfolio tickers (comma-separated)", value="BANK,NIFTY,INFRA")
    tickers_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
    n_days = st.number_input("Historical days", min_value=30, max_value=2000, value=252)
    confidence = st.slider("VaR confidence (%)", 90, 99, 99)

    # simulate returns
    np.random.seed(42)
    returns = {}
    for t in tickers_list:
        mu = np.random.uniform(-0.0002, 0.0008)
        sigma = np.random.uniform(0.008, 0.025)
        returns[t] = np.random.normal(loc=mu, scale=sigma, size=n_days)

    var_rows = []
    for t in tickers_list:
        v = compute_var_historical(returns[t], confidence/100.0)
        var_rows.append({"Ticker": t, "VaR_pct": round(v*100, 3)})

    st.dataframe(pd.DataFrame(var_rows))

    # portfolio (equal weight)
    if len(tickers_list) > 0:
        w = np.ones(len(tickers_list)) / len(tickers_list)
        stacked = np.vstack([returns[t] for t in tickers_list]).T
        port_returns = stacked.dot(w)
        port_var = compute_var_historical(port_returns, confidence/100.0)
        st.metric("Portfolio VaR (equal weight)", f"{round(port_var*100,3)}% at {confidence}%")

    st.markdown("---")
    st.subheader("Stress Scenario: Repo rate shock")
    shock_bps = st.slider("Repo shock (bps)", min_value=-200, max_value=300, value=50)
    st.write(f"Applying {shock_bps} bps shock — short-tenor yields will move more than long-tenor yields (simulated).")
    # simple shock table
    shocked = yield_df.copy()
    short_mask = shocked['Tenor'].isin(['1Y','2Y','3Y','5Y'])
    shocked['Yield_pct_shocked'] = shocked['Yield_pct'] + np.where(short_mask, shock_bps/100.0, (shock_bps/100.0)*0.4)
    st.table(shocked)

# -------------------------------
# Downloads
# -------------------------------
st.sidebar.header("Download Data")
st.sidebar.download_button("Download CPI CSV", data=cpi_df.to_csv(index=False), file_name="cpi.csv", mime='text/csv')
st.sidebar.download_button("Download Repo CSV", data=repo_df.to_csv(index=False), file_name="repo.csv", mime='text/csv')

st.markdown("---")
st.caption("This lightweight dashboard avoids external plotting libraries so it works in minimal environments. Replace fetch_* with live sources when ready.")


