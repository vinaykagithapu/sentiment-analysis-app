import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/predict")

st.set_page_config(page_title="Multi-Model Sentiment Analysis", layout="wide")
st.title("🧠 Multi-Model Sentiment Analysis")

# Available models (must match backend keys)
model_options = {
    "distilbert": "DistilBERT (English)",
    "bertweet": "BERTweet",
    "finbert": "FinBERT"
}

selected_models = st.multiselect("Select Models", list(model_options.keys()), default=["distilbert"])
text_input = st.text_area("Enter text to analyze", "I love this product!")

if st.button("Analyze Sentiment"):
    if not selected_models or not text_input.strip():
        st.warning("Please enter text and select at least one model.")
    else:
        payload = {"text": text_input, "models": selected_models}
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            predictions = response.json().get("predictions", [])

            if predictions:
                # Create DataFrame for a nice table view
                df = pd.DataFrame([
                    {
                        "Model": model_options.get(pred["model"], pred["model"]),
                        "Label": pred["label"],
                        "Confidence (%)": f"{pred['score']*100:.2f}"
                    }
                    for pred in predictions
                ])

                st.subheader("Results")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No predictions returned from backend.")
        else:
            st.error("Error fetching predictions from backend.")
