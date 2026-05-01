import numpy as np


class DeviationDetector:
    """
    Detects statistical deviation between RW and DW
    """

    def detect(self, rw_stats_list, dw_stats, alpha=2.0, beta=1.5):
        """
        rw_stats_list: list of dicts (stats of last K windows)
        dw_stats: dict (stats of current window)
        """

        # Aggregate RW statistics
        mean_rw = np.mean([s["mean"] for s in rw_stats_list])
        median_rw = np.mean([s["median"] for s in rw_stats_list])
        iqr_rw = np.mean([s["iqr"] for s in rw_stats_list])

        std_rw = np.sqrt(np.mean([s["variance"] for s in rw_stats_list]))

        # Deviations
        mean_shift = abs(dw_stats["mean"] - mean_rw)
        median_shift = abs(dw_stats["median"] - median_rw)

        mean_deviation = mean_shift > alpha * std_rw if std_rw > 0 else False
        median_deviation = median_shift > beta * iqr_rw if iqr_rw > 0 else False

        return {
            "mean_deviation": mean_deviation,
            "median_deviation": median_deviation,
            "deviation_detected": mean_deviation or median_deviation
        }