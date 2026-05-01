import pandas as pd


def detect_point_anomalies(data, window_size=50, threshold=2.0):
    """
    Detect point anomalies using a simple rolling mean/std rule.

    A point is anomalous when it is far from the recent normal behavior:
    abs(value - rolling_mean) > threshold * rolling_std
    """
    anomalies = []

    if data.empty or "value" not in data.columns:
        return anomalies

    for index in range(window_size, len(data)):
        history = data.iloc[index - window_size:index]
        current = data.iloc[index]

        mean_value = history["value"].mean()
        std_value = history["value"].std()

        if pd.isna(std_value) or std_value == 0:
            continue

        deviation = abs(current["value"] - mean_value)

        if deviation > threshold * std_value:
            anomalies.append({
                "label": "ANOMALY",
                "start_time": current["timestamp"],
                "end_time": current["timestamp"],
                "duration_minutes": 0,
                "severity": "MEDIUM" if deviation <= 3 * std_value else "HIGH",
                "index": int(index),
                "value": float(current["value"]),
                "mean_before": float(mean_value),
                "std_before": float(std_value),
                "message": (
                    "Anomaly detected: sudden deviation from normal behavior."
                ),
                "root_causes": [{
                    "feature": "value",
                    "message": (
                        f"value moved {deviation:.2f} away from the recent average."
                    ),
                    "impact": float(deviation)
                }],
                "recommendations": [
                    "Check whether this point is a one-time spike.",
                    "Investigate the data source around this timestamp."
                ]
            })

    return anomalies
