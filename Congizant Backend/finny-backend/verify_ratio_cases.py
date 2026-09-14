import sys
from app.services.analytics.ratio_analyzer import RatioAnalyzer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=== FINANCIAL RATIOS TEST CASES VERIFICATION ===")

t1 = RatioAnalyzer.calculate_current_ratio(200.0, 100.0)
print(f"TEST 1 - Current Ratio (200/100): val={t1['value']}, status={t1['status']}")

t2 = RatioAnalyzer.calculate_quick_ratio(200.0, 50.0, 100.0)
print(f"TEST 2 - Quick Ratio ((200-50)/100): val={t2['value']}, status={t2['status']}")

t3 = RatioAnalyzer.calculate_gross_profit_margin(400.0, 1000.0)
print(f"TEST 3 - Gross Profit Margin (400/1000): val={t3['value']}%, status={t3['status']}")

t4 = RatioAnalyzer.calculate_net_profit_margin(100.0, 1000.0)
print(f"TEST 4 - Net Profit Margin (100/1000): val={t4['value']}%, status={t4['status']}")

t5 = RatioAnalyzer.calculate_return_on_assets(100.0, 2000.0)
print(f"TEST 5 - ROA (100/2000): val={t5['value']}%, status={t5['status']}")

t6 = RatioAnalyzer.calculate_return_on_equity(100.0, 500.0)
print(f"TEST 6 - ROE (100/500): val={t6['value']}%, status={t6['status']}")

t7 = RatioAnalyzer.calculate_debt_to_equity(300.0, 600.0)
print(f"TEST 7 - Debt-to-Equity (300/600): val={t7['value']}, status={t7['status']}")

t8 = RatioAnalyzer.calculate_debt_ratio(300.0, 1000.0)
print(f"TEST 8 - Debt Ratio (300/1000): val={t8['value']}, status={t8['status']}")

t9 = RatioAnalyzer.calculate_current_ratio(200.0, None)
print(f"TEST 9 - Missing Current Liabilities: val={t9['value']}, status={t9['status']}, reason={t9['reason']}")

t10 = RatioAnalyzer.calculate_gross_profit_margin(400.0, None)
print(f"TEST 10 - Missing Revenue: val={t10['value']}, status={t10['status']}, reason={t10['reason']}")

t11 = RatioAnalyzer.calculate_return_on_equity(100.0, None)
print(f"TEST 11 - Missing Equity: val={t11['value']}, status={t11['status']}, reason={t11['reason']}")

t12 = RatioAnalyzer.calculate_gross_profit_margin(400.0, 0.0)
print(f"TEST 12 - Zero Revenue: val={t12['value']}, status={t12['status']}, reason={t12['reason']}")

t13 = RatioAnalyzer.calculate_return_on_assets(100.0, 0.0)
print(f"TEST 13 - Zero Assets: val={t13['value']}, status={t13['status']}, reason={t13['reason']}")

t14 = RatioAnalyzer.calculate_return_on_equity(100.0, 0.0)
print(f"TEST 14 - Zero Equity: val={t14['value']}, status={t14['status']}, reason={t14['reason']}")

t15 = RatioAnalyzer.calculate_net_profit_margin(-100.0, 1000.0)
print(f"TEST 15 - Negative Net Profit: val={t15['value']}%, status={t15['status']}")

t16 = RatioAnalyzer.calculate_debt_to_equity(0.0, 500.0)
print(f"TEST 16 - Zero Debt: val={t16['value']}, status={t16['status']}")

t17 = RatioAnalyzer.calculate_return_on_equity(250_000_000_000.0, 1_000_000_000_000.0)
print(f"TEST 17 - Large Values (Trillions): val={t17['value']}%, status={t17['status']}")

t18 = RatioAnalyzer.analyze_ratios({
    'current_assets': 200.0, 'current_liabilities': 100.0, 'inventory': 50.0,
    'revenue': 1000.0, 'gross_profit': 400.0, 'net_profit': 100.0,
    'assets': 2000.0, 'equity': 500.0, 'debt': 300.0
})
print(f"TEST 18 - Complete Dataset: status={t18['status']}, CR={t18['ratios']['liquidity']['current_ratio']['value']}, GPM={t18['ratios']['profitability']['gross_profit_margin']['value']}%")

t19 = RatioAnalyzer.analyze_ratios({'current_assets': 200.0, 'current_liabilities': 100.0, 'inventory': None})
print(f"TEST 19 - Missing Inventory: CR={t19['ratios']['liquidity']['current_ratio']['value']}, QR status={t19['ratios']['liquidity']['quick_ratio']['status']}")

t20 = RatioAnalyzer.analyze_ratios({'revenue': 1000.0, 'gross_profit': 400.0})
print(f"TEST 20 - Partial Dataset: GPM status={t20['ratios']['profitability']['gross_profit_margin']['status']}, CR status={t20['ratios']['liquidity']['current_ratio']['status']}")
