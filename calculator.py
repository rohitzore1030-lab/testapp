# app.py
import streamlit as st

# Page configuration
st.set_page_config(page_title="Normal Calculator", layout="centered")

# Title and styling
st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(to right, #00c6ff, #0072ff);
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    h1 {
        text-align: center;
        color: white;
        text-shadow: 2px 2px 5px #00000050;
    }
    .stButton>button {
        background-color: #ffffff;
        color: #0072ff;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-size: 1.1em;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #e0e0e0;
        color: #000;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Heading
st.title("🧮 Normal Calculator")

# Input fields
num1 = st.number_input("Enter first number:", step=1.0, format="%.6f")
num2 = st.number_input("Enter second number:", step=1.0, format="%.6f")

# Select operation
operation = st.selectbox("Select Operation", ["Addition", "Subtraction", "Multiplication", "Division"])

# Calculate on button click
if st.button("Calculate"):
    if operation == "Addition":
        result = num1 + num2
        st.success(f"✅ Result: {num1} + {num2} = {result}")
    elif operation == "Subtraction":
        result = num1 - num2
        st.success(f"✅ Result: {num1} - {num2} = {result}")
    elif operation == "Multiplication":
        result = num1 * num2
        st.success(f"✅ Result: {num1} × {num2} = {result}")
    elif operation == "Division":
        if num2 == 0:
            st.error("❌ Error: Division by zero is not allowed!")
        else:
            result = num1 / num2
            st.success(f"✅ Result: {num1} ÷ {num2} = {result}")

# Footer
st.markdown(
    """
    <hr style='border: 1px solid white;'>
    <p style='text-align: center; color: white;'>Made with ❤️ using Streamlit</p>
    """,
    unsafe_allow_html=True
)
