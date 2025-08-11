import streamlit as st
import requests

API_URL = "http://localhost:8000/predict"

st.set_page_config(page_title="Multi-Model Sentiment Analysis", layout="wide")
st.title("🧠 Multi-Model Sentiment Analysis")

# Available models (must match backend keys)
model_options = {
    "distilbert": "DistilBERT (English)",
    "bertweet": "BERTweet",
    "deberta": "DeBERTa"
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
            predictions = response.json()["predictions"]
            st.subheader("Results")
            for pred in predictions:
                model_name = model_options.get(pred["model"], pred["model"])
                st.write(f"**{model_name}** → {pred['label']} ({pred['score']*100:.2f}% confidence)")
        else:
            st.error("Error fetching predictions from backend.")
