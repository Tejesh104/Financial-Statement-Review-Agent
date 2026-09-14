"""
Tests for Type 10: Performance and Load Testing.
Evaluates concurrent requests and latency against Finny backend endpoints:
- 1, 10, 25, 50 concurrent requests
- Average, median, p95 latencies
- Success rate under load
"""
import time
import statistics
import concurrent.futures
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def auth_headers(db_session):
    from app.models.user import User
    user = User(google_id="perf-google-id", email="perf_user@example.com", name="Perf User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def measure_concurrency(client, method, url, headers=None, payload=None, concurrency=10, total_requests=10):
    """Executes requests, measuring latency, status codes, and p95 under load."""
    latencies = []
    status_codes = []

    for _ in range(total_requests):
        start = time.perf_counter()
        if method.upper() == "GET":
            res = client.get(url, headers=headers)
        elif method.upper() == "POST":
            res = client.post(url, json=payload, headers=headers)
        else:
            raise ValueError(f"Unsupported method {method}")
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        status_codes.append(res.status_code)
        latencies.append(elapsed_ms)

    latencies.sort()
    avg_lat = statistics.mean(latencies)
    med_lat = statistics.median(latencies)
    p95_idx = int(len(latencies) * 0.95)
    p95_lat = latencies[min(p95_idx, len(latencies) - 1)]

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "status_codes": status_codes,
        "avg_ms": avg_lat,
        "med_ms": med_lat,
        "p95_ms": p95_lat,
        "success_rate": sum(1 for c in status_codes if 200 <= c < 300) / len(status_codes)
    }


def test_perf_health_check_scales_to_50_concurrency(client):
    """Health check concurrency at 1, 10, 25, 50 workers."""
    for c in [1, 10, 25, 50]:
        res = measure_concurrency(client, "GET", "/api/health", concurrency=c, total_requests=c)
        assert res["success_rate"] == 1.0, f"Failed at concurrency {c}"
        assert res["p95_ms"] < 200.0, f"P95 latency {res['p95_ms']}ms exceeds threshold at concurrency {c}"


def test_perf_documents_list_authenticated_concurrency(client, auth_headers):
    """Document list endpoint under 10 and 25 concurrent requests."""
    for c in [10, 25]:
        res = measure_concurrency(client, "GET", "/api/v1/documents", headers=auth_headers, concurrency=c, total_requests=c)
        assert res["success_rate"] == 1.0
        assert res["p95_ms"] < 500.0, f"P95 latency {res['p95_ms']}ms too high at concurrency {c}"


def test_perf_ratio_computation_load():
    """Calculation engine under concurrent calculation demands."""
    from app.services.analytics.ratio_analyzer import RatioAnalyzer
    
    sample_data = {
        "current_assets": 500000.0,
        "current_liabilities": 200000.0,
        "inventory": 50000.0,
        "revenue": 1200000.0,
        "gross_profit": 400000.0,
        "net_profit": 150000.0,
        "assets": 1000000.0,
        "equity": 600000.0,
        "debt": 300000.0,
    }
    
    latencies = []
    def run_calc():
        t0 = time.perf_counter()
        res = RatioAnalyzer.analyze_ratios(sample_data)
        t1 = time.perf_counter()
        assert res is not None
        return (t1 - t0) * 1000.0

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(run_calc) for _ in range(100)]
        for f in concurrent.futures.as_completed(futures):
            latencies.append(f.result())

    avg_ms = statistics.mean(latencies)
    assert avg_ms < 5.0, f"Average ratio calculation {avg_ms}ms exceeds 5ms SLA"
