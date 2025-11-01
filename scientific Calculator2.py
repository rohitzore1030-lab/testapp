# app.py
import re
import streamlit as st
import numpy as np

# Page config
st.set_page_config(page_title="Casio-Style Scientific Calculator", layout="centered")

# CSS / styling
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
        width: 420px;
        margin: 36px auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        transition: transform .18s ease;
    }
    .calculator:hover { transform: translateY(-6px); }
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
    .wide { width: 100% !important; }
    .title { text-align:center; color: #ecf0f1; margin-bottom: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h2 class='title'>🧮 Casio-Style Scientific Calculator (fixed typing)</h2>", unsafe_allow_html=True)

# Session-state initialization
if "input_box" not in st.session_state:
    st.session_state["input_box"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = ""

# Helper: safe calculate with regex-aware replacements
def calculate(expr: str) -> str:
    """
    Safely convert user expression into python-evaluable expression using numpy.
    Important: preserves scientific notation like 1e3 and only replaces standalone 'e' constants.
    """
    try:
        # Keep original for display if error
        src = expr

        # Short replacements first
        # ^ -> **
        expr = expr.replace("^", "**")

        # Replace sqrt symbol with function
        expr = expr.replace("√", "np.sqrt")

        # Replace pi symbol with np.pi
        expr = expr.replace("π", "np.pi")

        # Replace common functions (require parentheses or arguments)
        # Use word boundaries to avoid accidental replacement inside other tokens
        expr = re.sub(r"\bexp\(", "np.exp(", expr)
        expr = re.sub(r"\blog\(", "np.log10(", expr)     # log -> log10
        expr = re.sub(r"\bln\(", "np.log(", expr)        # ln for natural log
        expr = re.sub(r"\bsin\(", "np.sin(", expr)
        expr = re.sub(r"\bcos\(", "np.cos(", expr)
        expr = re.sub(r"\btan\(", "np.tan(", expr)
        expr = re.sub(r"\basin\(", "np.arcsin(", expr)
        expr = re.sub(r"\bacos\(", "np.arccos(", expr)
        expr = re.sub(r"\batan\(", "np.arctan(", expr)
        expr = re.sub(r"\bsinh\(", "np.sinh(", expr)
        expr = re.sub(r"\bcosh\(", "np.cosh(", expr)
        expr = re.sub(r"\btanh\(", "np.tanh(", expr)

        # Replace standalone 'e' (Euler's constant) but NOT part of scientific notation (1e3)
        # We consider 'e' as standalone if not adjacent to digit or dot
        # pattern: (?<![0-9.])e(?![0-9.])  -> replace with np.e
        expr = re.sub(r"(?<![0-9.])e(?![0-9.])", "np.e", expr)

        # Also allow user to type 'pi' as literal
        expr = re.sub(r"(?<![A-Za-z0-9_])pi(?![A-Za-z0-9_])", "np.pi", expr)

        # Replace percent sign: e.g., 50% -> (50/100)
        expr = re.sub(r"([0-9\.]+)%", r"(\1/100)", expr)

        # Evaluate using numpy namespace - restrict builtins
        # Important: eval is potentially dangerous; using limited globals
        allowed_globals = {"np": np, "__builtins__": {}}
        result = eval(expr, allowed_globals, {})

        # If result is numpy array or similar, convert to python
        if isinstance(result, (np.ndarray,)):
            result = result.tolist()

        # Avoid very long floats; round
        if isinstance(result, (float, np.floating)):
            # show up to 10 decimal places, strip trailing zeros
            formatted = f"{round(float(result), 10):.10f}".rstrip("0").rstrip(".")
            return formatted
        else:
            return str(result)
    except Exception:
        return "Error"

# Main calculator UI container
st.markdown("<div class='calculator'>", unsafe_allow_html=True)

# Display the current expression in a styled screen (read-only)
st.markdown(f"<div class='screen'>{st.session_state['input_box']}</div>", unsafe_allow_html=True)

# Text input bound to input_box — keeps cursor behaviour smooth.
# Users can type expressions directly here (numbers, parentheses, scientific notation like 1e3).
user_value = st.text_input("Type expression (or edit) and press Calculate:", key="input_box")

# Buttons layout definition
buttons = [
    ["7", "8", "9", "/", "sin("],
    ["4", "5", "6", "*", "cos("],
    ["1", "2", "3", "-", "tan("],
    ["0", ".", "(", ")", "log("],
    ["√", "π", "e", "^", "exp("],
    ["C", "DEL", "+", "=", "Ans"]
]

# Render buttons in grid (5 columns)
for row_idx, row in enumerate(buttons):
    cols = st.columns(5)
    for col_idx, label in enumerate(row):
        btn_key = f"btn_{row_idx}_{col_idx}"
        # style class selectors via unsafe html class injection (Streamlit doesn't allow class on button)
        # we will apply classes by matching labels for styling via CSS tags (.op or .func)
        clicked = cols[col_idx].button(label, key=btn_key)
        if clicked:
            # Button behaviours
            if label == "C":
                st.session_state["input_box"] = ""
            elif label == "DEL":
                # Delete last character
                st.session_state["input_box"] = st.session_state["input_box"][:-1]
            elif label == "=":
                # Calculate current expression
                expr = st.session_state["input_box"]
                result = calculate(expr)
                st.session_state["input_box"] = result
                if result != "Error":
                    st.session_state["last_result"] = result
            elif label == "Ans":
                st.session_state["input_box"] += st.session_state.get("last_result", "")
            else:
                # Append button label to input_box. For constants, we insert characters that are easy
                # to distinguish (π, √ and e are fine) — calculate() will map them properly.
                st.session_state["input_box"] += label

st.markdown("</div>", unsafe_allow_html=True)

# Calculate button (explicit) so pressing it does not require clicking '=' only
if st.button("Calculate"):
    expr = st.session_state["input_box"]
    res = calculate(expr)
    st.session_state["input_box"] = res
    if res != "Error":
        st.session_state["last_result"] = res

# Helpful notes and small history
st.markdown(
    """
    <div style='text-align:center; color:#dfe9f3; margin-top:10px; font-size:0.92rem;'>
      <small>
        Tips: use parentheses `(` `)`. Use `1e3` for scientific notation (this is preserved).<br>
        Buttons insert function names with `(` where appropriate (e.g. `sin(`) — remember to close `)`.
      </small>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
