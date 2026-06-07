import streamlit as st

from core.decision_engine import build_decision_summary


def _event_name(label):
    if label == "CONCEPT_DRIFT":
        return "Concept Drift"
    if label == "ANOMALY":
        return "Anomaly"
    return "Normal"


def _drift_events(result):
    return [
        event
        for event in result.get("drifts", [])
        if event.get("label") == "CONCEPT_DRIFT"
    ]


def _anomaly_events(result):
    classifier_anomalies = [
        event
        for event in result.get("drifts", [])
        if event.get("label") == "ANOMALY"
    ]
    return result.get("anomalies", []) + classifier_anomalies


def _event_time(event):
    return str(event.get("start_time", "unknown time"))


def _critical_events(result):
    return [
        event
        for event in _drift_events(result) + _anomaly_events(result)
        if event.get("severity") == "HIGH"
    ]


def show_system_health_score(result):
    """Display an executive health strip for monitoring dashboards."""
    summary = build_decision_summary(result)
    health = summary["health"]
    drift_count = len(_drift_events(result))
    anomaly_count = len(_anomaly_events(result))
    critical_count = len(_critical_events(result))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "System Health",
        health,
        help="Overall rule-based status from drift severity, anomaly volume, and event duration.",
    )
    col2.metric(
        "Critical Events",
        critical_count,
        help="Events marked HIGH severity. These should be reviewed first.",
    )
    col3.metric(
        "Drift Events",
        drift_count,
        help="Longer behavior changes that may indicate the system baseline has shifted.",
    )
    col4.metric(
        "Anomalies",
        anomaly_count,
        help="Sudden unusual points or short-lived spikes.",
    )

    if health == "Critical":
        st.error("Critical status: review high-severity events and recent source or operational changes.")
    elif health == "Warning":
        st.warning("Warning status: behavior changed enough to require closer monitoring.")
    else:
        st.success("Stable status: no urgent drift or anomaly pressure detected.")


def show_realtime_alert_panel(result):
    """Show concise production-style alerts after an analysis run."""
    critical_events = _critical_events(result)
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)

    st.subheader("Alert Center")
    st.caption("Alerts are generated from simple rules and update after each analysis or live-monitor batch.")

    if critical_events:
        for event in critical_events[:3]:
            st.error(
                f"{_event_name(event.get('label'))} at {_event_time(event)} is HIGH severity. "
                "Review this period first."
            )
        if len(critical_events) > 3:
            st.caption(f"{len(critical_events) - 3} more critical event(s) available in the event details.")
        return

    if anomaly_events:
        st.warning(
            f"{len(anomaly_events)} anomaly event(s) detected. Validate the affected timestamps and source data."
        )
    if drift_events:
        st.warning(
            f"{len(drift_events)} drift event(s) detected. Compare the changed period with expected behavior."
        )
    if not anomaly_events and not drift_events:
        st.success("No active alerts. Current dataset looks stable.")


def show_why_it_matters(result):
    """Explain operational impact in plain language."""
    drift_count = len(_drift_events(result))
    anomaly_count = len(_anomaly_events(result))

    st.subheader("Why It Matters")
    if drift_count == 0 and anomaly_count == 0:
        st.info(
            "Stable behavior means the monitored process is behaving consistently, "
            "so teams can continue normal monitoring."
        )
        return

    if anomaly_count:
        st.info(
            "Anomalies can point to spikes, bad input, sensor issues, outages, or short-lived operational incidents."
        )
    if drift_count:
        st.info(
            "Concept drift means the normal pattern may have shifted. Thresholds, dashboards, and decisions based on older behavior may need review."
        )
    st.caption(
        "Use the quick focus buttons to narrow the dashboard before inspecting full details."
    )


def trigger_alert(event):
    """Show the right Streamlit alert for a detected event."""
    if event is None:
        st.success("System is normal. No active drift or anomaly detected.")
        return

    label = event.get("label", "UNKNOWN")
    severity = event.get("severity", "LOW")

    if label == "CONCEPT_DRIFT" and severity == "HIGH":
        st.error(
            "High severity concept drift detected. System behavior changed significantly.\n\n"
            "Recommended action: Review thresholds, source data, and operational changes."
        )
    elif label == "CONCEPT_DRIFT":
        st.warning(
            f"{severity.title()} severity concept drift detected. System behavior is changing.\n\n"
            "Recommended action: Monitor this period and compare it with expected behavior."
        )
    elif label == "ANOMALY":
        st.warning(
            "Anomaly detected. A sudden unusual value appeared.\n\n"
            "Recommended action: Validate the source data around this timestamp."
        )
    else:
        st.info(f"{_event_name(label)} detected.")


def show_alert_summary(events, anomalies=None):
    """Show the highest-priority alert after analysis completes."""
    anomalies = anomalies or []
    high_drift = next(
        (
            event
            for event in events
            if event.get("label") == "CONCEPT_DRIFT"
            and event.get("severity") == "HIGH"
        ),
        None
    )
    anomaly = next(
        (
            event
            for event in anomalies + events
            if event.get("label") == "ANOMALY"
        ),
        None
    )

    if high_drift is not None:
        trigger_alert(high_drift)
    elif anomaly is not None:
        trigger_alert(anomaly)
    elif events:
        st.info("Events were detected, but no high severity alert is active.")
    else:
        st.success("No drift or anomaly detected.")


def show_status_panel(current_state, last_event=None):
    """Display current monitoring status."""
    severity = "NONE"
    last_event_name = "No event detected yet"

    if last_event is not None:
        severity = last_event.get("severity", "LOW")
        last_event_name = _event_name(last_event.get("label", "UNKNOWN"))

    col1, col2, col3 = st.columns(3)
    col1.metric("Current State", current_state)
    col2.metric("Last Event", last_event_name)
    col3.metric("Severity", severity)


def show_live_status_banner(current_state):
    """Show a clear Streamlit-native status alert."""
    if current_state == "Waiting":
        st.warning("Waiting to start. Click Start Live Simulation when ready.")
    elif current_state == "Running":
        st.success("Monitoring is running. Incoming data is being analyzed.")
    elif current_state == "Normal":
        st.success("Normal behavior. No active drift or anomaly at this row.")
    elif current_state == "Anomaly":
        st.warning("Anomaly in progress. A sudden unusual point was detected.")
    elif current_state == "Drift":
        st.error("Drift in progress. System behavior is changing.")
    elif current_state == "Complete":
        st.success("Simulation complete.")
    else:
        st.info(current_state)
