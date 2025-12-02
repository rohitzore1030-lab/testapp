# streamlit_finance_app.py
# All-in-one Streamlit finance app: Risk-O-Meter, Inflation tools, Interest Rate calculators,
# and CPI data viewer (India & USA).
# Note: Some CPI data sources require API keys (e.g., FRED). There are fallbacks to CSV upload.

import os
from io import StringIO
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except Exception:
    FRED_AVAILABLE = False

st.set_page_config(page_title="Finance Toolkit — Risk-O-Meter & CPI", layout="wide")

st.title("Finance Toolkit — Risk-O-Meter, Inflation, Interest & CPI Viewer")

# SIDEBAR: keys and data uploads
st.sidebar.header("Configuration & Data")
st.sidebar.info("Provide keys if you want automatic CPI downloads; otherwise upload CSVs.")

fred_api_key = st.sidebar.text_input("FRED API Key (optional, for US CPI)")

uploaded_us_cpi = st.sidebar.file_uploader("Upload US CPI CSV (optional)", type=["csv"] , key="us")
uploaded_in_cpi = st.sidebar.file_uploader("Upload India CPI CSV (optional)", type=["csv"], key="in")

st.sidebar.markdown("---")
st.sidebar.write("Packages used: pandas, numpy, streamlit. Optional: fredapi for FRED access.")

# Helper utilities
@st.cache_data
def safe_parse_csv(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.sidebar.error(f"CSV parse error: {e}")
        return None

# CPI fetchers (best-effort):
@st.cache_data
def fetch_us_cpi_from_fred(api_key, start=None, end=None):
    """Fetch CPIAUCSL from FRED using fredapi if available and key provided."""
    if not api_key:
        raise ValueError("FRED API key not provided")
    if not FRED_AVAILABLE:
        raise ImportError("fredapi package not installed. Install via `pip install fredapi`")
    fred = Fred(api_key=api_key)
    series = fred.get_series("CPIAUCSL", start_date=start, end_date=end)
    df = series.rename("CPI").reset_index()
    df.columns = ["date", "CPI"]
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data
def try_fetch_india_cpi_esankhyiki(start=None, end=None):
    """Best-effort attempt to fetch India CPI from MoSPI eSankhyiki portal.
    If this fails, user should upload CSV manually.
    This function attempts common endpoints and returns None on failure.
    """
    import requests
    # eSankhyiki provides CSV downloads on its portal. We'll try a known overview page and search for a CSV link.
    try:
        base = "https://esankhyiki.mospi.gov.in"
        page = base + "/macroindicators?product=cpi"
        r = requests.get(page, timeout=10)
        r.raise_for_status()
        text = r.text
        # naive search for .csv link
        import re
        m = re.search(r"(https?:\\/\\/[^\"]+\\.csv)", text)
        if m:
            csv_url = m.group(1).replace('\\/', '/')
            r2 = requests.get(csv_url, timeout=15)
            r2.raise_for_status()
            df = pd.read_csv(StringIO(r2.text))
            # try to ensure a date column
            for col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    df = df.rename(columns={col: 'date'})
                    break
                except Exception:
                    continue
            return df
    except Exception:
        return None
    return None

# Utility: compute year-over-year inflation
def compute_yoy(df, value_col='CPI'):
    df = df.copy()
    df = df.sort_values('date')
    df['yoy_%'] = df[value_col].pct_change(periods=12) * 100
    return df

# RISK-O-METER module
def risk_o_meter():
    st.header("Risk-O-Meter — portfolio risk & VaR")
    st.write("Upload daily returns CSV (column: date, columns for asset returns) or generate sample returns.")
    uploaded = st.file_uploader("Upload returns CSV (optional)", type=["csv"], key="returns")
    if uploaded is None:
        st.info("No returns uploaded — using simulated returns for a 3-asset portfolio.")
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.today(), periods=252)
        rets = pd.DataFrame(np.random.normal(0, 0.01, size=(252,3)), index=dates, columns=['Asset A','Asset B','Asset C'])
    else:
        rets = pd.read_csv(uploaded, parse_dates=[0], index_col=0)
    st.subheader("Preview of returns")
    st.dataframe(rets.tail())

    weights_text = st.text_input("Portfolio weights (comma-separated, sum to 1)", value="0.4,0.3,0.3")
    try:
        weights = np.array([float(x.strip()) for x in weights_text.split(',')])
    except Exception:
        st.error("Invalid weights format")
        return
    if abs(weights.sum() - 1.0) > 1e-6:
        st.warning("Weights do not sum to 1. They will be normalized.")
        weights = weights / weights.sum()

    cov = rets.cov() * 252
    port_var = weights @ cov.values @ weights.T
    port_vol = np.sqrt(port_var)
    st.metric("Annualized Volatility (std dev)", f"{port_vol:.2%}")

    # Historical VaR
    alpha = st.slider("VaR confidence level (%)", min_value=90, max_value=99, value=95)
    port_returns = rets.dot(weights)
    var_historical = -np.percentile(port_returns, 100-alpha)
    st.metric(f"Historical VaR ({alpha}%) — daily", f"{var_historical:.2%}")

    st.write("**Notes:** Volatility is annualized (252 trading days). VaR is estimated using historical simulation on provided or simulated returns.")

# INFLATION TOOL
def inflation_tool():
    st.header("Inflation Calculator & CPI Viewer")
    st.write("You can load CPI data (upload CSV) or try automatic fetch (US via FRED key; India via MoSPI best-effort). Otherwise upload CSVs.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("US CPI")
        us_df = None
        if uploaded_us_cpi is not None:
            us_df = safe_parse_csv(uploaded_us_cpi)
            st.success("Loaded US CPI from uploaded CSV")
        else:
            if fred_api_key:
                try:
                    us_df = fetch_us_cpi_from_fred(fred_api_key)
                    st.success("Fetched US CPI from FRED (CPIAUCSL)")
                except Exception as e:
                    st.warning(f"US CPI fetch failed: {e}. Please upload CSV as fallback.")
        if us_df is not None:
            st.dataframe(us_df.tail())
            us_df = us_df.rename(columns={us_df.columns[0]:'date', us_df.columns[1]:'CPI'}) if 'date' not in us_df.columns else us_df
            us_df['date'] = pd.to_datetime(us_df['date'])
            us_df = compute_yoy(us_df, 'CPI')
            st.line_chart(us_df.set_index('date')['CPI'])
            st.line_chart(us_df.set_index('date')['yoy_%'])

    with col2:
        st.subheader("India CPI")
        in_df = None
        if uploaded_in_cpi is not None:
            in_df = safe_parse_csv(uploaded_in_cpi)
            st.success("Loaded India CPI from uploaded CSV")
        else:
            in_df = try_fetch_india_cpi_esankhyiki()
            if in_df is not None:
                st.success("Fetched India CPI from MoSPI eSankhyiki (best-effort)")
            else:
                st.info("India CPI automatic fetch failed — please upload CSV as fallback.")
        if in_df is not None:
            st.dataframe(in_df.tail())
            # try to standardize
            if 'CPI' not in in_df.columns:
                # try to find numeric column
                numeric_cols = in_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    in_df = in_df.rename(columns={numeric_cols[0]:'CPI'})
            if 'date' in in_df.columns:
                in_df['date'] = pd.to_datetime(in_df['date'])
                in_df = compute_yoy(in_df, 'CPI')
                st.line_chart(in_df.set_index('date')['CPI'])
                st.line_chart(in_df.set_index('date')['yoy_%'])

    st.markdown("---")
    st.subheader("Inflation rate calculator")
    cpi1 = st.number_input("Old CPI value", value=100.0)
    cpi2 = st.number_input("New CPI value", value=105.0)
    if st.button("Compute inflation %"):
        infl = (cpi2 - cpi1) / cpi1 * 100
        st.success(f"Inflation: {infl:.2f}%")

# INTEREST RATE CALCULATOR
def interest_rate_calculator():
    st.header("Interest Rate & Loan Calculators")
    st.subheader("EMI / Loan payment calculator")
    principal = st.number_input("Principal (loan amount)", value=100000.0)
    annual_rate = st.number_input("Annual nominal rate (%)", value=7.5)
    years = st.number_input("Term (years)", value=5)
    freq = st.selectbox("Compounding / payments per year", [12, 4, 2, 1], index=0)

    r = annual_rate / 100.0 / freq
    n = int(years * freq)
    if r == 0:
        emi = principal / n
    else:
        emi = principal * r * (1+r)**n / ((1+r)**n - 1)
    st.metric("Periodic payment (EMI)", f"{emi:.2f}")
    st.write(f"Total payment: {emi*n:.2f}; Total interest: {emi*n - principal:.2f}")

    st.subheader("Real interest rate (Fisher approximation)")
    nominal = st.number_input("Nominal interest rate (%)", value=6.0, key='nominal')
    inflation = st.number_input("Inflation rate (%)", value=2.0, key='infl')
    if st.button("Compute real rate"):
        real = (1 + nominal/100) / (1 + inflation/100) - 1
        st.success(f"Real interest rate: {real*100:.2f}%")

# MAIN app layout using tabs
tabs = st.tabs(["Risk-O-Meter", "Inflation & CPI", "Interest Rate Tools", "About & GitHub"])
with tabs[0]:
    risk_o_meter()
with tabs[1]:
    inflation_tool()
with tabs[2]:
    interest_rate_calculator()
with tabs[3]:
    st.header("About this app & GitHub")
    st.markdown("This Streamlit app bundles several finance utilities: a simple Risk-O-Meter (portfolio VaR & vol), inflation calculators (using CPI), and interest/loan calculators.")
    st.markdown("### How to run locally")
    st.code("""
    # create venv
    python -m venv venv
    source venv/bin/activate  # mac / linux
    venv\\Scripts\\activate   # windows
    pip install streamlit pandas numpy fredapi
    streamlit run streamlit_finance_app.py
    """)
    st.markdown("### Pushing to GitHub")
    st.markdown("1. Create repo on GitHub.\n2. git init; git add .; git commit -m 'initial'; git remote add origin <URL>; git push -u origin main")
    st.markdown("### Notes & troubleshooting")
    st.markdown("- Automatic US CPI fetch uses FRED (requires API key). If you don't have a key, upload a CSV with date and CPI columns.\n- India CPI automatic fetch is a best-effort grab from MoSPI eSankhyiki; if it fails, upload CSV.\n- If you see errors about fredapi, install it or leave the FRED API key blank and upload CSV instead.")

# End of file
