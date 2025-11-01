# app.py
import streamlit as st
import numpy as np

# Page configuration
st.set_page_config(page_title="Scientific Calculator", layout="centered")

# --- Custom CSS for Casio look and effects ---
st.markdown("""
<style>
body, .main {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    font-family: 'Courier New', monospace;
}
.calculator {
    background-color: #1e2b38;
    border-radius: 20px;
    padding: 20px;
    width: 360px;
    margin: 40px auto;
    box-shadow: 0px 0px 25px rgba(0,0,0,0.6);
    transition: transform 0.3s ease-in-out;
}
.calculator:hover {
    transform: scale(1.02);
}
.screen {
    background-color: #b0ffc0;
    color: black;
    border-radius: 10px;
    padding: 15px;
    text-align: right;
    font-size: 1.7em;
    margin-bottom: 15px;
    height: 55px;
    overflow-x: auto;
}
.stButton>button {
    background: linear-gradient(to bottom, #34495e, #2c3e50);
    color: white;
    border: none;
    border-radius: 10px;
    height: 50px;
    width: 100%;
    font-size: 1.1em;
    font-weight: bold;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    background: linear-gradient(to bottom, #5dade2, #3498db);
    transform: translateY(-3px);
}
.title {
    text-align: center;
    color: #ecf0f1;
    text-shadow: 1px 1px 5px #000000;
}
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("<h1 class='title'>🧮 Casio 991-Inspired Calculator</h1>", unsafe_allow_html=True)

# --- Initialize session state ---
if "expression" not in st.session_state:
    st.session_state.expression = ""
if "last_result" not in st.session_state:
    st.session_state.last_result = ""

# --- Display screen ---
st.markdown("<div class='calculator'>", unsafe_allow_html=True)
st.markdown(f"<div class='screen'>{st.session_state.expression}</div>", unsafe_allow_html=True)

# --- Calculator Buttons Layout ---
buttons = [
    ["7", "8", "9", "/", "sin"],
    ["4", "5", "6", "*", "cos"],
    ["1", "2", "3", "-", "tan"],
    ["0", ".", "(", ")", "log"],
    ["√", "π", "e", "^", "exp"],
    ["C", "DEL", "+", "=", "Ans"]
]

# --- Calculation Function ---
def calculate(expression):
    try:
        expr = expression.replace("^", "**").replace("√", "np.sqrt")
        expr = expr.replace("π", "np.pi").replace("e", "np.e")
        expr = expr.replace("sin", "np.sin").replace("cos", "np.cos").replace("tan", "np.tan")
        expr = expr.replace("log", "np.log10").replace("exp", "np.exp")
        result = eval(expr)
        if isinstance(result, complex):
            return "Error"
        return str(round(result, 10))
    except Exception:
        return "Error"

# --- Button Grid Rendering ---
for i, row in enumerate(buttons):
    cols = st.columns(5)
    for j, btn in enumerate(row):
        if cols[j].button(btn, key=f"{i}{j}"):
            if btn == "C":
                st.session_state.expression = ""
            elif btn == "DEL":
                st.session_state.expression = st.session_state.expression[:-1]
            elif btn == "=":
                result = calculate(st.session_state.expression)
                st.session_state.expression = result
                if result != "Error":
                    st.session_state.last_result = result
            elif btn == "Ans":
                st.session_state.expression += st.session_state.last_result
            else:
                st.session_state.expression += btn

st.markdown("</div>", unsafe_allow_html=True)

# --- Keyboard Input Support ---
user_input = st.text_input("Or type expression below:", value=st.session_state.expression)
if user_input != st.session_state.expression:
    st.session_state.expression = user_input

if st.button("Calculate (Enter)"):
    result = calculate(st.session_state.expression)
    st.session_state.expression = result
    if result != "Error":
        st.session_state.last_result = result

# --- Footer ---
st.markdown(
    "<p style='text-align:center; color:#bdc3c7;'>Made with ❤️ using Streamlit | Casio 991 Replica</p>",
    unsafe_allow_html=True
)
