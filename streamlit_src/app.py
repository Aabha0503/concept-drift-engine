import sys
import traceback
from datetime import datetime, timedelta
from math import pi, sin
from pathlib import Path

import pandas as pd
import streamlit as st

from components.file_upload import render_file_upload
from components.parameter_inputs import render_parameter_inputs
from app_utils.file_handler import save_uploaded_file


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent / "python src"
DEMO_DATA_DIR = CURRENT_DIR / "demo_data"

DEMO_SCENARIOS = {
    "Upload custom CSV": {
        "path": None,
        "summary": "Use your own timestamp,value CSV file.",
        "expectation": "Best for testing the system with a personal dataset.",
    },
    "Sudden anomaly (spike)": {
        "path": DEMO_DATA_DIR / "sudden_anomaly_spike.csv",
        "summary": "Mostly stable daily behavior with one sharp spike.",
        "expectation": "The dashboard should highlight a short-lived anomaly.",
    },
    "Concept drift (gradual change)": {
        "path": DEMO_DATA_DIR / "gradual_concept_drift.csv",
        "summary": "A metric slowly moves from one operating level to another.",
        "expectation": "The dashboard should mark a longer change as concept drift.",
    },
    "Stable data (no issues)": {
        "path": DEMO_DATA_DIR / "stable_no_issues.csv",
        "summary": "Predictable behavior with small natural variation.",
        "expectation": "The dashboard should remain calm with no major events.",
    },
}

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def configure_page():
    st.set_page_config(
        page_title="Real-Time Concept Drift Monitoring System",
        layout="wide"
    )
    st.markdown(
        """
        <style>
            :root {
                --card-bg: #1E1E2F;
                --card-border: #34344A;
                --primary-text: #FFFFFF;
                --secondary-text: #B0B0B0;
                --accent: #4F8BFF;
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
            }
            .block-container,
            .block-container p,
            .block-container li,
            .block-container label,
            .block-container span {
                color: var(--primary-text);
            }
            .block-container small,
            .block-container em,
            .block-container .stCaption,
            .block-container [data-testid="stCaptionContainer"] {
                color: var(--secondary-text);
            }
            h1, h2, h3, h4, h5, h6,
            .block-container strong {
                color: var(--primary-text);
            }
            div[data-testid="stMetric"] {
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                padding: 1rem;
                color: var(--primary-text);
            }
            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
                color: var(--secondary-text);
            }
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: var(--primary-text);
            }
            div[data-testid="stExpander"] details {
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
            }
            div[data-testid="stExpander"] summary,
            div[data-testid="stExpander"] p {
                color: var(--primary-text);
            }
            .demo-note {
                border: 1px solid var(--card-border);
                border-left: 4px solid var(--accent);
                background: var(--card-bg);
                color: var(--primary-text);
                padding: 0.85rem 1rem;
                border-radius: 6px;
                margin: 0.75rem 0 1.25rem 0;
            }
            .demo-note strong {
                color: var(--primary-text);
            }
            .demo-note .secondary-text {
                color: var(--secondary-text);
            }
        </style>
        """,
        unsafe_allow_html=True
    )


def initialize_session_state():
    defaults = {
        "analysis_result": None,
        "live_running": False,
        "live_logs": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_demo_datasets():
    """Create deterministic demo CSVs without changing detection logic."""
    DEMO_DATA_DIR.mkdir(exist_ok=True)
    start_time = datetime(2024, 1, 1)
    rows = 360
    timestamps = [start_time + timedelta(minutes=5 * index) for index in range(rows)]

    stable_values = [
        50 + 2 * sin(index * 2 * pi / 48)
        for index in range(rows)
    ]

    spike_values = stable_values.copy()
    spike_values[180] = 88

    drift_values = []
    for index in range(rows):
        seasonal = 0.4 * sin(index * 2 * pi / 48)
        if index < 120:
            baseline = 50
        elif index < 170:
            baseline = 50 + ((index - 120) / 50) * 25
        else:
            baseline = 75
        drift_values.append(baseline + seasonal)

    demo_frames = {
        "stable_no_issues.csv": stable_values,
        "sudden_anomaly_spike.csv": spike_values,
        "gradual_concept_drift.csv": drift_values,
    }

    for filename, values in demo_frames.items():
        path = DEMO_DATA_DIR / filename
        pd.DataFrame({
            "timestamp": timestamps,
            "value": [round(value, 3) for value in values],
        }).to_csv(path, index=False)


def render_intro():
    st.title("📊 Real-Time Concept Drift Monitoring System")
    st.subheader("Explainable drift and anomaly detection for time-series data")
    st.write(
        "Choose a ready-made demo scenario or upload your own CSV, then run the "
        "analysis to see alerts, graphs, explanations, and live monitoring."
    )


def render_dashboard_guide():
    st.header("🧠 How to Read This Dashboard")

    with st.expander("Open the guided explanation", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**📈 Concept drift**")
            st.write(
                "A longer-term change in the data pattern. It can mean the model "
                "was trained on behavior that no longer represents the current system."
            )

        with col2:
            st.markdown("**⚡ Anomaly**")
            st.write(
                "A sudden unusual point or short event. It may be a spike, outage, "
                "bad input, or one-time operational incident."
            )

        with col3:
            st.markdown("**🎨 Graph colors**")
            st.write(
                "Blue is normal data, red shaded regions are concept drift, and "
                "orange markers are anomalies."
            )


def render_demo_selector():
    create_demo_datasets()
    st.header("📊 Demo Scenario")

    selected = st.selectbox(
        "Select a scenario",
        list(DEMO_SCENARIOS.keys()),
        index=1,
        help="Use a predefined scenario for demos, or switch to a custom CSV upload."
    )
    scenario = DEMO_SCENARIOS[selected]

    st.markdown(
        (
            "<div class='demo-note'>"
            f"<strong>{selected}</strong><br>"
            f"<span class='secondary-text'>{scenario['summary']}</span><br>"
            f"<span class='secondary-text'>{scenario['expectation']}</span>"
            "</div>"
        ),
        unsafe_allow_html=True
    )

    return selected, scenario


def resolve_analysis_file(uploaded_file, selected_scenario, scenario):
    if selected_scenario == "Upload custom CSV":
        if uploaded_file is None:
            st.error("Please upload a CSV file first")
            return None

        file_path = save_uploaded_file(uploaded_file)
        st.success("File saved successfully")
        return file_path

    return scenario["path"]


def run_analysis(file_path, parameters):
    from core.pipeline import run_pipeline

    return run_pipeline(
        csv_path=str(file_path),
        window_size=parameters["window_size"],
        step_size=parameters["step_size"],
        K=parameters["K"],
        min_duration_minutes=parameters["min_duration_minutes"],
        alpha=parameters["alpha"],
        beta=parameters["beta"],
    )


def render_analysis_results(result):
    from components.visualization import show_analysis_results

    show_analysis_results(result)


def main():
    configure_page()
    initialize_session_state()
    render_intro()
    render_dashboard_guide()

    selected_scenario, scenario = render_demo_selector()
    uploaded_file = None

    if st.session_state.get("selected_scenario") != selected_scenario:
        st.session_state.selected_scenario = selected_scenario
        st.session_state.analysis_result = None
        st.session_state.live_running = False
        st.session_state.live_logs = []

    if selected_scenario == "Upload custom CSV":
        uploaded_file = render_file_upload()

        if uploaded_file is not None:
            st.success(f"File uploaded successfully: {uploaded_file.name}")

    parameters = render_parameter_inputs()

    st.header("⚡ Run Analysis")
    st.caption("Start here during a demo: select a scenario, keep the defaults, and click Analyze.")

    if st.button("Analyze", type="primary"):
        try:
            file_path = resolve_analysis_file(uploaded_file, selected_scenario, scenario)
            if file_path is None:
                return

            result = run_analysis(file_path, parameters)
            st.session_state.analysis_result = result
            st.session_state.live_running = False
            st.session_state.live_logs = []
            st.success(f"Analysis completed for: {selected_scenario}")
        except Exception as error:
            st.error(f"Analysis failed: {error}")
            with st.expander("Debug details"):
                st.code(traceback.format_exc())

    if st.session_state.analysis_result is not None:
        render_analysis_results(st.session_state.analysis_result)


if __name__ == "__main__":
    main()
