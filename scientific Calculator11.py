# app.py
"""
Robust Casio-style scientific calculator for Streamlit
- Avoids StreamlitAPIException causes (safe callbacks, no in-place session_state mutation)
- Supports typing in the input box, buttons, history, DEG/RAD.
- Uses functools.partial to safely pass button labels to callbacks.
"""

import re
import streamlit as st
import numpy as np
from functools import partial
from typing import Tuple

# ---- Page config + CSS ----
st.set_page_config(page_title="Scientific Calculator (Robust)", layout="centered")

st.markdown(
    """
    <style>
    body, .main {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .calculator {
        background: linear-gradient(180deg, #1f2d3a 0%, #162028 100%);
        border-radius: 14px;
        padding: 16px;
        width: 740px;
        margin: 28px auto;
        box-shadow: 0 12px 40px rgba(0,0,0,0.6);
    }
    .screen {
        background: linear-gradient(180deg, #f6fff0, #dfffd8);
        color: #08121a;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: right;
        font-size: 1.25rem;
        margin-bottom: 10px;
        min-height: 56px;
        overflow-x: auto;
        white-space: nowrap;
    }
    .stButton>button {
        background: linear-gradient(180deg,#3b4b62,#2b3948);
        color: white;
        border: none;
        border-radius: 8px;
        height: 46px;
        width: 100%;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 6px 12px rgba(0,0,0,0.35);
        transition: transform .06s ease, box-shadow .06s ease;
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 10px 18px rgba(0,0,0,0.45); }
    .title { text-align:center; color: #ecf0f1; margin-bottom: 6px; }
    .history { max-height: 220px; overflow-y: auto; background: #0f1720; padding:8px; border-radius:8px; color:#e6eef8; }
    .small { font-size:0.9rem; color:#d7e6f7; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h2 class='title'>🧮 Casio-like Scientific Calculator — Robust Edition</h2>", unsafe_allow_html=True)

# ---- Session state defaults ----
if "input_box" not in st.session_state:
    st.session_state["input_box"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []  # most recent first, list of (expr, result)
if "angle_mode" not in st.session_state:
    st.session_state["angle_mode"] = "RAD"  # or "DEG"

# ---- Utility setters (no in-place mutation) ----
def set_input(value: str) -> None:
    st.session_state["input_box"] = "" if value is None else str(value)

def append_input(s: str) -> None:
    current = st.session_state.get("input_box", "")
    # assign a NEW string (avoid in-place)
    st.session_state["input_box"] = current + str(s)

def delete_last() -> None:
    current = st.session_state.get("input_box", "")
    st.session_state["input_box"] = current[:-1]

def clear_input() -> None:
    st.session_state["input_box"] = ""

def push_history(expr: str, result: str) -> None:
    hist = st.session_state.get("history", [])
    # insert latest at front
    hist.insert(0, (expr, result))
    # cap history length
    st.session_state["history"] = hist[:100]

def clear_history() -> None:
    st.session_state["history"] = []

def toggle_angle_mode() -> None:
    st.session_state["angle_mode"] = "DEG" if st.session_state["angle_mode"] == "RAD" else "RAD"

# ---- Calculation logic (safe-ish) ----
def calculate_expression(expr: str) -> str:
    """
    Convert the display expression into a Python expression using numpy and evaluate.
    - Preserves scientific notation like 1e3
    - Replaces standalone e (Euler) not part of scientific notation with np.e
    - Supports pi, sqrt (√), functions sin, cos, tan, asin, acos, atan, ln, log, exp
    - If angle mode is DEG, converts inputs/outputs accordingly
    """
    try:
        if expr is None:
            return ""
        raw = str(expr).strip()
        if raw == "":
            return ""

        # 1) basic symbol replacements
        s = raw.replace("^", "**")
        s = s.replace("√", "np.sqrt")
        s = s.replace("π", "np.pi")

        # allow 'pi' literal
        s = re.sub(r"(?<![A-Za-z0-9_])pi(?![A-Za-z0-9_])", "np.pi", s)

        # Replace function names only when followed by '('
        s = re.sub(r"\bsin\(", "np.sin(", s)
        s = re.sub(r"\bcos\(", "np.cos(", s)
        s = re.sub(r"\btan\(", "np.tan(", s)
        s = re.sub(r"\basin\(", "np.arcsin(", s)
        s = re.sub(r"\bacos\(", "np.arccos(", s)
        s = re.sub(r"\batan\(", "np.arctan(", s)
        s = re.sub(r"\bln\(", "np.log(", s)
        s = re.sub(r"\blog\(", "np.log10(", s)
        s = re.sub(r"\bexp\(", "np.exp(", s)

        # Replace standalone 'e' with np.e but NOT when part of scientific notation like 1e3 or 2.3E-4
        # pattern: (?<![0-9\.eE\+\-])e(?![0-9\.eE\+\-])
        s = re.sub(r"(?<![0-9\.eE\+\-])e(?![0-9\.eE\+\-])", "np.e", s)

        # Percent handling: 50% -> (50/100)
        s = re.sub(r"([0-9]+(?:\.[0-9]+)?)\%", r"(\1/100)", s)

        # Angle mode conversion:
        if st.session_state.get("angle_mode", "RAD") == "DEG":
            # Convert trig arguments degrees->radians for sin/cos/tan
            s = s.replace("np.sin(", "np.sin(np.deg2rad(")
            s = s.replace("np.cos(", "np.cos(np.deg2rad(")
            s = s.replace("np.tan(", "np.tan(np.deg2rad("))
            # For inverse trig convert rad->deg on results:
            s = s.replace("np.arcsin(", "np.rad2deg(np.arcsin(")
            s = s.replace("np.arccos(", "np.rad2deg(np.arccos(")
            s = s.replace("np.arctan(", "np.rad2deg(np.arctan(")

        # Evaluate in a very limited global env
        allowed_globals = {"np": np, "__builtins__": {}}
        result = eval(s, allowed_globals, {})

        # Numpy arrays -> strings
        if isinstance(result, (np.ndarray,)):
            return str(result.tolist())

        # Format floats
        if isinstance(result, (float, np.floating)):
            formatted = f"{round(float(result), 12):.12f}".rstrip("0").rstrip(".")
            return formatted
        else:
            return str(result)
    except Exception:
        return "Error"

# ---- Callback functions (defined before UI creation) ----
def on_button_append(label: str) -> None:
    # append label safely
    append_input(label)

def on_button_equal() -> None:
    expr = st.session_state.get("input_box", "")
    res = calculate_expression(expr)
    # only store valid numeric/string results (not empty)
    if res not in ("", "Error"):
        st.session_state["last_result"] = res
        push_history(expr, res)
    set_input(res)

def on_button_ans() -> None:
    append_input(st.session_state.get("last_result", ""))

# ---- UI ----
st.markdown("<div class='calculator'>", unsafe_allow_html=True)

# top: screen + DEG/RAD toggle
left_col, right_col = st.columns([5, 1])
with left_col:
    st.markdown(f"<div class='screen'>{st.session_state.get('input_box','')}</div>", unsafe_allow_html=True)
with right_col:
    st.button("DEG/RAD", key="btn_toggle_angle", on_click=toggle_angle_mode)
    st.markdown(f"<div class='small' style='margin-top:6px;text-align:center;'>Mode: <strong>{st.session_state['angle_mode']}</strong></div>", unsafe_allow_html=True)

# text input bound to session_state
st.text_input("Type expression (supports 1e3):", key="input_box", value=st.session_state.get("input_box", ""))

# Define button layout
buttons = [
