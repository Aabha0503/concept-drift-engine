from fastapi import FastAPI
from pydantic import BaseModel
from core.pipeline import run_pipeline

app = FastAPI()


class AnalysisRequest(BaseModel):
    csv_path: str


@app.post("/analyze")
def analyze(request: AnalysisRequest):
    result = run_pipeline(csv_path=request.csv_path)
    return result
