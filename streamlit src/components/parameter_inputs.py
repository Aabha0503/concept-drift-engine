import streamlit as st


def render_parameter_inputs():
    """Render analysis controls and return selected values."""
    st.header("⚙️ Configuration")
    st.caption("The default settings are tuned for quick demos. Adjust them only when needed.")

    col1, col2, col3 = st.columns(3)

    with col1:
        window_size = st.number_input("Window Size", min_value=1, value=50)

    with col2:
        step_size = st.number_input("Step Size", min_value=1, value=10)

    with col3:
        min_duration = st.number_input("Min Duration (minutes)", min_value=1, value=60)

    with st.expander("Advanced Settings"):
        reference_windows = st.number_input("Reference Windows (K)", min_value=1, value=5)
        alpha = st.number_input("Alpha (Mean Threshold)", min_value=0.1, value=2.0)
        beta = st.number_input("Beta (Median Threshold)", min_value=0.1, value=1.5)

    return {
        "window_size": int(window_size),
        "step_size": int(step_size),
        "min_duration_minutes": int(min_duration),
        "K": int(reference_windows),
        "alpha": float(alpha),
        "beta": float(beta),
    }
