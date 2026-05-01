import pandas as pd


class DataLoader:
    """
    Responsible for loading and validating time-series CSV data
    """

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Loads a CSV file and returns a cleaned, sorted DataFrame
        with columns: [timestamp, value]
        """

        # Read CSV
        df = pd.read_csv(file_path)

        # Validate required columns
        required_columns = {"timestamp", "value"}
        if not required_columns.issubset(df.columns):
            raise ValueError(
                f"CSV must contain columns: {required_columns}"
            )

        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Sort by time
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Ensure value is numeric
        df["value"] = pd.to_numeric(df["value"], errors="raise")

        return df
