import pandas as pd


def _numeric_features(data):
    return [
        column
        for column in data.select_dtypes(include="number").columns
        if column != "timestamp"
    ]


def _event_times(event):
    start = pd.to_datetime(event.get("start_time"))
    end = pd.to_datetime(event.get("end_time"))
    return start, end


def _safe_percent_change(before_mean, during_mean):
    if pd.isna(before_mean) or pd.isna(during_mean) or before_mean == 0:
        return 0

    return ((during_mean - before_mean) / abs(before_mean)) * 100


def _describe_direction(feature, percent_change):
    if abs(percent_change) < 1:
        return f"{feature} changed very little during this event."

    if percent_change > 0:
        return f"{feature} increased by {abs(percent_change):.1f}% during this event."

    return f"{feature} dropped by {abs(percent_change):.1f}% during this event."


def _comparison_window(data, start_time, event_duration):
    before_start = start_time - event_duration
    before_end = start_time
    return data[(data["timestamp"] >= before_start) & (data["timestamp"] < before_end)]


def analyze_root_cause(data, drift_events):
    """
    Compare data before each event with data during the event.

    This uses simple mean/std/percentage-change statistics so the result stays
    interpretable for beginners.
    """
    features = _numeric_features(data)

    for event in drift_events:
        start_time, end_time = _event_times(event)
        event_duration = end_time - start_time

        before_data = _comparison_window(data, start_time, event_duration)
        during_data = data[(data["timestamp"] >= start_time) & (data["timestamp"] <= end_time)]

        feature_changes = []

        for feature in features:
            if before_data.empty or during_data.empty:
                continue

            before_mean = before_data[feature].mean()
            during_mean = during_data[feature].mean()
            before_std = before_data[feature].std()
            during_std = during_data[feature].std()
            percent_change = _safe_percent_change(before_mean, during_mean)

            feature_changes.append({
                "feature": feature,
                "before_mean": float(before_mean),
                "during_mean": float(during_mean),
                "before_std": float(before_std) if pd.notna(before_std) else 0,
                "during_std": float(during_std) if pd.notna(during_std) else 0,
                "percent_change": float(percent_change),
                "impact": abs(float(percent_change)),
                "message": _describe_direction(feature, percent_change)
            })

        feature_changes = sorted(
            feature_changes,
            key=lambda item: item["impact"],
            reverse=True
        )

        event["root_causes"] = feature_changes[:3]
        event["severity"] = calculate_severity(event)
        event["recommendations"] = generate_recommendations(event)

    return drift_events


def calculate_severity(event):
    """
    Classify severity using simple, explainable rules.

    Magnitude comes from the largest feature percentage change.
    Duration comes from the event length in minutes.
    """
    duration = event.get("duration_minutes", 0)
    root_causes = event.get("root_causes", [])
    max_change = max([cause.get("impact", 0) for cause in root_causes], default=0)

    score = 0

    if max_change >= 50:
        score += 2
    elif max_change >= 20:
        score += 1

    if duration >= 180:
        score += 2
    elif duration >= 60:
        score += 1

    if event.get("label") == "CONCEPT_DRIFT":
        score += 1

    if score >= 4:
        return "HIGH"
    if score >= 2:
        return "MEDIUM"
    return "LOW"


def generate_recommendations(event):
    recommendations = []
    label = event.get("label")
    severity = event.get("severity", "LOW")
    root_causes = event.get("root_causes", [])
    top_feature = root_causes[0]["feature"] if root_causes else "the main value"

    if label == "CONCEPT_DRIFT":
        recommendations.append("Review thresholds and source changes if this pattern continues.")
        recommendations.append(f"Monitor {top_feature} closely in the next data batches.")
    elif label == "ANOMALY":
        recommendations.append("Investigate whether this was a one-time spike or data issue.")
        recommendations.append(f"Check the data pipeline around {top_feature}.")

    if severity == "HIGH":
        recommendations.append("Treat this as urgent because it may affect system behavior.")
    elif severity == "MEDIUM":
        recommendations.append("Keep monitoring this event before making major changes.")
    else:
        recommendations.append("No immediate action is required, but keep tracking the trend.")

    return recommendations
