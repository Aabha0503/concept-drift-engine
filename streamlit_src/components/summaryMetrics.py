import pandas as pd
import streamlit as st


def _event_deviation(event):
    for key in ("deviation", "z_score", "score", "impact"):
        value = event.get(key)
        if value is not None:
            return abs(float(value))

    root_causes = event.get("root_causes", [])
    if root_causes:
        return max(abs(float(cause.get("impact", 0))) for cause in root_causes)

    return abs(float(event.get("value", 0)))


def _peak_occurrence_time(events):
    if not events:
        return "No events"

    hours = [pd.to_datetime(event.get("start_time")).hour for event in events]
    peak_hour = max(set(hours), key=hours.count)
    return f"{peak_hour:02d}:00-{peak_hour:02d}:59"


def _frequency_pattern(anomalies):
    if not anomalies:
        return "No anomaly pattern"

    event_times = sorted(pd.to_datetime(event.get("start_time")) for event in anomalies)
    if len(event_times) == 1:
        return "Single isolated anomaly"

    midpoint = event_times[0] + ((event_times[-1] - event_times[0]) / 2)
    early = sum(1 for event_time in event_times if event_time <= midpoint)
    later = len(event_times) - early

    if later > early:
        return "Increasing later"
    if later < early:
        return "Higher earlier"
    return "Evenly distributed"


def show_metrics(result):
    st.subheader("Summary Metrics")

    drifts = result.get("drifts", [])
    point_anomalies = result.get("anomalies", [])
    all_events = drifts + point_anomalies

    concept_drifts = sum(1 for drift in drifts if drift.get("label") == "CONCEPT_DRIFT")
    classifier_anomalies = [
        drift for drift in drifts if drift.get("label") == "ANOMALY"
    ]
    anomalies = point_anomalies + classifier_anomalies
    max_deviation = max([_event_deviation(event) for event in anomalies], default=0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Events",
        len(all_events),
        help="Combined count of detected drift periods and anomaly events.",
    )
    col2.metric(
        "Concept Drifts",
        concept_drifts,
        help="Longer behavior changes that may indicate a shifted baseline.",
    )
    col3.metric(
        "Anomalies",
        len(anomalies),
        help="Sudden unusual points or short-lived spikes.",
    )
    col4.metric(
        "Max Deviation",
        f"{max_deviation:.2f}",
        help="Largest anomaly movement away from recent normal behavior.",
    )

    col1, col2 = st.columns(2)
    col1.metric(
        "Peak Occurrence Time",
        _peak_occurrence_time(anomalies),
        help="Hour of day where anomalies occur most often.",
    )
    col2.metric(
        "Frequency Pattern",
        _frequency_pattern(anomalies),
        help="Simple comparison of anomaly counts in the earlier vs later period.",
    )
