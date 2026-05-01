import time

from utils.plot_utils import fig_to_base64
import matplotlib.pyplot as plt

def generate_raw_timeseries_plot(df):
    plt.figure(figsize=(10, 4))
    plt.plot(df["timestamp"], df["value"])
    plt.title(f"Raw Time Series (generated at {time.time()})")
    plt.xlabel("Time")
    plt.xticks(rotation=45)
    plt.ylabel("Value")
    plt.tight_layout()

    return fig_to_base64()
