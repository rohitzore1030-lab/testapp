# streamlit_finance_app.py
# Fixed and hardened Streamlit finance app.
# Key fixes:
# - Ensure returns DataFrame used for covariance is numeric and NaN-safe
# - Validate portfolio weights length vs assets
# - Robust VaR calculation and fallbacks
# - Safer CPI handling (uploads preferred)

import os
from io import StringIO
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Finance Toolkit — Risk-O-Meter & CPI", layout="wide")
st.title("Finance Toolkit — Risk-O-Meter, Inflation, Interest & CPI Viewer")

# SIDEBAR: data uploads
st.sidebar.header("Configuration & Data")
st.sidebar.info("Upload CSVs for CPI or returns. This app prefers uploaded CSVs to avoid external API issues.")

uploaded_us_cpi = st.sidebar.file_uploader("Upload US CPI CSV (optional)", type=["csv"], key="us")
uploaded_in_cpi = st.sidebar.file_uploader("Upload India CPI CSV (optional)", type=["csv"], key="in")

# Helpers
@st.cache_data
def safe_read_csv(f):
    try:
        return pd.read_csv(f)
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return None

def ensure_numeric_dataframe(df):
    """Return a dataframe containing only numeric columns and a datetime index if possible."""
    df = df.copy()
    # If first column looks like a date, set it as index
    if df.shape[1] >= 1:
        # try to parse first column as date
        try:
            df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
            df = df.set_index(df.columns[0])
        except Exception:
            # leave as-is
            pass
    # Convert all columns to numeric where possible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # Drop columns that are all NaN
    df = df.dropna(axis=1, how='all')
    # Drop rows that are all NaN
    df = df.dropna(axis=0, how='all')
    return df

# Utility: compute year-over-year inflation
def compute_yoy(df, value_col='CPI'):
    df = df.copy()
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        df = df.sort_values('date')
    elif df.index.dtype == 'datetime64[ns]':
        df = df.sort_index()
        df = df.reset_index().rename(columns={df.index.name: 'date'})
    else:
        # can't compute yoy without dates
        return df
    df['yoy_%'] = df[value_col].pct_change(periods=12) * 100
    return df

# RISK-O-METER module
def risk_o_meter():
    st.header("Risk-O-Meter — portfolio risk & VaR")
    st.write("Upload daily returns CSV (first column date, other columns numeric asset returns). Or use sample data.")

    uploaded = st.file_uploader("Upload returns CSV (optional)", type=["csv"], key="returns")

    if uploaded is None:
        st.info("No returns uploaded — using simulated returns for a 3-asset portfolio.")
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.today(), periods=252)
        rets = pd.DataFrame(np.random.normal(0, 0.01, size=(252,3)), index=dates, columns=['Asset A','Asset B','Asset C'])
    else:
        raw = safe_read_csv(uploaded)
        if raw is None:
            st.error("Unable to read uploaded file.")
            return
        rets = ensure_numeric_dataframe(raw)

    # At this point, rets should have only numeric columns and possibly a datetime index
    if rets.shape[1] == 0:
        st.error("No numeric columns found in returns data. Ensure your CSV has numeric return columns.")
        return

    # If index is not datetime, attempt to coerce first column to date
    if not np.issubdtype(rets.index.dtype, np.datetime64):
        # try to see if there's a 'date' column
        if 'date' in rets.columns:
            try:
                rets['date'] = pd.to_datetime(rets['date'])
                rets = rets.set_index('date')
            except Exception:
                pass

    # Ensure there are no non-numeric columns left
    rets = rets.select_dtypes(include=[np.number])
    # Drop rows with any NaN (or alternatively fill) — we'll drop rows with NaN across all columns
    rets = rets.dropna(how='all')

    if rets.empty:
        st.error("After cleaning, return series is empty. Check your data.")
        return

    st.subheader("Preview of returns (last 5 rows)")
    st.dataframe(rets.tail())

    # Weights input
    weights_text = st.text_input("Portfolio weights (comma-separated). Leave blank for equal weights.")
    n_assets = rets.shape[1]

    if weights_text:
        try:
            weights = np.array([float(x.strip()) for x in weights_text.split(',')])
        except Exception:
            st.error("Invalid weights format. Use comma-separated numbers, e.g. 0.5,0.3,0.2")
            return
        # If mismatch in length, try to auto-adjust
        if weights.size != n_assets:
            st.warning(f"Provided {weights.size} weights but data has {n_assets} assets. Adjusting to equal weights.")
            weights = np.repeat(1.0/n_assets, n_assets)
    else:
        weights = np.repeat(1.0/n_assets, n_assets)

    # Normalise weights
    if weights.sum() == 0:
        st.error("Sum of weights is zero. Provide non-zero weights.")
        return
    weights = weights / weights.sum()

    # Covariance: use available data; if insufficient, fallback to sample var
    try:
        cov = rets.cov()
        if cov.isnull().values.any():
            cov = cov.fillna(0.0)
        # Annualize
        cov_annual = cov * 252
        # compute portfolio variance
        port_var = float(weights @ cov_annual.values @ weights.T)
        port_vol = np.sqrt(max(port_var, 0.0))
    except Exception as e:
        st.warning(f"Covariance calculation failed: {e}. Using historical returns variance as fallback.")
        port_rets = rets.dot(weights)
        port_vol = np.sqrt(np.nanvar(port_rets) * 252)

    st.metric("Annualized Volatility (std dev)", f"{port_vol:.2%}")

    # Historical VaR
    alpha = st.slider("VaR confidence level (%)", min_value=90, max_value=99, value=95)
    port_returns = rets.dot(weights)
    port_returns = port_returns.dropna()
    if len(port_returns) < 1:
        st.error("Not enough return observations to compute VaR.")
    else:
        try:
            var_historical = -np.percentile(port_returns, 100 - alpha)
            st.metric(f"Historical VaR ({alpha}%) — daily", f"{var_historical:.2%}")
        except Exception as e:
            st.error(f"VaR calculation failed: {e}")

    st.write("**Notes:** Volatility is annualized using 252 trading days. VaR is historical (non-parametric).")

# INFLATION TOOL
def inflation_tool():
    st.header("Inflation Calculator & CPI Viewer")
    st.write("Upload CPI CSVs for US and India (date, CPI). Automatic web fetchers are disabled to avoid runtime errors.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("US CPI")
        us_df = None
        if uploaded_us_cpi is not None:
            us_df = safe_read_csv(uploaded_us_cpi)
            if us_df is not None and us_df.shape[1] >= 2:
                try:
                    us_df.columns = ['date', 'CPI'] + list(us_df.columns[2:])
                except Exception:
                    pass
                try:
                    us_df['date'] = pd.to_datetime(us_df['date'], errors='coerce')
                    us_df['CPI'] = pd.to_numeric(us_df['CPI'], errors='coerce')
                    us_df = us_df.dropna(subset=['date']).reset_index(drop=True)
                    us_df = compute_yoy(us_df, 'CPI')
                    st.dataframe(us_df.tail())
                    st.line_chart(us_df.set_index('date')['CPI'])
                    st.line_chart(us_df.set_index('date')['yoy_%'])
                except Exception as e:
                    st.error(f"Error processing US CPI: {e}")
        else:
            st.info("Upload US CPI CSV in the sidebar to view charts.")

    with col2:
        st.subheader("India CPI")
        in_df = None
        if uploaded_in_cpi is not None:
            in_df = safe_read_csv(uploaded_in_cpi)
            if in_df is not None and in_df.shape[1] >= 2:
                try:
                    in_df.columns = ['date', 'CPI'] + list(in_df.columns[2:])
                except Exception:
                    pass
                try:
                    in_df['date'] = pd.to_datetime(in_df['date'], errors='coerce')
                    in_df['CPI'] = pd.to_numeric(in_df['CPI'], errors='coerce')
                    in_df = in_df.dropna(subset=['date']).reset_index(drop=True)
                    in_df = compute_yoy(in_df, 'CPI')
                    st.dataframe(in_df.tail())
                    st.line_chart(in_df.set_index('date')['CPI'])
                    st.line_chart(in_df.set_index('date')['yoy_%'])
                except Exception as e:
                    st.error(f"Error processing India CPI: {e}")
        else:
            st.info("Upload India CPI CSV in the sidebar to view charts.")

    st.markdown("---")
    st.subheader("Inflation rate calculator")
    cpi1 = st.number_input("Old CPI value", value=100.0)
    cpi2 = st.number_input("New CPI value", value=105.0)
    if st.button("Compute inflation %"):
        try:
            infl = (cpi2 - cpi1) / cpi1 * 100
            st.success(f"Inflation: {infl:.2f}%")
        except Exception as e:
            st.error(f"Error computing inflation: {e}")

# INTEREST RATE CALCULATOR
def interest_rate_calculator():
    st.header("Interest Rate & Loan Calculators")
    st.subheader("EMI / Loan payment calculator")
    principal = st.number_input("Principal (loan amount)", value=100000.0)
    annual_rate = st.number_input("Annual nominal rate (%)", value=7.5)
    years = st.number_input("Term (years)", value=5)
    freq = st.selectbox("Compounding / payments per year", [12, 4, 2, 1], index=0)

    r = float(annual_rate) / 100.0 / float(freq)
    n = int(float(years) * float(freq))
    if n <= 0:
        st.error("Number of payments must be positive")
        return
    if abs(r) < 1e-12:
        emi = principal / n
    else:
        try:
            emi = principal * r * (1+r)**n / ((1+r)**n - 1)
        except Exception as e:
            st.error(f"EMI calculation error: {e}")
            return
    st.metric("Periodic payment (EMI)", f"{emi:.2f}")
    st.write(f"Total payment: {emi*n:.2f}; Total interest: {emi*n - principal:.2f}")

    st.subheader("Real interest rate (Fisher approximation)")
    nominal = st.number_input("Nominal interest rate (%)", value=6.0, key='nominal')
    inflation = st.number_input("Inflation rate (%)", value=2.0, key='infl')
    if st.button("Compute real rate"):
        try:
            real = (1 + nominal/100) / (1 + inflation/100) - 1
            st.success(f"Real interest rate: {real*100:.2f}%")
        except Exception as e:
            st.error(f"Error computing real rate: {e}")

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
    venv\Scripts\activate   # windows
    pip install streamlit pandas numpy
    streamlit run streamlit_finance_app.py
    """)
    st.markdown("### Notes & troubleshooting")
    st.markdown("- Upload clean CSVs for CPI and returns (first column date, second column CPI or subsequent numeric columns for returns).
- If you see errors, open the logs in Streamlit Cloud or run locally to inspect tracebacks.")
