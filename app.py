# app.py - Streamlit dashboard for the AI Learning Journey
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

# ------------------------------------------------------------------
# 0. Constants & helpers
DB_PATH = Path(os.getenv("SQLITE_PATH", "dashboard.db"))
ARTIFACTS_PATH = Path("artifacts")
DATA_PATH = ARTIFACTS_PATH / "data"
MODELS_PATH = ARTIFACTS_PATH / "models"
SPECIALIZATION_PATH = ARTIFACTS_PATH / "specialization"

PHASES = [
    ("Mindset", "00_mindset"),
    ("Data Foundations", "01_data"),
    ("Model Building", "02_model"),
    ("Specialization", "03_specialization"),
    ("Ethics & Deployment", "04_ethics"),
]


# 1. SQLite wrapper: initialise & CRUD
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                status TEXT CHECK(status IN ('not_started','running','completed','failed')) NOT NULL,
                progress REAL DEFAULT 0,
                mlflow_run_id TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Ensure every phase row exists
        for name, _key in PHASES:
            con.execute(
                "INSERT OR IGNORE INTO phases (name, status) VALUES (?, 'not_started')",
                (name,),
            )


def set_phase(name, status, progress=0.0, mlflow_run_id=None):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            UPDATE phases
            SET status = ?, progress = ?, mlflow_run_id = ?, last_updated = ?
            WHERE name = ?
            """,
            (status, progress, mlflow_run_id, datetime.utcnow(), name),
        )


def get_phases():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT name, status, progress, mlflow_run_id FROM phases")
        return [(row[0], row[1], row[2], row[3]) for row in cur]


# 2. Load config
with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

# 3. Streamlit UI
st.set_page_config(page_title=cfg["title"], layout="wide", initial_sidebar_state="expanded")
st.title(cfg["title"])
st.caption(f"Version {cfg['version']} - Powered by Streamlit")

# 4. Sidebar: phase selector + status
st.sidebar.header("Learning Journey")
init_db()
phases = get_phases()

for name, status, progress, _run_id in phases:
    if status == "running":
        st.sidebar.progress(min(max(progress, 0.0), 1.0))
    st.sidebar.write(f"{name} - {status}")

with st.sidebar.expander("Update Current Phase"):
    phase_name = st.selectbox("Select phase", options=[p[0] for p in PHASES])
    progress_pct = st.slider("Progress", 0, 100, 0) / 100.0
    col_a, col_b = st.columns(2)
    if col_a.button("Mark Running"):
        set_phase(phase_name, "running", progress_pct)
        st.sidebar.success(f"{phase_name} running - {progress_pct * 100:.0f}%")
    if col_b.button("Mark Completed"):
        set_phase(phase_name, "completed", 1.0)
        st.sidebar.success(f"{phase_name} completed!")

# 5. Main content: tabs
tabs = st.tabs(["Data Overview", "Model Health", "Specialization", "Ethics & Deployment"])

# ---- 5.1 Data Overview ----
with tabs[0]:
    st.subheader("Raw Data - Preview & Distribution")
    csv_files = sorted(DATA_PATH.glob("*.csv"))
    if csv_files:
        df = pd.read_csv(csv_files[0])
        st.dataframe(df.head(10))
        if "target" in df.columns:
            fig = px.histogram(df, x="target", color="target", barmode="overlay",
                               title="Target Distribution")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No CSV files in artifacts/data/. Upload one to see a preview.")

# ---- 5.2 Model Health ----
with tabs[1]:
    st.subheader("Model Performance & Metrics")
    metrics_file = MODELS_PATH / "metrics.json"
    if metrics_file.is_file():
        with open(metrics_file) as f:
            metrics = json.load(f)
        st.json(metrics)
        if "roc_curve" in metrics:
            tpr = metrics["roc_curve"]["tpr"]
            fpr = metrics["roc_curve"]["fpr"]
            fig = px.line(x=fpr, y=tpr, title="ROC Curve",
                          labels={"x": "False Positive Rate", "y": "True Positive Rate"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No model metrics found. Train a model in the Model Building phase.")

    mlflow_run_id = next((r for _, _, _, r in phases if r), None)
    if mlflow_run_id:
        mlflow_base = cfg.get("mlflow_base_url", "http://localhost:5000")
        run_url = f"{mlflow_base}/#/experiments/{mlflow_run_id}"
        st.markdown(f"[View MLflow Run]({run_url})")

# ---- 5.3 Specialization ----
with tabs[2]:
    st.subheader("Specialization Tracks")
    nb_files = sorted(SPECIALIZATION_PATH.glob("*.ipynb"))
    if nb_files:
        for nb in nb_files:
            st.write(f"- {nb.stem} (completed)")
    else:
        st.info("No specialization notebooks in artifacts/specialization/.")

# ---- 5.4 Ethics & Deployment ----
with tabs[3]:
    st.subheader("Ethics & Deployment Checklist")
    checklist = [
        ("Bias audit performed", "bias_audit"),
        ("Model version logged", "model_logged"),
        ("Docker image built", "docker_built"),
        ("Public endpoint reachable", "endpoint_live"),
    ]
    for text, key in checklist:
        st.checkbox(text, key=key)
