# streamlit_finance_app.py
# FINAL WORKING VERSION — NO SYNTAX ERRORS, NO scipy, NO fredapi REQUIRED
# (Optional FRED support included but will not crash if libs are missing)
# This file is pure Python — NO shell commands inside the script.
# It will run successfully in Streamlit Cloud, GitHub Codespaces, and offline.

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Finance Toolkit", layout="wide")
st.title("Finance Toolkit — Risk-O-Meter, Inflation, Interest & CPI")

# -------------------------------------------------------------
# OPTIONAL IMPORTS (SAFE)
# -------------------------------------------------------------
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except:
    HAS_SCIPY = False

try:
    from fredapi import Fred
    HAS_FRED = True
except:
    HAS_FRED = False

# -------------------------------------------------------------
# SAMPLE DATA GENERATORS
# -------------------------------------------------------------
@st.cache_data
def sample_returns():
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B')
    df = pd.DataFrame(np.random.normal(0,0.01,(252,3)), index=dates,
                      columns=['Asset A', 'Asset B', 'Asset C']).reset_index()
    df.rename(columns={'index':'date'}, inplace=True)
    return df

@st.cache_data
def sample_cpi(country='US'):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='M')
    base = 260 if country=='US' else 150
    cpi = base + np.linspace(0, 5, len(dates)).cumsum()/10
    return pd.DataFrame({'date':dates, 'CPI':np.round(cpi,2)})

# -------------------------------------------------------------
# CLEANER FOR RETURNS DATA
# -------------------------------------------------------------
def clean_returns(df):
    df = df.copy()
    # first col → date
    try:
        df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
        df = df.set_index(df.columns[0])
    except:
        pass
    # numeric only
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    return df

# -------------------------------------------------------------
# RISK-O-METER
# -------------------------------------------------------------
def ui_risk():
    st.header("Risk-O-Meter")
    st.write("Upload returns file OR use sample data.")

    f = st.file_uploader("Upload returns CSV", type=['csv'])
    if f:
        raw = pd.read_csv(f)
        df = clean_returns(raw)
    else:
        st.info("Using sample returns dataset.")
        df = clean_returns(sample_returns())

    if df.empty:
        st.error("No numeric return columns found.")
        return

    st.subheader("Returns Preview")
    st.dataframe(df.tail())

    # weights
    wtxt = st.text_input("Weights (comma-separated) OR leave blank", "")
    n = df.shape[1]

    if wtxt.strip():
        try:
            w = np.array([float(x.strip()) for x in wtxt.split(',')])
            if len(w) != n:
                st.warning("Weights length mismatch — using equal weights.")
                w = np.ones(n)/n
        except:
            st.warning("Invalid weights — using equal weights.")
            w = np.ones(n)/n
    else:
        w = np.ones(n)/n

    w = w / w.sum()

    # volatility
    cov = df.cov().fillna(0) * 252
    port_var = float(w @ cov.values @ w.T)
    port_vol = np.sqrt(max(port_var,0))
    st.metric("Annualized Volatility", f"{port_vol:.2%}")

    # VaR
    alpha = st.slider("VaR Confidence %", 90, 99, 95)
    pres = (df * w).sum(axis=1).dropna()

    if len(pres) < 10:
        st.warning("Not enough data for VaR.")
    else:
        hvar = -np.percentile(pres, 100-alpha)
        st.metric(f"Historical VaR ({alpha}%)", f"{hvar:.2%}")

        if HAS_SCIPY:
            mu = pres.mean()
            sigma = pres.std()
            z = norm.ppf(1-alpha/100)
            pvar = -(mu + z*sigma)
            st.metric(f"Parametric VaR ({alpha}%)", f"{pvar:.2%}")
        else:
            st.info("Install scipy for Parametric VaR:  pip install scipy")

# -------------------------------------------------------------
# CPI / INFLATION
# -------------------------------------------------------------
def ui_cpi():
    st.header("Inflation & CPI Data")

    st.sidebar.subheader("FRED API (optional)")
    fred_key = st.sidebar.text_input("Enter FRED API Key (optional)")

    # US CPI
    st.subheader("US CPI")

    if fred_key.strip() and HAS_FRED:
        try:
            fred = Fred(api_key=fred_key)
            s = fred.get_series("CPIAUCSL")
            df = s.reset_index().rename(columns={'index':'date',0:'CPI'})
            df['date'] = pd.to_datetime(df['date'])
            df['CPI'] = pd.to_numeric(df['CPI'], errors='coerce')
            df['yoy_%'] = df['CPI'].pct_change(12)*100
            st.success("Fetched CPI from FRED")
        except:
            st.warning("FRED fetch failed — using sample data.")
            df = sample_cpi('US')
            df['yoy_%'] = df['CPI'].pct_change(12)*100
    else:
        uploaded = st.file_uploader("Upload US CPI CSV", type=['csv'], key='us_cpi')
        if uploaded:
            df = pd.read_csv(uploaded)
            try:
                df.iloc[:,0] = pd.to_datetime(df.iloc[:,0])
                df.iloc[:,1] = pd.to_numeric(df.iloc[:,1], errors='coerce')
                df = df.rename(columns={df.columns[0]:'date', df.columns[1]:'CPI'})
                df['yoy_%'] = df['CPI'].pct_change(12)*100
            except:
                st.error("Invalid CPI format.")
                return
        else:
            df = sample_cpi('US')
            df['yoy_%'] = df['CPI'].pct_change(12)*100

    st.dataframe(df.tail())
    st.line_chart(df.set_index('date')['CPI'])
    st.line_chart(df.set_index('date')['yoy_%'])

    # Inflation calculator
    st.markdown("---")
    st.subheader("Inflation Calculator")
    old = st.number_input("Old CPI", value=100.0)
    new = st.number_input("New CPI", value=105.0)
    if st.button("Compute Inflation"):
        st.success(f"Inflation = {(new-old)/old*100:.2f}%")

# -------------------------------------------------------------
# INTEREST / EMI
# -------------------------------------------------------------
def ui_interest():
    st.header("Interest & EMI Calculator")

    P = st.number_input("Loan Amount", value=100000.0)
    r = st.number_input("Annual Rate (%)", value=7.5)
    y = st.number_input("Years", value=5)
    freq = st.selectbox("Payments per year", [12,4,2,1])

    rate = r/100/freq
    n = int(y*freq)

    if n <= 0:
        st.error("Invalid term")
        return

    if rate == 0:
        emi = P/n
    else:
        emi = P*rate*(1+rate)**n / ((1+rate)**n - 1)

    st.metric("EMI", f"{emi:.2f}")
    st.write(f"Total Payment: {emi*n:.2f}")
    st.write(f"Total Interest: {emi*n - P:.2f}")

# -------------------------------------------------------------
# APP TABS
# -------------------------------------------------------------
T = st.tabs(["Risk-O-Meter", "Inflation & CPI", "Interest", "About/GitHub"])
with T[0]: ui_risk()
with T[1]: ui_cpi()
with T[2]: ui_interest()
with T[3]:
    st.write("""
    ## About & GitHub
    This app is fully compatible with GitHub & Streamlit.

    ### Create requirements.txt:
    streamlit
    pandas
    numpy
    scipy       # optional
    fredapi     # optional

    ### Run locally:
    pip install -r requirements.txt
    streamlit run streamlit_finance_app.py
    """)
