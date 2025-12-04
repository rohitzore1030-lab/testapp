# RBI_DASHBOARD_FULL.py
"""
Professional RBI Macro Dashboard
- Plotly interactive charts + Matplotlib fallback
- 3D CPI surface, banking radar, yield curve, forex & VaR visuals
- Error-free and fully offline simulated data
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Optional imports
IMPORT_ERR = []
try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
except Exception:
    IMPORT_ERR.append("matplotlib")

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    IMPORT_ERR.append("plotly")

st.set_page_config(page_title="RBI Macro Dashboard", layout="wide")

# -------------------------------
# DATA GENERATORS
# -------------------------------
@st.cache_data
def generate_cpi(country, months=120, seed=None):
    rng = np.random.default_rng(seed or 42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=months, freq='M')
    base = 140 if country.lower().startswith("ind") else 260
    cpi = base + np.cumsum(rng.normal(0.35, 0.6, len(dates)))
    core = cpi - np.abs(rng.normal(1.6, 0.8, len(dates)))
    return pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2), "Core_CPI": np.round(core, 2)})

@st.cache_data
def fetch_repo_rate(months=60):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=months, freq='M')
    x = np.arange(len(dates))
    repo = 4.5 + 1.5*np.sin(x/7.0) + 0.5*np.cos(x/11.0)
    repo = np.clip(repo + np.random.normal(0, 0.15, len(dates)), 3.0, 8.0)
    return pd.DataFrame({"date": dates, "repo_rate": np.round(repo,2)})

@st.cache_data
def fetch_forex(months=36):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=months, freq='M')
    rng = np.random.default_rng(9)
    reserves = 400 + np.cumsum(rng.normal(1.2, 2.5, len(dates)))
    gold = 35 + np.cumsum(rng.normal(0.04, 0.15, len(dates)))
    return pd.DataFrame({"date": dates, "Forex_USD_bn": np.round(reserves,2), "Gold_Tonnes": np.round(gold,2)})

@st.cache_data
def fetch_banks():
    banks = ["SBI","HDFC","ICICI","PNB","AXIS","BOB"]
    rng = np.random.default_rng(21)
    return pd.DataFrame({
        "Bank": banks,
        "Gross_NPA_pct": np.round(rng.uniform(1,9,len(banks)),2),
        "CAR_pct": np.round(rng.uniform(11,16,len(banks)),2),
        "Credit_Growth_pct": np.round(rng.uniform(2,20,len(banks)),2)
    })

@st.cache_data
def fetch_upi(days=30):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D')
    rng = np.random.default_rng(123)
    txns = 400 + np.cumsum(rng.normal(5,10,len(dates)))
    value = 8 + np.cumsum(rng.normal(0.1,0.2,len(dates)))
    return pd.DataFrame({"date": dates, "Txn_Count_mn": np.round(txns,2), "Txn_Value_bn": np.round(value,2)})

@st.cache_data
def yield_curve():
    tenors = ["1Y","2Y","3Y","5Y","10Y","30Y"]
    yields = [5.2,5.3,5.4,5.6,6.1,6.5]
    return pd.DataFrame({"Tenor":tenors,"Yield_pct":yields})

def compute_var(returns, confidence=0.99):
    alpha = 1 - confidence
    var = -np.percentile(returns, alpha*100)
    return round(var*100,3)

# -------------------------------
# LOAD DATA
# -------------------------------
india_cpi = generate_cpi("India")
usa_cpi = generate_cpi("USA", seed=7)
repo_df = fetch_repo_rate()
forex_df = fetch_forex()
bank_df = fetch_banks()
upi_df = fetch_upi()
yield_df = yield_curve()

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title("RBI Macro Controls")
view = st.sidebar.radio("Select view", ["Overview","Inflation","Monetary Policy","Banking","Risk & Stability","3D Analytics"])

st.sidebar.header("Downloads")
st.sidebar.download_button("India CPI CSV", india_cpi.to_csv(index=False),"india_cpi.csv")
st.sidebar.download_button("USA CPI CSV", usa_cpi.to_csv(index=False),"usa_cpi.csv")
st.sidebar.download_button("Banks CSV", bank_df.to_csv(index=False),"banks.csv")
st.sidebar.download_button("Forex CSV", forex_df.to_csv(index=False),"forex.csv")

# -------------------------------
# HEADER KPIs
# -------------------------------
st.title("📊 RBI Macro Dashboard")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Repo Rate", f"{repo_df.iloc[-1]['repo_rate']}%")
c2.metric("India CPI", india_cpi.iloc[-1]['CPI'])
c3.metric("USA CPI", usa_cpi.iloc[-1]['CPI'])
c4.metric("Forex Reserves (USD bn)", forex_df.iloc[-1]['Forex_USD_bn'])

# -------------------------------
# OVERVIEW
# -------------------------------
if view=="Overview":
    st.subheader("Economic Overview")
    # CPI
    if "plotly" not in IMPORT_ERR:
        st.plotly_chart(px.line(india_cpi, x="date", y=["CPI","Core_CPI"], title="India Inflation"), use_container_width=True)
    else:
        st.line_chart(india_cpi.set_index("date")[["CPI","Core_CPI"]])
    # Repo Rate
    if "plotly" not in IMPORT_ERR:
        st.plotly_chart(px.line(repo_df, x="date", y="repo_rate", title="Repo Rate Trend"), use_container_width=True)
    else:
        st.line_chart(repo_df.set_index("date")["repo_rate"])
    # Bank NPA
    if "plotly" not in IMPORT_ERR:
        st.plotly_chart(px.bar(bank_df, x="Bank", y="Gross_NPA_pct", text="Gross_NPA_pct", title="Bank NPA Levels"), use_container_width=True)
    else:
        st.bar_chart(bank_df.set_index("Bank")["Gross_NPA_pct"])

# -------------------------------
# INFLATION
# -------------------------------
elif view=="Inflation":
    st.subheader("India vs USA CPI")
    if "plotly" not in IMPORT_ERR:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=india_cpi["date"], y=india_cpi["CPI"], name="India CPI"))
        fig.add_trace(go.Scatter(x=usa_cpi["date"], y=usa_cpi["CPI"], name="USA CPI"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(india_cpi.set_index("date")["CPI"])
        st.line_chart(usa_cpi.set_index("date")["CPI"])

# -------------------------------
# MONETARY POLICY
# -------------------------------
elif view=="Monetary Policy":
    st.subheader("Yield Curve")
    if "plotly" not in IMPORT_ERR:
        st.plotly_chart(px.line(yield_df, x="Tenor", y="Yield_pct", markers=True, title="Yield Curve"), use_container_width=True)
    elif "matplotlib" not in IMPORT_ERR:
        fig, ax = plt.subplots()
        ax.plot(yield_df["Tenor"], yield_df["Yield_pct"], marker="o")
        ax.set_title("Yield Curve")
        st.pyplot(fig)
    else:
        st.table(yield_df)

# -------------------------------
# BANKING
# -------------------------------
elif view=="Banking":
    st.subheader("Banking Health Radar")
    if "plotly" not in IMPORT_ERR:
        fig = go.Figure()
        for _, r in bank_df.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[r["Gross_NPA_pct"], r["CAR_pct"], r["Credit_Growth_pct"]],
                theta=["NPA","CAR","Credit Growth"],
                name=r["Bank"], fill="toself"
            ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    elif "matplotlib" not in IMPORT_ERR:
        fig = plt.figure()
        ax = fig.add_subplot(111, polar=True)
        categories = ["NPA","CAR","Credit Growth"]
        for _, r in bank_df.iterrows():
            values = [r["Gross_NPA_pct"], r["CAR_pct"], r["Credit_Growth_pct"]]
            values += values[:1]
            ax.plot(np.linspace(0,2*np.pi,len(values)), values, label=r["Bank"])
        ax.set_xticks(np.linspace(0,2*np.pi,len(categories)))
        ax.set_xticklabels(categories)
        ax.set_title("Banking Radar")
        ax.legend()
        st.pyplot(fig)

# -------------------------------
# RISK & STABILITY
# -------------------------------
elif view=="Risk & Stability":
    st.subheader("Portfolio VaR & Return Distribution")
    returns = np.random.normal(0.001,0.02,252)
    var = compute_var(returns)
    st.metric("Portfolio VaR (99%)", f"{var}%")
    if "plotly" not in IMPORT_ERR:
        st.plotly_chart(px.histogram(returns, nbins=50, title="Return Distribution"), use_container_width=True)
    elif "matplotlib" not in IMPORT_ERR:
        fig, ax = plt.subplots()
        ax.hist(returns, bins=50)
        ax.set_title("Return Distribution")
        st.pyplot(fig)

# -------------------------------
# 3D ANALYTICS
# -------------------------------
elif view=="3D Analytics":
    st.subheader("3D CPI Surface")
    z = np.outer(india_cpi["CPI"].values[:40], usa_cpi["CPI"].values[:40])
    if "plotly" not in IMPORT_ERR:
        fig = go.Figure(data=[go.Surface(z=z)])
        fig.update_layout(title="3D CPI Interaction (India vs USA)")
        st.plotly_chart(fig, use_container_width=True)
    elif "matplotlib" not in IMPORT_ERR:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        X, Y = np.meshgrid(range(z.shape[1]), range(z.shape[0]))
        ax.plot_surface(X,Y,z,cmap='viridis')
        ax.set_title("3D CPI Surface")
        st.pyplot(fig)

