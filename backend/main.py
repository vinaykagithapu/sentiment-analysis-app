from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from transformers import pipeline

# Load multiple models at startup
model_names = {
    "distilbert": "distilbert-base-uncased-finetuned-sst-2-english",
    "bertweet": "finiteautomata/bertweet-base-sentiment-analysis",
    "finbert": "ProsusAI/finbert"
}

models = {name: pipeline("sentiment-analysis", model=path) for name, path in model_names.items()}

class PredictRequest(BaseModel):
    text: str
    models: List[str]  # Selected model keys

app = FastAPI()

@app.post("/predict")
def predict(request: PredictRequest):
    results = []
    for model_key in request.models:
        if model_key not in models:
            continue
        model_pipeline = models[model_key]
        pred = model_pipeline(request.text)[0]
        results.append({
            "model": model_key,
            "label": pred["label"],
            "score": round(pred["score"], 4)
        })
    return {"predictions": results}

@app.get("/models")
def list_models():
    return {"available_models": list(models.keys())}