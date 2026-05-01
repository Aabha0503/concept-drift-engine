from core.data_loader import DataLoader
from core.anomaly_detection import detect_point_anomalies
from core.deviation_detector import DeviationDetector
from core.drift_classifier import DriftClassifier
from core.insights import analyze_root_cause
from core.sliding_window import SlidingWindow
from core.statistics import WindowStatistics


def run_pipeline(
        csv_path,
        window_size=50,
        step_size=10,
        K=5,
        min_duration_minutes=60,
        alpha=2.0,
        beta=1.5
):
    loader = DataLoader()
    window_engine = SlidingWindow()
    stats_engine = WindowStatistics()
    deviation_detector = DeviationDetector()
    classifier = DriftClassifier()

    # 1. Load and validate the uploaded CSV.
    df = loader.load_csv(csv_path)
    point_anomalies = detect_point_anomalies(
        df,
        window_size=window_size,
        threshold=2.0
    )

    # 2. Split the time series into sliding windows.
    windows = window_engine.generate_windows(df, window_size, step_size)
    window_stats = [stats_engine.compute(window) for window in windows]
    window_times = [window["timestamp"].iloc[0] for window in windows]

    # 3. Detect statistical deviations window by window.
    deviation_flags = []
    for i in range(K, len(window_stats)):
        reference_windows = window_stats[i - K:i]
        detection_window = window_stats[i]

        deviation = deviation_detector.detect(
            reference_windows,
            detection_window,
            alpha=alpha,
            beta=beta
        )
        deviation_flags.append(deviation["deviation_detected"])

    # 4. Classify deviation periods as anomalies or concept drift.
    drift_results = classifier.classify(
        deviation_flags=deviation_flags,
        window_times=window_times[K:],
        min_duration_minutes=min_duration_minutes
    )
    drift_results = analyze_root_cause(df, drift_results)

    return {
        "drifts": drift_results,
        "anomalies": point_anomalies,
        "dataframe": df
    }
