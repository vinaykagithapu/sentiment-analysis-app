# 📝 Sentiment Analysis Web App

A simple NLP web application that classifies text as **Positive**, **Negative**, or **Neutral** using a pre-trained HuggingFace Transformer model.

---

## 📌 Overview
This app allows users to type or paste text into a box and instantly see the predicted sentiment along with the model’s confidence score.

---

## 🎥 Demo
![Demo Screenshot](assets/demo.png)

---

## ✨ Features
- Real-time sentiment prediction
- Confidence score display
- Clean, responsive UI
- Built with Streamlit & HuggingFace

---

## 🛠 Tech Stack
- Python
- Streamlit
- HuggingFace Transformers
- PyTorch

---

## ⚙️ Setup & Run Locally
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/sentiment-analysis-app.git
cd sentiment-analysis-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure HF Token
export HUGGING_FACE_HUB_TOKEN=<huggingface_token>

# Start the Backend
uvicorn backend.main:app --reload --port 8000

# Start Frontend
streamlit run frontend/app.py

# Run app
streamlit run app.py
```
