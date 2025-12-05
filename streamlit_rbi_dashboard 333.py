"""
Streamlit RBI & Macro Dashboard
Features:
- Live RBI API data (attempts)
- Live World Bank CPI (attempts)
- Recession Probability Meter (heuristic)
- Stock Market Stress Index (using yfinance)
- Simple AI-like Inflation Forecasting (exponential smoothing)
- RBI Policy Decision Simulator (interactive)
- Login System (Admin / Viewer)
- PDF Auto-Report Generator (FPDF)

Run:
    pip install -r requirements.txt
    streamlit run streamlit_rbi_dashboard.py

Notes:
- This file is written to be robust: all external calls have try/except and fallback generated sample data so the app runs without API keys.
- To improve live quality, set environment variables or edit the constants for API keys / preferred tickers.

Author: Generated for resume project (example)
"""

import os
import io
import hashlib
import base64
from datetime import datetime, timedelta
import math

import pandas as pd
import numpy as np
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Optional libraries; used if available
try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from fpdf import FPDF
except Exception:
    FPDF = None

# -------------------------
# Configuration / Constants
# -------------------------
REPO_PASSWORD_HASH = hashlib.sha256(b"admin123").hexdigest()  # default admin password: admin123
VIEWER_PASSWORD_HASH = hashlib.sha256(b"viewer").hexdigest()  # default viewer password: viewer

RBI_API_URL = "https://api.rbi.org.in/content/"  # placeholder (RBI does not offer a single public JSON API in many cases)
WORLD_BANK_CPI_URL = "http://api.worldbank.org/v2/country/{}/indicator/FP.CPI.TOTL?date={}-{}&format=json"

DEFAULT_TICKERS = {
    "India_NSEI": "^NSEI",  # may or may not work depending on yfinance
    "US_S&P500": "^GSPC",
}

# -------------------------
# Utilities
# -------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(password: str, role: str = "admin") -> bool:
    h = hash_password(password)
    if role == "admin":
        return h == REPO_PASSWORD_HASH
    else:
        return h == VIEWER_PASSWORD_HASH


def set_passwords(admin_pwd: str = None, viewer_pwd: str = None):
    """Set passwords at runtime (for demo). In production, use env vars or a secret manager."""
    global REPO_PASSWORD_HASH, VIEWER_PASSWORD_HASH
    if admin_pwd:
        REPO_PASSWORD_HASH = hash_password(admin_pwd)
    if viewer_pwd:
        VIEWER_PASSWORD_HASH = hash_password(viewer_pwd)


# -------------------------
# Data fetching (robust)
# -------------------------

def fetch_rbi_rate_history(years: int = 10) -> pd.DataFrame:
    """Attempt to fetch RBI policy repo rate history. If fails, return generated sample data."""
    try:
        # NOTE: this is placeholder; replace with a real RBI endpoint if available
        # Simulate a real call to an API
        # resp = requests.get(RBI_API_URL + "repo-rate-history")
        # data = resp.json()
        raise Exception("No reliable public RBI JSON endpoint configured - using sample data")
    except Exception:
        # generate sample monthly repo rate for last 'years' years
        idx = pd.date_range(end=pd.Timestamp.today(), periods=years * 12, freq="M")
        base = 6.5
        # make some swings
        rates = base + np.sin(np.linspace(0, 4 * np.pi, len(idx))) * 1.5 + np.random.normal(0, 0.2, len(idx))
        df = pd.DataFrame({"date": idx, "repo_rate": np.round(rates, 2)})
        return df


def fetch_world_bank_cpi(country_code: str = "IND", start_year: int = 2015, end_year: int = 2024) -> pd.DataFrame:
    """Fetch CPI series from World Bank API. If fails, fallback to generated data."""
    try:
        url = WORLD_BANK_CPI_URL.format(country_code.lower(), start_year, end_year)
        r = requests.get(url, timeout=10)
        j = r.json()
        if not isinstance(j, list) or len(j) < 2:
            raise Exception("Unexpected World Bank response")
        values = j[1]
        records = []
        for entry in values:
            year = int(entry.get("date"))
            val = entry.get("value")
            records.append({"year": year, "cpi": None if val is None else float(val)})
        df = pd.DataFrame(records).sort_values("year")
        if df['cpi'].isna().all():
            raise Exception("Empty CPI data")
        return df
    except Exception:
        # fallback: create a plausible CPI index
        years = list(range(start_year, end_year + 1))
        base = 100
        cpis = [base]
        for _ in years[1:]:
            growth = np.random.normal(0.04, 0.02)  # ~4% average inflation
            cpis.append(cpis[-1] * (1 + growth))
        df = pd.DataFrame({"year": years, "cpi": np.round(cpis, 2)})
        return df


def fetch_market_prices(ticker: str, period: str = "3y") -> pd.DataFrame:
    """Fetch historical prices using yfinance if available. Fallback to simulated prices."""
    try:
        if yf is None:
            raise Exception("yfinance not available")
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            raise Exception("Empty price series")
        df = df.reset_index()[["Date", "Close"]].rename(columns={"Date": "date", "Close": "close"})
        return df
    except Exception:
        # simulate price series
        idx = pd.date_range(end=pd.Timestamp.today(), periods=365 * 3, freq="D")
        price = np.cumprod(1 + np.random.normal(0.0003, 0.02, len(idx))) * 1000
        df = pd.DataFrame({"date": idx, "close": price})
        return df


# -------------------------
# Analytics / Models
# -------------------------

def recession_probability_metric(repo_df: pd.DataFrame, yield_spread: float = None) -> float:
    """Heuristic recession probability (0-100). Based on repo rate trend and optional yield spread.
    Lower repo + inverted yield spread => higher probability. This is a heuristic for demo only.
    """
    try:
        repo_recent = repo_df.set_index('date').repo_rate
        short_mean = repo_recent.last('12M').mean()
        long_mean = repo_recent.last('60M').mean() if len(repo_recent) > 60 else repo_recent.mean()
        spread_indicator = (short_mean - long_mean)
        # normalize
        prob = 50 - spread_indicator * 10
        if yield_spread is not None:
            prob += -yield_spread * 5  # if positive spread reduces recession probability
        prob = max(0, min(100, prob + np.random.normal(0, 5)))
        return round(prob, 1)
    except Exception:
        return 20.0


def stock_market_stress_index(price_df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """Compute a Stress Index: rolling volatility + drawdown metric normalized 0-100"""
    df = price_df.copy().sort_values('date')
    df['return'] = df['close'].pct_change()
    df['vol'] = df['return'].rolling(window).std() * math.sqrt(252)
    # drawdown
    df['cummax'] = df['close'].cummax()
    df['drawdown'] = (df['close'] - df['cummax']) / df['cummax']
    # stress score
    v = df['vol'].fillna(0)
    d = df['drawdown'].fillna(0).abs()
    # normalize by percentile
    df['stress'] = (v.rank(pct=True) * 0.6 + d.rank(pct=True) * 0.4) * 100
    df['stress'] = df['stress'].fillna(0)
    return df


def simple_inflation_forecast(cpi_series: pd.Series, steps: int = 12, alpha: float = 0.3) -> pd.Series:
    """Simple exponential smoothing forecast (SES) for CPI index values."""
    series = cpi_series.dropna().astype(float).values
    if len(series) == 0:
        return pd.Series([None] * steps)
    level = series[0]
    for point in series[1:]:
        level = alpha * point + (1 - alpha) * level
    forecasts = []
    for _ in range(steps):
        # SES forecast is the last level
        forecasts.append(level)
        # optionally decay level slightly to mimic mean reversion
        level = level * (1 + (0.000))
    next_idx = pd.date_range(start=pd.Timestamp.today(), periods=steps, freq='M')
    return pd.Series(data=np.round(forecasts, 2), index=next_idx)


# -------------------------
# PDF Report
# -------------------------

def generate_pdf_report(title: str, sections: dict) -> bytes:
    """Generates a simple PDF with sections. Returns bytes. Uses FPDF if available, otherwise plain-text PDF via minimal fallback."""
    if FPDF is None:
        # simple text PDF fallback: create a very simple PDF by writing text to a file-like object
        content = title + "\n\n"
        for k, v in sections.items():
            content += f"== {k} ==\n{v}\n\n"
        return content.encode('utf-8')
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", size=12)
    for k, v in sections.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 8, f"{k}")
        pdf.set_font("Arial", size=11)
        # make sure v is a string
        if not isinstance(v, str):
            v = str(v)
        pdf.multi_cell(0, 7, v)
        pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')


# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(page_title="RBI Macro Dashboard", layout="wide")

# --- Authentication ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['role'] = None

with st.sidebar:
    st.title("Login")
    role = st.selectbox("Role", ['viewer', 'admin'])
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        ok = authenticate(pwd, role=role)
        if ok:
            st.session_state['authenticated'] = True
            st.session_state['role'] = role
            st.success(f"Logged in as {role}")
        else:
            st.error("Invalid password")

    st.markdown("---")
    st.write("**Demo credentials**:\n admin / admin123  \n viewer / viewer")
    st.markdown("---")
    if st.session_state['authenticated'] and st.session_state['role'] == 'admin':
        st.write("Admin controls")
        new_admin = st.text_input("Set new admin password (leave blank to keep)", type="password")
        new_viewer = st.text_input("Set new viewer password (leave blank to keep)", type="password")
        if st.button("Update passwords"):
            set_passwords(admin_pwd=new_admin or None, viewer_pwd=new_viewer or None)
            st.success("Passwords updated (in-memory)")

# If not authenticated show limited view
if not st.session_state['authenticated']:
    st.header("RBI Macro Dashboard (Public Preview)")
    st.info("Please login from the left to access simulator and admin features. The app will still show demo data.")

# Main layout
st.title("RBI Macro & Markets Dashboard")
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Key Live Metrics")
    repo_df = fetch_rbi_rate_history(years=10)
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest Repo Rate", f"{repo_df['repo_rate'].iloc[-1]}%")
    # CPI: show India and US
    cpi_ind = fetch_world_bank_cpi('IND', 2015, 2024)
    cpi_usa = fetch_world_bank_cpi('USA', 2015, 2024)
    c2.metric("India CPI (latest)", f"{round(cpi_ind['cpi'].iloc[-1],2)}")
    c3.metric("US CPI (latest)", f"{round(cpi_usa['cpi'].iloc[-1],2)}")

    st.markdown("---")
    st.subheader("Repo Rate Trend")
    fig_repo = px.line(repo_df, x='date', y='repo_rate', title='Repo Rate Trend (monthly)')
    st.plotly_chart(fig_repo, use_container_width=True)

    st.subheader("CPI Comparison (2015-2024)")
    merged = pd.DataFrame({
        'year': cpi_ind['year'],
        'India_CPI': cpi_ind['cpi'].values,
        'USA_CPI': cpi_usa['cpi'].values[:len(cpi_ind)]
    })
    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Scatter(x=merged['year'], y=merged['India_CPI'], mode='lines+markers', name='India CPI'))
    fig_cpi.add_trace(go.Scatter(x=merged['year'], y=merged['USA_CPI'], mode='lines+markers', name='US CPI'))
    fig_cpi.update_layout(title='CPI Indices (World Bank / Sample)')
    st.plotly_chart(fig_cpi, use_container_width=True)

    st.subheader("AI Inflation Forecasting (Simple SES)")
    # Use India CPI as index series
    ses_forecast = simple_inflation_forecast(pd.Series(cpi_ind['cpi'].values), steps=12, alpha=0.25)
    fig_fore = go.Figure()
    fig_fore.add_trace(go.Scatter(x=cpi_ind['year'], y=cpi_ind['cpi'], mode='lines+markers', name='Historical CPI'))
    fig_fore.add_trace(go.Scatter(x=ses_forecast.index, y=ses_forecast.values, mode='lines+markers', name='SES Forecast'))
    fig_fore.update_layout(title='Inflation Forecast (SES)')
    st.plotly_chart(fig_fore, use_container_width=True)

    st.markdown("---")
    st.subheader("Stock Market Stress Index")
    ticker = st.selectbox("Choose market ticker (demo)", list(DEFAULT_TICKERS.values()))
    price_df = fetch_market_prices(ticker)
    stress_df = stock_market_stress_index(price_df)
    latest_stress = stress_df['stress'].iloc[-1]
    st.metric("Current Market Stress Index", f"{round(latest_stress,1)} / 100")
    fig_stress = go.Figure()
    fig_stress.add_trace(go.Scatter(x=stress_df['date'], y=stress_df['stress'], mode='lines', name='Stress'))
    fig_stress.update_layout(title=f"Market Stress Index - {ticker}")
    st.plotly_chart(fig_stress, use_container_width=True)

with col2:
    st.subheader("Recession Probability Meter")
    # crude yield spread input
    yield_spread = st.slider("10y - 2y yield spread (%) (user input)", -3.0, 5.0, 1.0, step=0.1)
    recession_prob = recession_probability_metric(repo_df, yield_spread=yield_spread)
    st.metric("Recession Probability", f"{recession_prob}%")
    st.progress(int(recession_prob))

    st.markdown("---")
    st.subheader("RBI Policy Decision Simulator")
    sim_rate = st.number_input("Set hypothetical repo rate (%)", value=float(repo_df['repo_rate'].iloc[-1]), step=0.25)
    sim_recession = recession_probability_metric(repo_df.assign(repo_rate=repo_df['repo_rate'].where(repo_df.index < repo_df.index.max(), sim_rate)), yield_spread=yield_spread)
    st.write(f"Predicted recession probability if RBI sets repo = {sim_rate}%: **{sim_recession}%**")

    st.markdown("---")
    st.subheader("PDF Auto-Report Generator")
    report_title = st.text_input("Report title", value=f"Macro Report - {datetime.today().date()}")
    if st.button("Generate PDF Report"):
        sections = {
            "Repo rate summary": f"Latest repo rate: {repo_df['repo_rate'].iloc[-1]}\nMean (12M): {round(repo_df.last('12M')['repo_rate'].mean(),2)}",
            "CPI Overview": f"India CPI latest: {round(cpi_ind['cpi'].iloc[-1],2)}\nUS CPI latest: {round(cpi_usa['cpi'].iloc[-1],2)}",
            "Market Stress": f"Ticker: {ticker}\nStress index: {round(latest_stress,2)}",
            "Recession Probability": f"Input yield spread: {yield_spread} -> probability: {recession_prob}%"
        }
        pdf_bytes = generate_pdf_report(report_title, sections)
        b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        href = f"data:application/octet-stream;base64,{b64}"
        st.markdown(f"[Download report]({href})")

# --- Advanced / Admin panels ---
if st.session_state.get('authenticated') and st.session_state.get('role') == 'admin':
    st.markdown("---")
    st.header("Admin Panel")
    with st.expander("Live API Test & Logs"):
        st.write("RBI API URL (used as placeholder):", RBI_API_URL)
        st.write("World Bank CPI URL template:", WORLD_BANK_CPI_URL)
        st.write("yfinance available:", yf is not None)

    st.write("Manual data refresh")
    if st.button("Refresh all data"):
        st.experimental_rerun()

st.markdown("---")
st.caption("This dashboard is a demo-ready template. Replace placeholder endpoints with production APIs and secure authentication for deployment.")

# Footer - Requirements
st.markdown("**Requirements**: streamlit, pandas, numpy, plotly, requests, yfinance (optional), fpdf (optional)\nInstall: `pip install streamlit pandas numpy plotly requests yfinance fpdf`")
