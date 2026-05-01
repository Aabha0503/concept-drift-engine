from pyparsing import results

from core.data_loader import DataLoader
from core.deviation_detector import DeviationDetector
from core.drift_classifier import DriftClassifier
from core.sliding_window import SlidingWindow
from core.statistics import WindowStatistics
from core.explainer import DriftExplainer


def main():
    loader = DataLoader()

    window_engine = SlidingWindow()
    stats_engine = WindowStatistics()

    time_series = loader.load_csv(
        r"C:\Users\DELL\PycharmProjects\concept_drift_engine\python src\data\artificialNoAnomaly\artificialNoAnomaly\art_daily_no_noise.csv")

    windows = window_engine.generate_windows(
        time_series,
        window_size=50,
        step_size=10
    )

    for window in windows:
        stats = stats_engine.compute(window)
        print(stats)

        print("Total windows generated:", len(windows))

        #  //////////Test of sliding window //////////////
        print("\nFirst window preview:")
        print(windows[0].head())
        print("\nLast window preview:")
        print(windows[-1].tail())
        for i, window in enumerate(windows[:3]):
            stats:stats_engine.compute(window)
            print(f"\nStats for window {i}:", stats)

        #/////// test of satistics////////////
        for i in range(3):
            stats = stats_engine.compute(windows[i])
        print(f"\nStats for window {i}:")
        print(stats)

        #////////test of deviation detection//////////
        window_stats = []
        for w in windows:
            window_stats.append(stats_engine.compute(w))

    K = 5  # reference window size
    for i in range(K, K + 5):
        rw_stats = window_stats[i - K:i]
        dw_stats = window_stats[i]
        deviation_detector = DeviationDetector()
        deviation = deviation_detector.detect(rw_stats, dw_stats)
        print(f"\nWindow {i}:")
        print("Deviation result:", deviation)

    # /////////////// Test driftclassifier///////////////
    deviation_flags = []
    window_times = []
    for i in range(K, len(window_stats)):
        rw_stats = window_stats[i - K:i]
        dw_stats = window_stats[i]
        deviation = deviation_detector.detect(rw_stats, dw_stats)
        deviation_flags.append(deviation["deviation_detected"])
        window_times.append(windows[i]["timestamp"].iloc[0])
        classifier = DriftClassifier()
        results = classifier.classify(
            deviation_flags=deviation_flags,
            window_times=window_times,
            min_duration_minutes=60
        )
        print("\nDrift classification results:")
        for r in results:
            print(r)
    #//////////test drift explainer//////////////////
    explainer = DriftExplainer()
    print("\nExplainable Drift Results:\n")
    for r in results:
        start_time = r["start_time"]
        end_time = r["end_time"]
        duration = r["duration_minutes"]
        label = r["label"]

        # Find window indices
        start_idx = window_times.index(start_time)
        end_idx = window_times.index(end_time)

        # Reference windows (before drift)
        rw_stats = window_stats[max(0, start_idx - K):start_idx]

        # Detection windows (during drift)
        dw_stats = window_stats[start_idx:end_idx]

        explanation = explainer.explain(
            rw_stats_list=rw_stats,
            dw_stats_list=dw_stats,
            duration=duration,
            label=label
        )
        print(explanation)


if __name__ == "__main__":
    main()
