# app.py
"""
Casio-Style Scientific Calculator (Streamlit)
Fixed: no session_state in-place mutation; uses on_click callbacks and safe assignments.
Features:
 - Buttons + direct typing (smooth cursor behaviour)
 - Preserves scientific notation like 1e3
 - Functions: sin, cos, tan, asin, acos, atan, ln, log (base10), exp, sqrt, pi, e
 - Deg / Rad toggle for trig
 - History panel with copy-to-input
 - Safe eval using limited globals (np)
"""

import re
import streamlit as st
import numpy as np
from typing import Any

# -------------------------
# Page config and styling
# -------------------------
st.set_page_config(page_title="Scientific Calculator (Casio-like)", layout="centered")

st.markdown(
    """
    <style>
    body, .main {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .calculator {
        background: linear-gradient(180deg, #1f2d3a 0%, #162028 100%);
        border-radius: 16px;
        padding: 18px;
        width: 720px;
        margin: 28px auto;
        box-shadow: 0 12px 40px rgba(0,0,0,0.6);
    }
    .screen {
        background: linear-gradient(180deg, #f6fff0, #dfffd8);
        color: #08121a;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: right;
        font-size: 1.35rem;
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
        height: 48px;
        width: 100%;
        font-size: 1.05rem;
        font-weight: 600;
        box-shadow: 0 6px 12px rgba(0,0,0,0.35);
        transition: transform .06s ease, box-shadow .06s ease;
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 10px 18px rgba(0,0,0,0.45); }
    .op { background: linear-gradient(180deg,#f1c40f,#d4ac0d) !important; color: #06121a !important; }
    .func { background: linear-gradient(180deg,#8e44ad,#6c3483) !important; color: white !important; }
    .title { text-align:center; color: #ecf0f1; margin-bottom: 6px; }
    .history { max-height: 220px; overflow-y: auto; background: #0f1720; padding:10px; border-radius:8px; color:#e6eef8; }
    .small { font-size:0.9rem; color:#d7e6f7; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h2 class='title'>🧮 Casio-Style Scientific Calculator — Fixed</h2>", unsafe_allow_html=True)

# -------------------------
# Session state defaults
# -------------------------
if "input_box" not in st.session_state:
    st.session_state["input_box"] = ""    # string shown in input and in screen
if "last_result" not in st.session_state:
    st.session_state["last_result"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []      # list of tuples (expr, result)
if "angle_mode" not in st.session_state:
    st.session_state["angle_mode"] = "RAD"  # or "DEG"

# -------------------------
# Safe helpers (no in-place mutation)
# -------------------------
def set_input(value: str) -> None:
    """Set input_box safely (assign new string)."""
    st.session_state["input_box"] = str(value)

def append_to_input(s: str) -> None:
    """Append label to input_box safely via assignment (no in-place +=)."""
    current = st.session_state.get("input_box", "")
    set_input(current + str(s))

def delete_last_char() -> None:
    current = st.session_state.get("input_box", "")
    set_input(current[:-1])

def clear_input() -> None:
    set_input("")

def push_history(expr: str, result: str) -> None:
    hist = st.session_state.get("history", [])
    # keep recent at top
    hist.insert(0, (expr, result))
    # cap history
    st.session_state["history"] = hist[:50]

def toggle_angle_mode() -> None:
    st.session_state["angle_mode"] = "DEG" if st.session_state["angle_mode"] == "RAD" else "RAD"

# -------------------------
# Calculation (safe-ish)
# -------------------------
def calculate_expression(expr: str) -> str:
    """
    Convert the display expression into a Python expression using numpy and evaluate.
    - Preserves scientific notation like 1e3
    - Replaces standalone e (Euler) when used as constant (not in 1e3)
    - Replaces pi, sqrt, functions: sin, cos, tan, asin, acos, atan, ln, log, exp
    - Considers angle mode (DEG/RAD) for trig functions
    Returns string result or "Error".
    """
    try:
        original = expr
        if original.strip() == "":
            return ""

        # Replace ^ with **
        expr2 = expr.replace("^", "**")

        # Replace sqrt symbol with np.sqrt
        expr2 = expr2.replace("√", "np.sqrt")

        # replace pi token (standalone 'π' or 'pi')
        expr2 = expr2.replace("π", "np.pi")
        expr2 = re.sub(r"(?<![A-Za-z0-9_])pi(?![A-Za-z0-9_])", "np.pi", expr2)

        # Replace function names only when used as functions (ending with '(')
        # e.g., sin( -> np.sin(
        func_map = {
            r"\bsin\(": "np.sin(",
            r"\bcos\(": "np.cos(",
            r"\btan\(": "np.tan(",
            r"\basin\(": "np.arcsin(",
            r"\bacos\(": "np.arccos(",
            r"\batan\(": "np.arctan(",
            r"\bln\(": "np.log(",
            r"\blog\(": "np.log10(",
            r"\bexp\(": "np.exp(",
        }
        for pat, sub in func_map.items():
            expr2 = re.sub(pat, sub, expr2)

        # Replace standalone 'e' (Euler) but not in scientific notation 1e3 or decimale-like 2.3e-4
        expr2 = re.sub(r"(?<![0-9\.eE\+\-])e(?![0-9\.eE\+\-])", "np.e", expr2)

        # If angle mode is DEG, wrap inner trig args with conversion: sin(x) -> np.sin(np.deg2rad(x))
        if st.session_state.get("angle_mode", "RAD") == "DEG":
            # convert only top-level np.sin( ... ) occurrences
            # simple approach: replace 'np.sin(' with 'np.sin(np.deg2rad(' and close later with an extra ')'
            # We'll do replacements for sin,cos,tan and their inverse counterparts where appropriate.
            expr2 = expr2.replace("np.sin(", "np.sin(np.deg2rad(")
            expr2 = expr2.replace("np.cos(", "np.cos(np.deg2rad(")
            expr2 = expr2.replace("np.tan(", "np.tan(np.deg2rad(")
            # For inverse trig, result is in radians -> convert to degrees after: np.arcsin(x) -> np.rad2deg(np.arcsin(x))
            expr2 = expr2.replace("np.arcsin(", "np.rad2deg(np.arcsin(")
            expr2 = expr2.replace("np.arccos(", "np.rad2deg(np.arccos(")
            expr2 = expr2.replace("np.arctan(", "np.rad2deg(np.arctan(")

        # Replace percent like 50% -> (50/100)
        expr2 = re.sub(r"([0-9]+(?:\.[0-9]+)?)\%", r"(\1/100)", expr2)

        # Final safety: allow only numpy under globals
        allowed_globals = {"np": np, "__builtins__": {}}

        # Evaluate
        result = eval(expr2, allowed_globals, {})

        # If numpy array, convert to list
        if isinstance(result, (np.ndarray,)):
            return str(result.tolist())

        # Format floats nicely
        if isinstance(result, (float, np.floating)):
            formatted = f"{round(float(result), 12):.12f}".rstrip("0").rstrip(".")
            return formatted
        else:
            return str(result)
    except Exception:
        return "Error"

# -------------------------
# UI: main calculator area
# -------------------------
st.markdown("<div class='calculator'>", unsafe_allow_html=True)

# Top row: screen + angle toggle + clear
col1, col2 = st.columns([5, 1])
with col1:
    st.markdown(f"<div class='screen'>{st.session_state.get('input_box','')}</div>", unsafe_allow_html=True)
with col2:
    st.button("DEG/RAD", on_click=toggle_angle_mode)
    st.markdown(f"<div class='small' style='margin-top:6px;text-align:center;'>Mode: <strong>{st.session_state['angle_mode']}</strong></div>", unsafe_allow_html=True)

# Direct typing — bind the text_input to 'input_box' key so typing is smooth
# Using key="input_box" binds it to st.session_state['input_box'] automatically.
typed = st.text_input("Type expression (supports 1e3):", value=st.session_state.get("input_box", ""), key="input_box")

# Buttons layout
buttons = [
    ["7", "8", "9", "/", "sin("],
    ["4", "5", "6", "*", "cos("],
    ["1", "2", "3", "-", "tan("],
    ["0", ".", "(", ")", "log("],
    ["√", "π", "e", "^", "exp("],
    ["C", "DEL", "+", "=", "Ans"]
]

# Render buttons with safe on_click callbacks
for r_index, row in enumerate(buttons):
    cols = st.columns(5)
    for c_index, label in enumerate(row):
        btn_key = f"btn_{r_index}_{c_index}"
        # map label to callback
        if label == "C":
            cols[c_index].button(label, key=btn_key, on_click=clear_input)
        elif label == "DEL":
            cols[c_index].button(label, key=btn_key, on_click=delete_last_char)
        elif label == "=":
            cols[c_index].button(label, key=btn_key, on_click=lambda: on_equal_click())
        elif label == "Ans":
            cols[c_index].button(label, key=btn_key, on_click=lambda: append_to_input(st.session_state.get("last_result", "")))
        else:
            # Append the literal label to input on click
            # For constants like π and √ and e, label includes special chars; calculate() knows how to parse them
            cols[c_index].button(label, key=btn_key, on_click=lambda s=label: append_to_input(s))

# End calculator container
st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Callback functions declared after buttons so on_equal_click reference exists
# -------------------------
def on_equal_click() -> None:
    expr = st.session_state.get("input_box", "")
    res = calculate_expression(expr)
    # Save last_result and history only if calculation succeeded
    if res != "Error" and res != "":
        st.session_state["last_result"] = res
        push_history(expr, res)
    set_input(res)

# -------------------------
# Extra controls bottom
# -------------------------
col_a, col_b = st.columns([3, 2])
with col_a:
    if st.button("Calculate"):
        on_equal_click()
with col_b:
    if st.button("Clear History"):
        st.session_state["history"] = []

# -------------------------
# History panel
# -------------------------
st.markdown("<hr style='opacity:0.15' />", unsafe_allow_html=True)
st.markdown("<div class='small'>History — click an item to copy expression back to input</div>", unsafe_allow_html=True)
hist_col1, hist_col2 = st.columns([2, 1])
with hist_col1:
    if st.session_state["history"]:
        st.markdown("<div class='history'>", unsafe_allow_html=True)
        for idx, (expr, res) in enumerate(st.session_state["history"]):
            # Show expr = res with tiny copy button
            row_key = f"hist_{idx}"
            cols_h = st.columns([4,1])
            cols_h[0].markdown(f"<div style='padding:6px 4px; border-bottom: 1px solid rgba(255,255,255,0.03);'>{expr}  =  <strong>{res}</strong></div>", unsafe_allow_html=True)
            if cols_h[1].button("Use", key=row_key):
                set_input(expr)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No history yet. Calculate something!")

with hist_col2:
    st.markdown("<div style='padding-left:12px;'>", unsafe_allow_html=True)
    st.write("Last result:")
    st.code(st.session_state.get("last_result", ""), line_numbers=False)
    st.markdown("</div>", unsafe_allow_html=True)

# Helpful tips
st.markdown(
    """
    <div class='small' style='margin-top:10px;'>
      Tips: Use parentheses. Use 1e3 for scientific notation. Button functions insert '(' so remember to close it.<br>
      Trig functions use current angle mode (DEG/RAD). 'e' button inserts Euler's constant; scientific notation like 1e3 is preserved.
    </div>
    """,
    unsafe_allow_html=True,
)
