from app.services.validation.math_validator import MathValidator

cases = [
    ("CASE 1 — VALID", 45000000.0, 18000000.0, 27000000.0, 0.01),
    ("CASE 2 — INVALID", 45000000.0, 20000000.0, 27000000.0, 0.01),
    ("CASE 3 — ALL ZERO", 0.0, 0.0, 0.0, 0.01),
    ("CASE 4 — MISSING ASSETS", None, 18000000.0, 27000000.0, 0.01),
    ("CASE 5 — MISSING LIABILITIES", 45000000.0, None, 27000000.0, 0.01),
    ("CASE 6 — MISSING EQUITY", 45000000.0, 18000000.0, None, 0.01),
    ("CASE 7 — SMALL ROUNDING DIFFERENCE", 100.005, 50.0, 50.0, 0.01),
    ("CASE 8 — DIFFERENCE OUTSIDE TOLERANCE", 100.05, 50.0, 50.0, 0.01),
    ("CASE 9 — NEGATIVE VALUE", 10000000.0, 15000000.0, -5000000.0, 0.01),
    ("CASE 10 — LARGE VALUES", 1_000_000_000_000.0, 350_000_000_000.0, 650_000_000_000.0, 0.01),
]

for name, a, l, e, tol in cases:
    res = MathValidator.validate_balance_sheet(a, l, e, tolerance=tol)
    print(f"=== {name} ===")
    print(f"  assets: {res['assets']}")
    print(f"  liabilities: {res['liabilities']}")
    print(f"  equity: {res['equity']}")
    print(f"  liabilities_plus_equity: {res['liabilities_plus_equity']}")
    print(f"  difference: {res['difference']}")
    print(f"  tolerance: {res['tolerance']}")
    print(f"  is_valid: {res['is_valid']}")
    print(f"  status: {res['status']}")
    print(f"  reason: {res['reason']}")
    print()
