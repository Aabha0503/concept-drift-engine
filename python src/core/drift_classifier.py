class DriftClassifier:
    """
    Classifies deviation sequences into ANOMALY or CONCEPT_DRIFT
    using time-based persistence
    """

    def classify(self, deviation_flags, window_times, min_duration_minutes):
        """
        deviation_flags: list of booleans (True if deviation detected)
        window_times: list of window start timestamps
        min_duration_minutes: threshold for drift
        """

        results = []
        current_start = None

        for i, is_deviation in enumerate(deviation_flags):
            if is_deviation and current_start is None:
                current_start = window_times[i]

            if not is_deviation and current_start is not None:
                duration = (window_times[i] - current_start).total_seconds() / 60

                label = (
                    "CONCEPT_DRIFT"
                    if duration >= min_duration_minutes
                    else "ANOMALY"
                )

                results.append({
                    "start_time": current_start,
                    "end_time": window_times[i],
                    "duration_minutes": duration,
                    "label": label
                })

                current_start = None

        return results
