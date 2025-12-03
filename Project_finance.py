# -------------------------------------------------------------
# Finance Toolkit — Robust Dark Version (FINAL)
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
    # create plausible CPI series with gentle trend + noise
    rng = pd.date_range(end=pd.Timestamp.today(), periods=months, freq='M')
    base_map = {"US": 260, "IN": 150, "UK": 120, "DE": 110, "JP": 102, "CN": 95}
    base = base_map.get(country_code.upper(), 100)
    trend = np.linspace(0, base * 0.05, months)  # up to ~5% of base over period
    noise = np.random.normal(0, base * 0.002, months).cumsum()
    cpi = base + trend + noise
    return pd.DataFrame({"date": rng, "CPI": np.round(cpi, 2)})

# -------------------------------------------------------------
# HELPERS: read & detect returns/prices
# -------------------------------------------------------------
def try_parse_datetime(col_series):
    try:
        return pd.to_datetime(col_series, errors='coerce')
    except Exception:
        return pd.to_datetime(col_series.astype(str), errors='coerce')

def load_returns_from_csv(uploaded_file) -> pd.DataFrame:
    """
    Read CSV robustly. Return DataFrame with Date index (if present) and numeric columns.
    Accepts either returns or price series. Detects price series and converts to returns.
    """
    df_raw = pd.read_csv(uploaded_file)
    if df_raw.shape[1] < 1:
        raise ValueError("Uploaded CSV appears empty or malformed.")

    # If first column looks like a date, use it as date
    first_col = df_raw.iloc[:, 0]
    first_col_dt = try_parse_datetime(first_col)
    if first_col_dt.notna().sum() / max(1, len(first_col_dt)) > 0.5:
        # treat first column as date
        df_raw.iloc[:, 0] = first_col_dt
        df = df_raw.rename(columns={df_raw.columns[0]: "date"}).set_index("date")
    else:
        # no clear date column: try to set index to range and treat all as numeric
        df = df_raw.copy()
        # if header has "date" or "Date", try that
        for col in df.columns:
            if col.lower() == "date":
                df[col] = try_parse_datetime(df[col])
                df = df.set_index(col)
                break

    # convert all columns to numeric where possible
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # drop all-empty columns
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')

    if df.empty:
        raise ValueError("No numeric data found in uploaded CSV.")

    # Determine whether data are prices or returns:
    # Heuristic: if more than half of non-zero absolute values are > 0.5 (i.e., >50%), treat as prices
    sample_vals = df.stack().abs().values
    if len(sample_vals) > 0 and np.median(sample_vals) > 0.5:
        # treat as prices -> convert to returns (simple pct_change)
        df_returns = df.pct_change().dropna(how='all')
        # rename columns if necessary
        return df_returns
    else:
        # likely already returns
        return df

def ensure_returns_df(df: pd.DataFrame) -> pd.DataFrame:
    # Accept either (date index + numeric columns) or date column
    df = df.copy()
    # If index is not datetime, try find date column
    if not isinstance(df.index, pd.DatetimeIndex):
        for col in df.columns:
            if "date" in col.lower():
                df[col] = try_parse_datetime(df[col])
                df = df.set_index(col)
                break
    # Final numeric coercion
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(axis=0, how='all').dropna(axis=1, how='all')
    return df

# -------------------------------------------------------------
# RISK-O-METER UI
# -------------------------------------------------------------
def ui_risk():
    st.header("📈 Risk-O-Meter (Robust)")

    st.write("Upload a CSV of returns or price series (dates in first column or column named 'date'). If you skip upload, sample data is used.")

    col_left, col_right = st.columns([2, 1])
    with col_left:
        uploaded = st.file_uploader("Upload returns/prices CSV (returns or prices accepted)", type=['csv'], key="returns_upload")
        use_sample = st.checkbox("Use sample synthetic returns (250 trading days, 3 assets)", value=(uploaded is None))
    with col_right:
        freq_choice = st.selectbox("Data frequency (choose correctly for annualization)", ["Business days (252)", "Daily (365)", "Monthly (12)"])
        ann_factor = 252 if freq_choice.startswith("Business") else (365 if "Daily" in freq_choice else 12)

    # load data
    try:
        if uploaded and not use_sample:
            with st.spinner("Parsing uploaded file..."):
                df = load_returns_from_csv(uploaded)
        else:
            df = sample_returns(n_days=252, n_assets=3).set_index('date')
            # sample_returns returns simple returns already (not price series)
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")
        st.info("Using sample returns instead.")
        df = sample_returns(n_days=252, n_assets=3).set_index('date')

    # ensure returns frame
    df = ensure_returns_df(df)

    if df.empty:
        st.error("No usable numeric columns after parsing. Please check the CSV and try again.")
        return

    st.subheader("Preview (last 8 rows)")
    st.dataframe(df.tail(8))

    # portfolio weights input
    st.subheader("Portfolio Weights")
    cols = list(df.columns)
    default_weights = ",".join(["{:.3f}".format(1.0/len(cols)) for _ in cols])
    wtxt = st.text_input("Comma-separated weights (leave blank to use equal weights). Example: 0.5,0.3,0.2", value="")
    if wtxt.strip():
        try:
            w = np.array([float(x.strip()) for x in wtxt.split(",")])
            if len(w) != len(cols):
                st.warning("Number of weights does not match number of assets. Using equal weights.")
                w = np.ones(len(cols)) / len(cols)
        except Exception:
            st.warning("Invalid weight format. Using equal weights.")
            w = np.ones(len(cols)) / len(cols)
    else:
        w = np.ones(len(cols)) / len(cols)
    # normalize
    if w.sum() == 0:
        w = np.ones(len(cols)) / len(cols)
    else:
        w = w / w.sum()

    # compute portfolio returns (per-period)
    port_series = (df * w).sum(axis=1).dropna()
    if port_series.empty:
        st.error("Portfolio returns are empty after combining columns. Check your data.")
        return

    # Annualized return & volatility
    mean_period = port_series.mean()
    vol_period = port_series.std()
    ann_return = mean_period * ann_factor
    ann_vol = vol_period * np.sqrt(ann_factor)

    # Sharpe (rf input)
    rf_input = st.number_input("Risk-free rate (annual %, used for Sharpe)", value=2.0)
    rf = rf_input / 100.0

    sharpe = (ann_return - rf) / ann_vol if ann_vol > 0 else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Annualized Volatility", f"{ann_vol:.2%}")
    c2.metric("Annualized Return (est.)", f"{ann_return:.2%}")
    c3.metric("Sharpe Ratio", f"{sharpe:.2f}" if not np.isnan(sharpe) else "N/A")

    # risk class
    st.subheader("Risk Classification")
    if ann_vol < 0.08:
        st.success("🟢 Low Risk")
    elif ann_vol < 0.15:
        st.warning("🟡 Moderate Risk")
    else:
        st.error("🔴 High Risk")

    st.markdown("---")
    st.subheader("Value at Risk (VaR)")

    alpha = st.slider("VaR Confidence Level (%)", min_value=90, max_value=99, value=95)
    # require a minimal number of observations
    if len(port_series) < 30:
        st.warning(f"Only {len(port_series)} observations available. VaR estimates will be unreliable. Need >=30.")
    # Historical VaR:
    # Compute the alpha percentile of losses: VaR = -percentile(return, 100-alpha)
    # Eg alpha=95 -> 5th percentile of returns -> VaR = -R_5th (positive number)
    try:
        h_percentile = np.percentile(port_series.dropna(), 100 - alpha)
        historical_var = -h_percentile
    except Exception:
        historical_var = np.nan

    st.metric(f"Historical VaR ({alpha}%) (per-period)", f"{historical_var:.2%}" if not np.isnan(historical_var) else "N/A")

    # Parametric VaR (normal)
    use_parametric = st.checkbox("Show parametric VaR (Normal assumption)", value=True)
    if use_parametric:
        mu = port_series.mean()
        sigma = port_series.std()
        # z at alpha: for losses, quantile at 1-alpha -> using norm.ppf for tail
        if HAS_SCIPY:
            z = norm.ppf(1 - alpha / 100.0)
        else:
            # approximate z using inverse error function approximation (works fine for common alphas)
            from math import sqrt, log
            # Simple approximation: map alpha to z via scipy-less approximate values (95->1.645, 99->2.33)
            approx_map = {90: 1.2816, 95: 1.645, 97: 1.8808, 99: 2.3263}
            z = approx_map.get(alpha, 1.645)
        param_var = -(mu + z * sigma)
        st.metric(f"Parametric VaR ({alpha}%) (per-period)", f"{param_var:.2%}")

    # If user wants annualized VaR, scale naive (only if returns iid)
    if st.checkbox("Show approximate annualized VaR (assumes iid, scale by sqrt)", value=False):
        # naive scaling: multiply parametric VaR by sqrt(ann_factor)
        if not np.isnan(historical_var):
            st.write(f"Historical VaR annualized (approx): {historical_var * np.sqrt(ann_factor):.2%}")
        st.write(f"Parametric VaR annualized (approx): {param_var * np.sqrt(ann_factor):.2%}")

    # rolling volatility & charts
    st.markdown("---")
    st.subheader("Rolling Volatility & Component Weights")
    window = st.number_input("Rolling window (periods)", min_value=5, max_value=120, value=30)
    rolling_vol = port_series.rolling(window).std() * np.sqrt(ann_factor)
    st.line_chart(rolling_vol.dropna())

    st.subheader("Component Contributions (last observation)")
    try:
        latest = df.iloc[-1] if len(df) > 0 else None
        contrib = (w * df.cov().fillna(0).dot(w)) if latest is None else None
        # show table of weights & last returns
        info_df = pd.DataFrame({"weight": w}, index=cols)
        # last returns
        last_vals = df.tail(1).T
        last_vals.columns = ["last"]
        info_df = info_df.join(last_vals)
        st.dataframe(info_df)
    except Exception:
        st.info("Couldn't compute contributions for the dataset shape.")

# -------------------------------------------------------------
# CPI / World CPI UI
# -------------------------------------------------------------
def ui_cpi_world():
    st.header("🌍 World CPI Dashboard")

    st.sidebar.subheader("Optional FRED API")
    fred_key = st.sidebar.text_input("FRED API Key (optional for US) - leave blank to use samples")

    # allow multi-country selection
    available = ["US", "IN", "UK", "DE", "JP", "CN"]
    selected = st.multiselect("Select countries to include (sample data available for these):", available, default=["US", "IN", "UK"])

    # user can upload CSVs for specific country (optional)
    st.write("You may optionally upload a CSV per country. CSV must have `date` and `CPI` columns, or date in first column and values in second.")
    uploads = {}
    for c in selected:
        uploads[c] = st.file_uploader(f"Upload CPI CSV for {c} (optional)", type=['csv'], key=f"cpi_{c}")

    # assemble dataframe dictionary
    cpi_dfs = {}
    for c in selected:
        uploaded = uploads.get(c)
        df = None
        if uploaded is not None:
            try:
                tmp = pd.read_csv(uploaded)
                # try common layouts
                if tmp.shape[1] >= 2:
                    # if first column is date-like, use it
                    first = tmp.iloc[:, 0]
                    first_dt = try_parse_datetime(first)
                    if first_dt.notna().sum() / max(1, len(first_dt)) > 0.5:
                        tmp.iloc[:, 0] = first_dt
                        tmp = tmp.rename(columns={tmp.columns[0]: "date", tmp.columns[1]: "CPI"})
                        tmp['date'] = pd.to_datetime(tmp['date'])
                        tmp['CPI'] = pd.to_numeric(tmp['CPI'], errors='coerce')
                        df = tmp[['date', 'CPI']].dropna()
                    else:
                        # perhaps has named columns
                        if 'date' in tmp.columns.str.lower():
                            date_col = [col for col in tmp.columns if col.lower() == 'date'][0]
                            value_col = [col for col in tmp.columns if col.lower() != 'date'][0]
                            tmp = tmp.rename(columns={date_col: 'date', value_col: 'CPI'})
                            tmp['date'] = pd.to_datetime(tmp['date'])
                            tmp['CPI'] = pd.to_numeric(tmp['CPI'], errors='coerce')
                            df = tmp[['date', 'CPI']].dropna()
                if df is None:
                    st.warning(f"Couldn't parse uploaded CPI for {c}. Using sample.")
                    df = sample_cpi_for(c)
            except Exception:
                st.warning(f"Error reading uploaded CPI for {c}. Using sample.")
                df = sample_cpi_for(c)
        else:
            # If US and fred available + key, try to fetch US CPI; otherwise sample
            if c == "US" and fred_key.strip() and HAS_FRED:
                try:
                    fred = Fred(api_key=fred_key)
                    s = fred.get_series("CPIAUCSL")
                    df = s.reset_index().rename(columns={'index': 'date', 0: 'CPI'})
                    df['date'] = pd.to_datetime(df['date'])
                    df['CPI'] = pd.to_numeric(df['CPI'], errors='coerce')
                except Exception:
                    df = sample_cpi_for(c)
            else:
                df = sample_cpi_for(c)
        # compute YoY and MoM
        df = df.sort_values('date').reset_index(drop=True)
        df['YoY'] = df['CPI'].pct_change(12) * 100
        df['MoM'] = df['CPI'].pct_change() * 100
        cpi_dfs[c] = df

    # combine for plotting
    st.subheader("CPI time series (selected countries)")
    combined = pd.DataFrame()
    for c, df in cpi_dfs.items():
        s = df.set_index('date')['CPI'].rename(c)
        combined = pd.concat([combined, s], axis=1)
    st.line_chart(combined.dropna())

    st.subheader("Year-over-Year Inflation (YoY %)")
    combined_yoy = pd.DataFrame()
    for c, df in cpi_dfs.items():
        s = df.set_index('date')['YoY'].rename(c)
        combined_yoy = pd.concat([combined_yoy, s], axis=1)
    st.line_chart(combined_yoy.dropna())

    st.subheader("Latest CPI & YoY table")
    latest_rows = []
    for c, df in cpi_dfs.items():
        last = df.dropna().tail(1)
        if len(last) > 0:
            latest_rows.append({
                "Country": c,
                "Date": last['date'].dt.date.values[0],
                "CPI": float(last['CPI'].values[0]),
                "YoY %": float(last['YoY'].values[0]) if not np.isnan(last['YoY'].values[0]) else None,
                "MoM %": float(last['MoM'].values[0]) if not np.isnan(last['MoM'].values[0]) else None
            })
    if latest_rows:
        st.table(pd.DataFrame(latest_rows).set_index('Country'))
    else:
        st.info("No CPI data available to show.")

# -------------------------------------------------------------
# Interest / EMI UI
# -------------------------------------------------------------
def ui_interest():
    st.header("🏦 Interest & EMI Calculator (Enhanced)")

    P = st.number_input("Loan Amount (principal)", value=100000.0, format="%.2f")
    r = st.number_input("Annual Rate (%)", value=7.5, format="%.3f")
    y = st.number_input("Tenor (years)", value=5, min_value=0.0, format="%.1f")
    freq = st.selectbox("Payments per year", [12, 4, 2, 1], index=0)

    rate = r / 100.0 / freq
    n_periods = int(round(y * freq))

    if n_periods <= 0:
        st.warning("Please select a tenor > 0 years.")
        return

    if rate == 0:
        emi = P / n_periods
    else:
        emi = P * rate * (1 + rate) ** n_periods / ((1 + rate) ** n_periods - 1)

    st.metric("EMI (per period)", f"{emi:,.2f}")
    st.write(f"Total Payment: {emi * n_periods:,.2f}")
    st.write(f"Total Interest: {emi * n_periods - P:,.2f}")

    # amortization schedule download
    st.subheader("Amortization schedule (first 50 rows)")
    balance = P
    rows = []
    for period in range(1, n_periods + 1):
        interest = balance * rate
        principal = emi - interest
        balance = max(balance - principal, 0.0)
        rows.append([period, round(emi, 2), round(principal, 2), round(interest, 2), round(balance, 2)])
    am_df = pd.DataFrame(rows, columns=['Period', 'EMI', 'Principal', 'Interest', 'Balance'])
    st.dataframe(am_df.head(50))

    csv = am_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download full amortization schedule (CSV)", csv, file_name="amortization_schedule.csv", mime="text/csv")

# -------------------------------------------------------------
# APP LAYOUT: Tabs
# -------------------------------------------------------------
tabs = st.tabs(["Risk-O-Meter", "World CPI", "Interest & EMI", "About / Requirements"])

with tabs[0]:
    ui_risk()

with tabs[1]:
    ui_cpi_world()

with tabs[2]:
    ui_interest()

with tabs[3]:
    st.header("ℹ About & Requirements")
    st.write("""
    Finance Toolkit — Robust version.
    - Upload returns (or price series) CSVs for Risk-O-Meter.
    - Upload per-country CPI CSVs (optional) or use sample data.
    - VaR: Historical and parametric provided. Parametric uses normal assumption.
    - Annualization factor selectable for volatility/return scaling.

    Recommended requirements (put in requirements.txt):
    ```
    streamlit
    pandas
    numpy
    scipy       # optional (improves parametric VaR z-value)
    fredapi     # optional (fetch US CPI)
    ```

    Run:
    ```
    streamlit run streamlit_finance_app.py
    ```
    """)
