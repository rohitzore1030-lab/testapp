# app.py
import streamlit as st
import numpy as np

# Configure Streamlit page
st.set_page_config(page_title="Scientific Calculator", layout="centered")

# Custom CSS for Casio-style look
st.markdown("""
    <style>
    body, .main {
        background: radial-gradient(circle at center, #1b2735, #090a0f);
        color: white;
        font-family: 'Courier New', monospace;
    }
    .calculator {
        background-color: #2e3a4b;
        border-radius: 20px;
        padding: 20px;
        width: 350px;
        margin: 30px auto;
        box-shadow: 0px 0px 20px rgba(0,0,0,0.5);
    }
    .screen {
        background-color: #a4d3a2;
        color: black;
        border-radius: 8px;
        padding: 15px;
        text-align: right;
        font-size: 1.5em;
        margin-bottom: 10px;
        min-height: 50px;
    }
    .stButton>button {
        background-color: #394b63;
        color: white;
        border: none;
        border-radius: 8px;
        height: 45px;
        width: 70px;
        font-size: 1.1em;
        font-weight: bold;
        margin: 3px;
    }
    .stButton>button:hover {
        background-color: #627aad;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧮 Casio 991-Style Scientific Calculator")

# Initialize calculator state
if "expression" not in st.session_state:
    st.session_state.expression = ""

# Display screen
st.markdown("<div class='calculator'>", unsafe_allow_html=True)
st.markdown(f"<div class='screen'>{st.session_state.expression}</div>", unsafe_allow_html=True)

# Calculator button grid
buttons = [
    ["7", "8", "9", "/", "sin"],
    ["4", "5", "6", "*", "cos"],
    ["1", "2", "3", "-", "tan"],
    ["0", ".", "(", ")", "log"],
    ["√", "π", "e", "^", "exp"],
    ["C", "DEL", "+", "=", "Ans"]
]

# Button logic
def calculate(expression):
    try:
        expr = expression.replace("^", "**").replace("√", "np.sqrt").replace("π", "np.pi").replace("e", "np.e")
        expr = expr.replace("sin", "np.sin").replace("cos", "np.cos").replace("tan", "np.tan")
        expr = expr.replace("log", "np.log10").replace("exp", "np.exp")
        result = eval(expr)
        return str(round(result, 10))
    except Exception:
        return "Error"

# Button rendering
cols = st.columns(5)
for i, row in enumerate(buttons):
    cols = st.columns(5)
    for j, btn in enumerate(row):
        if cols[j].button(btn, key=f"{i}{j}"):
            if btn == "C":
                st.session_state.expression = ""
            elif btn == "DEL":
                st.session_state.expression = st.session_state.expression[:-1]
            elif btn == "=":
                st.session_state.expression = calculate(st.session_state.expression)
            elif btn == "Ans":
                # Keep last result if available
                if "last_result" in st.session_state:
                    st.session_state.expression += st.session_state.last_result
            else:
                st.session_state.expression += btn

# Store last result if valid
if st.session_state.expression not in ["", "Error"]:
    try:
        res = float(st.session_state.expression)
        st.session_state.last_result = str(res)
    except:
        pass

st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown(
    "<p style='text-align:center; color:gray; font-size:0.9em;'>Made with ❤️ using Streamlit | Casio-991 Replica</p>",
    unsafe_allow_html=True
)
