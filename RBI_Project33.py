# RBI_dashboard_safe.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --- Optional import of matplotlib (don't fail if missing) ---
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False

import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="RBI Economic Dashboard (Safe)", layout="wide")

# -------------------------------
# DATA GENERATORS
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
        "Gross_NPA_pct": np.round(np.random.uniform(1, 9, len(banks)), 2),
        "CAR_pct": np.round(np.random.uniform(10, 16, len(banks)), 2),
        "Credit_Growth_pct": np.round(np.random.uniform(2, 18, len(banks)), 2)
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
view = st.sidebar.selectbox("Dashboard View",
                            ["Overview", "Inflation", "Monetary Policy", "Banking", "Risk & Stability", "3D Analytics"])

# -------------------------------
# HEADER KPIs
# -------------------------------
st.title("📊 RBI Macro Economic Dashboard (Safe)")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Repo Rate", f"{repo_df.iloc[-1]['repo_rate']}%")
k2.metric("India CPI", india_cpi.iloc[-1]['CPI'])
k3.metric("USA CPI", usa_cpi.iloc[-1]['CPI'])
k4.metric("Forex Reserves (USD bn)", forex_df.iloc[-1]['Forex_USD_bn'])

# -------------------------------
# OVERVIEW DASHBOARD
# -------------------------------
if view == "Overview":
    st.subheader("📌 Economic Overview (Interactive)")
    # Plotly line charts — plotly works even if matplotlib is absent
    st.plotly_chart(px.line(india_cpi, x="date", y=["CPI", "Core_CPI"], title="India CPI & Core CPI"), use_container_width=True)
    st.plotly_chart(px.line(usa_cpi, x="date", y=["CPI", "Core_CPI"], title="USA CPI & Core CPI"), use_container_width=True)
    st.plotly_chart(px.line(repo_df, x="date", y="repo_rate", title="Repo Rate Trend"), use_container_width=True)
    st.plotly_chart(px.line(forex_df, x="date", y="Forex_USD_bn", title="Forex Reserves (USD bn)"), use_container_width=True)
    st.plotly_chart(px.bar(bank_df, x="Bank", y="Gross_NPA_pct", title="Gross NPA by Bank"), use_container_width=True)

# -------------------------------
# INFLATION
# -------------------------------
elif view == "Inflation":
    st.subheader("India Inflation")
    st.plotly_chart(px.line(india_cpi, x="date", y=["CPI", "Core_CPI"], title="India CPI & Core CPI"), use_container_width=True)
    st.subheader("USA Inflation")
    st.plotly_chart(px.line(usa_cpi, x="date", y=["CPI", "Core_CPI"], title="USA CPI & Core CPI"), use_container_width=True)

# -------------------------------
# MONETARY POLICY
# -------------------------------
elif view == "Monetary Policy":
    st.subheader("Repo Rate Trends (Interactive)")
    st.plotly_chart(px.line(repo_df, x="date", y="repo_rate", title="Repo Rate"), use_container_width=True)

    st.subheader("Yield Curve")
    st.plotly_chart(px.line(yield_df, x="Tenor", y="Yield_pct", title="Yield Curve", markers=True), use_container_width=True)

    # If matplotlib is available, show an additional correlation scatter from matplotlib
    if HAS_MATPLOTLIB:
        st.subheader("Repo Rate vs India CPI (Matplotlib scatter)")
        # prepare a merged sample by resampling CPI to monthly repo dates (safe operation)
        merged = pd.merge_asof(repo_df.sort_values("date"), india_cpi.sort_values("date"), on="date", direction="backward")
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.scatter(merged["repo_rate"], merged["CPI"])
        ax.set_xlabel("Repo Rate (%)")
        ax.set_ylabel("India CPI")
        ax.set_title("Repo Rate vs India CPI")
        st.pyplot(fig)
    else:
        st.info("Matplotlib not installed — showing same chart as an interactive Plotly scatter.")
        merged = pd.merge_asof(repo_df.sort_values("date"), india_cpi.sort_values("date"), on="date", direction="backward")
        st.plotly_chart(px.scatter(merged, x="repo_rate", y="CPI", title="Repo Rate vs India CPI"), use_container_width=True)

# -------------------------------
# BANKING
# -------------------------------
elif view == "Banking":
    st.subheader("Banking Stability Indicators")
    st.dataframe(bank_df)
    st.plotly_chart(px.bar(bank_df, x="Bank", y="Credit_Growth_pct", title="Credit Growth by Bank"), use_container_width=True)

    # Radar-like polar chart using plotly (works without matplotlib)
    st.plotly_chart(px.line_polar(bank_df, r="Credit_Growth_pct", theta="Bank", line_close=True, title="Bank Credit Growth (polar)"), use_container_width=True)

# -------------------------------
# RISK & STABILITY
# -------------------------------
elif view == "Risk & Stability":
    st.subheader("Portfolio Risk Meter (VaR)")
    returns = np.random.normal(0.001, 0.02, 252)  # simulated returns
    var = compute_var(returns)
    st.metric("Portfolio VaR (99%)", f"{var}%")

    st.plotly_chart(px.histogram(returns, nbins=50, title="Return Distribution (simulated)"), use_container_width=True)

# -------------------------------
# 3D ANALYTICS
# -------------------------------
elif view == "3D Analytics":
    st.subheader("3D CPI Interaction (Plotly surface)")
    # keep the surface small to avoid heavy memory usage
    n = 40
    z = np.outer(india_cpi["CPI"].values[:n], usa_cpi["CPI"].values[:n])
    fig = go.Figure(data=[go.Surface(z=z)])
    fig.update_layout(title="India CPI x USA CPI (surface)", autosize=True, height=500)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# DOWNLOADS
# -------------------------------
st.sidebar.header("Downloads")
st.sidebar.download_button("India CPI CSV", india_cpi.to_csv(index=False), "india_cpi.csv")
st.sidebar.download_button("USA CPI CSV", usa_cpi.to_csv(index=False), "usa_cpi.csv")

st.markdown("---")
if not HAS_MATPLOTLIB:
    st.warning("Matplotlib is not installed in this environment. For additional static plots (matplotlib) install `matplotlib` or include it in requirements.txt.")
st.caption("RBI-style macro dashboard — resilient to missing matplotlib.")
