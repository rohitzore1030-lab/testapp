import streamlit as st
import math
import ast
import operator

# ================= SAFE EVALUATOR =================
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}

SAFE_NAMES = {
    # constants
    "pi": math.pi,
    "e": math.e,
    # functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
}

def safe_eval(expr: str):
    if not expr or expr.strip() == "":
        return ""
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")

    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return "Syntax Error"

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        elif isinstance(n, ast.Num):  # for old Python versions
            return n.n
        elif isinstance(n, ast.Constant):  # for new Python versions
            return n.value
        elif isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            return OPERATORS[type(n.op)](left, right)
        elif isinstance(n, ast.UnaryOp):
            operand = _eval(n.operand)
            return OPERATORS[type(n.op)](operand)
        elif isinstance(n, ast.Call):
            func = n.func.id
            args = [_eval(a) for a in n.args]
            if func in SAFE_NAMES:
                return SAFE_NAMES[func](*args)
            else:
                raise ValueError(f"Function {func} not allowed")
        elif isinstance(n, ast.Name):
            if n.id in SAFE_NAMES:
                return SAFE_NAMES[n.id]
            else:
                raise ValueError(f"Name {n.id} not allowed")
        else:
            raise ValueError("Invalid expression")

    try:
        result = _eval(node)
        if isinstance(result, float) and abs(result - int(result)) < 1e-12:
            result = int(result)
        return result
    except Exception:
        return "Math Error"


# ================= STREAMLIT UI =================
st.set_page_config(page_title="Scientific Calculator", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0f172a, #1e293b);
        color: #e2e8f0;
        font-family: 'Segoe UI', sans-serif;
    }
    .title {
        text-align: center;
        color: #e2e8f0;
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .display {
        background-color: #1e293b;
        color: #e2e8f0;
        font-size: 24px;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
    }
    .button {
        width: 100%;
        height: 60px;
        font-size: 20px;
        border-radius: 8px;
        margin: 4px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>Casio fx-Style Scientific Calculator</div>", unsafe_allow_html=True)

# --- Display fields ---
if "expr" not in st.session_state:
    st.session_state.expr = ""
if "result" not in st.session_state:
    st.session_state.result = ""

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Input**")
    expr_input = st.text_input("", st.session_state.expr, key="input", label_visibility="collapsed")
with col2:
    st.markdown("**Output**")
    st.text_input("", st.session_state.result, key="output", label_visibility="collapsed")

# --- Button layout ---
buttons = [
    ["7", "8", "9", "/", "sqrt("],
    ["4", "5", "6", "*", "log10("],
    ["1", "2", "3", "-", "sin("],
    ["0", ".", "(", ")", "cos("],
    ["^", "exp(", "tan(", "pi", "C"],
    ["=", "DEL"],
]

def click(btn):
    if btn == "=":
        res = safe_eval(st.session_state.expr)
        st.session_state.result = str(res)
    elif btn == "C":
        st.session_state.expr = ""
        st.session_state.result = ""
    elif btn == "DEL":
        st.session_state.expr = st.session_state.expr[:-1]
    else:
        st.session_state.expr += btn

# --- Render buttons ---
for row in buttons:
    cols = st.columns(len(row))
    for i, b in enumerate(row):
        if cols[i].button(b, key=f"btn_{b}", use_container_width=True):
            click(b)

# --- Update display ---
st.session_state.expr = st.session_state.expr
st.rerun()
