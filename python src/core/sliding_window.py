class SlidingWindow:
    """
    Responsible for generating sliding windows over a time-series
    """

    def generate_windows(self, df, window_size: int, step_size: int):
        """
        Generates sliding windows from the dataframe.

        Returns:
            List of DataFrames (each representing a window)
        """

        windows = []
        total_rows = len(df)

        start = 0
        while start + window_size <= total_rows:
            window = df.iloc[start:start + window_size]
            windows.append(window)
            start += step_size

        return windows

