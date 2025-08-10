# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import os
import asyncio

# Transformers / datasets
from transformers import pipeline
from datasets import load_dataset

app = FastAPI(title="Sentiment Backend")

# Allow CORS from frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
BUILTIN_DATASETS = {
    "IMDB Reviews": {"loader": ("imdb", None)},
    "Yelp Reviews": {"loader": ("yelp_polarity", None)},
    "Twitter US Airline Sentiment": {"loader": ("tweet_eval", "sentiment")},
    "Sentiment140 (sample)": {"loader": ("sentiment140", None)},
    "Amazon Reviews (sample)": {"loader": ("amazon_polarity", None)},
}
SAMPLE_ROWS_PER_DATASET = 500  # adjust as needed
MODEL_NAME = os.getenv("SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")

# In-memory stores
DATASETS: Dict[str, pd.DataFrame] = {}
CLASSIFIER = None

# ----------------- Startup: load datasets & model -----------------
@app.on_event("startup")
async def startup_event():
    # Load datasets concurrently (simple concurrency)
    loop = asyncio.get_event_loop()
    tasks = []
    for name, meta in BUILTIN_DATASETS.items():
        tasks.append(loop.run_in_executor(None, load_dataset_sample, name, meta))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, dict) and res.get("name"):
            DATASETS[res["name"]] = res["df"]

    # Load classifier pipeline once (CPU by default)
    global CLASSIFIER
    CLASSIFIER = pipeline("sentiment-analysis", model=MODEL_NAME, device=-1)  # set device=0 for GPU
    print(f"Loaded classifier: {MODEL_NAME}")
    print(f"Available datasets: {list(DATASETS.keys())}")

def load_dataset_sample(name: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Load a small sample (pandas DataFrame) from datasets library"""
    try:
        ds_name, ds_config = meta["loader"]
        if ds_config:
            ds = load_dataset(ds_name, ds_config, split=f"train[:{SAMPLE_ROWS_PER_DATASET}]")
        else:
            ds = load_dataset(ds_name, split=f"train[:{SAMPLE_ROWS_PER_DATASET}]")
        # try to standardize to column names
        if "text" in ds.column_names:
            texts = ds["text"]
        elif "content" in ds.column_names:
            texts = ds["content"]
        elif "review" in ds.column_names:
            texts = ds["review"]
        else:
            # fall back to first text-like column
            texts = ds[ds.column_names[0]]
        # label handling: convert ints to strings where possible
        label_col = None
        for cand in ["label", "sentiment", "label-coarse"]:
            if cand in ds.column_names:
                label_col = ds[cand]
                break
        df = pd.DataFrame({"text": texts})
        if label_col is not None:
            df["label"] = label_col
        # lowercase text for easier validation checks
        df["text_lc"] = df["text"].astype(str).str.strip().str.lower()
        return {"name": name, "df": df}
    except Exception as e:
        print(f"Could not load dataset {name}: {e}")
        return {"name": name, "df": pd.DataFrame(columns=['text','text_lc'])}

# ----------------- Pydantic models -----------------
class PredictRequest(BaseModel):
    dataset: str
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    validate_in_dataset: Optional[bool] = False

class PredictResponse(BaseModel):
    dataset_used: str
    model: str
    results: List[Dict[str, Any]]

# ----------------- Endpoints -----------------
@app.get("/datasets")
def list_datasets():
    """Return available datasets and their sample sizes."""
    return {
        "datasets": [
            {"name": name, "rows": int(df.shape[0])}
            for name, df in DATASETS.items()
        ]
    }

@app.post("/upload_dataset")
async def upload_dataset(name: str = "Custom", file: UploadFile = File(...)):
    """Upload a dataset (CSV/XLSX/TXT), store in memory under given name."""
    content = await file.read()
    try:
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            # treat as text file: one example per line
            text = content.decode("utf-8")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            df = pd.DataFrame({"text": lines})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded file: {e}")
    if "text" not in df.columns:
        # try to use first column as text
        df = df.rename(columns={df.columns[0]: "text"})
    df["text_lc"] = df["text"].astype(str).str.strip().str.lower()
    DATASETS[name] = df
    return {"message": f"Uploaded dataset '{name}' with {len(df)} rows."}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if CLASSIFIER is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet.")
    # gather inputs
    inputs = []
    if req.text:
        inputs = [req.text]
    elif req.texts:
        inputs = req.texts
    else:
        raise HTTPException(status_code=400, detail="Provide 'text' or 'texts' for prediction.")

    # optional validation: ensure each text exists in selected dataset (case-insensitive)
    dataset_df = DATASETS.get(req.dataset)
    if req.validate_in_dataset:
        if dataset_df is None:
            raise HTTPException(status_code=400, detail=f"Dataset '{req.dataset}' not found for validation.")
        # lowercased check
        missing = []
        for t in inputs:
            if str(t).strip().lower() not in set(dataset_df["text_lc"].astype(str)):
                missing.append(t)
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Some inputs were not found in the selected dataset.",
                    "missing_count": len(missing),
                    "missing_examples": missing[:5],
                }
            )

    # Run classifier with return_all_scores to get distribution
    try:
        preds_all = CLASSIFIER(inputs, return_all_scores=True)
    except Exception as e:
        # fallback: per example
        preds_all = []
        for t in inputs:
            preds_all.append(CLASSIFIER(t, return_all_scores=True))

    results = []
    for text, preds in zip(inputs, preds_all):
        # preds is list of dicts like [{'label':'NEGATIVE','score':0.98}, {...}]
        # convert to mapping
        scores = {p['label']: float(p['score']) for p in preds}
        # choose top label
        top = max(preds, key=lambda x: x['score'])
        results.append({
            "text": text,
            "text_length": len(text),
            "prediction": top['label'],
            "confidence": float(top['score']),
            "scores": scores
        })

    return {
        "dataset_used": req.dataset,
        "model": MODEL_NAME,
        "results": results
    }
