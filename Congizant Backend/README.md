# FINNY — Financial Statement Extraction & Normalization Backend

A production-ready, backend-only system for ingesting financial statements (PDF, Excel, CSV), extracting structured tabular data, and applying canonical accounting normalization.

---

## 1. Project Overview

**FINNY** provides a foundational ingestion and normalization layer for financial documents. It accepts raw files, abstracts away the differences between document formats (PDF, Excel, CSV), transforms them into a unified internal representation, and normalizes them into a canonical financial schema with standardized field keys, numeric floats, ISO currencies, and standardized reporting periods.

> [!IMPORTANT]
> **Strict Backend Scope**: This system contains NO frontend, NO UI dashboard, and NO downstream ML/AI analysis agents (e.g. Isolation Forest, anomaly detection, YoY calculations, Ollama, GenAI). The scope concludes after Data Normalization and persisting/returning the normalized dataset.

---

## 2. System Architecture

```
                    BACKEND ONLY
                         │
                         ▼
              ┌─────────────────────┐
              │   File Upload API   │
              │  PDF / Excel / CSV  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Document Extraction │
              │                     │
              │ PDF → Tables        │
              │ Excel → Data        │
              │ CSV → Data          │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Data Normalization │
              │                     │
              │ Revenue             │
              │ Assets              │
              │ Liabilities         │
              │ Equity              │
              │ Dates / Currency    │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Normalized Dataset  │
              │                     │
              │ JSON / PostgreSQL   │
              └─────────────────────┘

                    END OF SCOPE
```

### Document Status Lifecycle
```
UPLOADED  ──►  EXTRACTING  ──►  EXTRACTED  ──►  NORMALIZING  ──►  NORMALIZED
     │              │                                │
     ▼              ▼                                ▼
   (Error)  EXTRACTION_FAILED              NORMALIZATION_FAILED
```

---

## 3. Technology Stack

- **Runtime**: Python 3.11+ (verified with Python 3.13)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Data Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Database & ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [PostgreSQL](https://www.postgresql.org/) (via `psycopg2-binary`, SQLite supported for local testing)
- **Spreadsheet Processing**: [pandas](https://pandas.pydata.org/) & [openpyxl](https://openpyxl.readthedocs.io/)
- **PDF Processing**: [pdfplumber](https://github.com/jsvine/pdfplumber) & [PyMuPDF](https://pymupdf.readthedocs.io/)
- **Testing**: [pytest](https://docs.pytest.org/) & [httpx](https://www.python-httpx.org/)

---

## 4. Project Structure

```
finny-backend/
│
├── app/
│   ├── main.py                      # FastAPI app instance, CORS middleware, lifespan events
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py          # API V1 router aggregation
│   │       ├── upload.py            # POST /api/v1/documents/upload
│   │       └── documents.py         # POST /process, GET /{id}, GET /{id}/normalized
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extraction/
│   │   │   ├── __init__.py
│   │   │   ├── base_extractor.py    # Abstract BaseExtractor class
│   │   │   ├── pdf_extractor.py     # PDF table & text line extractor
│   │   │   ├── excel_extractor.py   # Multi-sheet Excel workbook extractor
│   │   │   ├── csv_extractor.py     # Delimiter-sniffing CSV extractor
│   │   │   └── extractor_factory.py # Factory resolving extractor by extension
│   │   │
│   │   └── normalization/
│   │       ├── __init__.py
│   │       ├── normalizer.py        # Normalization orchestrator
│   │       ├── field_mapper.py      # Canonical taxonomy dictionary mapper
│   │       ├── value_cleaner.py     # Financial number parser (commas, scales, negatives)
│   │       ├── date_normalizer.py   # ISO date and fiscal year parser
│   │       └── currency_normalizer.py # ISO-4217 standard currency detector (no conversion)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py              # Document SQL model
│   │   └── financial_data.py        # FinancialData SQL model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── upload.py                # Upload & Status Pydantic schemas
│   │   └── financial.py             # Raw & Normalized financial schemas
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py              # Engine, Base, session maker, init_db
│   │   └── session.py               # Dependency injection get_db session generator
│   │
│   └── core/
│       ├── __init__.py
│       └── config.py                # Configuration and environment variables
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures and sample generators
│   ├── test_upload.py               # Upload validation tests
│   ├── test_pdf_extraction.py       # PDF extraction tests
│   ├── test_excel_extraction.py     # Excel multi-sheet extraction tests
│   ├── test_csv_extraction.py       # CSV delimiter & parsing tests
│   └── test_normalization.py        # Normalization logic & pipeline tests
│
├── uploads/
│   └── .gitkeep                     # Secure uploaded file storage directory
│
├── .env.example                     # Environment variable blueprint
├── .gitignore                       # Git ignore configuration
├── requirements.txt                 # Pinned dependencies
├── README.md                        # Documentation
└── run.py                           # CLI entrypoint to start uvicorn
```

---

## 5. Installation & Setup

### Step 1: Clone and Navigate
```bash
cd finny-backend
```

### Step 2: Virtual Environment Setup
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 6. PostgreSQL & Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### Environment Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///./finny.db` (fallback) |
| `UPLOAD_DIR` | Directory to store uploaded documents | `uploads` |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed upload size in megabytes | `20` |
| `APP_ENV` | Application environment (`development`, `production`) | `development` |
| `API_V1_PREFIX` | Prefix for API routes | `/api/v1` |

### PostgreSQL Setup
1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE finny;
   ```
2. Update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/finny
   ```
   *(Note: If `DATABASE_URL` is omitted or points to SQLite, the application runs seamlessly on SQLite for local development and zero-config testing).*

---

## 7. Running the Server

Start the API with `run.py`:
```bash
python run.py
```
Or directly with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 8. API Endpoints & Usage

### 1. Upload Financial Document
**`POST /api/v1/documents/upload`**

Accepts multipart form-data (`.pdf`, `.xlsx`, `.xls`, `.csv`). Enforces max file size (20MB) and prevents path traversal attacks.

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@sample_report.pdf"
```

**Response (`201 Created`):**
```json
{
  "document_id": "8f8b86ee-7c64-4bf8-b80c-7b0b178dae31",
  "filename": "sample_report.pdf",
  "file_type": "pdf",
  "status": "UPLOADED"
}
```

---

### 2. Process Document (Extract & Normalize)
**`POST /api/v1/documents/{document_id}/process`**

Triggers document extraction, passes the unified raw data to the normalizer, saves the normalized dataset to the database, and transitions status to `NORMALIZED`.

```bash
curl -X POST "http://localhost:8000/api/v1/documents/8f8b86ee-7c64-4bf8-b80c-7b0b178dae31/process"
```

**Response (`200 OK`):**
```json
{
  "document_id": "8f8b86ee-7c64-4bf8-b80c-7b0b178dae31",
  "status": "NORMALIZED",
  "company": {
    "name": "ABC Limited"
  },
  "currency": "INR",
  "period": {
    "start": null,
    "end": "2025-03-31",
    "fiscal_year": "2024-25"
  },
  "financial_data": {
    "revenue": 12500000.0,
    "assets": 45000000.0,
    "liabilities": 18000000.0,
    "equity": 27000000.0
  },
  "source": {
    "filename": "sample_report.pdf",
    "file_type": "pdf"
  },
  "normalization_warnings": []
}
```

---

### 3. Get Document Status
**`GET /api/v1/documents/{document_id}`**

Returns processing lifecycle status and timestamp metadata.

```bash
curl "http://localhost:8000/api/v1/documents/8f8b86ee-7c64-4bf8-b80c-7b0b178dae31"
```

**Response (`200 OK`):**
```json
{
  "document_id": "8f8b86ee-7c64-4bf8-b80c-7b0b178dae31",
  "filename": "sample_report.pdf",
  "file_type": "pdf",
  "status": "NORMALIZED",
  "uploaded_at": "2026-09-13T14:58:48.834000Z",
  "processed_at": "2026-09-13T14:58:48.850000Z",
  "error_message": null
}
```

---

### 4. Get Normalized Data
**`GET /api/v1/documents/{document_id}/normalized`**

Retrieves the persisted canonical normalized dataset. Returns `400 Bad Request` if the document has not yet been processed.

```bash
curl "http://localhost:8000/api/v1/documents/8f8b86ee-7c64-4bf8-b80c-7b0b178dae31/normalized"
```

---

## 9. Normalization Rules & Capabilities

### Common Internal Format
All extractors (`PDFExtractor`, `ExcelExtractor`, `CSVExtractor`) map into `RawExtractionData`:
```json
{
  "source": {"filename": "report.pdf", "file_type": "pdf"},
  "tables": [
    {
      "headers": ["Particulars", "2025"],
      "rows": [
        ["Revenue", "12,500,000"],
        ["Total Assets", "45,000,000"]
      ]
    }
  ]
}
```

### Supported Normalizations
1. **Field Taxonomy Mapping**:
   - `revenue`: "Revenue", "Total Revenue", "Net Revenue", "Net Sales", "Sales", "Turnover", "Revenue from operations".
   - `assets`: "Assets", "Total Assets", "Aggregate Assets".
   - `liabilities`: "Liabilities", "Total Liabilities", "Total debt and liabilities".
   - `equity`: "Equity", "Shareholders' Equity", "Shareholders Equity", "Owners' Equity", "Net Worth".
2. **Numeric Values**:
   - Commas removed: `"12,500,000"` → `12500000.0`
   - Currency stripped: `"₹12,500,000"` → `12500000.0`
   - Parentheses negatives: `"(5,000,000)"` → `-5000000.0`
   - Scale multipliers: `"12.5M"` / `"12.5 million"` → `12500000.0`, `"2.5B"` → `2500000000.0`, `"10 Cr"` → `100000000.0`, `"50 L"` → `5000000.0`
   - Traceability: Unparseable values are preserved and flagged in `normalization_warnings` without silent data corruption.
3. **Currency Standardization**:
   - `₹`, `Rs`, `Rs.`, `INR` → `INR`
   - `$`, `USD` → `USD`
   - `€`, `EUR` → `EUR`
   - `£`, `GBP` → `GBP`
   - *NO currency exchange conversion is performed.*
4. **Date & Period Normalization**:
   - `31-03-2025`, `31/03/2025`, `March 31, 2025` → `2025-03-31`
   - `FY 2024-25`, `FY2024-2025` → `{"fiscal_year": "2024-25"}`

---

## 10. Automated Testing

Run the test suite with pytest:
```bash
pytest tests -v
```

### Test Coverage Summary (25 Passing Tests)
- `tests/test_upload.py`: PDF upload, Excel upload, CSV upload, invalid extension rejection, empty file rejection, missing file handling.
- `tests/test_pdf_extraction.py`: PDF tabular extraction, multi-page document parsing, missing file handling.
- `tests/test_excel_extraction.py`: Single sheet and multi-sheet Excel extraction, column inference, missing file handling.
- `tests/test_csv_extraction.py`: Comma, semicolon, and tab delimiter detection, missing and NaN value handling.
- `tests/test_normalization.py`: Field synonyms, numeric values (parentheses, scales, commas), currency detection, ISO dates & fiscal years, end-to-end API pipeline, 404 validation, and uniformity across formats (verifying PDF, Excel, and CSV with the same financial figures yield identical normalized models).

---

## 11. Known Limitations & Future Extensibility

- **Encrypted/Password-Protected PDFs**: Password-protected PDFs must be unlocked before upload.
- **Scanned Image-Only PDFs**: PDFs containing scanned images without embedded text layers require an OCR pre-processor before tabular extraction.
- **Future Extensibility**: The `financial_data` Pydantic schema and database model have `extra="allow"` enabled, facilitating future integration with additional line items (`operating_income`, `net_income`, `cash`, `inventory`, `accounts_receivable`, etc.) and subsequent financial validation or AI reasoning agents.
