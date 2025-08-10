# frontend/app.py
import streamlit as st
import requests
import pandas as pd
import altair as alt

st.set_page_config(page_title="Sentiment Analysis — Interactive", layout="wide")

BACKEND = st.sidebar.text_input("Backend URL", value="http://localhost:8000")
st.sidebar.markdown("Tip: run FastAPI backend first (`uvicorn backend.main:app --reload --port 8000`)")

st.title("📝 Sentiment Analysis — Choose Dataset / Upload / Validate")

# Fetch datasets on load
with st.spinner("Fetching available datasets..."):
    try:
        r = requests.get(f"{BACKEND}/datasets", timeout=10)
        r.raise_for_status()
        datasets_info = r.json().get("datasets", [])
        dataset_names = [d["name"] for d in datasets_info]
    except Exception as e:
        st.error(f"Could not fetch datasets: {e}")
        dataset_names = []

dataset_names.append("Custom (upload)")

selected = st.selectbox("Select dataset", dataset_names)

# Upload custom dataset UI
if selected == "Custom (upload)":
    st.info("Upload a CSV/XLSX/TXT with a 'text' column (or plain text lines).")
    upload = st.file_uploader("Upload dataset to backend", type=["csv","xlsx","txt"])
    if upload is not None:
        files = {"file": (upload.name, upload.getvalue())}
        name = st.text_input("Name for this dataset in backend", value="Custom")
        if st.button("Upload to backend"):
            resp = requests.post(f"{BACKEND}/upload_dataset", params={"name": name}, files=files)
            st.write(resp.json())

# Mode: single or batch
mode = st.radio("Mode", ["Single Input", "Batch Input"], horizontal=True)

validate_toggle = st.checkbox("Validate: ensure input exists in selected dataset", value=False)

if mode == "Single Input":
    text = st.text_area("Enter text to analyze", height=140)
    if st.button("Predict"):
        payload = {"dataset": selected if selected != "Custom (upload)" else name, "text": text, "validate_in_dataset": validate_toggle}
        with st.spinner("Calling backend..."):
            resp = requests.post(f"{BACKEND}/predict", json=payload)
        if resp.status_code != 200:
            st.error(resp.json())
        else:
            data = resp.json()
            r = data["results"][0]
            st.markdown("### Result")
            st.metric("Prediction", r["prediction"], delta=None)
            st.write(f"**Confidence:** {r['confidence']:.3f}")
            st.write(f"**Dataset used:** {data['dataset_used']}")
            st.write(f"**Text length:** {r['text_length']}")
            # show scores as bar chart
            scores = pd.DataFrame(list(r["scores"].items()), columns=["label","score"])
            chart = alt.Chart(scores).mark_bar().encode(x="label", y="score")
            st.altair_chart(chart, use_container_width=True)
            st.write("Full scores:")
            st.dataframe(scores)

else:
    st.write("Batch: paste lines or upload CSV/XLSX/TXT (need 'text' column for CSV/XLSX).")
    batch_input_type = st.radio("Batch input type", ["Paste lines", "Upload file", "Use dataset sample"])
    texts = []
    if batch_input_type == "Paste lines":
        pasted = st.text_area("Paste lines (one example per line)", height=200)
        if pasted:
            texts = [l.strip() for l in pasted.splitlines() if l.strip()]
    elif batch_input_type == "Upload file":
        bfile = st.file_uploader("Upload CSV/XLSX/TXT", type=["csv","xlsx","txt"])
        if bfile is not None:
            if bfile.name.lower().endswith(".csv"):
                df = pd.read_csv(bfile)
                if "text" not in df.columns:
                    df = df.rename(columns={df.columns[0]: "text"})
                texts = df["text"].astype(str).tolist()
            elif bfile.name.lower().endswith((".xls",".xlsx")):
                df = pd.read_excel(bfile)
                if "text" not in df.columns:
                    df = df.rename(columns={df.columns[0]: "text"})
                texts = df["text"].astype(str).tolist()
            else:
                s = bfile.getvalue().decode("utf-8")
                texts = [l.strip() for l in s.splitlines() if l.strip()]
    else:
        # request dataset sample from backend (dataset already loaded)
        if st.button("Use sample from backend dataset"):
            # fetch /datasets again to check sizes and then use sample n rows by calling predict later
            # Backend already has sample content; we'll let user run batch with empty texts -> error; instead show instruction
            st.info("Backend already holds dataset samples; paste or upload if you want to select particular rows.")

    if texts:
        st.write(f"Ready to predict {len(texts)} rows")
        max_rows = st.number_input("Limit rows (0 for all)", min_value=0, value=0)
        if max_rows > 0:
            texts = texts[:max_rows]
        if st.button("Run batch predict"):
            payload = {"dataset": selected if selected != "Custom (upload)" else name, "texts": texts, "validate_in_dataset": validate_toggle}
            with st.spinner("Running predictions... (this may take a bit)"):
                resp = requests.post(f"{BACKEND}/predict", json=payload, timeout=120)
            if resp.status_code != 200:
                st.error(resp.json())
            else:
                data = resp.json()
                df = pd.DataFrame([{
                    "text": r["text"],
                    "prediction": r["prediction"],
                    "confidence": r["confidence"],
                    "dataset_used": data["dataset_used"],
                    "text_length": r["text_length"],
                    **{f"score_{k}": v for k, v in r["scores"].items()}
                } for r in data["results"]])
                st.success("Batch predictions complete")
                st.dataframe(df.head(200))
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", data=csv, file_name="predictions.csv", mime="text/csv")
                # show distribution chart
                st.bar_chart(df["prediction"].value_counts())
