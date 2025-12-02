# streamlit_finance_app.py
# Final polished, minimal-dependency Streamlit app that runs and displays reliably.
# Features:
# - Risk-O-Meter (portfolio volatility, historical & parametric VaR)
# - Inflation & CPI viewer (CSV upload or sample data)
# - Interest / EMI calculator
# - Sample CSVs available for download so you can test immediately

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Finance Toolkit", layout="wide")
st.title("Finance Toolkit — Risk-O-Meter, Inflation & Interest")

# ------------------ Utilities ------------------
@st.cache_data
def generate_sample_returns():
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B')
    rets = pd.DataFrame(np.random.normal(0, 0.01, size=(len(dates), 3)),
                        index=dates, columns=['Asset A', 'Asset B', 'Asset C'])
    rets = rets.reset_index().rename(columns={'index': 'date'})
    return rets

@st.cache_data
def generate_sample_cpi(country='US'):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='M')
    base = 260 if country=='US' else 150
    cpi = base * (1 + np.linspace(0, 0.03, len(dates))).cumsum() / len(dates)
    df = pd.DataFrame({'date': dates, 'CPI': np.round(cpi, 2)})
    return df

# safe csv loader
@st.cache_data
def safe_read_csv(file) -> pd.DataFrame:
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"CSV read error: {e}")
        return pd.DataFrame()

# Ensure numeric returns and datetime index
def clean_returns_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # if first column is date-like, convert and set as index
    if df.shape[1] >= 1:
        try:
            df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
            df = df.set_index(df.columns[0])
        except Exception:
            pass
    # convert all columns to numeric where possible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # drop columns with all NaN
    df = df.dropna(axis=1, how='all')
    # drop rows with all NaN
    df = df.dropna(axis=0, how='all')
    return df

# ------------------ RISK-O-METER ------------------
def risk_o_meter_ui():
    st.header("Risk-O-Meter")
    st.write("Upload daily returns CSV (first column = date, other columns = returns). Or use the sample data below.")

    col1, col2 = st.columns([2,1])

    with col1:
        uploaded = st.file_uploader("Returns CSV", type=['csv'], key='returns_upload')
        if uploaded is not None:
            raw = safe_read_csv(uploaded)
            if raw.empty:
                st.info("Uploaded file could not be read or is empty.")
                return
            rets = clean_returns_df(raw)
        else:
            st.info("Using generated sample returns (3 assets, 252 business days)")
            rets = generate_sample_returns()
            rets = clean_returns_df(rets)

        if rets.empty:
            st.error("No usable numeric return columns found. Ensure CSV has date + numeric returns.")
            return

        st.subheader("Returns preview")
        st.dataframe(rets.tail())

    with col2:
        st.subheader("Options")
        weights_text = st.text_input("Portfolio weights (comma-separated). Leave blank for equal weights.")
        alpha = st.slider("VaR confidence (%)", 90, 99, 95)
        show_parametric = st.checkbox("Show parametric (Gaussian) VaR", value=True)

    # prepare weights
    n = rets.shape[1]
    if weights_text:
        try:
            w = np.array([float(x.strip()) for x in weights_text.split(',')])
            if w.size != n:
                st.warning(f"Weights length {w.size} != number of assets {n}. Using equal weights.")
                w = np.repeat(1.0/n, n)
        except Exception:
            st.warning("Invalid weight format. Using equal weights.")
            w = np.repeat(1.0/n, n)
    else:
        w = np.repeat(1.0/n, n)
    w = w / w.sum()

    # compute covariance (annualized) and portfolio vol
    try:
        cov_daily = rets.cov()
        cov_daily = cov_daily.fillna(0.0)
        cov_annual = cov_daily * 252
        port_var = float(w @ cov_annual.values @ w.T)
        port_vol = np.sqrt(max(port_var, 0.0))
        st.metric("Annualized Volatility", f"{port_vol:.2%}")
    except Exception as e:
        st.error(f"Covariance calculation error: {e}")
        return

    # Historical VaR
    port_returns = (rets * w).sum(axis=1)
    port_returns = port_returns.dropna()
    if len(port_returns) < 5:
        st.warning("Not enough return observations to compute VaR reliably.")
    else:
        hist_var = -np.percentile(port_returns, 100 - alpha)
        st.metric(f"Historical VaR ({alpha}%) - daily", f"{hist_var:.2%}")

        if show_parametric:
            mu = port_returns.mean()
            sigma = port_returns.std()
            from scipy.stats import norm
            z = norm.ppf(1 - alpha/100)
            # parametric VaR (loss) = -(mu + z*sigma)
            param_var = -(mu + z * sigma)
            st.metric(f"Parametric VaR ({alpha}%) - daily", f"{param_var:.2%}")

    st.markdown("---")
    st.write("Notes: Volatility annualized using 252 trading days. VaR reported as daily loss amount (positive = loss).")

    # Download sample returns CSV
    sample_rets = generate_sample_returns()
    csv = sample_rets.to_csv(index=False)
    st.download_button("Download sample returns CSV", csv, "sample_returns.csv", "text/csv")

# ------------------ INFLATION & CPI ------------------
def inflation_ui():
    st.header("Inflation & CPI Viewer")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("US CPI")
        us_file = st.file_uploader("Upload US CPI CSV (date, CPI)", type=['csv'], key='us_cpi')
        if us_file is not None:
            df = safe_read_csv(us_file)
            if not df.empty:
                # standardize
                try:
                    df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
                    df.iloc[:,1] = pd.to_numeric(df.iloc[:,1], errors='coerce')
                    df = df.dropna(subset=[df.columns[0], df.columns[1]])
                    df = df.rename(columns={df.columns[0]:'date', df.columns[1]:'CPI'})
                    df = df.sort_values('date')
                    df['yoy_%'] = df['CPI'].pct_change(periods=12) * 100
                    st.dataframe(df.tail())
                    st.line_chart(df.set_index('date')['CPI'])
                    st.line_chart(df.set_index('date')['yoy_%'])
                except Exception as e:
                    st.error(f"Error processing US CPI: {e}")
        else:
            st.info("No US CPI uploaded — using sample data")
            sample = generate_sample_cpi('US')
            st.dataframe(sample.tail())
            st.line_chart(sample.set_index('date')['CPI'])

    with col2:
        st.subheader("India CPI")
        in_file = st.file_uploader("Upload India CPI CSV (date, CPI)", type=['csv'], key='in_cpi')
        if in_file is not None:
            df = safe_read_csv(in_file)
            if not df.empty:
                try:
                    df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
                    df.iloc[:,1] = pd.to_numeric(df.iloc[:,1], errors='coerce')
                    df = df.dropna(subset=[df.columns[0], df.columns[1]])
                    df = df.rename(columns={df.columns[0]:'date', df.columns[1]:'CPI'})
                    df = df.sort_values('date')
                    df['yoy_%'] = df['CPI'].pct_change(periods=12) * 100
                    st.dataframe(df.tail())
                    st.line_chart(df.set_index('date')['CPI'])
                    st.line_chart(df.set_index('date')['yoy_%'])
                except Exception as e:
                    st.error(f"Error processing India CPI: {e}")
        else:
            st.info("No India CPI uploaded — using sample data")
            sample = generate_sample_cpi('IN')
            st.dataframe(sample.tail())
            st.line_chart(sample.set_index('date')['CPI'])

    # sample CPI downloads
    st.download_button("Download sample US CPI CSV", generate_sample_cpi('US').to_csv(index=False), "sample_us_cpi.csv", "text/csv")
    st.download_button("Download sample India CPI CSV", generate_sample_cpi('IN').to_csv(index=False), "sample_in_cpi.csv", "text/csv")

    st.markdown("---")
    st.subheader("Simple inflation calculator")
    old = st.number_input("Old CPI", value=100.0)
    new = st.number_input("New CPI", value=105.0)
    if st.button("Compute inflation"):
        try:
            inf = (new - old) / old * 100
            st.success(f"Inflation = {inf:.2f}%")
        except Exception as e:
            st.error(f"Error: {e}")

# ------------------ INTEREST & EMI ------------------
def interest_ui():
    st.header("Interest & EMI Calculator")
    P = st.number_input("Principal (loan amount)", value=100000.0)
    annual = st.number_input("Annual interest rate (%)", value=7.5)
    years = st.number_input("Term (years)", value=5)
    freq = st.selectbox("Payments per year", [12,4,2,1])

    r = annual/100.0/freq
    n = int(years * freq)
    if n <= 0:
        st.error("Term must be positive")
        return
    if abs(r) < 1e-12:
        emi = P / n
    else:
        emi = P * r * (1+r)**n / ((1+r)**n - 1)
    st.metric("Payment per period", f"{emi:.2f}")
    st.write(f"Total payment = {emi*n:.2f}; Total interest = {emi*n - P:.2f}")

    st.markdown("---")
    st.subheader("Real interest rate (Fisher formula)")
    nom = st.number_input("Nominal rate (%)", value=7.0)
    infl = st.number_input("Inflation rate (%)", value=4.0)
    if st.button("Compute real rate"):
        real = (1 + nom/100) / (1 + infl/100) - 1
        st.success(f"Real interest rate = {real*100:.2f}%")

# ------------------ APP LAYOUT ------------------
tabs = st.tabs(["Risk-O-Meter", "Inflation & CPI", "Interest & EMI", "About / GitHub"])
with tabs[0]:
    risk_o_meter_ui()
with tabs[1]:
    inflation_ui()
with tabs[2]:
    interest_ui()
with tabs[3]:
    st.header("About / GitHub")
    st.write("This single-file Streamlit app includes risk, inflation and interest tools.\n\nTo push to GitHub: create a repo, add this file, add a requirements.txt with 'streamlit,pandas,numpy,scipy' and push.")
    st.code('''
    # example commands
    git init
    git add streamlit_finance_app.py
    echo "streamlit\npandas\nnumpy\nscipy" > requirements.txt
    git add requirements.txt
    git commit -m "Initial commit"
    git remote add origin <your-repo-url>
    git push -u origin main
    ''')

# End of file
