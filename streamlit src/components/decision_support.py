import streamlit as st

from core.decision_engine import build_decision_summary


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


def _key_insights(result):
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)
    insights = []

    if anomaly_events:
        insights.append(f"{len(anomaly_events)} anomaly event(s) require data-quality review.")
    else:
        insights.append("No anomaly pressure detected.")

    if drift_events:
        longest = max(drift_events, key=lambda event: event.get("duration_minutes", 0))
        insights.append(
            f"{len(drift_events)} drift event(s) detected; longest duration is "
            f"{longest.get('duration_minutes', 0):.2f} minutes."
        )
    else:
        insights.append("No sustained drift period detected.")

    high_severity = [
        event for event in drift_events if event.get("severity") == "HIGH"
    ]
    if high_severity:
        insights.append("High-severity drift is present; review thresholds and upstream changes.")

    return insights


def _show_health_status(health):
    if health == "Critical":
        st.error("System Health: Critical. Immediate attention recommended.")
    elif health == "Warning":
        st.warning("System Health: Warning. Monitor closely and review recommendations.")
    else:
        st.success("System Health: Stable. No urgent action needed.")


def _show_smart_alert(alert):
    text = f"{alert['message']}\n\n{alert['action']}"

    if alert["level"] == "error":
        st.error(text)
    elif alert["level"] == "warning":
        st.warning(text)
    else:
        st.success(text)


def show_decision_support(result):
    """Render decision-making insights for non-technical users."""
    st.subheader("Decision Support")

    summary = build_decision_summary(result)

    _show_health_status(summary["health"])

    st.write("Smart Alert Panel")
    for alert in summary["alerts"]:
        _show_smart_alert(alert)

    with st.expander("Recommended Actions", expanded=True):
        for item in summary["recommendations"]:
            st.write(f"**{item['title']}**")
            st.caption(item["reason"])

    with st.expander("Key Decision Insights", expanded=True):
        for insight in _key_insights(result):
            st.write(f"- {insight}")

    with st.expander("How decisions are made"):
        st.write(
            "This decision layer uses simple rules: high severity drift suggests "
            "threshold and source-data review, frequent anomalies suggest data validation, "
            "and long drift duration suggests closer monitoring."
        )
