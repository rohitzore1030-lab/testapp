# RBI_dashboard_pro.py
"""
Professional RBI Macro Dashboard
- Interactive Plotly charts + Matplotlib fallbacks/features
- 3D CPI surface, yield curve, banking radar, forex dual-axis, VaR visuals
- Designed to run locally (requires plotly + matplotlib installed)
"""

import streamlit as st
st.set_page_config(page_title="RBI Macro — Pro Dashboard", layout="wide")

import pandas as pd
import numpy as np
from datetime import datetime
from math import ceil

# Try imports and show guidance if missing
IMPORT_ERR = []
try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception as e:
    IMPORT_ERR.append("plotly")
try:
    import matplotlib.pyplot as plt
except Exception as e:
    IMPORT_ERR.append("matplotlib")
try:
    from scipy.signal import savgol_filter
except Exception:
    IMPORT_ERR.append("scipy")

if IMPORT_ERR:
    st.sidebar.warning(
        "Missing packages detected: " + ", ".join(IMPORT_ERR) +
        ".\nInstall them with:\n\npip install streamlit pandas numpy plotly matplotlib scipy\n\nApp may still run but visuals requiring those packages will fallback."
    )

# -------------------------------
# Utility / Data generators
# -------------------------------
@st.cache_data
def generate_cpi(country, months=120):
    dates = pd.date_range(end=datetime.today(), periods=months, freq='M')
    base = 140 if country.lower().startswith("ind") else 260
    rng = np.random.default_rng(seed=42 if country=="India" else 7)
    cpi = base + np.cumsum(rng.normal(0.35, 0.6, len(dates)))
    core = cpi - np.abs(rng.normal(1.6, 0.8, len(dates)))
    df = pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2), "Core_CPI": np.round(core, 2)})
    return df

@st.cache_data
def fetch_repo_rate(months=60):
    dates = pd.date_range(end=datetime.today(), periods=months, freq='M')
    x = np.arange(len(dates))
    repo = 4.5 + 1.5*np.sin(x/7.0) + 0.5*np.cos(x/11.0)
    repo = np.clip(repo + np.random.normal(0, 0.15, len(dates)), 3.0, 8.0)
    return pd.DataFrame({"date": dates, "repo_rate": np.round(repo, 2)})

@st.cache_data
def fetch_forex(months=48):
    dates = pd.date_range(end=datetime.today(), periods=months, freq='M')
    rng = np.random.default_rng(9)
    reserves = 400 + np.cumsum(rng.normal(1.2, 2.5, len(dates)))
    gold = 35 + np.cumsum(rng.normal(0.04, 0.15, len(dates)))
    return pd.DataFrame({"date": dates, "Forex_USD_bn": np.round(reserves, 2), "Gold_Tonnes": np.round(gold, 2)})

@st.cache_data
def fetch_banks():
    banks = ["SBI", "HDFC", "ICICI", "PNB", "AXIS", "BOB"]
    rng = np.random.default_rng(21)
    return pd.DataFrame({
        "Bank": banks,
        "Gross_NPA_pct": np.round(rng.uniform(1, 8.5, len(banks)), 2),
        "CAR_pct": np.round(rng.uniform(11, 16.5, len(banks)), 2),
        "Credit_Growth_pct": np.round(rng.uniform(2, 20, len(banks)), 2)
    })

@st.cache_data
def fetch_upi(days=60):
    dates = pd.date_range(end=datetime.today(), periods=days, freq='D')
    rng = np.random.default_rng(123)
    txns = 350 + np.cumsum(rng.normal(6, 12, len(dates)))
    value = 7.5 + np.cumsum(rng.normal(0.08, 0.28, len(dates)))
    return pd.DataFrame({"date": dates, "Txn_Count_mn": np.round(txns, 2), "Txn_Value_bn": np.round(value, 2)})

@st.cache_data
def yield_curve():
    tenors = ["1Y", "2Y", "3Y", "5Y", "10Y", "30Y"]
    yields = [5.0, 5.15, 5.25, 5.45, 6.0, 6.45]
    return pd.DataFrame({"Tenor": tenors, "Yield_pct": yields})

def compute_var(returns, confidence=0.99):
    alpha = 1 - confidence
    var = -np.percentile(returns, alpha * 100)
    return round(var * 100, 3)

# -------------------------------
# Load data
# -------------------------------
india_cpi = generate_cpi("India", months=120)
usa_cpi = generate_cpi("USA", months=120)
repo_df = fetch_repo_rate(60)
forex_df = fetch_forex(48)
bank_df = fetch_banks()
upi_df = fetch_upi(90)
yield_df = yield_curve()

# -------------------------------
# Sidebar controls
# -------------------------------
st.sidebar.title("RBI — Controls")
view = st.sidebar.radio("Select view", ["Overview", "Inflation", "Monetary Policy", "Banking", "Risk & Stability", "3D Analytics", "Export / Help"])

st.sidebar.markdown("---")
st.sidebar.write("Data: simulated offline (for demo).")
if st.sidebar.button("Regenerate (random seed)"):
    # Clear cache and reload (simple way)
    st.cache_data.clear()
    st.experimental_rerun()

# -------------------------------
# Header & KPIs
# -------------------------------
st.title("📈 RBI Macro Economic Dashboard — PRO")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Repo Rate (latest)", f"{repo_df['repo_rate'].iloc[-1]}%")
c2.metric("India CPI (latest)", f"{india_cpi['CPI'].iloc[-1]}")
c3.metric("USA CPI (latest)", f"{usa_cpi['CPI'].iloc[-1]}")
c4.metric("Forex Reserves (USD bn)", f"{forex_df['Forex_USD_bn'].iloc[-1]}")

st.markdown("Made for a finance resume — interactive Plotly + some Matplotlib visuals.")

# -------------------------------
# Overview
# -------------------------------
if view == "Overview":
    st.subheader("Economic Overview")

    # Two-column layout: inflation trends (left) and repo+forex (right)
    left, right = st.columns([2,1])

    with left:
        st.write("### Inflation: India vs USA")
        # Smooth CPI series for visual clarity using Savitzky-Golay if available
        plot_df = pd.DataFrame({
            "date": india_cpi["date"],
            "India_CPI": india_cpi["CPI"].values,
            "USA_CPI": usa_cpi["CPI"].values
        })
        try:
            plot_df["India_smooth"] = savgol_filter(plot_df["India_CPI"], window_length=11, polyorder=2)
            plot_df["USA_smooth"] = savgol_filter(plot_df["USA_CPI"], window_length=11, polyorder=2)
        except Exception:
            plot_df["India_smooth"] = plot_df["India_CPI"]
            plot_df["USA_smooth"] = plot_df["USA_CPI"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plot_df["date"], y=plot_df["India_CPI"], mode='lines', name='India CPI', opacity=0.35))
        fig.add_trace(go.Scatter(x=plot_df["date"], y=plot_df["India_smooth"], mode='lines', name='India CPI (smooth)'))
        fig.add_trace(go.Scatter(x=plot_df["date"], y=plot_df["USA_CPI"], mode='lines', name='USA CPI', opacity=0.35))
        fig.add_trace(go.Scatter(x=plot_df["date"], y=plot_df["USA_smooth"], mode='lines', name='USA CPI (smooth)'))
        fig.update_layout(height=420, legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        st.write("### UPI Activity (Recent)")
        st.plotly_chart(px.area(upi_df, x="date", y=["Txn_Count_mn", "Txn_Value_bn"], title="UPI Txn Count & Value (simulated)"), use_container_width=True)

    with right:
        st.write("### Policy & Reserves Snapshot")
        st.plotly_chart(px.line(repo_df, x="date", y="repo_rate", title="Repo Rate (monthly)"), use_container_width=True)
        st.plotly_chart(px.line(forex_df, x="date", y="Forex_USD_bn", title="Forex Reserves (USD bn)"), use_container_width=True)

    st.write("---")
    st.write("### Banking — Gross NPA")
    st.plotly_chart(px.bar(bank_df, x="Bank", y="Gross_NPA_pct", text="Gross_NPA_pct", title="Gross NPA by Bank"), use_container_width=True)

# -------------------------------
# Inflation tab
# -------------------------------
elif view == "Inflation":
    st.subheader("Detailed Inflation Analysis")

    st.write("#### India: CPI & Core CPI")
    st.plotly_chart(px.line(india_cpi, x="date", y=["CPI", "Core_CPI"], title="India CPI vs Core CPI"), use_container_width=True)

    st.write("#### USA: CPI & Core CPI")
    st.plotly_chart(px.line(usa_cpi, x="date", y=["CPI", "Core_CPI"], title="USA CPI vs Core CPI"), use_container_width=True)

    # Correlation heatmap between India and USA CPI (lagged correlations)
    st.write("#### Cross-correlation (rolling)")
    merged = india_cpi.set_index("date").join(usa_cpi.set_index("date"), lsuffix="_ind", rsuffix="_usa", how="inner")
    merged = merged.dropna()
    merged["ratio"] = merged["CPI_ind"] / merged["CPI_usa"]
    # Compute rolling corr
    merged["rolling_corr"] = merged["CPI_ind"].rolling(12).corr(merged["CPI_usa"])
    st.plotly_chart(px.line(merged.reset_index(), x="date", y="rolling_corr", title="12-month rolling correlation: India vs USA CPI"), use_container_width=True)

# -------------------------------
# Monetary Policy tab
# -------------------------------
elif view == "Monetary Policy":
    st.subheader("Monetary Policy & Yield Curve")

    st.write("### Interactive Yield Curve")
    st.plotly_chart(px.line(yield_df, x="Tenor", y="Yield_pct", markers=True, title="Yield Curve (synthetic)"), use_container_width=True)

    st.write("### Repo vs CPI scatter (Matplotlib static if available)")
    merged = pd.merge_asof(repo_df.sort_values("date"), india_cpi.sort_values("date"), on="date", direction="backward")
    merged = merged.dropna().tail(60)
    if "matplotlib" in IMPORT_ERR:
        st.info("Matplotlib not available — showing an interactive scatter (Plotly)")
        st.plotly_chart(px.scatter(merged, x="repo_rate", y="CPI", trendline="ols", title="Repo Rate vs India CPI (interactive)"), use_container_width=True)
    else:
        fig, ax = plt.subplots(figsize=(6,4))
        ax.scatter(merged["repo_rate"], merged["CPI"], alpha=0.7)
        ax.set_xlabel("Repo Rate (%)")
        ax.set_ylabel("India CPI")
        ax.set_title("Repo Rate vs India CPI (latest 60 months)")
        # trendline
        m, b = np.polyfit(merged["repo_rate"], merged["CPI"], 1)
        ax.plot(merged["repo_rate"], m*merged["repo_rate"] + b, color='red', linewidth=1)
        st.pyplot(fig)

    st.write("### Forex & Gold (Dual axis - Matplotlib if available)")
    if "matplotlib" in IMPORT_ERR:
        st.plotly_chart(px.line(forex_df, x="date", y=["Forex_USD_bn", "Gold_Tonnes"], title="Forex & Gold (interactive)"), use_container_width=True)
    else:
        fig, ax1 = plt.subplots(figsize=(8,3.5))
        ax1.plot(forex_df["date"], forex_df["Forex_USD_bn"], marker='', label="Forex (USD bn)")
        ax1.set_ylabel("Forex (USD bn)")
        ax2 = ax1.twinx()
        ax2.plot(forex_df["date"], forex_df["Gold_Tonnes"], marker='', linestyle='--', label="Gold (Tonnes)")
        ax2.set_ylabel("Gold (Tonnes)")
        ax1.set_title("Forex Reserves & Gold Holdings")
        fig.tight_layout()
        st.pyplot(fig)

# -------------------------------
# Banking tab
# -------------------------------
elif view == "Banking":
    st.subheader("Banking Health & Indicators")
    st.dataframe(bank_df)

    st.write("### Credit Growth by bank")
    st.plotly_chart(px.bar(bank_df, x="Bank", y="Credit_Growth_pct", title="Credit Growth (%)"), use_container_width=True)

    st.write("### Banking Radar (polar) — compare CAR & NPA")
    polar_df = bank_df.melt(id_vars="Bank", value_vars=["Gross_NPA_pct", "CAR_pct"], var_name="metric", value_name="value")
    # we make a radar by grouping per bank; easier - create separate traces
    fig = go.Figure()
    for _, r in bank_df.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[r["Gross_NPA_pct"], r["CAR_pct"]],
            theta=["Gross_NPA_pct", "CAR_pct"],
            name=r["Bank"],
            fill='toself',
            opacity=0.6
        ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True, title="Bank NPA vs CAR (radar slices)")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Risk & Stability tab
# -------------------------------
elif view == "Risk & Stability":
    st.subheader("Risk & Stability — Portfolio VaR + Distribution")

    st.write("### Simulated returns & VaR calculator")
    days = st.slider("Simulated trading days", min_value=60, max_value=252, value=252)
    mu = st.number_input("Mean daily return (decimal)", value=0.0008, step=0.0001, format="%.6f")
    sigma = st.number_input("Std dev daily return", value=0.012, step=0.001, format="%.4f")
    returns = np.random.normal(mu, sigma, days)
    conf = st.selectbox("VaR confidence", [0.95, 0.975, 0.99], index=2)
    var = compute_var(returns, confidence=conf)
    st.metric(f"Portfolio VaR ({int(conf*100)}%)", f"{var}%")

    # distribution plot (plotly)
    fig = px.histogram(returns, nbins=50, marginal="box", title="Simulated return distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.write("### Value-at-Risk by confidence band")
    bands = [0.9, 0.95, 0.975, 0.99]
    vals = [compute_var(returns, confidence=b) for b in bands]
    df_bands = pd.DataFrame({"Confidence": [f"{int(b*100)}%" for b in bands], "VaR_pct": vals})
    st.table(df_bands)

# -------------------------------
# 3D Analytics
# -------------------------------
elif view == "3D Analytics":
    st.subheader("3D CPI Surface & Interactive Exploration")
    n = 40  # keep grid small
    z = np.outer(india_cpi["CPI"].values[:n], usa_cpi["CPI"].values[:n])
    x = india_cpi["date"].dt.strftime("%Y-%m").values[:n]
    y = usa_cpi["date"].dt.strftime("%Y-%m").values[:n]

    fig = go.Figure(data=[go.Surface(z=z, x=list(range(n)), y=list(range(n)), name="CPI Surface")])
    fig.update_layout(title="3D interaction: India CPI × USA CPI (synthetic)", autosize=True, scene=dict(
        xaxis_title="India time idx", yaxis_title="USA time idx", zaxis_title="CPI product"
    ), height=600)
    st.plotly_chart(fig, use_container_width=True)

    st.write("Tip: rotate and zoom the surface to explore interactions.")

# -------------------------------
# Export / Help tab
# -------------------------------
elif view == "Export / Help":
    st.subheader("Export & Deployment Help")

    st.write("You can download the generated CSVs (simulated data) for further analysis:")
    st.download_button("Download India CPI CSV", india_cpi.to_csv(index=False), "india_cpi.csv")
    st.download_button("Download USA CPI CSV", usa_cpi.to_csv(index=False), "usa_cpi.csv")
    st.download_button("Download Banks CSV", bank_df.to_csv(index=False), "banks.csv")
    st.download_button("Download Forex CSV", forex_df.to_csv(index=False), "forex.csv")

    st.write("---")
    st.write("### Local Run Steps (recap)")
    st.code("""pip install streamlit pandas numpy plotly matplotlib scipy
streamlit run RBI_dashboard_pro.py""")

    st.write("### Notes")
    st.write("- This app uses simulated data for demo. Replace generators with real APIs (RBI, FRED) for production.")
    st.write("- If a package is missing, install with pip. On Windows open an Administrator terminal if necessary.")

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
st.caption("Built for demonstration & learning — interactive charts (Plotly) and polished visuals. If you want, I can convert this into a GitHub repo with README + requirements pinned.")
