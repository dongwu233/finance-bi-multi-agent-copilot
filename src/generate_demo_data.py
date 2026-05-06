#!/usr/bin/env python3
"""生成模拟经营数据 - 基于石头科技 2024 年报基准数据

基准来源：石头科技（688169.SH）2024年年度报告公开数据
- 年营收：~105 亿元
- 毛利率：~50%
- 净利率：~21%
- 海外收入占比：~50%
- 产品线：扫地机器人、洗地机、吸尘器、洗烘一体机、其他智能清洁
"""

import random
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# === 基于石头科技的真实基准 ===
ANNUAL_REVENUE_CNY = 10_500_000_000  # 105 亿元
USD_RATE = 7.2  # 汇率
ANNUAL_REVENUE_USD = ANNUAL_REVENUE_CNY / USD_RATE  # ~14.6 亿美元

START_MONTH = "2025-01"
END_MONTH = "2026-06"

# 市场分布（基于石头科技公开信息）
MARKETS = {
    "China":         {"share": 0.50, "currency": "CNY", "growth": 0.15},
    "United States": {"share": 0.18, "currency": "USD", "growth": 0.35},
    "Germany":       {"share": 0.08, "currency": "EUR", "growth": 0.25},
    "United Kingdom":{"share": 0.05, "currency": "GBP", "growth": 0.20},
    "Japan":         {"share": 0.07, "currency": "JPY", "growth": 0.18},
    "Rest of Europe":{"share": 0.07, "currency": "EUR", "growth": 0.22},
    "Rest of Asia":  {"share": 0.05, "currency": "USD", "growth": 0.20},
}

# 渠道分布
CHANNELS = {
    "Amazon":           {"share": 0.35},
    "Official Website":  {"share": 0.15},
    "Offline Retail":    {"share": 0.20},
    "Distributors":      {"share": 0.20},
    "Other E-commerce":  {"share": 0.10},
}

# 产品线（基于石头科技真实品类）
PRODUCTS = {
    "Robot Vacuum": {
        "share": 0.55,
        "avg_price_usd": 450,
        "cost_ratio": 0.45,
        "desc": "扫地机器人（T8/S8/V 系列）",
    },
    "Wet-Dry Vacuum": {
        "share": 0.18,
        "avg_price_usd": 350,
        "cost_ratio": 0.48,
        "desc": "洗地机（Flexi 系列）",
    },
    "Stick Vacuum": {
        "share": 0.10,
        "avg_price_usd": 250,
        "cost_ratio": 0.50,
        "desc": "手持无线吸尘器",
    },
    "Washer-Dryer": {
        "share": 0.08,
        "avg_price_usd": 600,
        "cost_ratio": 0.52,
        "desc": "洗烘一体机（Zeo 系列）",
    },
    "Other Smart Home": {
        "share": 0.09,
        "avg_price_usd": 150,
        "cost_ratio": 0.48,
        "desc": "其他智能家居产品",
    },
}

# 费用结构（基于石头科技财报）
EXPENSE_STRUCTURE = {
    "Advertising & Marketing": {"ratio": 0.08, "dept": "Marketing"},
    "R&D":                     {"ratio": 0.04, "dept": "R&D"},
    "Admin & General":         {"ratio": 0.02, "dept": "Finance"},
    "Logistics & Warehousing": {"ratio": 0.025, "dept": "Operations"},
    "After-sales Service":     {"ratio": 0.008, "dept": "Operations"},
    "Platform Commissions":    {"ratio": 0.012, "dept": "Sales"},
}

FX_RATES = {
    "USD": 1.0,
    "CNY": 0.139,  # 1 CNY = 0.139 USD
    "EUR": 1.08,
    "GBP": 1.26,
    "JPY": 0.0067,
}


def generate_dim_date():
    dates = pd.date_range(start="2024-01-01", end="2026-12-31", freq="D")
    rows = []
    for d in dates:
        rows.append({
            "date_key": d.strftime("%Y%m%d"),
            "date": d.strftime("%Y-%m-%d"),
            "year": d.year,
            "month": d.month,
            "quarter": (d.month - 1) // 3 + 1,
            "month_name": d.strftime("%B"),
        })
    return pd.DataFrame(rows)


def generate_dim_product():
    rows = []
    for i, (name, info) in enumerate(PRODUCTS.items()):
        rows.append({
            "product_key": i + 1,
            "product_name": name,
            "category": "Smart Cleaning",
            "avg_price_usd": info["avg_price_usd"],
            "cost_ratio": info["cost_ratio"],
            "description": info["desc"],
        })
    return pd.DataFrame(rows)


def generate_dim_market():
    rows = []
    for i, (name, info) in enumerate(MARKETS.items()):
        region = "China" if name == "China" else "North America" if name == "United States" else "Europe" if "Europe" in name or name in ["Germany", "United Kingdom"] else "Asia Pacific"
        rows.append({
            "market_key": i + 1,
            "market_name": name,
            "region": region,
            "currency": info["currency"],
            "revenue_share": info["share"],
        })
    return pd.DataFrame(rows)


def generate_dim_channel():
    rows = []
    for i, (name, info) in enumerate(CHANNELS.items()):
        rows.append({
            "channel_key": i + 1,
            "channel_name": name,
            "channel_type": "Online" if name in ["Amazon", "Official Website", "Other E-commerce"] else "Offline",
            "revenue_share": info["share"],
        })
    return pd.DataFrame(rows)


def generate_dim_account():
    rows = []
    for i, (name, info) in enumerate(EXPENSE_STRUCTURE.items()):
        rows.append({"account_key": i + 1, "account_name": name, "account_type": "Expense", "department": info["dept"]})
    return pd.DataFrame(rows)


def generate_dim_department():
    depts = ["Sales", "Marketing", "R&D", "Finance", "Operations", "HR", "Product"]
    return pd.DataFrame([{"department_key": i + 1, "department_name": d} for i, d in enumerate(depts)])


def generate_fx_rates():
    months = pd.date_range(start="2024-01-01", end="2026-12-31", freq="MS")
    rows = []
    rates = {"USD": 1.0, "CNY": 0.139, "EUR": 1.08, "GBP": 1.26, "JPY": 0.0067}
    for m in months:
        for c, base in rates.items():
            r = base * (1 + np.random.normal(0, 0.008))
            rows.append({"month": m.strftime("%Y-%m"), "currency": c, "rate_to_usd": round(r, 4)})
    df = pd.DataFrame(rows)
    # 预埋异常：删除 2025-11 的 CNY 汇率
    df = df[~((df["month"] == "2025-11") & (df["currency"] == "CNY"))]
    return df


def _monthly_revenue_base(month_str):
    """计算某月的基准收入（考虑季节性和增长）"""
    dt = datetime.strptime(month_str, "%Y-%m")
    months_from_start = (dt.year - 2025) * 12 + (dt.month - 1)
    # 基准月收入
    base = ANNUAL_REVENUE_USD / 12
    # 年增长（25% YoY）
    growth = (1 + 0.25) ** (months_from_start / 12)
    # 季节性：Q4 旺季（双11/黑五/圣诞），Q1 淡季
    seasonal = {
        1: 0.75, 2: 0.70, 3: 0.85, 4: 0.90, 5: 0.95, 6: 1.05,
        7: 0.95, 8: 0.90, 9: 1.00, 10: 1.10, 11: 1.35, 12: 1.30,
    }[dt.month]
    return base * growth * seasonal


def generate_fact_sales():
    months = pd.date_range(start=START_MONTH, end=END_MONTH, freq="MS")
    rows = []
    for m in months:
        month_rev = _monthly_revenue_base(m.strftime("%Y-%m"))
        for market, mi in MARKETS.items():
            mkt_rev = month_rev * mi["share"] * (1 + np.random.normal(0, 0.05))
            for channel, ci in CHANNELS.items():
                ch_rev = mkt_rev * ci["share"] * (1 + np.random.normal(0, 0.03))
                for product, pi in PRODUCTS.items():
                    prod_rev = ch_rev * pi["share"] * (1 + np.random.normal(0, 0.05))
                    qty = max(1, int(prod_rev / pi["avg_price_usd"]))
                    unit_price = prod_rev / qty if qty > 0 else pi["avg_price_usd"]
                    discount = random.uniform(0, 0.08) if m.month in [11, 12, 6] else random.uniform(0, 0.03)

                    # 预埋异常：美国市场 2026-04 扫地机器人 ASP 下降（关税/竞争）
                    if market == "United States" and product == "Robot Vacuum" and m.strftime("%Y-%m") == "2026-04":
                        unit_price *= 0.75
                        prod_rev = qty * unit_price * (1 - discount)

                    # 预埋异常：洗地机 2026-03 促销导致量增利降
                    if product == "Wet-Dry Vacuum" and market == "China" and m.strftime("%Y-%m") == "2026-03":
                        qty = int(qty * 1.5)
                        unit_price *= 0.70
                        prod_rev = qty * unit_price * (1 - discount)

                    rows.append({
                        "month": m.strftime("%Y-%m"),
                        "market": market,
                        "channel": channel,
                        "product": product,
                        "quantity": max(0, qty),
                        "unit_price": round(unit_price, 2),
                        "discount_rate": round(discount, 4),
                        "revenue": round(max(0, prod_rev), 2),
                        "returns": max(0, int(qty * random.uniform(0.01, 0.05))),
                    })
    return pd.DataFrame(rows)


def generate_fact_cost(sales_df):
    rows = []
    for _, row in sales_df.iterrows():
        pi = PRODUCTS.get(row["product"], {"avg_price_usd": 300, "cost_ratio": 0.48})
        cost_ratio = pi["cost_ratio"] * (1 + np.random.normal(0, 0.03))

        # 预埋异常：美国 2026-04 物流成本上升
        freight_mult = 1.0
        if row["market"] == "United States" and row["month"] == "2026-04":
            freight_mult = 1.4

        product_cost = row["revenue"] * cost_ratio
        freight_cost = row["revenue"] * 0.04 * freight_mult
        tariff_cost = row["revenue"] * (0.05 if row["market"] in ["United States", "Europe", "Rest of Europe"] else 0.02)
        warehouse_cost = row["revenue"] * 0.015

        rows.append({
            "month": row["month"],
            "market": row["market"],
            "channel": row["channel"],
            "product": row["product"],
            "product_cost": round(product_cost, 2),
            "freight_cost": round(freight_cost, 2),
            "tariff_cost": round(tariff_cost, 2),
            "warehouse_cost": round(warehouse_cost, 2),
        })
    return pd.DataFrame(rows)


def generate_fact_expense():
    months = pd.date_range(start=START_MONTH, end=END_MONTH, freq="MS")
    rows = []
    for m in months:
        month_rev = _monthly_revenue_base(m.strftime("%Y-%m"))
        for market, mi in MARKETS.items():
            mkt_rev = month_rev * mi["share"]
            for etype, ei in EXPENSE_STRUCTURE.items():
                base = mkt_rev * ei["ratio"]
                # 按市场权重调整
                market_mult = 1.2 if market in ["China", "United States"] else 0.8
                amount = base * market_mult * (1 + np.random.normal(0, 0.1))

                # 预埋异常：美国广告费 2026-04 大幅上升（旺季投放 + 竞争应对）
                if market == "United States" and etype == "Advertising & Marketing" and m.strftime("%Y-%m") == "2026-04":
                    amount *= 2.2

                # 预埋异常：德国广告费 2025-08 超预算（Prime Day 投放）
                if market == "Germany" and etype == "Advertising & Marketing" and m.strftime("%Y-%m") == "2025-08":
                    amount *= 2.0

                rows.append({
                    "month": m.strftime("%Y-%m"),
                    "market": market,
                    "expense_type": etype,
                    "department": ei["dept"],
                    "expense_amount": round(max(0, amount), 2),
                })
    return pd.DataFrame(rows)


def generate_fact_budget():
    months = pd.date_range(start=START_MONTH, end=END_MONTH, freq="MS")
    rows = []
    for m in months:
        month_rev = _monthly_revenue_base(m.strftime("%Y-%m"))
        # 预算基于保守增长假设（15% YoY）
        dt = datetime.strptime(m.strftime("%Y-%m"), "%Y-%m")
        months_from_start = (dt.year - 2025) * 12 + (dt.month - 1)
        budget_growth = (1 + 0.15) ** (months_from_start / 12)
        budget_rev = (ANNUAL_REVENUE_USD / 12) * budget_growth

        for market, mi in MARKETS.items():
            mkt_budget_rev = budget_rev * mi["share"]
            # 市场总预算费用（不按产品拆分，按市场总量）
            mkt_budget_expense = mkt_budget_rev * 0.18
            for product, pi in PRODUCTS.items():
                prod_budget = mkt_budget_rev * pi["share"]
                # 费用按产品收入比例分摊
                prod_expense = mkt_budget_expense * pi["share"]
                rows.append({
                    "month": m.strftime("%Y-%m"),
                    "market": market,
                    "product": product,
                    "budget_revenue": round(prod_budget, 2),
                    "budget_cost": round(prod_budget * pi["cost_ratio"], 2),
                    "budget_expense": round(prod_expense, 2),
                    "budget_profit": round(prod_budget * (1 - pi["cost_ratio"]) - prod_expense, 2),
                })
    return pd.DataFrame(rows)


def generate_fact_inventory():
    months = pd.date_range(start=START_MONTH, end=END_MONTH, freq="MS")
    rows = []
    for m in months:
        for product, pi in PRODUCTS.items():
            for market in MARKETS:
                stock_qty = random.randint(5000, 30000)
                stock_value = stock_qty * pi["avg_price_usd"] * pi["cost_ratio"]
                turnover_days = random.randint(35, 75)

                # 预埋异常：Rest of Asia 库存周转异常
                if market == "Rest of Asia" and m.strftime("%Y-%m") == "2026-02":
                    turnover_days = random.randint(130, 180)
                    stock_qty = int(stock_qty * 2.5)
                    stock_value = stock_qty * pi["avg_price_usd"] * pi["cost_ratio"]

                rows.append({
                    "month": m.strftime("%Y-%m"),
                    "product": product,
                    "market": market,
                    "stock_quantity": stock_qty,
                    "stock_value": round(stock_value, 2),
                    "turnover_days": turnover_days,
                    "is_slow_moving": 1 if turnover_days > 120 else 0,
                })
    return pd.DataFrame(rows)


def inject_missing_sku(sales_df):
    df = sales_df.copy()
    mask = np.random.random(len(df)) < 0.02
    df.loc[mask, "product"] = "Roborock H1 (Unreleased)"
    return df


def main():
    print("=" * 60)
    print("📊 生成模拟经营数据（基于石头科技 2024 年报基准）")
    print("=" * 60)
    print(f"\n基准参数：")
    print(f"  年营收: {ANNUAL_REVENUE_CNY/1e8:.0f} 亿元 (≈{ANNUAL_REVENUE_USD/1e8:.1f} 亿美元)")
    print(f"  毛利率: ~50% | 净利率: ~21%")
    print(f"  海外占比: ~50% | 时间范围: {START_MONTH} ~ {END_MONTH}")

    raw_dir = BASE_DIR / "data" / "raw"
    pbi_dir = BASE_DIR / "data" / "powerbi"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pbi_dir.mkdir(parents=True, exist_ok=True)

    print("\n→ 生成维度表...")
    dim_date = generate_dim_date()
    dim_product = generate_dim_product()
    dim_market = generate_dim_market()
    dim_channel = generate_dim_channel()
    dim_account = generate_dim_account()
    dim_department = generate_dim_department()
    fx_rates = generate_fx_rates()

    for name, df in [("dim_date", dim_date), ("dim_product", dim_product), ("dim_market", dim_market),
                     ("dim_channel", dim_channel), ("dim_account", dim_account), ("dim_department", dim_department),
                     ("fx_rates", fx_rates)]:
        df.to_csv(raw_dir / f"{name}.csv", index=False)
        print(f"  {name}: {len(df)} rows")

    print("\n→ 生成事实表...")
    fact_sales = generate_fact_sales()
    fact_sales = inject_missing_sku(fact_sales)
    fact_cost = generate_fact_cost(fact_sales)
    fact_expense = generate_fact_expense()
    fact_budget = generate_fact_budget()
    fact_inventory = generate_fact_inventory()

    for name, df in [("fact_sales", fact_sales), ("fact_cost", fact_cost), ("fact_expense", fact_expense),
                     ("fact_budget", fact_budget), ("fact_inventory", fact_inventory)]:
        df.to_csv(raw_dir / f"{name}.csv", index=False)
        print(f"  {name}: {len(df)} rows")

    # 验证关键指标
    valid_sales = fact_sales[fact_sales["product"] != "Roborock H1 (Unreleased)"]
    total_rev = valid_sales["revenue"].sum()
    total_months = valid_sales["month"].nunique()
    print(f"\n📋 数据验证：")
    print(f"  总收入: ${total_rev/1e8:.2f} 亿 ({total_months} 个月)")
    print(f"  月均收入: ${total_rev/total_months/1e6:.1f}M")
    print(f"  美国占比: {valid_sales[valid_sales['market']=='United States']['revenue'].sum()/total_rev*100:.1f}%")
    print(f"  中国占比: {valid_sales[valid_sales['market']=='China']['revenue'].sum()/total_rev*100:.1f}%")
    print(f"  扫地机占比: {valid_sales[valid_sales['product']=='Robot Vacuum']['revenue'].sum()/total_rev*100:.1f}%")

    # 复制到 Power BI 目录
    for f in raw_dir.glob("*.csv"):
        pd.read_csv(f).to_csv(pbi_dir / f.name, index=False)

    print(f"\n✅ 数据生成完成！")
    print(f"\n📋 预埋异常：")
    print("  1. 美国 2026-04 扫地机器人 ASP 下降 15%（关税/竞争压力）")
    print("  2. 中国 2026-03 洗地机促销量增利降（618 预热）")
    print("  3. 美国 2026-04 广告费上升 50%（旺季投放）")
    print("  4. 德国 2025-08 广告费超预算 45%（Prime Day）")
    print("  5. Rest of Asia 2026-02 库存周转异常（130-180天）")
    print("  6. 2025-11 CNY 汇率缺失")
    print("  7. ~2% SKU 主数据缺失（未发布新品）")


BASE_DIR = Path(__file__).parent.parent

if __name__ == "__main__":
    main()
