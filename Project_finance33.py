# -------------------------------------------------------------
# Finance Toolkit — Robust Dark Version (FINAL FIXED)
# -------------------------------------------------------------
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# -------------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------------
st.set_page_config(
    page_title="Finance Toolkit",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Simple dark styling
st.markdown(
    """
    <style>
        .reportview-container, .main, .stApp {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .css-18e3th9, .css-1d391kg {
            background-color: #0d1117;
            color: #e6edf3;
        }
        .stButton>button {
            background-color: #0b7285;
            color: white;
        }
        /* FOOTER FIX */
        #custom-footer {
            position: fixed;
            bottom: 0;
            right: 0;
            left: 0;
            padding: 10px;
            text-align: center;
            font-size: 13px;
            color: #8b949e;
            background-color: #0d1117;
            border-top: 1px solid #21262d;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Finance Toolkit — Risk, Inflation, Interest & World CPI (Pro Edition)")

# -------------------------------------------------------------
# OPTIONAL IMPORTS (SAFE)
# -------------------------------------------------------------
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False

try:
    from fredapi import Fred
    HAS_FRED = True
except Exception:
    HAS_FRED = False

# -------------------------------------------------------------
# SAMPLE DATA
# -------------------------------------------------------------
@st.cache_data
def sample_returns(n_days: int = 252, n_assets: int = 3):
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq='B')
    arr = np.random.normal(0, 0.01, size=(n_days, n_assets))
    df = pd.DataFrame(arr, index=dates, columns=[f"Asset {i+1}" for i in range(n_assets)])
    df = df.reset_index().rename(columns={'index': 'date'})
    return df

@st.cache_data
def sample_cpi_for(country_code: str = "US", months: int = 120):
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base_map = {"US": 260, "IN": 150, "UK": 120, "DE": 110, "JP": 102, "CN": 95}
    base = base_map.get(country_code.upper(), 100)
    trend = np.linspace(0, base * 0.05, months)
    noise = np.random.normal(0, base * 0.002, months).cumsum()
    cpi = base + trend + noise
    return pd.DataFrame({"date": rng, "CPI": np.round(cpi, 2)})

# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------
def try_parse_datetime(col_series):
    try:
        return pd.to_datetime(col_series, errors='coerce')
    except:
        return pd.to_datetime(col_series.astype(str), errors='coerce')

def load_returns_from_csv(uploaded_file) -> pd.DataFrame:
    df_raw = pd.read_csv(uploaded_file)
    if df_raw.shape[1] < 1:
        raise ValueError("Uploaded CSV appears empty or malformed.")

    first_col = df_raw.iloc[:, 0]
    first_col_dt = try_parse_datetime(first_col)

    if first_col_dt.notna().sum() / max(1, len(first_col_dt)) > 0.5:
        df_raw.iloc[:, 0] = first_col_dt
        df = df_raw.rename(columns={df_raw.columns[0]: "date"}).set_index("date")
    else:
        df = df_raw.copy()
        for col in df.columns:
            if col.lower() == "date":
                df[col] = try_parse_datetime(df[col])
                df = df.set_index(col)
                break

    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.empty:
        raise ValueError("No numeric data found in uploaded CSV.")

    sample_vals = df.stack().abs().values
    if len(sample_vals) > 0 and np.median(sample_vals) > 0.5:
        return df.pct_change().dropna(how="all")
    else:
        return df

def ensure_returns_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        for col in df.columns:
            if "date" in col.lower():
                df[col] = try_parse_datetime(df[col])
                df = df.set_index(col)
                break
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(axis=0, how="all").dropna(axis=1, how="all")

# -------------------------------------------------------------
# RISK-O-METER
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter (Robust)")

    uploaded = st.file_uploader("Upload returns/prices CSV", type=['csv'], key="returns_upload")
    use_sample = st.checkbox("Use sample synthetic returns", value=(uploaded is None))

    freq_choice = st.selectbox("Data frequency", ["Business days (252)", "Daily (365)", "Monthly (12)"])
    ann_factor = 252 if freq_choice.startswith("Business") else (365 if "Daily" in freq_choice else 12)

    try:
        if uploaded and not use_sample:
            df = load_returns_from_csv(uploaded)
        else:
            df = sample_returns(n_days=252, n_assets=3).set_index('date')
    except:
        df = sample_returns(n_days=252, n_assets=3).set_index('date')

    df = ensure_returns_df(df)
    st.dataframe(df.tail(8))

    st.subheader("Portfolio Weights")
    cols = list(df.columns)
    wtxt = st.text_input("Comma-separated weights (leave blank for equal)")

    if wtxt.strip():
        try:
            w = np.array([float(x) for x in wtxt.split(",")])
            if len(w) != len(cols):
                w = np.ones(len(cols)) / len(cols)
        except:
            w = np.ones(len(cols)) / len(cols)
    else:
        w = np.ones(len(cols)) / len(cols)

    if w.sum() == 0:
        w = np.ones(len(cols)) / len(cols)
    w = w / w.sum()

    port_series = (df * w).sum(axis=1).dropna()

    mean_period = port_series.mean()
    vol_period = port_series.std()
    ann_return = mean_period * ann_factor
    ann_vol = vol_period * np.sqrt(ann_factor)

    rf = st.number_input("Risk-free rate (annual %)", value=2.0, format="%.2f")
    sharpe = (ann_return - rf/100) / ann_vol if ann_vol > 0 else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Annualized Volatility", f"{ann_vol:.2%}")
    c2.metric("Annualized Return", f"{ann_return:.2%}")
    c3.metric("Sharpe Ratio", f"{sharpe:.2f}")

    st.subheader("Value at Risk (VaR)")
    alpha = st.slider("VaR Confidence Level (%)", 90, 99, 95)

    try:
        h_percent = np.percentile(port_series, 100 - alpha)
        historical_var = -h_percent
    except:
        historical_var = np.nan

    st.metric(f"Historical VaR ({alpha}%)", f"{historical_var:.2%}" if not np.isnan(historical_var) else "N/A")

    if st.checkbox("Parametric VaR (Normal assumption)", value=True):
        mu = port_series.mean()
        sigma = port_series.std()
        if HAS_SCIPY:
            z = norm.ppf(1 - alpha/100)
        else:
            z = {90:1.28, 95:1.65, 99:2.33}.get(alpha, 1.65)
        param_var = -(mu + z*sigma)
        st.metric(f"Parametric VaR ({alpha}%)", f"{param_var:.2%}")

    st.subheader("Rolling Volatility")
    window = st.number_input("Rolling window", min_value=5, max_value=120, value=30, step=1)
    rolling_vol = port_series.rolling(window).std()*np.sqrt(ann_factor)
    st.line_chart(rolling_vol.dropna())

# -------------------------------------------------------------
# CPI UI — FIXED VERSION
# -------------------------------------------------------------
def ui_cpi_world():
    st.header("🌍 World CPI Dashboard")

    available = ["US", "IN", "UK", "DE", "JP", "CN"]
    selected = st.multiselect("Select countries:", available, default=["US", "IN", "UK"])

    uploads = {}
    for c in selected:
        uploads[c] = st.file_uploader(f"Upload CPI CSV for {c}", type=['csv'], key=f"cpi_{c}")

    cpi_dfs = {}

    for c in selected:
        up = uploads[c]
        if up:
            try:
                tmp = pd.read_csv(up)
                tmp.columns = ['date','CPI']
                tmp['date'] = pd.to_datetime(tmp['date'])
                tmp['CPI'] = pd.to_numeric(tmp['CPI'], errors='coerce')
                df = tmp.dropna()
            except:
                df = sample_cpi_for(c)
        else:
            df = sample_cpi_for(c)

        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df['YoY'] = df['CPI'].pct_change(12) * 100
        df['MoM'] = df['CPI'].pct_change() * 100

        cpi_dfs[c] = df

    # ---- FIXED: USE OUTER MERGE TO ALIGN ALL COUNTRY SERIES ----
    combined_cpi = pd.concat({k: v['CPI'] for k, v in cpi_dfs.items()}, axis=1)
    st.subheader("CPI Index")
    st.line_chart(combined_cpi.dropna())

    combined_yoy = pd.concat({k: v['YoY'] for k, v in cpi_dfs.items()}, axis=1)
    st.subheader("YoY Inflation (%)")
    st.line_chart(combined_yoy.dropna())

# -------------------------------------------------------------
# INTEREST UI  (unchanged)
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator")

    P = st.number_input("Loan Amount (principal)", value=100000.0, format="%.2f")
    r = st.number_input("Annual Rate (%)", value=7.5, format="%.3f")
    y = st.number_input("Tenor (years)", value=5.0, min_value=0.0, format="%.1f")
    freq = st.selectbox("Payments per year", [12, 4, 2, 1])

    rate = r/100/freq
    n_periods = int(round(y*freq))

    if n_periods <= 0:
        st.warning("Tenor must be >0")
        return

    if rate == 0:
        emi = P/n_periods
    else:
        emi = P * rate * (1+rate)**n_periods / ((1+rate)**n_periods - 1)

    st.metric("EMI per period", f"{emi:,.2f}")
    st.write(f"Total Payment: {emi*n_periods:,.2f}")
    st.write(f"Total Interest: {emi*n_periods - P:,.2f}")

    st.subheader("Amortization (first 50 rows)")
    balance = P
    rows=[]
    for period in range(1,n_periods+1):
        interest = balance * rate
        principal = emi - interest
        balance = max(balance-principal, 0)
        rows.append([period, round(emi,2), round(principal,2), round(interest,2), round(balance,2)])

    am_df = pd.DataFrame(rows, columns=['Period','EMI','Principal','Interest','Balance'])
    st.dataframe(am_df.head(50))

    csv = am_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Full Amortization CSV", csv, file_name="amortization_schedule.csv")

# -------------------------------------------------------------
# TABS
# -------------------------------------------------------------
tabs = st.tabs(["Risk-O-Meter", "World CPI", "Interest & EMI", "About"])

with tabs[0]:
    ui_risk()

with tabs[1]:
    ui_cpi_world()

with tabs[2]:
    ui_interest()

with tabs[3]:
    st.write("""
    Finance Toolkit — Requirements:
    streamlit  
    pandas  
    numpy  
    scipy (optional)  
    fredapi (optional)

    Run:
    streamlit run Project_finance.py
    """)

# -------------------------------------------------------------
# COPYRIGHT FOOTER
# -------------------------------------------------------------
st.markdown(
    """
    <div id="custom-footer">
        © 2025 Finance Toolkit — Designed & Developed by <b>Rohit</b>
    </div>
    """,
    unsafe_allow_html=True
)
