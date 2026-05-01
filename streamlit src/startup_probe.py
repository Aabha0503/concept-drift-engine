import streamlit as st


st.set_page_config(page_title="Streamlit Probe", layout="wide")

st.title("Streamlit Startup Probe")
st.success("If you can see this page, Streamlit itself is running correctly.")
st.write("This file does not import the drift detection app or matplotlib.")
