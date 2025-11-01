import streamlit as st
import math
import ast
import operator

# --------------------------
# SAFE EVALUATOR (AST-based)
# --------------------------
# Allowed operators map
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}

# Allowed names (math functions + constants)
SAFE_NAMES = {
    # constants
    "pi": math.pi,
    "e": math.e,
    # functions - basic
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": lambda x, base=math.e: math.log(x, base) if base != math.e else math.log(x),
    "ln": math.log,
    "log10": math.log10,
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "fact": math.factorial,
    "deg": math.degrees,
    "rad": math.radians,
    # hyperbolic inverse helpers
    "asinh": math.asinh if hasattr(math, "asinh") else None,
    "acosh": math.acosh if hasattr(math, "acosh") else None,
    "atanh": math.atanh if hasattr(math, "atanh") else None,
}

# Remove any None functions (for Python versions lacking them)
SAFE_NAMES = {k: v for k, v in SAFE_NAMES.items() if v is not None}

class SafeEvalError(Exception):
    pass

def safe_eval(expr: str):
    """
    Evaluate a mathematical expression safely using AST.
    Supports function calls listed in SAFE_NAMES and operators in OPERATORS.
    """
    if not expr or expr.strip() == "":
        return ""

    # Replace unicode characters sometimes pasted by users
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")

    try:
        node = ast.parse(expr, mode="eval")
    except Exception as e:
        raise SafeEvalError("Parse error")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        # numbers
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise SafeEvalError("Invalid constant")

        # For older Python, ast.Num:
        if hasattr(ast, "Num") and isinstance(node, ast.Num):
            return node.n

        # binary operations
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in OPERATORS:
                return OPERATORS[op_type](left, right)
            raise SafeEvalError("Unsupported binary operator")

        # unary operations
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type in OPERATORS:
                return OPERATORS[op_type](operand)
            raise SafeEvalError("Unsupported unary operator")

        # function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in SAFE_NAMES:
                    raise SafeEvalError(f"Function '{func_name}' not allowed")
                func = SAFE_NAMES[func_name]
                args = [_eval(a) for a in node.args]
                # keyword args support (basic)
                kwargs = {}
                for kw in getattr(node, "keywords", []):
                    kwargs[kw.arg] = _eval(kw.value)
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    raise SafeEvalError(str(e))
            else:
                raise SafeEvalError("Unsafe function call")
        # names (constants)
        if isinstance(node, ast.Name):
            if node.id in SAFE_NAMES:
                val = SAFE_NAMES[node.id]
                if callable(val):
                    # user typed a bare function name, that's not a value
                    raise SafeEvalError(f"'{node.id}' is a function, call it with ()")
                return val
            raise SafeEvalError(f"Name '{node.id}' not allowed")

        if isinstance(node, ast.Subscript):
            raise SafeEvalError("Subscript not allowed")

        raise SafeEvalError("Unsupported expression element")

    result = _eval(node)
    # convert floats that are near-int to int for display neatness
    if isinstance(result, float) and abs(result - round(result)) < 1e-12:
        result = round(result)
    return result

# --------------------------
# STREAMLIT UI
# --------------------------
st.set_page_config(page_title="Casio-like Scientific Calculator", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for look and equal-sized input/output
st.markdown(
    """
    <style>
    /* page background */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #111827 60%);
        color: #e6eef8;
        font-family: "Segoe UI", Roboto, Arial, sans-serif;
    }

    /* container card */
    .calc-card {
        background: linear-gradient(180deg, #1f2937 0%, #0b1220 100%);
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.6);
        border: 1px solid rgba(255,255,255,0.03);
    }

    /* big displays */
    .display-textarea > div > textarea {
        height: 96px !important;
        resize: none;
        font-size: 20px !important;
        background: linear-gradient(180deg, #111827, #0b1220) !important;
        color: #e6eef8 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        box-shadow: inset 0 -2px 8px rgba(0,0,0,0.6);
    }

    /* button style to resemble calculator keys */
    .key-btn button {
        border-radius: 10px;
        padding: 12px 10px;
        height: 52px;
        width: 100%;
        font-weight: 600;
        box-shadow: 0 4px 8px rgba(0,0,0,0.45);
        border: 1px solid rgba(255,255,255,0.03);
    }
    /* distinct color groups */
    .op { background: linear-gradient(180deg,#fb923c,#f97316); color: #06121a; }
    .func { background: linear-gradient(180deg,#94a3b8,#64748b); color: #fff; }
    .num { background: linear-gradient(180deg,#f8fafc,#e6eef8); color: #031022; }
    .eq { background: linear-gradient(180deg,#10b981,#059669); color: #fff; font-size:18px; font-weight:800; }

    /* reduce gap on small screens */
    @media (max-width: 768px) {
        .display-textarea > div > textarea { height: 72px !important; font-size:18px !important;}
        .key-btn button { height: 44px; padding:8px 6px; font-size:14px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title header
st.markdown("<h1 style='color:#e6eef8; margin-bottom:6px'>Investment Calculator ─ Casio fx-style</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#9aa7bf; margin-top:0;'>Scientific calculator styled like Casio fx series — powered by Streamlit</p>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])
with col1:
    with st.container():
        st.markdown("<div class='calc-card'>", unsafe_allow_html=True)

        # Initialize expression state
        if "expr" not in st.session_state:
            st.session_state.expr = ""
        if "result" not in st.session_state:
            st.session_state.result = ""

        # Display input and output side-by-side (same size via CSS)
        st.markdown("<div style='display:flex; gap:12px;'>", unsafe_allow_html=True)

        # Input box (left)
        st.markdown("<div style='flex:1'>", unsafe_allow_html=True)
        st.markdown("<label style='color:#9aa7bf; font-weight:600'>Input</label>", unsafe_allow_html=True)
        input_text = st.text_area("", value=st.session_state.expr, key="input_display", placeholder="Enter expression (e.g. sin(pi/2) + 3^2 )", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

        # Output box (right) - same size due to CSS targeting textarea height
        st.markdown("<div style='flex:1'>", unsafe_allow_html=True)
        st.markdown("<label style='color:#9aa7bf; font-weight:600'>Output</label>", unsafe_allow_html=True)
        output_text =_
