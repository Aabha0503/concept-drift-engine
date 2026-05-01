import numpy as np


class WindowStatistics:
    """
    Computes descriptive statistics for a single window
    """

    def compute(self, window_df):
        """
        Input: DataFrame with column 'value'
        Output: dict of statistics
        """

        values = window_df["value"].values

        mean = float(np.mean(values))
        variance = float(np.var(values))          # population variance
        median = float(np.median(values))

        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = float(q3 - q1)

        return {
            "mean": mean,
            "variance": variance,
            "median": median,
            "iqr": iqr
        }