# FINNY — Financial Statement Review Agent

FINNY is an end-to-end intelligent Financial Statement Review and Anomaly Detection system. It ingests multi-format financial filings (PDF, Excel, CSV, and Word `.docx`), applies deterministic accounting validation and multi-year ratio analysis, identifies anomalies using a machine learning Isolation Forest model, and performs grounded qualitative financial reasoning via a local GenAI engine (Ollama with `qwen2.5:7b`).

---

## 🏛️ Architecture Overview

```
User (Upload PDF / Excel / CSV / DOCX)
  │
  ▼
Document Extraction (PDF → tables, Excel/CSV → data, Word → tables/text)
  │
  ▼
Data Normalization (Revenue, assets, liabilities, equity, net income, cash...)
  │
  ▼
Agent 1 — Financial Validation & Analytics
  ├── Math Validation (Assets = Liabilities + Equity)
  ├── YoY Analysis (Current vs. previous fiscal years)
  └── Financial Ratios (Liquidity, profitability, leverage)
  │
  ▼
ML Model — Isolation Forest (Trained on financial filings dataset for anomaly detection)
  │
  ▼
Anomaly Detection Result (Normal / Unusual classification + Anomaly score)
  │
  ▼
Agent 1 Findings (Validations, Variances, Anomalies, Ratios, Evidence)
  │
  ▼
Agent 2 — AI Financial Review Agent
  ├── Investigate Findings (Deep-dive into flagged items)
  └── Compare Related Metrics (Cross-metric correlation analysis)
  │
  ▼
Ollama / GenAI Reasoning (Strictly grounded over verified analytical evidence)
  │
  ▼
Review Observations ({finding, explanation, severity, evidence, recommendation})
  │
  ▼
FINNY Dashboard (Risk Score, Financial Health, Anomalies, AI Review, Evidence)
```

---

## 📁 Repository Structure

```
.
├── Frontend/                           # React + Vite Financial Review Web Application
│   ├── src/                            # Components, pages, hooks, services
│   ├── package.json                    # Frontend dependencies
│   ├── .env.example                    # Frontend environment configuration template
│   └── vite.config.js                  # Vite configuration
│
└── Congizant Backend/
    └── finny-backend/                  # Active FastAPI Financial Review Backend
        ├── app/
        │   ├── api/                    # REST API endpoints (/upload, /process, /dashboard, /chat...)
        │   ├── core/                   # Security, JWT, config, CORS
        │   ├── database/               # SQLAlchemy models and SQLite/Postgres sessions
        │   ├── models/                 # ORM entities and Pydantic schemas
        │   └── services/               # Extraction, normalization, Agent 1, Agent 2, ML, Chat
        ├── ml_models/                  # Serialized Isolation Forest model
        ├── tests/                      # Pytest automated test suite (352 tests)
        ├── requirements.txt            # Python dependencies
        └── .env.example                # Backend environment configuration template
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python:** 3.11+
- **Node.js:** 18+
- **Ollama:** Running locally with model `qwen2.5:0.5b`
  ```bash
  ollama pull qwen2.5:0.5b
  ollama run qwen2.5:0.5b
  ```

### 2. Backend Setup
```bash
cd "Congizant Backend/finny-backend"
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run FastAPI Server (port 8001)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
Swagger documentation available at: `http://localhost:8001/docs`

### 3. Frontend Setup
```bash
cd Frontend
npm install
cp .env.example .env

# Run Vite Dev Server (port 5173)
npm run dev
```
Web application available at: `http://localhost:5173`

---

## 🧪 Testing

- **Backend Pytest Suite:**
  ```bash
  cd "Congizant Backend/finny-backend"
  pytest tests/ -q
  ```
- **Frontend Vitest Suite:**
  ```bash
  cd Frontend
  npm run test -- --run
  ```

---

## 🔒 Security & Privacy
- Zero credentials or API secrets stored in version control.
- Grounded GenAI architecture prevents hallucinations by constraining LLM responses strictly to verified mathematical output.
- Multi-tenant tenant-scoped document isolation with JWT authentication.
