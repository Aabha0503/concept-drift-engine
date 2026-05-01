import pandas as pd


def _event_time(event):
    return pd.to_datetime(event.get("start_time"))


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


def calculate_system_health(result):
    """Return Stable, Warning, or Critical using simple rule-based checks."""
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)

    high_drift_count = sum(
        1 for event in drift_events if event.get("severity") == "HIGH"
    )
    long_drift_count = sum(
        1 for event in drift_events if event.get("duration_minutes", 0) >= 180
    )

    if high_drift_count > 0 or len(drift_events) >= 3 or len(anomaly_events) >= 10:
        return "Critical"

    if long_drift_count > 0 or len(drift_events) > 0 or len(anomaly_events) >= 3:
        return "Warning"

    return "Stable"


def generate_recommendations(result):
    """Generate simple decision recommendations from detected events."""
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)
    recommendations = []

    high_drift = any(event.get("severity") == "HIGH" for event in drift_events)
    long_drift = any(event.get("duration_minutes", 0) >= 180 for event in drift_events)

    if high_drift:
        recommendations.append({
            "title": "Review drift drivers",
            "reason": "High severity drift means the data behavior changed enough to require threshold, source-data, and operational review."
        })

    if len(anomaly_events) >= 3:
        recommendations.append({
            "title": "Validate incoming data",
            "reason": "Frequent anomalies may indicate sensor spikes, missing values, or data pipeline issues."
        })

    if long_drift:
        recommendations.append({
            "title": "Monitor this drift period",
            "reason": "Long drift duration suggests a sustained behavior change, not just a short spike."
        })

    if not recommendations:
        recommendations.append({
            "title": "Continue monitoring",
            "reason": "No urgent action is needed based on the current detected events."
        })

    return recommendations


def generate_smart_alerts(result):
    """Create alert messages that explain both meaning and next action."""
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)
    alerts = []

    high_drift = next(
        (event for event in drift_events if event.get("severity") == "HIGH"),
        None
    )

    if high_drift is not None:
        alerts.append({
            "level": "error",
            "message": "High severity drift detected. System behavior changed significantly.",
            "action": "Recommended action: Review thresholds, source data, and recent operational changes."
        })

    if len(anomaly_events) >= 3:
        alerts.append({
            "level": "warning",
            "message": "Frequent anomalies detected. Incoming data may be unstable.",
            "action": "Recommended action: Validate the data pipeline."
        })
    elif len(anomaly_events) > 0:
        alerts.append({
            "level": "warning",
            "message": "Anomaly detected. A sudden unusual value appeared.",
            "action": "Recommended action: Inspect the timestamp and source data."
        })

    if not alerts:
        alerts.append({
            "level": "success",
            "message": "System behavior looks stable.",
            "action": "Recommended action: Continue monitoring."
        })

    return alerts


def build_event_timeline(result):
    """Build a simple Normal -> Event -> Recovery textual timeline."""
    events = _drift_events(result) + _anomaly_events(result)
    events = sorted(events, key=_event_time)

    if not events:
        return ["Normal monitoring", "No drift or anomaly detected"]

    timeline = ["Normal monitoring"]

    for event in events:
        label = event.get("label")
        time_text = _event_time(event).strftime("%Y-%m-%d %I:%M %p")

        if label == "CONCEPT_DRIFT":
            timeline.append(f"Drift detected at {time_text}")
            timeline.append("Recovery / monitoring after drift")
        elif label == "ANOMALY":
            timeline.append(f"Anomaly detected at {time_text}")
            timeline.append("Returned to monitoring")

    return timeline


def build_decision_summary(result):
    return {
        "health": calculate_system_health(result),
        "alerts": generate_smart_alerts(result),
        "recommendations": generate_recommendations(result),
        "timeline": build_event_timeline(result),
    }
