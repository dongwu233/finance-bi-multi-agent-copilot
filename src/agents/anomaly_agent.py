"""Anomaly Agent - 规则型，异常检测与归因"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


# 异常规则阈值
RULES = {
    "gross_margin_drop_pct": 1.0,       # 毛利率环比下降超过 1pct
    "expense_over_budget_pct": 25.0,     # 费用超预算超过 25%
    "ad_roas_min": 3.0,                  # 广告 ROAS 低于 3.0
    "net_profit_yoy_drop_pct": 15.0,     # 净利润同比下降超过 15%
    "inventory_turnover_max_days": 100,   # 库存周转天数超过 100
    "negative_contribution_revenue_pct": 3.0,  # 贡献利润为负且收入占比 > 3%
}


def run(data_dir: Path, output_dir: Path, metrics: dict) -> list:
    """检测异常事件"""
    events = []
    event_id = 0

    monthly = metrics["monthly"]
    by_market = metrics["by_market"]
    by_product = metrics["by_product"]
    ad_roas = metrics["ad_roas"]
    inventory = metrics["inventory"]

    # 1. 毛利率环比下降检测（按市场）
    for market in by_market["market"].unique():
        mkt = by_market[by_market["market"] == market].sort_values("month")
        for i in range(1, len(mkt)):
            curr = mkt.iloc[i]
            prev = mkt.iloc[i - 1]
            if pd.notna(curr["gross_margin_pct"]) and pd.notna(prev["gross_margin_pct"]):
                drop = (prev["gross_margin_pct"] - curr["gross_margin_pct"]) * 100
                if drop > RULES["gross_margin_drop_pct"]:
                    event_id += 1
                    events.append({
                        "event_id": f"ANOMALY_{event_id:03d}",
                        "type": "gross_margin_drop",
                        "month": curr["month"],
                        "market": market,
                        "metric": "Gross Margin %",
                        "severity": "high" if drop > 5 else "medium",
                        "current_value": round(curr["gross_margin_pct"], 4),
                        "previous_value": round(prev["gross_margin_pct"], 4),
                        "change_pct_point": round(-drop, 2),
                        "description": f"{market} 毛利率环比下降 {drop:.1f}pct",
                    })

    # 2. 费用超预算检测
    budget = pd.read_csv(data_dir / "fact_budget.csv")
    expense = pd.read_csv(data_dir / "fact_expense.csv")
    expense_by_mkt = expense.groupby(["month", "market"]).agg(actual_expense=("expense_amount", "sum")).reset_index()
    budget_by_mkt = budget.groupby(["month", "market"]).agg(budget_expense=("budget_expense", "sum")).reset_index()
    exp_budget = expense_by_mkt.merge(budget_by_mkt, on=["month", "market"], how="left")
    exp_budget["variance_pct"] = ((exp_budget["actual_expense"] - exp_budget["budget_expense"]) / exp_budget["budget_expense"] * 100)

    over_budget = exp_budget[exp_budget["variance_pct"] > RULES["expense_over_budget_pct"]]
    for _, row in over_budget.iterrows():
        event_id += 1
        events.append({
            "event_id": f"ANOMALY_{event_id:03d}",
            "type": "expense_over_budget",
            "month": row["month"],
            "market": row["market"],
            "metric": "Expense vs Budget",
            "severity": "high" if row["variance_pct"] > 25 else "medium",
            "current_value": round(row["actual_expense"], 2),
            "budget_value": round(row["budget_expense"], 2),
            "variance_pct": round(row["variance_pct"], 2),
            "description": f"{row['market']} {row['month']} 费用超预算 {row['variance_pct']:.1f}%",
        })

    # 3. 广告 ROAS 过低检测
    low_roas = ad_roas[(ad_roas["ad_roas"] > 0) & (ad_roas["ad_roas"] < RULES["ad_roas_min"])]
    for _, row in low_roas.iterrows():
        event_id += 1
        events.append({
            "event_id": f"ANOMALY_{event_id:03d}",
            "type": "low_ad_roas",
            "month": row["month"],
            "market": row["market"],
            "metric": "Ad ROAS",
            "severity": "high" if row["ad_roas"] < 1.5 else "medium",
            "current_value": round(row["ad_roas"], 2),
            "threshold": RULES["ad_roas_min"],
            "description": f"{row['market']} {row['month']} 广告 ROAS 仅 {row['ad_roas']:.2f}，低于 {RULES['ad_roas_min']}",
        })

    # 4. 库存周转天数异常
    high_inv = inventory[inventory["turnover_days"] > RULES["inventory_turnover_max_days"]]
    for _, row in high_inv.iterrows():
        event_id += 1
        events.append({
            "event_id": f"ANOMALY_{event_id:03d}",
            "type": "high_inventory_turnover",
            "month": row["month"],
            "market": row["market"],
            "product": row.get("product", ""),
            "metric": "Inventory Turnover Days",
            "severity": "high" if row["turnover_days"] > 150 else "medium",
            "current_value": int(row["turnover_days"]),
            "threshold": RULES["inventory_turnover_max_days"],
            "description": f"{row['market']} {row.get('product', '')} {row['month']} 库存周转 {int(row['turnover_days'])} 天",
        })

    # 5. 净利润同比检测（简化：用最近月 vs 去年同月）
    if len(monthly) >= 13:
        curr = monthly.iloc[-1]
        prev_year = monthly.iloc[-13]
        if pd.notna(curr["net_profit"]) and pd.notna(prev_year["net_profit"]) and prev_year["net_profit"] > 0:
            yoy_drop = (prev_year["net_profit"] - curr["net_profit"]) / prev_year["net_profit"] * 100
            if yoy_drop > RULES["net_profit_yoy_drop_pct"]:
                event_id += 1
                events.append({
                    "event_id": f"ANOMALY_{event_id:03d}",
                    "type": "net_profit_yoy_drop",
                    "month": curr["month"],
                    "market": "ALL",
                    "metric": "Net Profit",
                    "severity": "high",
                    "current_value": round(curr["net_profit"], 2),
                    "previous_value": round(prev_year["net_profit"], 2),
                    "change_pct": round(-yoy_drop, 2),
                    "description": f"净利润同比下降 {yoy_drop:.1f}%",
                })

    # 6. 单品贡献利润为负且收入占比高
    latest_month = by_product["month"].max()
    latest_product = by_product[by_product["month"] == latest_month].copy()
    total_rev = latest_product["revenue"].sum()
    latest_product["revenue_share"] = latest_product["revenue"] / total_rev * 100
    negative_contrib = latest_product[
        (latest_product["gross_profit"] < 0) & (latest_product["revenue_share"] > RULES["negative_contribution_revenue_pct"])
    ]
    for _, row in negative_contrib.iterrows():
        event_id += 1
        events.append({
            "event_id": f"ANOMALY_{event_id:03d}",
            "type": "negative_contribution",
            "month": latest_month,
            "market": "ALL",
            "product": row["product"],
            "metric": "Product Contribution Profit",
            "severity": "medium",
            "current_value": round(row["gross_profit"], 2),
            "revenue_share_pct": round(row["revenue_share"], 2),
            "description": f"{row['product']} 贡献利润为负 ({row['gross_profit']:,.0f})，收入占比 {row['revenue_share']:.1f}%",
        })

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "anomaly_events.json").write_text(
        json.dumps(events, indent=2, ensure_ascii=False)
    )

    return events
