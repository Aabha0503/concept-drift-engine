from utils.plot_utils import fig_to_base64
import matplotlib.pyplot as plt

def generate_window_mean_plot(window_times, window_stats):
    window_means = [s["mean"] for s in window_stats]

    plt.figure(figsize=(10, 4))
    plt.plot(window_times, window_means)
    plt.title("Window-wise Mean Over Time")
    plt.xlabel("Time")
    plt.ylabel("Mean Value")
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig_to_base64()
