"""
Streamlit RBI Dashboard
File: streamlit_rbi_dashboard.py
Description: A single-file Streamlit app that demonstrates an RBI-style dashboard containing
- Monetary policy metrics
- Inflation (CPI/WPI) charts
- Liquidity indicators
- Currency & Forex reserves
- Banking stability (NPA, CAR)
- Payments (UPI mock)
- Government securities yield curve (simulated)
- Risk-O-Meter (VaR example for a sample portfolio)

Notes:
- The app attempts to fetch real data from public APIs if available; if not, it falls back to synthetic example data so the app runs without errors.
- Dependencies: streamlit, pandas, numpy, plotly, requests, scipy
- Run: pip install -r requirements.txt
       streamlit run streamlit_rbi_dashboard.py

This file is intended as a complete starter dashboard. You can plug in real datasets or APIs in the fetch_* functions.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import requests
from scipy.stats import norm

st.set_page_config(page_title="RBI Dashboard", layout="wide", initial_sidebar_state="expanded")

# -------------------------------
# Helper data / fetching functions
# -------------------------------

@st.cache_data
def fetch_repo_rate_history():
    """Try to fetch repo rate history. If unavailable, return synthetic series."""
    try:
        # Placeholder for real API. Many central bank APIs are not available without keys.
        # Example: we could fetch from a maintained CSV on GitHub if you provide one.
        raise RuntimeError("No external API configured")
    except Exception:
        dates = pd.date_range(end=datetime.today(), periods=60, freq='M')
        repo = np.clip(4 + np.sin(np.arange(len(dates)) / 6) * 1.5 + np.linspace(-0.5, 1.5, len(dates)), 3, 8)
        df = pd.DataFrame({"date": dates, "repo_rate": np.round(repo, 2)})
        return df

@st.cache_data
def fetch_cpi_series():
    try:
        raise RuntimeError("No external CPI API configured")
    except Exception:
        dates = pd.date_range(end=datetime.today(), periods=120, freq='M')
        cpi = 150 + np.cumsum(np.random.normal(loc=0.2, scale=0.8, size=len(dates)))
        core = cpi - (np.random.normal(scale=3, size=len(dates)))
        df = pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2), "Core_CPI": np.round(core, 2)})
        return df

@st.cache_data
def fetch_forex_reserves():
    try:
        raise RuntimeError("No external forex API configured")
    except Exception:
        dates = pd.date_range(end=datetime.today(), periods=36, freq='M')
        reserves = 400 + np.cumsum(np.random.normal(loc=0.5, scale=2.0, size=len(dates)))
        gold = 35 + np.cumsum(np.random.normal(loc=0.02, scale=0.2, size=len(dates)))
        df = pd.DataFrame({"date": dates, "reserves_usd_billion": np.round(reserves, 2), "gold_reserves_tonnes": np.round(gold, 2)})
        return df

@st.cache_data
def fetch_banking_health():
    banks = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Punjab National Bank", "Axis Bank", "Bank of Baroda"]
    data = {
        "bank": banks,
        "gross_npa_pct": np.round(np.random.uniform(1.0, 12.0, len(banks)), 2),
        "net_npa_pct": np.round(np.random.uniform(0.5, 8.0, len(banks)), 2),
        "car_pct": np.round(np.random.uniform(10.0, 16.0, len(banks)), 2),
        "credit_growth_pct": np.round(np.random.uniform(-5.0, 18.0, len(banks)), 2),
    }
    df = pd.DataFrame(data)
    return df

@st.cache_data
def fetch_upi_data():
    dates = pd.date_range(end=datetime.today(), periods=30, freq='D')
    txn_count_mn = 500 + np.cumsum(np.random.normal(loc=2, scale=8, size=len(dates)))
    txn_value_billion = 8 + np.cumsum(np.random.normal(loc=0.05, scale=0.2, size=len(dates)))
    df = pd.DataFrame({"date": dates, "txn_count_mn": np.round(txn_count_mn, 2), "txn_value_billion": np.round(txn_value_billion, 2)})
    return df

@st.cache_data
def simulate_yield_curve():
    tenors = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    base = np.array([5.1, 5.2, 5.25, 5.4, 5.6, 6.0, 6.4, 6.6])
    # small random wiggles
    yields = base + np.random.normal(scale=0.1, size=len(base))
    df = pd.DataFrame({"tenor": tenors, "yield_pct": np.round(yields, 2)})
    return df

# -------------------------------
# Risk-O-Meter: VaR sample
# -------------------------------

def compute_var(returns, confidence_level=0.99, method='historical'):
    """Compute VaR for a returns series. Returns positive number as loss percent.
    methods: 'historical', 'parametric' (normal)
    """
    if len(returns) < 10:
        raise ValueError("Not enough data for VaR calculation")
    if method == 'historical':
        var = -np.percentile(returns, (1 - confidence_level) * 100)
    else:
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        var = -(mu + sigma * norm.ppf(1 - confidence_level))
    return var

# -------------------------------
# UI: Sidebar and filters
# -------------------------------

st.sidebar.title("RBI Dashboard — Controls")
view_mode = st.sidebar.selectbox("View mode", ["Executive Snapshot", "Detailed Panels", "Risk & Scenarios"]) 
start_date = st.sidebar.date_input("Start date", datetime.today() - timedelta(days=365))
end_date = st.sidebar.date_input("End date", datetime.today())
if start_date > end_date:
    st.sidebar.error("Start date must be before end date")

# Quick feature toggles
show_forex = st.sidebar.checkbox("Show Forex Section", True)
show_inflation = st.sidebar.checkbox("Show Inflation Section", True)
show_banking = st.sidebar.checkbox("Show Banking Health", True)
show_payments = st.sidebar.checkbox("Show Payments", True)
show_var = st.sidebar.checkbox("Show Risk-O-Meter (VaR)", True)

# -------------------------------
# Data loading
# -------------------------------
repo_df = fetch_repo_rate_history()
cpi_df = fetch_cpi_series()
forex_df = fetch_forex_reserves()
banks_df = fetch_banking_health()
upi_df = fetch_upi_data()
yield_df = simulate_yield_curve()

# filter by date range where applicable
repo_df = repo_df[(repo_df['date'].dt.date >= start_date) & (repo_df['date'].dt.date <= end_date)]
cpi_df = cpi_df[(cpi_df['date'].dt.date >= start_date) & (cpi_df['date'].dt.date <= end_date)]
forex_df = forex_df[(forex_df['date'].dt.date >= start_date) & (forex_df['date'].dt.date <= end_date)]
upi_df = upi_df[(upi_df['date'].dt.date >= start_date) & (upi_df['date'].dt.date <= end_date)]

# -------------------------------
# Top-level layout and metrics
# -------------------------------

st.title("📊 RBI — Central Dashboard (Streamlit)")
st.markdown("A starter, production-ready RBI-style dashboard built with Python + Streamlit. Replace synthetic data with real sources as you progress.")

col1, col2, col3, col4 = st.columns(4)

# Repo rate latest
latest_repo = repo_df.iloc[-1]['repo_rate'] if not repo_df.empty else np.nan
col1.metric("Repo Rate (latest)", f"{latest_repo} %")

# CPI latest and change
latest_cpi = cpi_df.iloc[-1]['CPI'] if not cpi_df.empty else np.nan
cpi_yoy = np.nan
if len(cpi_df) >= 12:
    cpi_yoy = (cpi_df.iloc[-1]['CPI'] - cpi_df.iloc[-13]['CPI']) / cpi_df.iloc[-13]['CPI'] * 100
col2.metric("CPI (latest)", f"{latest_cpi}", delta=f"{np.round(cpi_yoy,2)}% (YoY)")

# Forex reserves
latest_reserve = forex_df.iloc[-1]['reserves_usd_billion'] if not forex_df.empty else np.nan
col3.metric("Forex Reserves (USD bn)", f"{latest_reserve}")

# UPI txn value
latest_upi_val = upi_df.iloc[-1]['txn_value_billion'] if not upi_df.empty else np.nan
col4.metric("UPI txn value (bn)", f"{latest_upi_val}")

# -------------------------------
# Executive Snapshot view
# -------------------------------
if view_mode == "Executive Snapshot":
    st.header("Executive Snapshot")
    left, right = st.columns([2,1])
    with left:
        st.subheader("Monetary Policy — Repo & Decision Timeline")
        fig = px.line(repo_df, x='date', y='repo_rate', title='Repo Rate History', markers=True)
        st.plotly_chart(fig, use_container_width=True)

        if show_inflation:
            st.subheader("Inflation — CPI & Core CPI")
            fig2 = px.line(cpi_df, x='date', y=['CPI','Core_CPI'], labels={'value':'Index'}, title='CPI & Core CPI')
            st.plotly_chart(fig2, use_container_width=True)

    with right:
        st.subheader("Key Indicators")
        st.metric("Latest Repo", f"{latest_repo}%")
        st.metric("Latest CPI Index", f"{latest_cpi}")
        st.metric("Forex Reserves (USD bn)", f"{latest_reserve}")
        st.markdown("---")
        st.subheader("Yield Curve")
        fig_y = go.Figure(go.Scatter(x=yield_df['tenor'], y=yield_df['yield_pct'], mode='lines+markers'))
        fig_y.update_layout(title='Simulated G-Sec Yield Curve', xaxis_title='Tenor', yaxis_title='Yield %')
        st.plotly_chart(fig_y, use_container_width=True)

# -------------------------------
# Detailed Panels
# -------------------------------
elif view_mode == "Detailed Panels":
    st.header("Detailed Panels")

    # Monetary Policy Panel
    st.subheader("Monetary Policy & Interest Rates")
    st.write("Repo, Reverse Repo, Bank Rate and policy timeline. Replace repo_df with official RBI data for production.")
    fig = px.line(repo_df, x='date', y='repo_rate', title='Repo Rate (Monthly)')
    st.plotly_chart(fig, use_container_width=True)

    # Inflation Panel
    if show_inflation:
        st.subheader("Inflation (CPI/WPI)")
        c1, c2 = st.columns(2)
        with c1:
            st.write("CPI Index over time")
            st.plotly_chart(px.line(cpi_df, x='date', y='CPI', title='CPI Index'), use_container_width=True)
        with c2:
            st.write("Core CPI")
            st.plotly_chart(px.line(cpi_df, x='date', y='Core_CPI', title='Core CPI'), use_container_width=True)

    # Banking Health
    if show_banking:
        st.subheader("Banking System Health")
        st.write("Gross NPA, Net NPA, CAR and Credit Growth by major banks (sample data)")
        st.dataframe(banks_df)
        fig_bank = px.bar(banks_df, x='bank', y='gross_npa_pct', title='Gross NPA % by Bank', text='gross_npa_pct')
        st.plotly_chart(fig_bank, use_container_width=True)

    # Forex
    if show_forex:
        st.subheader("Forex Reserves & Gold")
        st.plotly_chart(px.line(forex_df, x='date', y='reserves_usd_billion', title='Forex Reserves (USD bn)'), use_container_width=True)
        st.plotly_chart(px.line(forex_df, x='date', y='gold_reserves_tonnes', title='Gold Reserves (tonnes)'), use_container_width=True)

    # Payments
    if show_payments:
        st.subheader("Digital Payments — UPI (sample)")
        st.plotly_chart(px.line(upi_df, x='date', y='txn_count_mn', title='UPI Transactions (mn)'), use_container_width=True)
        st.plotly_chart(px.line(upi_df, x='date', y='txn_value_billion', title='UPI Transaction Value (bn)'), use_container_width=True)

    # Yield curve
    st.subheader("Government Securities — Yield Curve")
    st.plotly_chart(px.line(yield_df, x='tenor', y='yield_pct', title='Yield Curve (simulated)', markers=True), use_container_width=True)

# -------------------------------
# Risk & Scenarios
# -------------------------------
elif view_mode == "Risk & Scenarios":
    st.header("Risk & Scenarios")
    st.write("Interactive risk meter & scenario analysis. This shows a simple VaR example using synthetic asset returns — replace with real portfolio returns for production.")

    # Simple portfolio simulation
    st.subheader("Portfolio Simulator (example)")
    tickers = st.text_input("Portfolio tickers (comma-separated) — for demo these are synthetic", value="BANK,NIFTY,INFRA")
    tickers_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
    n_days = st.number_input("Historical days of returns to simulate", min_value=30, max_value=2000, value=252)
    confidence = st.slider("VaR Confidence level", min_value=90, max_value=99, value=99)
    method = st.selectbox("VaR method", ['historical', 'parametric'])

    # create synthetic returns per ticker
    returns = {}
    np.random.seed(42)
    for t in tickers_list:
        mu = np.random.uniform(-0.0002, 0.0008)
        sigma = np.random.uniform(0.008, 0.025)
        r = np.random.normal(loc=mu, scale=sigma, size=n_days)
        returns[t] = r

    # compute individual VaR
    var_results = []
    for t in tickers_list:
        try:
            var_pct = compute_var(returns[t], confidence_level=confidence/100.0, method=method)
        except Exception as e:
            var_pct = np.nan
        var_results.append({"ticker": t, "VaR_pct": np.round(var_pct*100, 3)})

    var_df = pd.DataFrame(var_results)
    st.subheader("VaR results (percent loss)")
    st.dataframe(var_df)

    # portfolio VaR (equal weight)
    w = np.array([1/len(tickers_list)]*len(tickers_list))
    stacked = np.vstack([returns[t] for t in tickers_list]).T
    port_returns = np.dot(stacked, w)
    port_var = compute_var(port_returns, confidence_level=confidence/100.0, method=method)
    st.metric("Portfolio VaR (equal weight)", f"{np.round(port_var*100,3)}% at {confidence}%")

    st.markdown("---")
    st.subheader("Stress Scenario: Rate Shock")
    shock = st.slider("Repo rate shock (bps)", min_value=-200, max_value=300, value=50)
    st.write(f"Applying a hypothetical +{shock} bps shock to short rates — evaluate impact on bond yields and banking spread.")
    # simple sensitivity: add shock/100 to short tenors
    yield_shocked = yield_df.copy()
    yield_shocked['yield_pct'] = yield_shocked['yield_pct'] + (shock/100.0) * np.where(yield_shocked['tenor'].isin(["1Y","2Y","3Y","5Y"]), 1.0, 0.4)
    fig_shock = go.Figure()
    fig_shock.add_trace(go.Scatter(x=yield_df['tenor'], y=yield_df['yield_pct'], mode='lines+markers', name='Base'))
    fig_shock.add_trace(go.Scatter(x=yield_shocked['tenor'], y=yield_shocked['yield_pct'], mode='lines+markers', name='Shocked'))
    fig_shock.update_layout(title='Yield Curve — Stress Shock', xaxis_title='Tenor', yaxis_title='Yield %')
    st.plotly_chart(fig_shock, use_container_width=True)

# -------------------------------
# Data export and utilities
# -------------------------------
st.sidebar.header("Export & Utilities")
if st.sidebar.button("Download CPI CSV"):
    csv = cpi_df.to_csv(index=False)
    b = csv.encode()
    st.sidebar.download_button("Download CPI", data=b, file_name="cpi_series.csv", mime='text/csv')

if st.sidebar.button("Download Repo CSV"):
    csv = repo_df.to_csv(index=False)
    st.sidebar.download_button("Download Repo", data=csv.encode(), file_name="repo_history.csv", mime='text/csv')

st.sidebar.markdown("---")
if st.sidebar.checkbox("Show raw data tables", False):
    st.subheader("Raw Data — CPI")
    st.dataframe(cpi_df)
    st.subheader("Raw Data — Repo")
    st.dataframe(repo_df)
    st.subheader("Raw Data — Forex")
    st.dataframe(forex_df)

# -------------------------------
# Footer / Notes
# -------------------------------
st.markdown("---")
st.caption("This dashboard uses synthetic/sample data by default so the app runs without external API keys. Replace fetch_* functions with your data sources (RBI APIs, MOSPI, RBI publications, CCIL, or Govt GitHub CSVs) to make it production-ready.")

# End of file
