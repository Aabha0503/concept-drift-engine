import pandas as pd
from numbers import Real


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


def _format_number(value):
    if not isinstance(value, Real) or pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


def _safe_percent(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float((numerator / denominator) * 100)


def _period_text(value):
    if value is None or value == "N/A" or pd.isna(value):
        return "N/A"
    return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M:%S")


def _trend_direction(dataframe):
    if dataframe is None or dataframe.empty or len(dataframe) < 2:
        return "Stable", 0, 0

    values = dataframe["value"].reset_index(drop=True)
    sample_size = max(3, len(values) // 4)
    first_mean = values.head(sample_size).mean()
    last_mean = values.tail(sample_size).mean()
    change = last_mean - first_mean
    threshold = max(values.std() * 0.25, abs(first_mean) * 0.02)
    change_percent = _safe_percent(change, abs(first_mean))

    if change > threshold:
        return "Increasing", float(change), change_percent
    if change < -threshold:
        return "Decreasing", float(change), change_percent
    return "Stable", float(change), change_percent


def _moving_average_summary(dataframe, moving_average_window):
    if dataframe is None or dataframe.empty:
        return {
            "window": 0,
            "latest": 0,
            "previous": 0,
            "change": 0,
            "direction": "Unavailable",
        }

    rolling_window = min(moving_average_window, len(dataframe))
    rolling = dataframe["value"].rolling(rolling_window, min_periods=1).mean()
    latest = rolling.iloc[-1]
    previous_index = max(0, len(rolling) - rolling_window - 1)
    previous = rolling.iloc[previous_index]
    change = latest - previous
    tolerance = max(dataframe["value"].std() * 0.10, abs(previous) * 0.01)

    if change > tolerance:
        direction = "Rising"
    elif change < -tolerance:
        direction = "Falling"
    else:
        direction = "Flat"

    return {
        "window": rolling_window,
        "latest": float(latest) if pd.notna(latest) else 0,
        "previous": float(previous) if pd.notna(previous) else 0,
        "change": float(change) if pd.notna(change) else 0,
        "direction": direction,
    }


def _variance_direction(dataframe):
    if dataframe is None or dataframe.empty or len(dataframe) < 4:
        return "Stable", 0, 0

    midpoint = len(dataframe) // 2
    first_variance = dataframe["value"].iloc[:midpoint].var()
    second_variance = dataframe["value"].iloc[midpoint:].var()

    if pd.isna(first_variance) or pd.isna(second_variance):
        return "Stable", 0, 0

    change_ratio = (
        (second_variance - first_variance) / first_variance
        if first_variance > 0
        else 0
    )

    if change_ratio > 0.25:
        return "Rising", float(first_variance), float(second_variance)
    if change_ratio < -0.25:
        return "Falling", float(first_variance), float(second_variance)
    return "Stable", float(first_variance), float(second_variance)


def _range_status(dataframe):
    if dataframe is None or dataframe.empty:
        return "N/A", 0, 0

    value_range = dataframe["value"].max() - dataframe["value"].min()
    standard_deviation = dataframe["value"].std()
    mean_value = dataframe["value"].mean()

    if pd.isna(standard_deviation):
        standard_deviation = 0

    coefficient_of_variation = abs(_safe_percent(standard_deviation, mean_value))

    if standard_deviation == 0:
        return "Very stable", float(value_range), coefficient_of_variation
    if value_range > standard_deviation * 6:
        return "Wide range", float(value_range), coefficient_of_variation
    if value_range > standard_deviation * 3:
        return "Moderate range", float(value_range), coefficient_of_variation
    return "Narrow range", float(value_range), coefficient_of_variation


def _event_start(event):
    return pd.to_datetime(event.get("start_time"))


def _event_frequency(events):
    if not events:
        return {
            "total_events": 0,
            "first_half_events": 0,
            "second_half_events": 0,
            "status": "No events",
        }

    event_times = sorted(_event_start(event) for event in events)
    if len(event_times) == 1:
        return {
            "total_events": 1,
            "first_half_events": 1,
            "second_half_events": 0,
            "status": "Stable",
        }

    midpoint = event_times[0] + ((event_times[-1] - event_times[0]) / 2)
    first_half = sum(1 for event_time in event_times if event_time <= midpoint)
    second_half = len(event_times) - first_half

    if second_half > first_half:
        status = "Increasing"
    elif second_half < first_half:
        status = "Decreasing"
    else:
        status = "Stable"

    return {
        "total_events": len(events),
        "first_half_events": first_half,
        "second_half_events": second_half,
        "status": status,
    }


def _event_rates(events, dataframe):
    if dataframe is None or dataframe.empty:
        return {
            "events_per_100_points": 0,
            "events_per_day": 0,
        }

    row_rate = _safe_percent(len(events), len(dataframe))
    start_time = dataframe["timestamp"].min()
    end_time = dataframe["timestamp"].max()
    elapsed_days = max((end_time - start_time).total_seconds() / 86400, 1 / 24)

    return {
        "events_per_100_points": row_rate,
        "events_per_day": float(len(events) / elapsed_days),
    }


def _time_pattern(events):
    if not events:
        return {
            "peak_period": "No event pattern",
            "peak_count": 0,
            "bucket_counts": {},
            "summary": "No drift or anomaly events were available for time-pattern analysis.",
        }

    buckets = {
        "Night (00:00-05:59)": 0,
        "Morning (06:00-11:59)": 0,
        "Afternoon (12:00-17:59)": 0,
        "Evening (18:00-23:59)": 0,
    }

    for event in events:
        hour = _event_start(event).hour
        if hour < 6:
            buckets["Night (00:00-05:59)"] += 1
        elif hour < 12:
            buckets["Morning (06:00-11:59)"] += 1
        elif hour < 18:
            buckets["Afternoon (12:00-17:59)"] += 1
        else:
            buckets["Evening (18:00-23:59)"] += 1

    peak_period, peak_count = max(buckets.items(), key=lambda item: item[1])

    return {
        "peak_period": peak_period,
        "peak_count": peak_count,
        "bucket_counts": buckets,
        "summary": f"Events occur most frequently during {peak_period}.",
    }


def _risk_assessment(drift_events, anomaly_events, frequency, variance_status):
    high_drift_count = sum(
        1 for event in drift_events if event.get("severity") == "HIGH"
    )
    long_drift_count = sum(
        1 for event in drift_events if event.get("duration_minutes", 0) >= 180
    )

    if (
        high_drift_count > 0
        or len(drift_events) >= 3
        or len(anomaly_events) >= 10
        or (frequency["status"] == "Increasing" and len(anomaly_events) >= 5)
        or (variance_status == "Rising" and len(anomaly_events) >= 5)
    ):
        return "Critical"

    if (
        long_drift_count > 0
        or len(drift_events) > 0
        or len(anomaly_events) >= 3
        or frequency["status"] == "Increasing"
        or variance_status == "Rising"
    ):
        return "Warning"

    return "Stable"


def _risk_drivers(health, drift_events, anomaly_events, frequency, variance_status):
    drivers = []

    high_drift_count = sum(
        1 for event in drift_events if event.get("severity") == "HIGH"
    )
    long_drift_count = sum(
        1 for event in drift_events if event.get("duration_minutes", 0) >= 180
    )

    if high_drift_count:
        drivers.append(f"{high_drift_count} high-severity drift event(s)")
    if len(drift_events) >= 3:
        drivers.append("multiple drift periods")
    if long_drift_count:
        drivers.append("sustained drift duration")
    if len(anomaly_events) >= 10:
        drivers.append("high anomaly volume")
    elif len(anomaly_events) >= 3:
        drivers.append("repeated anomalies")
    if frequency["status"] == "Increasing":
        drivers.append("anomaly frequency is increasing")
    if variance_status == "Rising":
        drivers.append("data variability is rising")

    if not drivers:
        drivers.append("no material drift, anomaly, or variability pressure")

    return {
        "level": health,
        "drivers": drivers,
    }


def _recommendations(health, statistical_insights):
    frequency = statistical_insights["frequency"]
    time_pattern = statistical_insights["time_pattern"]
    recommendations = []

    if health == "Critical":
        recommendations.append(
            "- Start immediate operational review for the affected period and validate upstream data sources."
        )
    elif health == "Warning":
        recommendations.append(
            "- Increase monitoring frequency and review the latest drift/anomaly timestamps."
        )
    else:
        recommendations.append(
            "- Continue normal monitoring cadence and keep the current alert thresholds under observation."
        )

    if statistical_insights["trend"] in {"Increasing", "Decreasing"}:
        recommendations.append(
            "- Compare the directional trend with expected business or system seasonality before changing thresholds."
        )

    if statistical_insights["variance_status"] == "Rising":
        recommendations.append(
            "- Investigate variance growth by checking data collection consistency, source changes, and recent deployments."
        )

    if frequency["status"] == "Increasing":
        recommendations.append(
            "- Review anomaly-heavy intervals and confirm whether the increase is caused by real behavior or data-quality issues."
        )

    if time_pattern["peak_count"] > 0:
        recommendations.append(
            f"- Schedule focused checks around {time_pattern['peak_period']} where events are most concentrated."
        )

    return recommendations


def build_statistical_insights(result, moving_average_window=20):
    """Build simple, explainable analytics without machine learning models."""
    dataframe = result.get("dataframe")
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)
    all_events = drift_events + anomaly_events

    if dataframe is None or dataframe.empty:
        frequency = _event_frequency(all_events)
        time_pattern = _time_pattern(all_events)
        risk_assessment = {
            "level": "Stable",
            "drivers": ["no data available for risk scoring"],
        }

        return {
            "trend": "Unavailable",
            "trend_change": 0,
            "trend_change_percent": 0,
            "moving_average": 0,
            "moving_average_previous": 0,
            "moving_average_change": 0,
            "moving_average_direction": "Unavailable",
            "moving_average_window": 0,
            "variance_status": "Unavailable",
            "first_half_variance": 0,
            "second_half_variance": 0,
            "standard_deviation": 0,
            "coefficient_of_variation": 0,
            "range_status": "Unavailable",
            "value_range": 0,
            "frequency": frequency,
            "event_rates": {
                "events_per_100_points": 0,
                "events_per_day": 0,
            },
            "time_pattern": time_pattern,
            "risk": "Stable",
            "risk_assessment": risk_assessment,
            "insights": ["No data available for statistical analysis."],
        }

    trend, trend_change, trend_change_percent = _trend_direction(dataframe)
    variance_status, first_variance, second_variance = _variance_direction(dataframe)
    range_status, value_range, coefficient_of_variation = _range_status(dataframe)
    frequency = _event_frequency(anomaly_events)
    event_rates = _event_rates(anomaly_events, dataframe)
    time_pattern = _time_pattern(all_events)
    risk = _risk_assessment(drift_events, anomaly_events, frequency, variance_status)
    moving_average = _moving_average_summary(dataframe, moving_average_window)
    standard_deviation = dataframe["value"].std()
    risk_assessment = _risk_drivers(
        risk,
        drift_events,
        anomaly_events,
        frequency,
        variance_status,
    )

    insights = []
    if trend == "Increasing":
        insights.append(
            f"Increasing trend detected ({_format_number(trend_change)} absolute change, "
            f"{_format_number(trend_change_percent)}% relative change)."
        )
    elif trend == "Decreasing":
        insights.append(
            f"Decreasing trend detected ({_format_number(trend_change)} absolute change, "
            f"{_format_number(trend_change_percent)}% relative change)."
        )
    else:
        insights.append("No strong directional trend detected.")

    if variance_status == "Rising":
        insights.append("Data variability rising.")
    elif variance_status == "Falling":
        insights.append("Data variability decreasing.")
    else:
        insights.append("Data variability appears stable.")

    insights.append(
        f"Moving average baseline is {_format_number(moving_average['latest'])} "
        f"over the latest {moving_average['window']} points and is {moving_average['direction'].lower()}."
    )
    insights.append(
        f"Anomaly frequency is {frequency['status'].lower()} "
        f"({frequency['first_half_events']} early vs {frequency['second_half_events']} later)."
    )
    insights.append(time_pattern["summary"])
    insights.append(
        f"Risk level is {risk} because of {', '.join(risk_assessment['drivers'])}."
    )

    return {
        "trend": trend,
        "trend_change": trend_change,
        "trend_change_percent": trend_change_percent,
        "moving_average": moving_average["latest"],
        "moving_average_previous": moving_average["previous"],
        "moving_average_change": moving_average["change"],
        "moving_average_direction": moving_average["direction"],
        "moving_average_window": moving_average["window"],
        "variance_status": variance_status,
        "first_half_variance": first_variance,
        "second_half_variance": second_variance,
        "standard_deviation": float(standard_deviation) if pd.notna(standard_deviation) else 0,
        "coefficient_of_variation": coefficient_of_variation,
        "range_status": range_status,
        "value_range": value_range,
        "frequency": frequency,
        "event_rates": event_rates,
        "time_pattern": time_pattern,
        "risk": risk,
        "risk_assessment": risk_assessment,
        "insights": insights,
    }


def _root_cause_lines(events):
    lines = []

    for event in events[:5]:
        label = event.get("label", "EVENT").replace("_", " ").title()
        start_time = event.get("start_time", "unknown time")
        root_causes = event.get("root_causes", [])

        if not root_causes:
            lines.append(f"- {label} at {start_time}: root cause not available.")
            continue

        top_cause = root_causes[0]
        lines.append(
            f"- {label} at {start_time}: {top_cause.get('message', 'Change detected.')}"
        )

    if not lines:
        lines.append("- No drift or anomaly root causes were identified.")

    return lines


def build_mis_report(result):
    """Create a structured MIS-style report as text plus reusable sections."""
    dataframe = result.get("dataframe")
    drift_events = _drift_events(result)
    anomaly_events = _anomaly_events(result)
    all_events = drift_events + anomaly_events
    statistical_insights = build_statistical_insights(result)
    health = statistical_insights["risk"]
    recommendations = _recommendations(health, statistical_insights)

    row_count = len(dataframe) if dataframe is not None else 0
    start_time = dataframe["timestamp"].min() if dataframe is not None and not dataframe.empty else "N/A"
    end_time = dataframe["timestamp"].max() if dataframe is not None and not dataframe.empty else "N/A"

    if health == "Critical":
        executive_summary = (
            "The monitored system requires immediate attention due to high-risk "
            "drift or frequent anomalies."
        )
    elif health == "Warning":
        executive_summary = (
            "The monitored system shows behavior changes that should be reviewed "
            "and tracked closely."
        )
    else:
        executive_summary = (
            "The monitored system appears stable with no urgent operational risk."
        )

    critical_findings = []
    if drift_events:
        critical_findings.append(f"{len(drift_events)} concept drift event(s) detected.")
    if anomaly_events:
        critical_findings.append(f"{len(anomaly_events)} anomaly event(s) detected.")
    critical_findings.extend(statistical_insights["insights"])
    if not critical_findings:
        critical_findings.append("No critical findings detected.")

    recommendation_lines = recommendations

    sections = {
        "Executive Summary": [executive_summary],
        "Key Metrics": [
            f"Rows analyzed: {row_count}",
            f"Monitoring period: {_period_text(start_time)} to {_period_text(end_time)}",
            f"Concept drift events: {len(drift_events)}",
            f"Anomaly events: {len(anomaly_events)}",
            f"Trend status: {statistical_insights['trend']}",
            f"Trend change: {_format_number(statistical_insights['trend_change'])} ({_format_number(statistical_insights['trend_change_percent'])}%)",
            f"Moving average baseline: {_format_number(statistical_insights['moving_average'])}",
            f"Moving average direction: {statistical_insights['moving_average_direction']}",
            f"Standard deviation: {_format_number(statistical_insights['standard_deviation'])}",
            f"Coefficient of variation: {_format_number(statistical_insights['coefficient_of_variation'])}%",
            f"Observed range: {_format_number(statistical_insights['value_range'])}",
            f"Range status: {statistical_insights['range_status']}",
            (
                "Variance tracking: "
                f"{statistical_insights['variance_status']} "
                f"({_format_number(statistical_insights['first_half_variance'])} -> "
                f"{_format_number(statistical_insights['second_half_variance'])})"
            ),
            (
                "Anomaly frequency: "
                f"{statistical_insights['frequency']['status']} "
                f"({statistical_insights['frequency']['first_half_events']} early, "
                f"{statistical_insights['frequency']['second_half_events']} later)"
            ),
            f"Anomaly rate: {_format_number(statistical_insights['event_rates']['events_per_100_points'])} per 100 records",
            f"Anomalies per day: {_format_number(statistical_insights['event_rates']['events_per_day'])}",
            f"Peak event period: {statistical_insights['time_pattern']['peak_period']}",
        ],
        "Behavioral Insights": statistical_insights["insights"],
        "Critical Findings": critical_findings,
        "Risk Assessment": [
            f"Overall risk level: {health}",
            f"Risk drivers: {', '.join(statistical_insights['risk_assessment']['drivers'])}",
            (
                "Risk is based on concept drift count, anomaly frequency, "
                "event acceleration, and variability changes."
            ),
        ],
        "Recommendations": recommendation_lines,
    }

    report_lines = ["Concept Drift Monitoring MIS Report", ""]
    for title, lines in sections.items():
        report_lines.append(title)
        report_lines.append("-" * len(title))
        report_lines.extend(lines)
        report_lines.append("")

    return {
        "sections": sections,
        "statistical_insights": statistical_insights,
        "health": health,
        "text": "\n".join(report_lines).strip(),
    }
