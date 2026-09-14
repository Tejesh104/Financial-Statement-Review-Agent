import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import pymupdf as fitz

# Ensure finny-backend is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app
from app.database.database import Base, get_db
from app.core.config import settings

# In-memory SQLite for testing isolation
TEST_DATABASE_URL = "sqlite:///./test_finny.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_db_file = Path("./test_finny.db")
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except Exception:
            pass


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_csv(tmp_path) -> Path:
    csv_path = tmp_path / "financial_sample.csv"
    content = (
        "Particulars,2025\n"
        "ABC Limited,\n"
        "Revenue,12,500,000\n"
        "Total Assets,45,000,000\n"
        "Total Liabilities,18,000,000\n"
        "Shareholders' Equity,27,000,000\n"
    )
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_semicolon_csv(tmp_path) -> Path:
    csv_path = tmp_path / "semicolon_sample.csv"
    content = (
        "Line Item;FY 2024-25\n"
        "Total Revenue;₹ 15.5M\n"
        "Assets;₹ 50M\n"
        "Total Liabilities;₹ 20M\n"
        "Owners' Equity;₹ 30M\n"
    )
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_excel(tmp_path) -> Path:
    excel_path = tmp_path / "financial_sample.xlsx"
    df = pd.DataFrame({
        "Particulars": ["Revenue", "Total Assets", "Total Liabilities", "Shareholders' Equity"],
        "2024": [10000000, 40000000, 17000000, 23000000],
        "2025": [12500000, 45000000, 18000000, 27000000]
    })
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Income_Balance", index=False)
    return excel_path


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    pdf_path = tmp_path / "financial_sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Write financial report text
    report_text = (
        "ABC Limited\n"
        "Annual Financial Report for FY 2024-25\n"
        "Currency: INR (₹)\n\n"
        "Particulars                 Amount\n"
        "Revenue                     12,500,000\n"
        "Total Assets                45,000,000\n"
        "Total Liabilities           18,000,000\n"
        "Shareholders' Equity        27,000,000\n"
    )
    page.insert_text((50, 72), report_text, fontsize=11)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path
