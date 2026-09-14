import sys
from app.services.analytics.yoy_analyzer import YoYAnalyzer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== YoY TEST CASES VERIFICATION ===")

# TEST 1 - NORMAL GROWTH
t1 = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=12_500_000.0)
print(f"TEST 1 - NORMAL GROWTH: status={t1['status']}, abs={t1['absolute_change']}, pct={t1['percentage_change']}%, dir={t1['direction']}")

# TEST 2 - DECLINE
t2 = YoYAnalyzer.calculate_field_yoy(previous=12_500_000.0, current=10_000_000.0)
print(f"TEST 2 - DECLINE: status={t2['status']}, abs={t2['absolute_change']}, pct={t2['percentage_change']}%, dir={t2['direction']}")

# TEST 3 - NO CHANGE
t3 = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=10_000_000.0)
print(f"TEST 3 - NO CHANGE: status={t3['status']}, abs={t3['absolute_change']}, pct={t3['percentage_change']}%, dir={t3['direction']}")

# TEST 4 - PREVIOUS VALUE ZERO
t4 = YoYAnalyzer.calculate_field_yoy(previous=0.0, current=500_000.0)
print(f"TEST 4 - PREVIOUS VALUE ZERO: status={t4['status']}, abs={t4['absolute_change']}, pct={t4['percentage_change']}, reason={t4['reason']}")

# TEST 5 - CURRENT VALUE ZERO
t5 = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=0.0)
print(f"TEST 5 - CURRENT VALUE ZERO: status={t5['status']}, abs={t5['absolute_change']}, pct={t5['percentage_change']}%, dir={t5['direction']}")

# TEST 6 - MISSING PREVIOUS
t6 = YoYAnalyzer.calculate_field_yoy(previous=None, current=500_000.0)
print(f"TEST 6 - MISSING PREVIOUS: status={t6['status']}, abs={t6['absolute_change']}, pct={t6['percentage_change']}, reason={t6['reason']}")

# TEST 7 - MISSING CURRENT
t7 = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=None)
print(f"TEST 7 - MISSING CURRENT: status={t7['status']}, abs={t7['absolute_change']}, pct={t7['percentage_change']}, reason={t7['reason']}")

# TEST 8 - ONLY ONE PERIOD
t8 = YoYAnalyzer.analyze_periods(
    previous_period="2024-25",
    current_period=None,
    previous_metrics={"revenue": 10_000_000.0},
    current_metrics=None,
)
print(f"TEST 8 - ONLY ONE PERIOD: status={t8['status']}, reason={t8['reason']}")

# TEST 9 - NEGATIVE VALUES
t9 = YoYAnalyzer.calculate_field_yoy(previous=-10_000_000.0, current=-5_000_000.0)
print(f"TEST 9 - NEGATIVE VALUES: status={t9['status']}, abs={t9['absolute_change']}, pct={t9['percentage_change']}%, dir={t9['direction']}")

# TEST 10 - LARGE VALUES
t10 = YoYAnalyzer.calculate_field_yoy(previous=1_000_000_000_000.0, current=1_250_000_000_000.0)
print(f"TEST 10 - LARGE VALUES: status={t10['status']}, abs={t10['absolute_change']}, pct={t10['percentage_change']}%, dir={t10['direction']}")

# TEST 11 - MULTIPLE FINANCIAL FIELDS
t11 = YoYAnalyzer.analyze_periods(
    previous_period="2023-24",
    current_period="2024-25",
    previous_metrics={"revenue": 10_000_000.0, "assets": 40_000_000.0, "liabilities": 15_000_000.0, "equity": 25_000_000.0},
    current_metrics={"revenue": 12_500_000.0, "assets": 45_000_000.0, "liabilities": 18_000_000.0, "equity": 27_000_000.0},
)
print(f"TEST 11 - MULTIPLE FIELDS: status={t11['status']}, fields={list(t11['financial_data'].keys())}")

# TEST 12 - PERIOD ORDERING
t12 = YoYAnalyzer.analyze_periods(
    previous_period="2024-25",
    current_period="2023-24",
    previous_metrics={"revenue": 12_500_000.0},
    current_metrics={"revenue": 10_000_000.0},
)
print(f"TEST 12 - PERIOD ORDERING: prev={t12['periods']['previous']}, curr={t12['periods']['current']}, pct={t12['financial_data']['revenue']['percentage_change']}%")
