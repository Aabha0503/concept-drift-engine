from pathlib import Path


UPLOAD_DIR = Path(__file__).resolve().parents[1] / "temp_uploads"


def save_uploaded_file(uploaded_file):
    """Save a Streamlit uploaded file and return its path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_path = UPLOAD_DIR / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())

    return file_path
