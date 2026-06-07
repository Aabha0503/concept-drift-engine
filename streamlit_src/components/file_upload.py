import streamlit as st


def render_file_upload():
    """Render the dataset upload control."""
    st.header("📁 Upload Dataset")
    st.caption("CSV format expected: one timestamp column and one value column.")

    return st.file_uploader(
        "Upload your time-series CSV file",
        type=["csv"]
    )
