from utils.plot_utils import fig_to_base64
import matplotlib.pyplot as plt

def generate_deviation_timeline(window_times, deviation_flags):
    """
    window_times: list of timestamps (aligned with deviation_flags)
    deviation_flags: list of True / False
    """

    deviation_numeric = [1 if d else 0 for d in deviation_flags]

    plt.figure(figsize=(10, 3))
    plt.step(window_times, deviation_numeric, where="post")
    plt.ylim(-0.1, 1.1)
    plt.yticks([0, 1], ["Normal", "Deviation"])
    plt.title("Deviation Timeline (Window-level)")
    plt.xlabel("Time")
    plt.ylabel("Deviation")
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig_to_base64()
