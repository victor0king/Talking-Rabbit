# Talking Rabbitt — AI-Powered Business Intelligence Dashboard

> **Research-grade schema degradation benchmarking platform** with conversational AI analytics,
> unsupervised ML clustering, time-series forecasting, and auto-generated executive reports.

An AI-powered "talking dashboard" that ingests business spreadsheets, automatically
analyzes them, and lets users converse with the data in natural language — by text
or voice — instead of reading static charts.

---

## ✨ Features

### Core Analytics
- **CSV/Excel Upload** — drag-and-drop with auto-cleaning (null imputation, deduplication, date parsing, column type classification)
- **KPI Dashboard** — auto-generated cards, trend charts, top/worst performers, and anomaly detection
- **Ask Rabbitt** — conversational AI chat (text or voice) with LLM tool-calling grounded in your actual data
- **Forecast** — Prophet-style seasonality + trend and Linear Regression baselines with uncertainty bands
- **Executive Report** — auto-generated business health summary with risks, strengths, and prioritized recommendations

### Advanced ML & Analytics
- **DBSCAN Clustering** — unsupervised density-based clustering with PCA 2D projections, Silhouette scoring, and segment profiling
- **Isolation Forest** — anomaly detection with contamination controls and outlier scoring
- **Correlation Matrix** — Pearson correlation heatmaps with strong-correlation flagging
- **Z-Score Analysis** — statistical outlier detection across numeric columns

### Research & Benchmarking
- **Schema Degradation Benchmarking** — 750-trial suite across 5 SME datasets (Sales, Inventory, Finance, Customer, Operations)
- **D0–D4 Degradation Pipeline** — progressive schema corruption: abbreviations, type noise, decoy columns, cryptic encoding
- **Statistical Analysis** — Wilson score confidence intervals, Cochran-Armitage trend tests, Cohen's kappa inter-run stability
- **Research Demo Page** — interactive visualization of degradation architecture and degraded schema previews
- **CSV Export** — download full benchmark results for external analysis

---

## 🏗 Architecture

```
frontend/            HTML5 + CSS3 + vanilla JS (no framework, no build step)
├── css/             Stylesheets with dark glassmorphism theme
├── js/              Per-page scripts (dashboard, chat, forecast, benchmark, clustering, etc.)
└── *.html           11 pages (home, dashboard, chat, upload, forecast, report, benchmark,
                     research, clustering, login, sign_up)

backend/
├── main.py          FastAPI app entrypoint with CORS, static file serving
├── config.py        Environment configuration (Settings class)
├── database.py      SQLAlchemy engine with MySQL→SQLite auto-fallback
├── models.py        ORM models (Dataset, ChatHistory, Report, Forecast, User, BenchmarkResult)
├── schemas.py       Pydantic request/response contracts
├── crud.py          All DB reads/writes
├── routes/          One file per feature area
│   ├── upload.py    File upload + cleaning pipeline
│   ├── analytics.py KPI dashboard data
│   ├── chat.py      Conversational AI endpoint
│   ├── forecast.py  Time-series forecasting
│   ├── clustering.py DBSCAN + anomaly detection
│   ├── benchmark.py Schema degradation benchmark runner + export
│   └── ...
├── services/        Business logic (pure functions, no HTTP/DB knowledge)
│   ├── pandas_processor.py     Data cleaning, typing, KPIs
│   ├── analytics_engine.py     Trends, anomalies, comparisons, risk detection
│   ├── forecast_engine.py      Prophet-style + linear regression forecasting
│   ├── benchmark_runner.py     750-trial benchmark execution engine
│   ├── benchmark_scorer.py     Classification scoring (CBW, hedging, tolerance)
│   ├── statistics_engine.py    Wilson CI, trend tests, kappa
│   ├── schema_degrader.py      D0–D4 degradation pipeline
│   ├── clustering_engine.py    DBSCAN + PCA + Silhouette
│   ├── anomaly_engine.py       Z-score + Isolation Forest
│   ├── correlation_engine.py   Pearson correlation matrix
│   ├── chat_engine.py          LLM tool-calling orchestration
│   └── ...
└── utils/           Logger, validators, helpers

benchmark/
├── datasets/        30 CSV files (5 domains × 6 levels: clean + D0–D4)
├── questions.json   30 benchmark questions + 15 ambiguous probes
├── ground_truth.json Ground truth values for scoring
├── demo_results.json Pre-generated 750-trial results
└── generate_sme_benchmark.py  Dataset + degradation generator

storage/             SQLite DB + parquet cache (auto-created)
```

**Key design:** The database stores only *metadata* — dataset info, chat history, reports, forecasts, benchmark results. The actual cleaned dataframes live in-memory and as parquet caches, keeping analytics fast.

---

## 🚀 Quick Start

### 1. Clone & install
```bash
git clone https://github.com/victor0king/Talking-Rabbit.git
cd Talking-Rabbit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure (optional)
```bash
cp .env.example .env
# Edit .env with your MySQL credentials and API keys
# If no MySQL is available, SQLite is used automatically
```

### 3. Run
```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**

> **No MySQL?** No problem — the app auto-falls back to SQLite at `storage/talking_rabbitt.db`.
> **No API key?** Chat falls back gracefully; Dashboard, Forecast, Report, Benchmark, and Clustering all work independently.

---

## 📊 Schema Degradation Benchmark

The benchmark evaluates LLM resilience to progressively degraded data schemas:

| Level | Description | Example |
|-------|-------------|---------|
| **D0** | Ambiguous questions on clean data | "What's the total revenue?" (multiple revenue columns) |
| **D1** | Column name abbreviations | `revenue` → `rev`, `quantity` → `qty` |
| **D2** | Type noise + format corruption | Dates as epoch, currency as text ("$2,400") |
| **D3** | Decoy columns injected | Plausible-sounding fake columns added |
| **D4** | Cryptic encoding | Column names replaced with codes (`COL_A1`, `FLD_X9`) |

**750 trials** across 5 SME domains with Wilson score confidence intervals and Cochran-Armitage trend analysis.

---

## 🧪 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/upload` | Upload CSV/Excel |
| `GET` | `/api/analytics/dashboard/{id}` | Dashboard KPIs |
| `POST` | `/api/chat` | Chat with data |
| `POST` | `/api/forecast/run` | Run forecast |
| `POST` | `/api/clustering/run` | DBSCAN clustering |
| `GET` | `/api/benchmark/results` | Benchmark results |
| `POST` | `/api/benchmark/run-single` | Run single probe |
| `GET` | `/api/benchmark/export-csv` | Export results CSV |
| `GET` | `/api/research/architecture` | Degradation architecture |
| `GET` | `/api/research/preview-degraded` | Preview degraded data |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, vanilla JS, Chart.js, Web Speech API |
| Backend | FastAPI, SQLAlchemy, Uvicorn |
| Database | MySQL (primary) / SQLite (auto-fallback) |
| Analytics | Pandas, NumPy, scikit-learn, SciPy |
| ML | DBSCAN, Isolation Forest, PCA, Linear Regression, Fourier decomposition |
| AI | Anthropic API (Claude) with tool-calling |
| Fonts | Space Grotesk, Inter, JetBrains Mono |

---

## 📄 License

MIT
