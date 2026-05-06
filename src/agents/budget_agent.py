"""Budget Agent - 规则型，预算偏差分析"""

import pandas as pd
import json
from pathlib import Path


def run(data_dir: Path, output_dir: Path) -> dict:
    """分析实际 vs 预算"""
    sales = pd.read_csv(data_dir / "fact_sales.csv")
    cost = pd.read_csv(data_dir / "fact_cost.csv")
    expense = pd.read_csv(data_dir / "fact_expense.csv")
    budget = pd.read_csv(data_dir / "fact_budget.csv")
    products = pd.read_csv(data_dir / "dim_product.csv")

    # 过滤有效产品
    valid = set(products["product_name"])
    sales = sales[sales["product"].isin(valid)]
    cost = cost[cost["product"].isin(valid)]

    # === 按月+市场 汇总实际 ===
    actual_rev = sales.groupby(["month", "market"]).agg(actual_revenue=("revenue", "sum")).reset_index()
    cost_agg = cost.groupby(["month", "market"]).agg(
        actual_cost=("product_cost", "sum"),
        actual_freight=("freight_cost", "sum"),
        actual_tariff=("tariff_cost", "sum"),
    ).reset_index()
    actual_exp = expense.groupby(["month", "market"]).agg(actual_expense=("expense_amount", "sum")).reset_index()

    # === 按月+市场 汇总预算 ===
    budget_agg = budget.groupby(["month", "market"]).agg(
        budget_revenue=("budget_revenue", "sum"),
        budget_cost=("budget_cost", "sum"),
        budget_expense=("budget_expense", "sum"),
        budget_profit=("budget_profit", "sum"),
    ).reset_index()

    # === 合并 ===
    detail = actual_rev.merge(cost_agg, on=["month", "market"], how="left")
    detail = detail.merge(actual_exp, on=["month", "market"], how="left")
    detail = detail.merge(budget_agg, on=["month", "market"], how="left")

    detail["actual_cogs"] = detail["actual_cost"].fillna(0) + detail["actual_freight"].fillna(0) + detail["actual_tariff"].fillna(0)
    detail["actual_profit"] = detail["actual_revenue"] - detail["actual_cogs"] - detail["actual_expense"].fillna(0)

    # 偏差计算
    detail["revenue_variance"] = detail["actual_revenue"] - detail["budget_revenue"]
    detail["revenue_variance_pct"] = ((detail["revenue_variance"] / detail["budget_revenue"]) * 100).round(2)
    detail["profit_variance"] = detail["actual_profit"] - detail["budget_profit"]
    detail["profit_variance_pct"] = ((detail["profit_variance"] / detail["budget_profit"]) * 100).round(2)
    detail["expense_variance"] = detail["actual_expense"].fillna(0) - detail["budget_expense"]

    # === 按费用科目分析 ===
    expense_detail = expense.groupby(["month", "market", "expense_type"]).agg(
        actual=("expense_amount", "sum")
    ).reset_index()
    budget_exp_by_type = budget.groupby(["month", "market"]).agg(
        budget_expense_total=("budget_expense", "sum")
    ).reset_index()
    # 简化：按比例分配预算到各科目
    expense_types = expense["expense_type"].unique()
    type_weights = {t: 1 / len(expense_types) for t in expense_types}
    expense_detail["budget"] = expense_detail.apply(
        lambda r: budget_exp_by_type[
            (budget_exp_by_type["month"] == r["month"]) & (budget_exp_by_type["market"] == r["market"])
        ]["budget_expense_total"].sum() * type_weights.get(r["expense_type"], 0.15),
        axis=1,
    )
    expense_detail["variance"] = expense_detail["actual"] - expense_detail["budget"]
    expense_detail["variance_pct"] = ((expense_detail["variance"] / expense_detail["budget"]) * 100).round(2)

    # === 汇总报告 ===
    latest_month = detail["month"].max()
    latest = detail[detail["month"] == latest_month]

    report = {
        "month": latest_month,
        "summary": {
            "total_actual_revenue": round(latest["actual_revenue"].sum(), 2),
            "total_budget_revenue": round(latest["budget_revenue"].sum(), 2),
            "revenue_variance": round(latest["revenue_variance"].sum(), 2),
            "revenue_achievement_pct": round(latest["actual_revenue"].sum() / latest["budget_revenue"].sum() * 100, 2),
            "total_actual_profit": round(latest["actual_profit"].sum(), 2),
            "total_budget_profit": round(latest["budget_profit"].sum(), 2),
            "profit_variance": round(latest["profit_variance"].sum(), 2),
        },
        "by_market": [],
        "top_over_budget": [],
    }

    for _, row in latest.iterrows():
        report["by_market"].append({
            "market": row["market"],
            "actual_revenue": round(row["actual_revenue"], 2),
            "budget_revenue": round(row["budget_revenue"], 2),
            "revenue_variance_pct": round(row["revenue_variance_pct"], 2),
            "profit_variance_pct": round(row.get("profit_variance_pct", 0), 2),
        })

    # 超预算最多的科目
    over_budget = expense_detail[expense_detail["variance_pct"] > 15].sort_values("variance_pct", ascending=False).head(10)
    for _, row in over_budget.iterrows():
        report["top_over_budget"].append({
            "month": row["month"],
            "market": row["market"],
            "expense_type": row["expense_type"],
            "actual": round(row["actual"], 2),
            "budget": round(row["budget"], 2),
            "variance_pct": round(row["variance_pct"], 2),
        })

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "budget_variance_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    detail.round(2).to_csv(output_dir / "budget_variance_detail.csv", index=False)

    return report
