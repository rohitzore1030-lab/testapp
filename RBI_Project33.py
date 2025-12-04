import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="RBI Economic Dashboard", layout="wide")

# -------------------------------
# DATA GENERATORS (OFFLINE SAFE)
# -------------------------------
@st.cache_data
def generate_cpi(country):
    dates = pd.date_range(end=datetime.today(), periods=120, freq='M')
    base = 140 if country == "India" else 260
    cpi = base + np.cumsum(np.random.normal(0.3, 0.6, len(dates)))
    core = cpi - np.random.normal(2, 1, len(dates))
    return pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2), "Core_CPI": np.round(core, 2)})

@st.cache_data
def fetch_repo_rate():
    dates = pd.date_range(end=datetime.today(), periods=60, freq='M')
    repo = np.clip(5 + np.sin(np.arange(len(dates)) / 7), 3, 8)
    return pd.DataFrame({"date": dates, "repo_rate": np.round(repo, 2)})

@st.cache_data
def fetch_forex():
    dates = pd.date_range(end=datetime.today(), periods=36, freq='M')
    reserves = 400 + np.cumsum(np.random.normal(1, 2, len(dates)))
    gold = 35 + np.cumsum(np.random.normal(0.05, 0.2, len(dates)))
    return pd.DataFrame({"date": dates, "Forex_USD_bn": np.round(reserves, 2), "Gold_Tonnes": np.round(gold, 2)})

@st.cache_data
def fetch_banks():
    banks = ["SBI", "HDFC", "ICICI", "PNB", "AXIS", "BOB"]
    return pd.DataFrame({
        "Bank": banks,
        "Gross_NPA_pct": np.round(np.random.uniform(1, 9, 6), 2),
        "CAR_pct": np.round(np.random.uniform(10, 16, 6), 2),
        "Credit_Growth_pct": np.round(np.random.uniform(2, 18, 6), 2)
    })

@st.cache_data
def fetch_upi():
    dates = pd.date_range(end=datetime.today(), periods=30, freq='D')
    txns = 400 + np.cumsum(np.random.normal(5, 10, len(dates)))
    value = 8 + np.cumsum(np.random.normal(0.1, 0.2, len(dates)))
    return pd.DataFrame({"date": dates, "Txn_Count_mn": np.round(txns, 2), "Txn_Value_bn": np.round(value, 2)})

@st.cache_data
def yield_curve():
    tenors = ["1Y", "2Y", "3Y", "5Y", "10Y", "30Y"]
    yields = [5.2, 5.3, 5.4, 5.6, 6.1, 6.5]
    return pd.DataFrame({"Tenor": tenors, "Yield_pct": yields})

# -------------------------------
# VAR FUNCTION
# -------------------------------
def compute_var(returns, confidence=0.99):
    alpha = 1 - confidence
    var = -np.percentile(returns, alpha * 100)
    return round(var * 100, 3)

# -------------------------------
# LOAD DATA
# -------------------------------
india_cpi = generate_cpi("India")
usa_cpi = generate_cpi("USA")
repo_df = fetch_repo_rate()
forex_df = fetch_forex()
bank_df = fetch_banks()
upi_df = fetch_upi()
yield_df = yield_curve()

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title("RBI Macro Controls")
view = st.sidebar.selectbox("Dashboard View", ["Overview", "Inflation", "Monetary Policy", "Banking", "Risk & Stability"])

# -------------------------------
# HEADER KPIs
# -------------------------------
st.title("📊 RBI Macro Economic Dashboard")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Repo Rate", f"{repo_df.iloc[-1]['repo_rate']}%")
k2.metric("India CPI", india_cpi.iloc[-1]['CPI'])
k3.metric("USA CPI", usa_cpi.iloc[-1]['CPI'])
k4.metric("Forex Reserves (USD bn)", forex_df.iloc[-1]['Forex_USD_bn'])

# -------------------------------
# OVERVIEW DASHBOARD
# -------------------------------
if view == "Overview":
    st.subheader("📌 Economic Overview")
    st.line_chart(india_cpi.set_index("date")[["CPI", "Core_CPI"]])
    st.line_chart(usa_cpi.set_index("date")[["CPI", "Core_CPI"]])
    st.line_chart(repo_df.set_index("date")["repo_rate"])
    st.line_chart(forex_df.set_index("date")["Forex_USD_bn"])
    st.bar_chart(bank_df.set_index("Bank")["Gross_NPA_pct"])

# -------------------------------
# INFLATION
# -------------------------------
elif view == "Inflation":
    st.subheader("India Inflation")
    st.line_chart(india_cpi.set_index("date"))
    st.subheader("USA Inflation")
    st.line_chart(usa_cpi.set_index("date"))

# -------------------------------
# MONETARY POLICY
# -------------------------------
elif view == "Monetary Policy":
    st.subheader("Repo Rate Trends")
    st.line_chart(repo_df.set_index("date"))
    st.subheader("Yield Curve")
    st.table(yield_df)

# -------------------------------
# BANKING
# -------------------------------
elif view == "Banking":
    st.subheader("Banking Stability Indicators")
    st.dataframe(bank_df)
    st.bar_chart(bank_df.set_index("Bank")["Credit_Growth_pct"])

# -------------------------------
# RISK & STABILITY
# -------------------------------
elif view == "Risk & Stability":
    st.subheader("Portfolio Risk Meter (VaR)")
    tickers = ["NIFTY", "BANK", "IT"]
    returns = np.random.normal(0.001, 0.02, 252)
    var = compute_var(returns)
    st.metric("Portfolio VaR (99%)", f"{var}%")

# -------------------------------
# DOWNLOADS
# -------------------------------
st.sidebar.header("Downloads")
st.sidebar.download_button("India CPI CSV", india_cpi.to_csv(index=False), "india_cpi.csv")
st.sidebar.download_button("USA CPI CSV", usa_cpi.to_csv(index=False), "usa_cpi.csv")

st.markdown("---")
st.caption("Professional RBI-style macro dashboard with Inflation, Policy, Banking, Risk & Forex.")
