---
title: AI Data Analyst
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AI Data Analyst 📊

An end-to-end autonomous data analyst web platform designed for non-technical and moderately technical users. Upload CSV or Excel files, explore instant health scorecards, execute 15 deterministic cleaning transformations, view interactive visualizations, and receive executive AI narrative reports.

---

## 🌟 Core Features

- **Defensive Ingestion**: Accepts CSV and XLSX files under 25 MB with automatic delimiter, character encoding (via `chardet`), and column header sanitization.
- **Data Health Scorecard (0–100)**: Detects missingness, constant columns, duplicate rows, IQR outliers, and PII leaks (emails, phones, SSNs, credit cards).
- **15 Deterministic Cleaning Operations**:
  - Missing values: `fill_missing` (mean, median, mode, constant), `drop_missing_rows`.
  - Hygiene: `remove_duplicates`, `trim_text`, `normalize_case`.
  - Schema: `convert_type`, `rename_column`, `drop_columns`.
  - Numeric & Outliers: `numeric_round`, `clip_values`, `handle_outliers` (IQR clipping/filtering).
  - Dates: `parse_date`, `create_date_part`.
- **AI Operation Planner**: Natural language conversation interface translating user intents into validated JSON operations with pre-flight dry runs and human approval.
- **Statistical Analysis & Visualizations**: Parametric/non-parametric summaries, Pearson correlation matrix ($|r| \ge 0.4$), and automated chart recommendations (Bar, Line, Scatter, Histogram, Heatmap).
- **Executive Narrative Reports & Exporter**: Synthesizes narrative findings into Markdown, HTML, and JSON reports with one-click CSV and Excel (`.xlsx`) downloads.
- **Immutable Version History & Lineage**: Non-destructive append-only version snapshots with semantic diffing and one-click safe rollbacks.

---

## 🚀 Running Locally

### 1. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🐳 Deployment to Hugging Face Spaces

This repository is ready to deploy directly to Hugging Face Spaces:
1. Create a new Space on [Hugging Face](https://huggingface.co/new-space).
2. Choose **Docker** as the Space SDK.
3. Push or sync this repository to your Space.
4. Hugging Face will automatically execute the multi-stage `Dockerfile` and serve the full-stack application on port 7860!

<!--
================================================================================
FILE SUMMARY: README.md
================================================================================
WHAT THIS FILE CONTAINS AND DOES:
This file documents the project architecture, features, and deployment instructions:
  1. Contains Hugging Face Spaces YAML frontmatter specifying Docker SDK and port 7860.
  2. Outlines platform capabilities (ingestion, health, 15 transforms, AI planner, charts, reports).
  3. Provides local development startup instructions for backend and frontend.
================================================================================
-->
