import matplotlib.pyplot as plt
import io
import base64

def fig_to_base64():
    """
    Converts the current matplotlib figure to a base64 string.
    """
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
