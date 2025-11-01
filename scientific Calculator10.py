"""
scientific_calculator.py
A single-file Tkinter scientific calculator inspired by Casio fx-series.
Safe expression evaluation using AST (no eval).
Works in IDLE / standard Python.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import ast
import operator

# ---------------- Safe evaluator (AST-based) ----------------
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

# Allowed functions and constants exposed to the user
SAFE_NAMES = {
    # constants
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau if hasattr(math, "tau") else 2 * math.pi,
    # trig
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    # hyperbolic
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "asinh": math.asinh if hasattr(math, "asinh") else None,
    "acosh": math.acosh if hasattr(math, "acosh") else None,
    "atanh": math.atanh if hasattr(math, "atanh") else None,
    # logs & roots
    "log": lambda x, base=math.e: math.log(x, base),
    "ln": math.log,
    "log10": math.log10,
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1.0 / 3.0),
    # misc
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "fact": math.factorial,
    "deg": math.degrees,
    "rad": math.radians,
    # combinatorics
    "comb": math.comb if hasattr(math, "comb") else None,
    "perm": math.perm if hasattr(math, "perm") else None,
}

# remove None entries for older Python versions
SAFE_NAMES = {k: v for k, v in SAFE_NAMES.items() if v is not None}

class SafeEvalError(Exception):
    pass

def safe_eval(expr: str, extra_names=None):
    """
    Safely evaluate a math expression string.
    Supports numeric literals, + - * / ** % // unary ops, function calls from SAFE_NAMES,
    and parentheses. Replaces common unicode operators.
    """
    if not expr or expr.strip() == "":
        raise SafeEvalError("Empty expression")

    # clean some user input
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-")
    # allow ANS constant injected by caller via extra_names

    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        raise SafeEvalError("Syntax error")

    names = dict(SAFE_NAMES)
    if extra_names:
        names.update(extra_names)

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            else:
                raise SafeEvalError("Invalid literal")

        # numbers in older AST
        if hasattr(ast, "Num") and isinstance(node, ast.Num):
            return node.n

        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in OPERATORS:
                try:
                    return OPERATORS[op_type](left, right)
                except Exception as e:
                    raise SafeEvalError(str(e))
            raise SafeEvalError("Unsupported operator")

        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type in OPERATORS:
                return OPERATORS[op_type](operand)
            raise SafeEvalError("Unsupported unary operator")

        if isinstance(node, ast.Call):
            # only allow simple function names
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                if fname not in names:
                    raise SafeEvalError(f"Function '{fname}' not allowed")
                func = names[fname]
                args = [_eval(a) for a in node.args]
                kwargs = {}
                for kw in getattr(node, "keywords", []):
                    if kw.arg is None:
                        raise SafeEvalError("Invalid keyword")
                    kwargs[kw.arg] = _eval(kw.value)
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    raise SafeEvalError(f"Function error: {e}")
            else:
                raise SafeEvalError("Unsafe function call")

        if isinstance(node, ast.Name):
            if node.id in names:
                val = names[node.id]
                if callable(val):
                    raise SafeEvalError(f"'{node.id}' is a function; call it with ()")
                return val
            raise SafeEvalError(f"Unknown name: {node.id}")

        raise SafeEvalError("Unsupported expression element")

    result = _eval(node)
    # format small floats that are near ints
    if isinstance(result, float) and abs(result - round(result)) < 1e-12:
        result = int(round(result))
    return result

# ---------------- Tkinter UI ----------------
class SciCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scientific Calculator — Casio-style")
        self.resizable(False, False)
        # Appearance
        self.config(bg="#0a0f1a")
        self['padx'] = 12
        self['pady'] = 12

        # state
        self.ans = None  # last answer
        self.expression = tk.StringVar()
        self.output = tk.StringVar()

        # fonts and sizes
        self.display_font = ("Consolas", 18)
        self.button_font = ("Segoe UI", 11, "bold")

        # Build UI
        self._build_display()
        self._build_buttons()
        self._bind_keys()

    def _build_display(self):
        # Frame to hold displays
        disp_frame = tk.Frame(self, bg="#0a0f1a")
        disp_frame.grid(row=0, column=0, sticky="ew", columnspan=6, pady=(0,10))

        # Input and Output entries of equal visual size
        # We'll use two Entry widgets with same width and font so they appear same size.
        entry_width = 28
        self.inp = tk.Entry(disp_frame, textvariable=self.expression, font=self.display_font,
                            width=entry_width, justify="right", bd=0, relief="ridge", highlightthickness=2)
        self.inp.grid(row=0, column=0, columnspan=6, sticky="we", ipady=10, pady=(0,6))
        self.inp.configure(highlightbackground="#1f2937", highlightcolor="#64ffda", bg="#071024", fg="#e6eef8", insertbackground="#e6eef8")

        self.out = tk.Entry(disp_frame, textvariable=self.output, font=self.display_font,
                            width=entry_width, justify="right", bd=0, relief="ridge", state="readonly")
        self.out.grid(row=1, column=0, columnspan=6, sticky="we", ipady=10)
        self.out.configure(readonlybackground="#071024", fg="#aee6c5")

    def _add_button(self, text, row, col, width=1, colspan=1, style=None, command=None):
        btn = tk.Button(self, text=text, font=self.button_font, bd=0,
                        fg="#06202b" if style == "num" else "#f8fafc",
                        bg="#e6eef8" if style == "num" else ("#f97316" if style == "op" else "#6b7280"),
                        activebackground="#111827", activeforeground="#ffffff",
                        width=8*width, height=2, command=command or (lambda t=text: self._on_key(t)))
        btn.grid(row=row, column=col, columnspan=colspan, padx=4, pady=4, sticky="nsew")
        return btn

    def _build_buttons(self):
        # Row index offset after display (display used rows 0-1)
        r = 2

        # First row (functions)
        funcs = [
            ("(",  r, 0), (")", r, 1), ("DEL", r, 2), ("AC", r, 3), ("Ans", r, 4), ("=", r, 5)
        ]
        for txt, rr, cc in funcs:
            if txt == "=":
                self._add_button(txt, rr, cc, style="op", command=self._calculate)
            elif txt == "DEL":
                self._add_button(txt, rr, cc, style="func", command=self._backspace)
            elif txt == "AC":
                self._add_button(txt, rr, cc, style="func", command=self._clear_all)
            elif txt == "Ans":
                self._add_button(txt, rr, cc, style="func", command=self._use_ans)
            else:
                self._add_button(txt, rr, cc, style="func")

        # Scientific and numeric rows
        button_rows = [
            ["sin(", "cos(", "tan(", "ln(", "log(", "sqrt("],
            ["pi", "e", "x^y", "fact(", "mod", "EXP"],
            ["7", "8", "9", "/", "floor(", "ceil("],
            ["4", "5", "6", "*", "(", ")"],
            ["1", "2", "3", "-", "abs(", "round("],
            ["0", ".", "+", "%", "rad(", "deg("],
        ]
        r_start = 3
        for i, row in enumerate(button_rows):
            for j, label in enumerate(row):
                text = label
                # special mapping
                if label == "x^y":
                    cmd = lambda: self._on_key("**")
                    style = "op"
                elif label == "EXP":
                    cmd = lambda: self._on_key("e")
                    style = "op"
                elif label == "mod":
                    cmd = lambda: self._on_key("%")
                    style = "op"
                elif label in ("/", "*", "-", "+", "%"):
                    cmd = None
                    style = "op"
                elif label in ("0","1","2","3","4","5","6","7","8","9","."):
                    cmd = None
                    style = "num"
                else:
                    cmd = None
                    style = "func"
                self._add_button(text, r_start + i, j, style=style, command=cmd)

        # make grid expand nicely (even sizing)
        for c in range(6):
            self.grid_columnconfigure(c, weight=1)

    # --------- Button actions ----------
    def _on_key(self, key_text):
        current = self.expression.get()
        # append
        self.expression.set(current + key_text)
        self.output.set("")  # clear temporary output until = pressed

    def _backspace(self):
        s = self.expression.get()
        self.expression.set(s[:-1])

    def _clear_all(self):
        self.expression.set("")
        self.output.set("")

    def _use_ans(self):
        if self.ans is not None:
            # append previous answer numeric representation
            self.expression.set(self.expression.get() + str(self.ans))

    def _calculate(self, *_):
        expr = self.expression.get().strip()
        if not expr:
            return
        try:
            # supply Ans if present
            extra = {}
            if self.ans is not None:
                extra["ANS"] = self.ans
                extra["Ans"] = self.ans
            result = safe_eval(expr, extra_names=extra)
            self.ans = result
            self.output.set(str(result))
        except SafeEvalError as e:
            self.output.set("Error: " + str(e))
        except Exception as e:
            self.output.set("Error")

    # --------- Keyboard support ----------
    def _bind_keys(self):
        # enter -> equal
        self.bind("<Return>", lambda e: self._calculate())
        # backspace
        self.bind("<BackSpace>", lambda e: self._backspace())
        # escape -> clear
        self.bind("<Escape>", lambda e: self._clear_all())
        # allow typical characters
        allowed = "0123456789.+-*/%^()"
        def on_key(e):
            if e.char in allowed:
                self.expression.set(self.expression.get() + e.char)
            elif e.char == "\r":
                self._calculate()
            # allow 'p' => pi shortcut
            elif e.char.lower() == "p":
                self.expression.set(self.expression.get() + "pi")
            elif e.char.lower() == "e":
                # be careful: 'e' could be used for exp or Euler's number; keep as 'e'
                self.expression.set(self.expression.get() + "e")
            # ignore others
        self.bind("<Key>", on_key)

# ---------------- Run App ----------------
def main():
    app = SciCalculator()
    # center the window
    app.update_idletasks()
    width = app.winfo_width()
    height = app.winfo_height()
    x = (app.winfo_screenwidth() // 2) - (width // 2)
    y = (app.winfo_screenheight() // 3) - (height // 3)
    app.geometry(f"+{x}+{y}")
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
