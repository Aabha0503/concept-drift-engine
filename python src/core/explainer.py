import numpy as np


class DriftExplainer:
    """
    Generates feature-level explanations for drift/anomaly events
    """

    def explain(self, rw_stats_list, dw_stats_list, duration, label):
        """
        rw_stats_list: list of dicts (reference windows)
        dw_stats_list: list of dicts (windows during deviation)
        """

        def avg(feature, stats):
            return np.mean([s[feature] for s in stats])

        explanation = {
            "label": label,
            "duration_minutes": duration,
            "before": {},
            "after": {},
            "delta": {}
        }

        def to_float(x):
            return float(x)

        for feature in ["mean", "median", "variance", "iqr"]:
            before_val = avg(feature, rw_stats_list)
            after_val = avg(feature, dw_stats_list)

            explanation["before"][feature] = to_float(before_val)
            explanation["after"][feature] = to_float(after_val)
            explanation["delta"][feature] = to_float(after_val - before_val)
            return explanation
