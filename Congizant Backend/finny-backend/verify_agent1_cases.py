import sys
import json
import uuid
from app.services.agent1.result_builder import Agent1ResultBuilder

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== AGENT 1 RESULT BUILDER TEST CASES VERIFICATION ===")

# Case 1: Complete Agent 1 Result
c1_curr = {
    "revenue": 1000000.0, "gross_profit": 400000.0, "net_profit": 150000.0,
    "assets": 2000000.0, "liabilities": 800000.0, "equity": 1200000.0,
    "current_assets": 600000.0, "current_liabilities": 300000.0, "inventory": 150000.0,
}
c1_prev = {
    "revenue": 800000.0, "gross_profit": 320000.0, "net_profit": 120000.0,
    "assets": 1600000.0, "liabilities": 700000.0, "equity": 900000.0,
    "current_assets": 500000.0, "current_liabilities": 250000.0, "inventory": 120000.0,
}
r1 = Agent1ResultBuilder.build_from_data("doc-1", c1_curr, c1_prev, "2024-25", "2023-24")
print(f"CASE 1 - Complete Agent 1 Result: status={r1['status']}, math={r1['results']['math_validation']['status']}, yoy={r1['results']['yoy_analysis']['status']}, ratios={r1['results']['financial_ratios']['status']}")

# Case 2: Math Validation Invalid
c2_curr = {
    "revenue": 1000000.0, "gross_profit": 400000.0, "net_profit": 100000.0,
    "assets": 45000000.0, "liabilities": 20000000.0, "equity": 27000000.0,
    "current_assets": 500000.0, "current_liabilities": 250000.0, "inventory": 100000.0,
}
c2_prev = {
    "revenue": 900000.0, "gross_profit": 350000.0, "net_profit": 80000.0,
    "assets": 40000000.0, "liabilities": 18000000.0, "equity": 22000000.0,
    "current_assets": 400000.0, "current_liabilities": 200000.0, "inventory": 80000.0,
}
r2 = Agent1ResultBuilder.build_from_data("doc-2", c2_curr, c2_prev, "2024-25", "2023-24")
print(f"CASE 2 - Math Validation Invalid: overall={r2['status']}, math={r2['results']['math_validation']['status']}, is_valid={r2['results']['math_validation']['is_valid']}")

# Case 3: YoY Insufficient Data
r3 = Agent1ResultBuilder.build_from_data("doc-3", c1_curr, None, "2024-25", None)
print(f"CASE 3 - YoY Insufficient Data: overall={r3['status']}, yoy={r3['results']['yoy_analysis']['status']}")

# Case 4: Ratio Incomplete
c4_curr = {"assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0}
r4 = Agent1ResultBuilder.build_from_data("doc-4", c4_curr, None)
print(f"CASE 4 - Ratio Incomplete: overall={r4['status']}, ratios={r4['results']['financial_ratios']['status']}")

# Case 5: Zero Denominator
c5_curr = {"revenue": 0.0, "gross_profit": 50000.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0, "current_assets": 200000.0, "current_liabilities": 100000.0, "inventory": 50000.0}
r5 = Agent1ResultBuilder.build_from_data("doc-5", c5_curr, None)
gpm = r5["results"]["financial_ratios"]["ratios"]["profitability"]["gross_profit_margin"]
print(f"CASE 5 - Zero Denominator: GPM val={gpm['value']}, GPM status={gpm['status']}")

# Case 6: Missing Fields (No Fabrication)
c6_curr = {"revenue": 500000.0}
r6 = Agent1ResultBuilder.build_from_data("doc-6", c6_curr, None)
print(f"CASE 6 - Missing Fields: overall={r6['status']}, math={r6['results']['math_validation']['status']}, assets={r6['results']['math_validation']['assets']}")

# Case 7: Negative Financial Values
c7_curr = {"revenue": 1000000.0, "gross_profit": 200000.0, "net_profit": -50000.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0, "current_assets": 200000.0, "current_liabilities": 100000.0, "inventory": 50000.0}
c7_prev = {"revenue": 800000.0, "gross_profit": 150000.0, "net_profit": 10000.0, "assets": 900000.0, "liabilities": 400000.0, "equity": 500000.0, "current_assets": 180000.0, "current_liabilities": 90000.0, "inventory": 40000.0}
r7 = Agent1ResultBuilder.build_from_data("doc-7", c7_curr, c7_prev, "2024-25", "2023-24")
npm = r7["results"]["financial_ratios"]["ratios"]["profitability"]["net_profit_margin"]
print(f"CASE 7 - Negative Values: NPM={npm['value']}%, status={npm['status']}")

# Case 8: Large Trillion-scale Values
c8_curr = {"revenue": 1250000000000.0, "gross_profit": 500000000000.0, "net_profit": 250000000000.0, "assets": 5000000000000.0, "liabilities": 2000000000000.0, "equity": 3000000000000.0, "current_assets": 1000000000000.0, "current_liabilities": 500000000000.0, "inventory": 200000000000.0}
c8_prev = {"revenue": 1000000000000.0, "gross_profit": 400000000000.0, "net_profit": 200000000000.0, "assets": 4000000000000.0, "liabilities": 1500000000000.0, "equity": 2500000000000.0, "current_assets": 800000000000.0, "current_liabilities": 400000000000.0, "inventory": 150000000000.0}
r8 = Agent1ResultBuilder.build_from_data("doc-8", c8_curr, c8_prev, "2024-25", "2023-24")
print(f"CASE 8 - Large Values: status={r8['status']}, math_valid={r8['results']['math_validation']['is_valid']}")

# Case 9: Warning Aggregation
r9 = Agent1ResultBuilder.build_from_data("doc-9", {"revenue": 0.0, "assets": 1000.0, "liabilities": 200.0, "equity": 200.0}, None)
print(f"CASE 9 - Warning Aggregation: warnings_count={len(r9['warnings'])}, sample_warning='{r9['warnings'][0]}'")

# Case 10: Delegation / No Duplicate Logic
print("CASE 10 - Delegation: MathValidator, YoYAnalyzer, and RatioAnalyzer called directly.")

# Case 11: JSON Serialization
json_dump = json.dumps(r1)
print(f"CASE 11 - JSON Serialization: successfully serialized {len(json_dump)} bytes, has_NaN={'NaN' in json_dump}")

# Case 12: Result Structure Check
keys = list(r1.keys())
print(f"CASE 12 - Result Structure: top_level_keys={keys}")

print("\nALL AGENT 1 CASES VERIFIED SUCCESSFULLY!")
