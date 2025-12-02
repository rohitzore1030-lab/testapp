python -m venv venv
# mac / linux:
source venv/bin/activate
# windows:
# venv\Scripts\activate

pip install streamlit pandas numpy
# optional (for parametric VaR and FRED):
pip install scipy fredapi

# then
streamlit run streamlit_finance_app.py

# streamlit_finance_app.py
# Single-file Streamlit app: Risk-O-Meter, Inflation/CPI (with optional FRED), Interest/EMI.
#
# Dependencies (minimal): streamlit, pandas, numpy
# Optional but recommended: scipy (for parametric VaR), fredapi (for FRED CPI)
#
# How to run:
#   pip install streamlit pandas numpy
#   # optional:
#   pip install scipy fredapi
#   streamlit run streamlit_finance_app.py

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Finance Toolkit", layout="wide")
st.title("Finance Toolkit — Risk-O-Meter, Inflation (CPI) & Interest Tools")

# Try to import optional libs
HAS_SCIPY = False
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False

HAS_FREDAPI = False
try:
    from fredapi import Fred
    HAS_FREDAPI = True
except Exception:
    HAS_FREDAPI = False

# ---------------- utilities ----------------
@st.cache_data
def generate_sample_returns():
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq="B")
    df = pd.DataFrame(np.random.normal(0, 0.01, (len(dates), 3)),
                      index=dates, columns=["Asset A", "Asset B", "Asset C"])
    df = df.reset_index().rename(columns={"index": "date"})
    return df

@st.cache_data
def generate_sample_cpi(country="US"):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq="M")
    base = 260 if country == "US" else 150
    # create monotonic-ish sample CPI
    cpi = base + np.linspace(0, 10, len(dates)).cumsum() / len(dates)
    df = pd.DataFrame({"date": dates, "CPI": np.round(cpi, 2)})
    return df

@st.cache_data
def safe_read_csv(file) -> pd.DataFrame:
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"CSV read error: {e}")
        return pd.DataFrame()

def clean_returns_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.shape[1] >= 1:
        # If first column looks like dates, set as index
        try:
            df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
            df = df.set_index(df.columns[0])
        except Exception:
            pass
    # convert to numeric where possible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    return df

# ---------------- FRED helper ----------------
def fetch_us_cpi_from_fred(api_key, start=None, end=None):
    """Return DataFrame with columns ['date','CPI'] if successful or raise."""
    if not api_key:
        raise ValueError("FRED API key not provided")
    if not HAS_FREDAPI:
        raise ImportError("fredapi package not installed. Install via `pip install fredapi`")
    fred = Fred(api_key=api_key)
    s = fred.get_series("CPIAUCSL", start_date=start, end_date=end)
    df = s.rename("CPI").reset_index()
    df.columns = ["date", "CPI"]
    df["date"] = pd.to_datetime(df["date"])
    return df

# ---------------- RISK-O-METER ----------------
def risk_o_meter_ui():
    st.header("Risk-O-Meter")
    st.write("Upload daily returns CSV (first col = date, others numeric returns) or use sample data.")

    c1, c2 = st.columns([2, 1])
    with c1:
        uploaded = st.file_uploader("Returns CSV", type=["csv"], key="returns")
        if uploaded is not None:
            raw = safe_read_csv(uploaded)
            if raw.empty:
                st.info("Uploaded file could not be read or is empty.")
                return
            rets = clean_returns_df(raw)
        else:
            st.info("Using generated sample returns (3 assets, 252 business days).")
            rets = generate_sample_returns()
            rets = clean_returns_df(rets)

        if rets.empty:
            st.error("No usable numeric return columns found. Ensure CSV has date + numeric returns.")
            return

        st.subheader("Returns preview")
        st.dataframe(rets.tail())

    with c2:
        st.subheader("Options")
        weights_text = st.text_input("Portfolio weights (comma-separated). Leave blank = equal weights.")
        alpha = st.slider("VaR confidence (%)", 90, 99, 95)
        show_param = st.checkbox("Show parametric (Gaussian) VaR", value=True)

    # prepare weights
    n_assets = rets.shape[1]
    if weights_text:
        try:
            w = np.array([float(x.strip()) for x in weights_text.split(",")], dtype=float)
            if w.size != n_assets:
                st.warning(f"Weights length {w.size} != number of assets {n_assets}. Using equal weights.")
                w = np.repeat(1.0 / n_assets, n_assets)
        except Exception:
            st.warning("Invalid weight format. Using equal weights.")
            w = np.repeat(1.0 / n_assets, n_assets)
    else:
        w = np.repeat(1.0 / n_assets, n_assets)
    if w.sum() == 0:
        st.error("Sum of weights is zero. Provide non-zero weights.")
        return
    w = w / w.sum()

    # covariance and volatility
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
    # portfolio returns (weighted sum)
    port_rets = (rets * w).sum(axis=1).dropna()
    if len(port_rets) < 5:
        st.warning("Not enough return observations to compute VaR reliably.")
    else:
        try:
            hist_var = -np.percentile(port_rets, 100 - alpha)
            st.metric(f"Historical VaR ({alpha}%) - daily", f"{hist_var:.2%}")
        except Exception as e:
            st.error(f"Historical VaR error: {e}")

        # Parametric VaR only if scipy available and user asked
        if show_param:
            if HAS_SCIPY:
                mu = port_rets.mean()
                sigma = port_rets.std(ddof=1)
                z = norm.ppf(1 - alpha/100.0)
                param_var = -(mu + z * sigma)
                st.metric(f"Parametric VaR ({alpha}%) - daily", f"{param_var:.2%}")
            else:
                st.info("`scipy` not installed — parametric VaR not available. Install with: pip install scipy")

    st.markdown("---")
    # sample download
    sample_csv = generate_sample_returns().to_csv(index=False)
    st.download_button("Download sample returns CSV", sample_csv, "sample_returns.csv", "text/csv")

# ---------------- INFLATION & CPI ----------------
def inflation_ui():
    st.header("Inflation & CPI Viewer")
    # FRED key in sidebar
    st.sidebar.header("Optional API")
    fred_key = st.sidebar.text_input("FRED API key (optional for US CPI fetch)", value="", help="If you provide a FRED API key and fredapi is installed the app will fetch US CPI (CPIAUCSL).")
    use_fred = bool(fred_key.strip())

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("US CPI")
        if use_fred:
            if HAS_FREDAPI:
                try:
                    us_df = fetch_us_cpi_from_fred(fred_key)
                    us_df = us_df.sort_values("date")
                    us_df["yoy_%"] = us_df["CPI"].pct_change(periods=12) * 100
                    st.success("Fetched US CPI from FRED (CPIAUCSL)")
                    st.dataframe(us_df.tail())
                    st.line_chart(us_df.set_index("date")["CPI"])
                    st.line_chart(us_df.set_index("date")["yoy_%"])
                except Exception as e:
                    st.error(f"FRED fetch failed: {e}. You can upload a CSV or leave blank to use sample data.")
                    uploaded_us = st.file_uploader("Or upload US CPI CSV (date, CPI)", type=["csv"], key="us_cpi_upload")
                    if uploaded_us is not None:
                        df = safe_read_csv(uploaded_us)
                        if not df.empty and df.shape[1] >= 2:
                            try:
                                df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                                df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
                                df = df.dropna(subset=[df.columns[0], df.columns[1]])
                                df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "CPI"})
                                df = df.sort_values("date")
                                df["yoy_%"] = df["CPI"].pct_change(periods=12) * 100
                                st.dataframe(df.tail())
                                st.line_chart(df.set_index("date")["CPI"])
                                st.line_chart(df.set_index("date")["yoy_%"])
                            except Exception as e2:
                                st.error(f"Error processing uploaded US CPI: {e2}")
            else:
                st.info("fredapi not installed. Install with `pip install fredapi` to use FRED. Using upload or sample data instead.")
                uploaded_us = st.file_uploader("Upload US CPI CSV (date, CPI)", type=["csv"], key="us_cpi_upload2")
                if uploaded_us is not None:
                    df = safe_read_csv(uploaded_us)
                    if not df.empty:
                        try:
                            df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                            df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
                            df = df.dropna(subset=[df.columns[0], df.columns[1]])
                            df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "CPI"})
                            df = df.sort_values("date")
                            df["yoy_%"] = df["CPI"].pct_change(periods=12) * 100
                            st.dataframe(df.tail())
                            st.line_chart(df.set_index("date")["CPI"])
                            st.line_chart(df.set_index("date")["yoy_%"])
                        except Exception as e2:
                            st.error(f"Error processing uploaded US CPI: {e2}")
        else:
            uploaded_us = st.file_uploader("Upload US CPI CSV (date, CPI) — optional", type=["csv"], key="us_cpi_upload3")
            if uploaded_us is not None:
                df = safe_read_csv(uploaded_us)
                if not df.empty and df.shape[1] >= 2:
                    try:
                        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                        df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
                        df = df.dropna(subset=[df.columns[0], df.columns[1]])
                        df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "CPI"})
                        df = df.sort_values("date")
                        df["yoy_%"] = df["CPI"].pct_change(periods=12) * 100
                        st.dataframe(df.tail())
                        st.line_chart(df.set_index("date")["CPI"])
                        st.line_chart(df.set_index("date")["yoy_%"])
                    except Exception as e:
                        st.error(f"Error processing uploaded US CPI: {e}")
            else:
                st.info("No US CPI uploaded — using sample US CPI data.")
                sample = generate_sample_cpi("US")
                sample["yoy_%"] = sample["CPI"].pct_change(periods=12) * 100
                st.dataframe(sample.tail())
                st.line_chart(sample.set_index("date")["CPI"])
                st.line_chart(sample.set_index("date")["yoy_%"])

    with c2:
        st.subheader("India CPI")
        uploaded_in = st.file_uploader("Upload India CPI CSV (date, CPI) — optional", type=["csv"], key="in_cpi")
        if uploaded_in is not None:
            df = safe_read_csv(uploaded_in)
            if not df.empty and df.shape[1] >= 2:
                try:
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                    df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
                    df = df.dropna(subset=[df.columns[0], df.columns[1]])
                    df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "CPI"})
                    df = df.sort_values("date")
                    df["yoy_%"] = df["CPI"].pct_change(periods=12) * 100
                    st.dataframe(df.tail())
                    st.line_chart(df.set_index("date")["CPI"])
                    st.line_chart(df.set_index("date")["yoy_%"])
                except Exception as e:
                    st.error(f"Error processing uploaded India CPI: {e}")
        else:
            st.info("No India CPI uploaded — using sample India CPI data.")
            sample = generate_sample_cpi("IN")
            sample["yoy_%"] = sample["CPI"].pct_change(periods=12) * 100
            st.dataframe(sample.tail())
            st.line_chart(sample.set_index("date")["CPI"])
            st.line_chart(sample.set_index("date")["yoy_%"])

    st.markdown("---")
    old = st.number_input("Old CPI", value=100.0)
    new = st.number_input("New CPI", value=105.0)
    if st.button("Compute inflation"):
        try:
            inflation_pct = (new - old) / old * 100
            st.success(f"Inflation = {inflation_pct:.2f}%")
        except Exception as e:
            st.error(f"Error computing inflation: {e}")

# ---------------- INTEREST & EMI ----------------
def interest_ui():
    st.header("Interest & EMI Calculator")
    P = st.number_input("Principal (loan amount)", value=100000.0)
    annual = st.number_input("Annual interest rate (%)", value=7.5)
    years = st.number_input("Term (years)", value=5)
    freq = st.selectbox("Payments per year", [12, 4, 2, 1])

    r = annual / 100.0 / freq
    n = int(years * freq)
    if n <= 0:
        st.error("Term must be positive")
        return

    if abs(r) < 1e-12:
        emi = P / n
    else:
        try:
            emi = P * r * (1 + r) ** n / ((1 + r) ** n - 1)
        except Exception as e:
            st.error(f"EMI formula error: {e}")
            return

    st.metric("Payment per period", f"{emi:.2f}")
    st.write(f"Total payment = {emi * n:.2f}; Total interest = {emi * n - P:.2f}")

    st.markdown("---")
    st.subheader("Real interest (Fisher)")
    nom = st.number_input("Nominal rate (%)", value=7.0)
    infl = st.number_input("Inflation rate (%)", value=4.0)
    if st.button("Compute real rate"):
        real = (1 + nom / 100) / (1 + infl / 100) - 1
        st.success(f"Real interest rate = {real * 100:.2f}%")

# ---------------- APP LAYOUT ----------------
tabs = st.tabs(["Risk-O-Meter", "Inflation & CPI", "Interest & EMI", "About / GitHub"])
with tabs[0]:
    risk_o_meter_ui()
with tabs[1]:
    inflation_ui()
with tabs[2]:
    interest_ui()
with tabs[3]:
    st.header("About & GitHub")
    st.write(
        "This app includes Risk-O-Meter (volatility & VaR), Inflation/CPI viewer (optional FRED), and interest/EMI calculators."
    )
    st.markdown("**To push to GitHub:**\n\n1. Create repo on GitHub.\n2. Add this file.\n3. Add `requirements.txt` as below and push.")
    st.code(
        "streamlit\npandas\nnumpy\nscipy  # optional but recommended for parametric VaR\nfredapi  # optional for FRED CPI fetch\n"
    )
