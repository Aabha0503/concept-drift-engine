import pandas as pd
import streamlit as st


def _badge(label):
    if label == "CONCEPT_DRIFT":
        color = "#d62728"
        text = "Concept Drift"
    elif label == "ANOMALY":
        color = "#ff7f0e"
        text = "Anomaly"
    else:
        color = "#6c757d"
        text = label.title()

    return (
        f"<span style='background:{color}; color:white; padding:4px 8px; "
        f"border-radius:4px; font-size:0.85rem;'>{text}</span>"
    )


def _event_name(label):
    if label == "CONCEPT_DRIFT":
        return "Concept Drift"
    if label == "ANOMALY":
        return "Anomaly"
    return label.title()


def _severity_badge(severity):
    colors = {
        "HIGH": "#d62728",
        "MEDIUM": "#f2c94c",
        "LOW": "#2ca02c",
    }
    text_color = "#111111" if severity == "MEDIUM" else "white"
    color = colors.get(severity, "#6c757d")

    return (
        f"<span style='background:{color}; color:{text_color}; padding:4px 8px; "
        f"border-radius:4px; font-size:0.85rem;'>{severity} severity</span>"
    )


def _format_time(value):
    return pd.to_datetime(value).strftime("%Y-%m-%d %I:%M %p")


def _event_deviation(event):
    for key in ("deviation", "z_score", "score", "impact"):
        value = event.get(key)
        if value is not None:
            return abs(float(value))

    root_causes = event.get("root_causes", [])
    if root_causes:
        return max(abs(float(cause.get("impact", 0))) for cause in root_causes)

    return abs(float(event.get("value", 0)))


def _top_anomalies(events, limit=5):
    anomalies = [event for event in events if event.get("label") == "ANOMALY"]
    return sorted(anomalies, key=_event_deviation, reverse=True)[:limit]


def _top_drifts(events, limit=5):
    drifts = [event for event in events if event.get("label") == "CONCEPT_DRIFT"]
    return sorted(
        drifts,
        key=lambda event: event.get("duration_minutes", 0),
        reverse=True,
    )[:limit]


def _is_critical(event):
    return event.get("severity") == "HIGH"


def _apply_quick_focus(events):
    focus = st.session_state.get("event_focus", "All")

    if focus == "Critical":
        return [event for event in events if _is_critical(event)]
    if focus == "Anomalies":
        return [event for event in events if event.get("label") == "ANOMALY"]
    if focus == "Drift":
        return [event for event in events if event.get("label") == "CONCEPT_DRIFT"]
    return events


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
        return "Increasing later in the period"
    if later < early:
        return "Higher earlier in the period"
    return "Evenly distributed"


def _filter_events(events):
    col1, col2 = st.columns([1, 2])
    with col1:
        event_type = st.selectbox(
            "Filter event type",
            ["All", "Concept Drift", "Anomaly"],
            key="explain_event_filter",
        )
    with col2:
        search_text = st.text_input(
            "Search timestamp",
            placeholder="Example: 2024-01-01 or 09:30",
            key="explain_event_search",
        )

    filtered = events
    if event_type != "All":
        target = "CONCEPT_DRIFT" if event_type == "Concept Drift" else "ANOMALY"
        filtered = [event for event in filtered if event.get("label") == target]

    if search_text:
        filtered = [
            event
            for event in filtered
            if search_text.lower() in str(event.get("start_time", "")).lower()
            or search_text.lower() in str(event.get("end_time", "")).lower()
        ]

    return filtered


def _show_event_table(events, include_deviation=False):
    if not events:
        st.write("No matching events.")
        return

    rows = []
    for event in events:
        row = {
            "Type": _event_name(event.get("label", "UNKNOWN")),
            "Start": _format_time(event.get("start_time")),
            "End": _format_time(event.get("end_time")),
            "Duration (min)": round(float(event.get("duration_minutes", 0)), 2),
            "Severity": event.get("severity", "LOW"),
        }
        if include_deviation:
            row["Deviation"] = round(_event_deviation(event), 2)
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _show_event_detail(event, index):
    label = event.get("label", "UNKNOWN")
    start_time = event.get("start_time")
    end_time = event.get("end_time")
    duration = event.get("duration_minutes", 0)
    severity = event.get("severity", "LOW")
    root_causes = event.get("root_causes", [])
    recommendations = event.get("recommendations", [])

    with st.expander(f"Event {index + 1}: {_event_name(label)} at {_format_time(start_time)}"):
        st.markdown(_badge(label), unsafe_allow_html=True)
        st.markdown(_severity_badge(severity), unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Start", str(start_time))
        col2.metric("End", str(end_time))
        col3.metric("Duration", f"{duration:.2f} min")

        st.write("Why this may have happened")
        if root_causes:
            for cause in root_causes:
                st.write(f"- {cause.get('message')}")
        else:
            st.write("- Not enough previous data was available to compare behavior.")

        st.write("What to do next")
        for recommendation in recommendations:
            st.write(f"- {recommendation}")


def show_explanation(result):
    st.subheader("Drift Explanation")

    drifts = result.get("drifts", [])
    point_anomalies = result.get("anomalies", [])
    all_events = drifts + point_anomalies
    events = _apply_quick_focus(all_events)
    anomalies = [event for event in events if event.get("label") == "ANOMALY"]

    if len(all_events) == 0:
        st.info("No drift or anomaly detected")
        return

    st.caption(f"Current quick focus: {st.session_state.get('event_focus', 'All')}")

    max_deviation = max([_event_deviation(event) for event in anomalies], default=0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Anomalies",
        len(anomalies),
        help="Anomalies visible under the current quick focus.",
    )
    col2.metric(
        "Peak Time",
        _peak_occurrence_time(anomalies),
        help="Hour of day where visible anomalies occur most often.",
    )
    col3.metric(
        "Max Deviation",
        f"{max_deviation:.2f}",
        help="Largest visible anomaly movement away from recent normal behavior.",
    )
    col4.metric(
        "Frequency",
        _frequency_pattern(anomalies),
        help="Whether visible anomalies are concentrated early, later, or evenly.",
    )

    if not events:
        st.info("No events match the current quick focus.")
        return

    st.write("Top Events")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Top 5 anomalies by deviation")
        _show_event_table(_top_anomalies(events), include_deviation=True)
    with col2:
        st.caption("Top drift events by duration")
        _show_event_table(_top_drifts(events))

    with st.expander("Filter and Search Full Event Details"):
        filtered_events = _filter_events(events)
        _show_event_table(filtered_events[:50], include_deviation=True)
        if len(filtered_events) > 50:
            st.caption(f"Showing first 50 of {len(filtered_events)} matching events.")

        for index, event in enumerate(filtered_events[:10]):
            _show_event_detail(event, index)
