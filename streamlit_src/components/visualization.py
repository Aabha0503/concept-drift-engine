import pandas as pd
import streamlit as st

from components.alerts import (
    show_live_status_banner,
    show_status_panel,
    show_system_health_score,
    show_why_it_matters,
    trigger_alert,
)
from components.explain import show_explanation
from components.mis_report import show_mis_report
from components.summaryMetrics import show_metrics

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


DRIFT_COLOR = "#d62728"
ANOMALY_COLOR = "#ff7f0e"
NORMAL_COLOR = "#1f77b4"
MAX_CHART_POINTS = 700


def _event_name(label):
    if label == "CONCEPT_DRIFT":
        return "Concept Drift"
    if label == "ANOMALY":
        return "Anomaly"
    return "Normal"


def _event_message(label):
    if label == "CONCEPT_DRIFT":
        return "Concept drift detected: behavior changed for a longer period."
    if label == "ANOMALY":
        return "Anomaly detected: this point is unusual compared to past data."
    return "Normal behavior: this point looks similar to recent data."


def _format_time(value):
    timestamp = pd.to_datetime(value)
    return timestamp.strftime("%Y-%m-%d %I:%M %p")


def _event_deviation(event):
    for key in ("deviation", "z_score", "score", "impact"):
        value = event.get(key)
        if value is not None:
            return abs(float(value))

    root_causes = event.get("root_causes", [])
    if root_causes:
        return max(abs(float(cause.get("impact", 0))) for cause in root_causes)

    return abs(float(event.get("value", 0)))


def _event_times(event):
    start = pd.to_datetime(event.get("start_time"))
    end = pd.to_datetime(event.get("end_time"))
    return start, end


def _nearest_point(dataframe, timestamp):
    distances = (dataframe["timestamp"] - timestamp).abs()
    nearest_index = distances.idxmin()
    return dataframe.loc[nearest_index]


def _events_by_label(events, label):
    return [event for event in events if event.get("label") == label]


def _drift_events(result):
    return _events_by_label(result.get("drifts", []), "CONCEPT_DRIFT")


def _anomaly_events(result):
    classifier_anomalies = _events_by_label(result.get("drifts", []), "ANOMALY")
    point_anomalies = result.get("anomalies", [])
    return point_anomalies + classifier_anomalies


def _active_event_at(timestamp, events):
    timestamp = pd.to_datetime(timestamp)

    for event in events:
        start, end = _event_times(event)
        if start <= timestamp <= end:
            return event

    return None


def _active_anomalies_at(timestamp, anomalies):
    timestamp = pd.to_datetime(timestamp)
    active = []

    for anomaly in anomalies:
        start, end = _event_times(anomaly)
        if start <= timestamp <= end:
            active.append(anomaly)

    return active


def _last_event_at(timestamp, events):
    timestamp = pd.to_datetime(timestamp)
    past_events = [
        event
        for event in events
        if _event_times(event)[0] <= timestamp
    ]

    if not past_events:
        return None

    return sorted(past_events, key=lambda event: _event_times(event)[0])[-1]


def _visible_events_until(events, current_time):
    current_time = pd.to_datetime(current_time)
    visible_events = []

    for event in events:
        start, end = _event_times(event)

        if start > current_time:
            continue

        visible_event = event.copy()
        visible_event["end_time"] = min(end, current_time)
        visible_events.append(visible_event)

    return visible_events


def _event_key(event):
    if event is None:
        return None

    return (
        event.get("label"),
        str(event.get("start_time")),
        str(event.get("end_time"))
    )


def _event_log_message(event):
    label = event.get("label")
    start_time = _format_time(event.get("start_time"))

    if label == "CONCEPT_DRIFT":
        severity = event.get("severity", "LOW")
        return f"Concept drift detected at {start_time} ({severity} severity)"

    if label == "ANOMALY":
        return f"Anomaly detected at {start_time}: sudden deviation from normal behavior"

    return f"{_event_name(label)} detected at {start_time}"


def _render_logs(logs):
    log_text = "\n".join(f"- {message}" for message in logs[-12:])
    st.markdown(log_text if log_text else "- No live logs yet")


def _add_live_log(message):
    if "live_logs" not in st.session_state:
        st.session_state.live_logs = []

    st.session_state.live_logs.append(message)
    st.session_state.live_logs = st.session_state.live_logs[-40:]


def _speed_settings(speed_mode):
    if speed_mode == "Slow":
        return 5, 0.25
    if speed_mode == "Fast":
        return 15, 0.05
    return 25, 0.0


def _add_event_context(dataframe, events):
    data = dataframe.copy()
    data["event_type"] = "Normal"
    data["hover_explanation"] = _event_message("NORMAL")

    for event in events:
        label = event.get("label", "UNKNOWN")
        start, end = _event_times(event)
        mask = (data["timestamp"] >= start) & (data["timestamp"] <= end)

        data.loc[mask, "event_type"] = _event_name(label)
        data.loc[mask, "hover_explanation"] = _event_message(label)

    return data


def _build_anomaly_points(dataframe, anomalies):
    points = []

    for anomaly in anomalies:
        start, _ = _event_times(anomaly)
        nearest = _nearest_point(dataframe, start)
        points.append({
            "timestamp": nearest["timestamp"],
            "value": anomaly.get("value", nearest["value"]),
            "event_type": "Anomaly",
            "hover_explanation": (
                anomaly.get("message")
                or "Anomaly detected: sudden deviation from normal behavior."
            ),
        })

    return pd.DataFrame(points)


def _downsample_frame(dataframe, max_points=MAX_CHART_POINTS):
    if len(dataframe) <= max_points:
        return dataframe

    step = max(1, len(dataframe) // max_points)
    return dataframe.iloc[::step].copy()


def _top_anomalies(anomalies, limit=5):
    return sorted(anomalies, key=_event_deviation, reverse=True)[:limit]


def _top_drifts(drift_events, limit=5):
    return sorted(
        drift_events,
        key=lambda event: event.get("duration_minutes", 0),
        reverse=True,
    )[:limit]


def _event_frequency_pattern(anomalies):
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


def _peak_occurrence_time(events):
    if not events:
        return "No events"

    hours = [pd.to_datetime(event.get("start_time")).hour for event in events]
    peak_hour = max(set(hours), key=hours.count)
    return f"{peak_hour:02d}:00-{peak_hour:02d}:59"


def _event_summary(result):
    drift_events = _drift_events(result)
    anomalies = _anomaly_events(result)
    max_deviation = max([_event_deviation(event) for event in anomalies], default=0)

    return {
        "drift_events": drift_events,
        "anomalies": anomalies,
        "total_anomalies": len(anomalies),
        "total_drifts": len(drift_events),
        "peak_occurrence": _peak_occurrence_time(anomalies),
        "max_deviation": max_deviation,
        "frequency_pattern": _event_frequency_pattern(anomalies),
        "top_anomalies": _top_anomalies(anomalies),
        "top_drifts": _top_drifts(drift_events),
    }


def _is_critical(event):
    return event.get("severity") == "HIGH"


def _focus_events(drift_events, anomalies):
    focus = st.session_state.get("event_focus", "All")

    if focus == "Critical":
        return (
            [event for event in drift_events if _is_critical(event)],
            [event for event in anomalies if _is_critical(event)],
        )
    if focus == "Anomalies":
        return [], anomalies
    if focus == "Drift":
        return drift_events, []
    return drift_events, anomalies


def _show_quick_action_buttons():
    if "event_focus" not in st.session_state:
        st.session_state.event_focus = "All"

    st.caption("Quick focus")
    col1, col2, col3, col4 = st.columns(4)

    if col1.button(
        "All Events",
        help="Show anomalies and drift together.",
        use_container_width=True,
    ):
        st.session_state.event_focus = "All"
    if col2.button(
        "Critical Only",
        help="Show only HIGH severity events that need attention first.",
        use_container_width=True,
    ):
        st.session_state.event_focus = "Critical"
    if col3.button(
        "Anomalies",
        help="Focus on sudden unusual points or spikes.",
        use_container_width=True,
    ):
        st.session_state.event_focus = "Anomalies"
    if col4.button(
        "Drift",
        help="Focus on longer behavior changes.",
        use_container_width=True,
    ):
        st.session_state.event_focus = "Drift"

    st.caption(f"Current focus: {st.session_state.event_focus}")


def _render_event_table(events, include_deviation=False):
    if not events:
        st.write("No events to show.")
        return

    rows = []
    for event in events:
        row = {
            "Type": _event_name(event.get("label", "UNKNOWN")),
            "Start": _format_time(event.get("start_time")),
            "End": _format_time(event.get("end_time")),
            "Duration (min)": round(float(event.get("duration_minutes", 0)), 2),
        }
        if include_deviation:
            row["Deviation"] = round(_event_deviation(event), 2)
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_event_filters(all_events):
    col1, col2 = st.columns([1, 2])
    with col1:
        event_type = st.selectbox(
            "Filter event type",
            ["All", "Concept Drift", "Anomaly"],
            key="graph_event_filter",
        )
    with col2:
        search_text = st.text_input(
            "Search timestamp",
            placeholder="Example: 2024-01-01 or 09:30",
            key="graph_event_search",
        )

    filtered = all_events
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


def plot_interactive_time_series(data, drift_events, anomalies):
    """Create an interactive Plotly time-series chart."""
    if go is None:
        return None

    visible_anomalies = _top_anomalies(anomalies)
    chart_data = _downsample_frame(_add_event_context(data, drift_events))
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_data["timestamp"],
        y=chart_data["value"],
        mode="lines",
        name="Normal",
        line={"color": NORMAL_COLOR, "width": 2},
        customdata=chart_data[["event_type", "hover_explanation"]],
        hovertemplate=(
            "Time: %{x}<br>"
            "Value: %{y}<br>"
            "Status: %{customdata[0]}<br>"
            "%{customdata[1]}"
            "<extra></extra>"
        )
    ))

    for index, event in enumerate(drift_events):
        start, end = _event_times(event)
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor=DRIFT_COLOR,
            opacity=0.18,
            layer="below",
            line_width=0,
            annotation_text="Concept Drift" if index == 0 else None,
            annotation_position="top left"
        )

    anomaly_points = _build_anomaly_points(data, visible_anomalies)
    if not anomaly_points.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_points["timestamp"],
            y=anomaly_points["value"],
            mode="markers",
            name="Top Anomalies",
            marker={
                "color": ANOMALY_COLOR,
                "size": 10,
                "line": {"color": "black", "width": 1}
            },
            customdata=anomaly_points[["event_type", "hover_explanation"]],
            hovertemplate=(
                "Time: %{x}<br>"
                "Value: %{y}<br>"
                "Status: %{customdata[0]}<br>"
                "%{customdata[1]}"
                "<extra></extra>"
            )
        ))

    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        name="Concept Drift",
        marker={"color": DRIFT_COLOR, "size": 10, "symbol": "square"}
    ))

    fig.update_layout(
        title="Interactive Time Series",
        xaxis_title="Timestamp",
        yaxis_title="Value",
        hovermode="x unified",
        legend_title="Color Meaning",
        margin={"l": 20, "r": 20, "t": 55, "b": 20}
    )

    return fig


def plot_event_timeline(events):
    """Create an interactive timeline of detected events."""
    if go is None:
        return None

    fig = go.Figure()

    if not events:
        fig.add_annotation(
            text="No events detected",
            x=0.5,
            y=0.5,
            showarrow=False,
            xref="paper",
            yref="paper"
        )
        return fig

    shown_labels = set()

    for index, event in enumerate(events):
        label = event.get("label", "UNKNOWN")
        start, end = _event_times(event)
        y_value = f"Event {index + 1}"
        color = DRIFT_COLOR if label == "CONCEPT_DRIFT" else ANOMALY_COLOR
        show_in_legend = label not in shown_labels
        shown_labels.add(label)

        fig.add_trace(go.Scatter(
            x=[start, end],
            y=[y_value, y_value],
            mode="lines",
            name=_event_name(label),
            line={"color": color, "width": 16},
            hovertemplate=(
                f"{_event_name(label)}<br>"
                f"Start: {_format_time(start)}<br>"
                f"End: {_format_time(end)}<br>"
                f"Duration: {event.get('duration_minutes', 0):.2f} minutes"
                "<extra></extra>"
            ),
            showlegend=show_in_legend
        ))

    fig.update_layout(
        title="Event Timeline",
        xaxis_title="Timestamp",
        yaxis_title="Detected Events",
        margin={"l": 20, "r": 20, "t": 55, "b": 20}
    )

    return fig


def plot_summary_chart(events):
    """Create an interactive summary chart."""
    if go is None:
        return None

    drift_count = len(_events_by_label(events, "CONCEPT_DRIFT"))
    anomaly_count = len(_events_by_label(events, "ANOMALY"))

    fig = go.Figure(go.Bar(
        x=["Concept Drift", "Anomaly"],
        y=[drift_count, anomaly_count],
        marker_color=[DRIFT_COLOR, ANOMALY_COLOR],
        text=[drift_count, anomaly_count],
        textposition="outside",
        hovertemplate="%{x}: %{y} events<extra></extra>"
    ))

    fig.update_layout(
        title="Event Summary",
        xaxis_title="Event Type",
        yaxis_title="Count",
        margin={"l": 20, "r": 20, "t": 55, "b": 20}
    )

    return fig


def generate_explanation_text(events):
    """Generate human-readable explanations for detected events."""
    if not events:
        return ["No unusual behavior was detected in this dataset."]

    explanations = []

    for event in events:
        label = event.get("label", "UNKNOWN")
        start, end = _event_times(event)

        if label == "CONCEPT_DRIFT":
            explanations.append(
                "Between "
                f"{_format_time(start)} and {_format_time(end)}, "
                "the system behavior changed for a longer period. "
                "This is marked as concept drift."
            )
        elif label == "ANOMALY":
            explanations.append(
                f"A sudden unusual change was detected around {_format_time(start)}. "
                "This is marked as an anomaly."
            )

    return explanations


def generate_key_insights(drift_events, anomalies):
    if not drift_events and not anomalies:
        return ["No unusual behavior was detected in this dataset."]

    insights = []
    if anomalies:
        strongest = _top_anomalies(anomalies, 1)[0]
        insights.append(
            f"{len(anomalies)} anomalies were found; the highest deviation occurred "
            f"around {_format_time(strongest.get('start_time'))}."
        )
        insights.append(f"Anomaly frequency pattern: {_event_frequency_pattern(anomalies)}.")
    if drift_events:
        longest = _top_drifts(drift_events, 1)[0]
        insights.append(
            f"{len(drift_events)} drift event(s) were found; the longest lasted "
            f"{longest.get('duration_minutes', 0):.2f} minutes."
        )
    insights.append(
        f"Peak event occurrence window: {_peak_occurrence_time(drift_events + anomalies)}."
    )
    return insights


def _latest_alert_event(result):
    events = _drift_events(result) + _anomaly_events(result)
    if not events:
        return None

    return sorted(events, key=lambda event: _event_times(event)[0])[-1]


def _show_latest_alert(result):
    event = _latest_alert_event(result)
    if event is None:
        st.success("Latest Alert: No drift or anomaly detected.")
        return

    label = _event_name(event.get("label", "UNKNOWN"))
    severity = event.get("severity", "LOW")
    message = f"Latest Alert: {label} at {_format_time(event.get('start_time'))} ({severity} severity)."

    if severity == "HIGH":
        st.error(message)
    elif event.get("label") in {"CONCEPT_DRIFT", "ANOMALY"}:
        st.warning(message)
    else:
        st.info(message)


def _show_top_insight(result):
    drift_events = _drift_events(result)
    anomalies = _anomaly_events(result)
    insight = generate_key_insights(drift_events, anomalies)[0]
    st.info(insight)


def _show_root_cause_summary(result):
    events = _drift_events(result) + _anomaly_events(result)
    root_rows = []

    for event in events:
        root_causes = event.get("root_causes", [])
        if not root_causes:
            continue

        top_cause = root_causes[0]
        root_rows.append({
            "Event": _event_name(event.get("label", "UNKNOWN")),
            "Time": _format_time(event.get("start_time")),
            "Likely Driver": top_cause.get("feature", "value"),
            "Summary": top_cause.get("message", "Change detected."),
        })

    if not root_rows:
        st.info("No root-cause summary is available for the detected events.")
        return

    st.dataframe(pd.DataFrame(root_rows[:5]), use_container_width=True, hide_index=True)


def _show_overview_tab(result):
    show_system_health_score(result)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Top Insight")
        _show_top_insight(result)
    with col2:
        st.subheader("Latest Alert")
        _show_latest_alert(result)

    st.subheader("Key Metrics")
    show_metrics(result)

    _show_quick_action_buttons()

    with st.expander("Why It Matters", expanded=True):
        show_why_it_matters(result)


def _show_insights_tab(result):
    show_explanation(result)

    with st.expander("Root Cause Summary", expanded=True):
        _show_root_cause_summary(result)


def _show_legend_text():
    st.caption(
        "Blue shows normal data. Red shaded regions indicate long-term behavior "
        "change, while orange points indicate sudden unusual spikes."
    )


def show_graphs(result):
    """Render interactive graph section using Plotly."""
    st.subheader("Interactive Graphs")

    if go is None:
        st.error("Plotly is not installed. Install it with: pip install plotly")
        return

    dataframe = result.get("dataframe")
    if dataframe is None or dataframe.empty:
        st.info("No time-series data available for graphing")
        return

    technical_view = st.checkbox("Show Technical View", value=False)

    summary = _event_summary(result)
    all_drift_events = summary["drift_events"]
    all_anomalies = summary["anomalies"]
    drift_events, anomalies = _focus_events(all_drift_events, all_anomalies)

    _show_legend_text()
    st.caption(
        f"Showing a simplified chart with up to {MAX_CHART_POINTS} sampled points "
        "and the top 5 anomalies by deviation."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Anomalies",
        summary["total_anomalies"],
        help="Total anomaly count in the complete analysis, before quick-focus filtering.",
    )
    col2.metric(
        "Peak Time",
        summary["peak_occurrence"],
        help="Hour of day where anomalies occur most often.",
    )
    col3.metric(
        "Max Deviation",
        f"{summary['max_deviation']:.2f}",
        help="Largest observed anomaly deviation from recent normal behavior.",
    )
    col4.metric(
        "Frequency",
        summary["frequency_pattern"],
        help="Whether anomalies are concentrated early, later, or evenly across the period.",
    )

    time_series_fig = plot_interactive_time_series(dataframe, drift_events, anomalies)
    if technical_view:
        time_series_fig.update_xaxes(rangeslider_visible=True)
    else:
        time_series_fig.update_xaxes(rangeslider_visible=False)

    st.plotly_chart(time_series_fig, use_container_width=True)

    st.write("Key insights")
    for explanation in generate_key_insights(drift_events, anomalies):
        st.info(explanation)

    combined_events = drift_events + anomalies
    st.plotly_chart(plot_summary_chart(combined_events), use_container_width=True)

    with st.expander("Top Events", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("Top 5 Anomalies")
            _render_event_table(_top_anomalies(anomalies), include_deviation=True)
        with col2:
            st.write("Top Drift Events")
            _render_event_table(_top_drifts(drift_events))

    with st.expander("Filter and Search Full Event List"):
        filtered_events = _render_event_filters(combined_events)
        _render_event_table(filtered_events[:50], include_deviation=True)
        if len(filtered_events) > 50:
            st.caption(f"Showing first 50 of {len(filtered_events)} matching events.")

    if technical_view:
        with st.expander("Full Event Timeline"):
            st.plotly_chart(plot_event_timeline(combined_events), use_container_width=True)
        with st.expander("Raw data preview"):
            st.dataframe(dataframe.head(100), use_container_width=True)


def show_live_monitor(result):
    """Replay the uploaded data as a simple live monitoring simulation."""
    st.subheader("⚡ Live Monitor")
    st.caption("Replay the uploaded dataset in batches to simulate active monitoring.")

    if "live_running" not in st.session_state:
        st.session_state.live_running = False
    if "live_logs" not in st.session_state:
        st.session_state.live_logs = []

    if go is None:
        st.error("Plotly is not installed. Install it with: pip install plotly")
        return

    dataframe = result.get("dataframe")
    events = result.get("drifts", [])

    if dataframe is None or dataframe.empty:
        st.info("No time-series data available for live simulation")
        return

    speed_mode = st.selectbox(
        "Simulation speed",
        ["Slow", "Fast", "Instant"],
        index=1,
        key="live_speed_mode"
    )
    batch_size, delay = _speed_settings(speed_mode)

    st.caption(
        f"{speed_mode} mode processes {batch_size} rows per update "
        f"with {delay:.2f}s delay between batches."
    )

    min_rows = min(10, len(dataframe))
    max_rows = st.number_input(
        "Rows to simulate",
        min_value=min_rows,
        max_value=len(dataframe),
        value=min(200, len(dataframe)),
        step=max(1, min_rows),
        key="live_max_rows"
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Start Live Simulation", disabled=st.session_state.live_running):
            st.session_state.live_running = True
            st.session_state.live_logs = ["Simulation started..."]

    with col2:
        if st.button("Stop Simulation", disabled=not st.session_state.live_running):
            st.session_state.live_running = False
            _add_live_log("Simulation stopped by user.")

    with col3:
        skip_simulation = st.button("Skip Simulation", disabled=st.session_state.live_running)

    drift_events = _drift_events(result)
    anomalies = _anomaly_events(result)
    all_monitor_events = drift_events + anomalies

    if skip_simulation:
        final_data = dataframe.head(int(max_rows))
        final_time = final_data.iloc[-1]["timestamp"]
        final_drift_events = _visible_events_until(drift_events, final_time)
        final_anomalies = _visible_events_until(anomalies, final_time)

        show_live_status_banner("Complete")
        show_status_panel("Normal", _last_event_at(final_time, all_monitor_events))
        st.progress(1.0)
        st.write(f"Processing batch complete: {len(final_data)} of {int(max_rows)} rows shown")
        _add_live_log("Simulation skipped. Showing final monitoring state.")
        st.write("Real-time logs")
        _render_logs(st.session_state.live_logs)

        figure = plot_interactive_time_series(
            final_data,
            final_drift_events,
            final_anomalies
        )
        figure.update_layout(title="Live Time Series Monitor - Final State")
        figure.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(figure, use_container_width=True)
        return

    if not st.session_state.live_running:
        show_live_status_banner("Waiting")
        show_status_panel("Waiting")
        st.info("Click Start Live Simulation to begin monitoring.")
        st.write("Real-time logs")
        _render_logs(st.session_state.live_logs)
        return

    from core.streaming import simulate_stream_batches

    show_live_status_banner("Running")
    _add_live_log("Analyzing incoming data...")

    status_placeholder = st.empty()
    alert_placeholder = st.empty()
    row_placeholder = st.empty()
    chart_placeholder = st.empty()
    log_placeholder = st.empty()
    progress_bar = st.progress(0)

    last_alert_key = None
    last_anomaly_keys = set()

    for batch in simulate_stream_batches(
        dataframe,
        batch_size=batch_size,
        delay=delay,
        max_rows=int(max_rows)
    ):
        row = batch["current_row"]
        current_data = batch["current_data"]
        current_time = row["timestamp"]
        active_drift = _active_event_at(current_time, drift_events)
        active_anomalies = [
            anomaly
            for anomaly in anomalies
            if batch["start_row"] <= anomaly.get("index", -1) + 1 <= batch["end_row"]
        ]
        active_anomaly = active_anomalies[0] if active_anomalies else None
        last_event = _last_event_at(current_time, all_monitor_events)

        if active_anomaly is not None:
            current_state = "Anomaly"
        elif active_drift is not None:
            current_state = "Drift"
        else:
            current_state = "Normal"

        with status_placeholder.container():
            show_live_status_banner(current_state)
            show_status_panel(current_state, last_event)
            st.caption(f"Latest point: {_format_time(current_time)} | Value: {row['value']}")

        with row_placeholder.container():
            progress_percent = batch["end_row"] / batch["total_rows"]
            st.write(
                f"Processing batch {batch['batch_number']} of {batch['total_batches']} "
                f"({progress_percent:.0%} complete)"
            )
            st.caption(
                f"Rows {batch['start_row']} to {batch['end_row']} of "
                f"{batch['total_rows']} are now visible."
            )

        _add_live_log(
            f"Processing batch {batch['batch_number']} "
            f"(rows {batch['start_row']}-{batch['end_row']})"
        )

        event_key = _event_key(active_drift)

        if event_key != last_alert_key:
            with alert_placeholder.container():
                trigger_alert(active_drift)
            if active_drift is not None:
                _add_live_log(_event_log_message(active_drift))
            last_alert_key = event_key

        for anomaly in active_anomalies:
            anomaly_key = _event_key(anomaly)
            if anomaly_key not in last_anomaly_keys:
                with alert_placeholder.container():
                    trigger_alert(anomaly)
                _add_live_log(_event_log_message(anomaly))
                last_anomaly_keys.add(anomaly_key)

        with log_placeholder.container():
            st.write("Real-time logs")
            _render_logs(st.session_state.live_logs)

        visible_drift_events = _visible_events_until(drift_events, current_time)
        visible_anomalies = _visible_events_until(anomalies, current_time)

        figure = plot_interactive_time_series(
            current_data,
            visible_drift_events,
            visible_anomalies
        )
        figure.update_layout(title="Live Time Series Monitor")
        figure.update_xaxes(rangeslider_visible=False)

        figure.add_trace(go.Scatter(
            x=[current_time],
            y=[row["value"]],
            mode="markers",
            name="Current Row",
            marker={
                "color": "#111111",
                "size": 13,
                "symbol": "circle-open",
                "line": {"width": 3}
            },
            hovertemplate=(
                "Current row<br>"
                "Time: %{x}<br>"
                "Value: %{y}"
                "<extra></extra>"
            )
        ))

        chart_placeholder.plotly_chart(figure, use_container_width=True)

        progress_bar.progress(batch["end_row"] / batch["total_rows"])

    with status_placeholder.container():
        show_live_status_banner("Complete")
        final_time = dataframe.iloc[int(max_rows) - 1]["timestamp"]
        show_status_panel("Normal", _last_event_at(final_time, all_monitor_events))

    st.session_state.live_running = False
    _add_live_log("Simulation complete.")
    with log_placeholder.container():
        st.write("Real-time logs")
        _render_logs(st.session_state.live_logs)

    st.success("Live simulation complete.")


def show_analysis_results(result):
    """Display pipeline output in beginner-friendly tabs."""
    st.header("📊 Analysis Results")
    st.success("Analysis Complete")

    tab_overview, tab_analysis, tab_insights, tab_live, tab_report = st.tabs([
        "Overview",
        "Analysis",
        "Insights",
        "Live Monitor",
        "Report",
    ])

    with tab_overview:
        _show_overview_tab(result)

    with tab_analysis:
        show_graphs(result)

    with tab_insights:
        _show_insights_tab(result)

    with tab_live:
        show_live_monitor(result)

    with tab_report:
        show_mis_report(result)
