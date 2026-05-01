from numbers import Real

import streamlit as st

from core.statistical_report import build_mis_report


def _metric_number(value):
    return f"{value:.2f}" if isinstance(value, Real) else "N/A"


def _show_section(title, lines):
    st.markdown(f"### {title}")

    for line in lines:
        st.write(line)


def _show_health(health):
    if health == "Critical":
        st.error("System Health Status: Critical")
    elif health == "Warning":
        st.warning("System Health Status: Warning")
    else:
        st.success("System Health Status: Stable")


def _show_bucket_counts(bucket_counts):
    if not bucket_counts:
        st.write("No time-based event pattern found.")
        return

    for period, count in bucket_counts.items():
        st.write(f"- {period}: {count} event(s)")


def show_mis_report(result):
    """Render business-ready statistical insights and downloadable MIS report."""
    st.subheader("MIS Report")
    st.caption(
        "Business summary generated from moving averages, standard deviation, "
        "event frequency, and time-based patterns. No machine learning models are used."
    )

    report = build_mis_report(result)
    statistical_insights = report["statistical_insights"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Trend", statistical_insights["trend"])
    col2.metric("Moving Avg", _metric_number(statistical_insights["moving_average"]))
    col3.metric("Variability", statistical_insights["variance_status"])
    col4.metric("Risk", report["health"])

    _show_health(report["health"])

    frequency = statistical_insights["frequency"]
    event_rates = statistical_insights["event_rates"]
    time_pattern = statistical_insights["time_pattern"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Anomaly Frequency", frequency["status"])
    col2.metric("Total Anomalies", frequency["total_events"])
    col3.metric("Peak Event Period", time_pattern["peak_period"])

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Trend Change",
        _metric_number(statistical_insights["trend_change"]),
        f"{_metric_number(statistical_insights['trend_change_percent'])}%",
    )
    col2.metric(
        "Std Deviation",
        _metric_number(statistical_insights["standard_deviation"]),
        statistical_insights["range_status"],
    )
    col3.metric(
        "Anomaly Rate",
        _metric_number(event_rates["events_per_100_points"]),
        "per 100 records",
    )

    with st.expander("Trend and Variability Analysis", expanded=True):
        st.write(
            f"Moving average uses the latest {statistical_insights['moving_average_window']} "
            f"records and is {statistical_insights['moving_average_direction'].lower()}."
        )
        st.write(
            "Variance comparison: "
            f"{_metric_number(statistical_insights['first_half_variance'])} -> "
            f"{_metric_number(statistical_insights['second_half_variance'])}."
        )
        st.write(
            "Coefficient of variation: "
            f"{_metric_number(statistical_insights['coefficient_of_variation'])}%."
        )

    with st.expander("Frequency and Time-Based Patterns", expanded=True):
        st.write(
            f"Anomaly frequency is {frequency['status'].lower()} "
            f"({frequency['first_half_events']} early vs {frequency['second_half_events']} later)."
        )
        st.write(f"Anomalies per day: {_metric_number(event_rates['events_per_day'])}.")
        _show_bucket_counts(time_pattern.get("bucket_counts", {}))

    with st.expander("Risk Drivers", expanded=True):
        for driver in statistical_insights["risk_assessment"]["drivers"]:
            st.write(f"- {driver}")

    with st.expander("Statistical Behavioral Insights", expanded=True):
        for insight in statistical_insights["insights"]:
            st.info(insight)

    for title, lines in report["sections"].items():
        with st.expander(title, expanded=title in {"Executive Summary", "Key Metrics"}):
            _show_section(title, lines)

    st.download_button(
        label="Download Report",
        data=report["text"],
        file_name="concept_drift_mis_report.txt",
        mime="text/plain",
        use_container_width=True,
    )
