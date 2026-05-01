import matplotlib.pyplot as plt
from utils.plot_utils import fig_to_base64

def generate_drift_timeline(drift_results):
    """
    drift_results: list of dicts with
    - label: ANOMALY / CONCEPT_DRIFT
    - start_time
    - end_time
    """

    plt.figure(figsize=(12, 2))

    for r in drift_results:
        if r["label"] == "CONCEPT_DRIFT":
            color = "red"
        else:
            color = "orange"

        plt.axvspan(
            r["start_time"],
            r["end_time"],
            color=color,
            alpha=0.3
        )

    plt.title("Anomaly vs Concept Drift Timeline")
    plt.xlabel("Time")
    plt.yticks([])  # cleaner timeline
    plt.tight_layout()

    return fig_to_base64()
