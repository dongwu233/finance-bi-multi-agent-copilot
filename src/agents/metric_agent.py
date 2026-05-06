"""Metric Agent - 规则型，计算所有 KPI"""

import pandas as pd
import numpy as np
from pathlib import Path


def run(data_dir: Path, output_dir: Path) -> dict:
    """计算所有 KPI 指标"""
    sales = pd.read_csv(data_dir / "fact_sales.csv")
    cost = pd.read_csv(data_dir / "fact_cost.csv")
    expense = pd.read_csv(data_dir / "fact_expense.csv")
    budget = pd.read_csv(data_dir / "fact_budget.csv")
    inventory = pd.read_csv(data_dir / "fact_inventory.csv")

    # 只取产品维表中有效的 SKU
    products = pd.read_csv(data_dir / "dim_product.csv")
    valid_products = set(products["product_name"])
    sales = sales[sales["product"].isin(valid_products)]
    cost = cost[cost["product"].isin(valid_products)]

    # === 合并销售和成本 ===
    cost_agg = cost.groupby(["month", "market", "channel", "product"]).agg(
        product_cost=("product_cost", "sum"),
        freight_cost=("freight_cost", "sum"),
        tariff_cost=("tariff_cost", "sum"),
        warehouse_cost=("warehouse_cost", "sum"),
    ).reset_index()
    cost_agg["cogs"] = cost_agg["product_cost"] + cost_agg["freight_cost"] + cost_agg["tariff_cost"]

    merged = sales.merge(cost_agg, on=["month", "market", "channel", "product"], how="left")
    merged["cogs"] = merged["cogs"].fillna(0)
    merged["gross_profit"] = merged["revenue"] - merged["cogs"]
    merged["gross_margin_pct"] = np.where(merged["revenue"] > 0, merged["gross_profit"] / merged["revenue"], 0)

    # === 费用汇总 ===
    expense_agg = expense.groupby(["month", "market"]).agg(
        total_expense=("expense_amount", "sum"),
    ).reset_index()
    ad_expense = expense[expense["expense_type"] == "Advertising"].groupby(["month", "market"]).agg(
        ad_expense=("expense_amount", "sum")
    ).reset_index()

    # === 月度汇总 KPI ===
    monthly_rev = merged.groupby("month").agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum")).reset_index()
    monthly_exp = expense.groupby("month").agg(total_expense=("expense_amount", "sum")).reset_index()
    monthly = monthly_rev.merge(monthly_exp, on="month", how="left")
    monthly["net_profit"] = monthly["gross_profit"] - monthly["total_expense"]
    monthly["gross_margin_pct"] = (monthly["gross_profit"] / monthly["revenue"]).round(4)
    monthly["net_profit_pct"] = (monthly["net_profit"] / monthly["revenue"]).round(4)
    monthly["expense_ratio"] = (monthly["total_expense"] / monthly["revenue"]).round(4)

    # 预算达成
    budget_monthly = budget.groupby("month").agg(budget_revenue=("budget_revenue", "sum")).reset_index()
    monthly = monthly.merge(budget_monthly, on="month", how="left")
    monthly["budget_achievement_pct"] = (monthly["revenue"] / monthly["budget_revenue"]).round(4)
    monthly["budget_variance"] = (monthly["revenue"] - monthly["budget_revenue"]).round(2)

    # === 按市场 KPI ===
    market_rev = merged.groupby(["month", "market"]).agg(
        revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum")
    ).reset_index()
    market_exp = expense.groupby(["month", "market"]).agg(total_expense=("expense_amount", "sum")).reset_index()
    by_market = market_rev.merge(market_exp, on=["month", "market"], how="left")
    by_market["net_profit"] = by_market["gross_profit"] - by_market["total_expense"]
    by_market["gross_margin_pct"] = (by_market["gross_profit"] / by_market["revenue"]).round(4)

    # === 按产品 KPI ===
    product_rev = merged.groupby(["month", "product"]).agg(
        revenue=("revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        quantity=("quantity", "sum"),
    ).reset_index()
    product_rev["gross_margin_pct"] = (product_rev["gross_profit"] / product_rev["revenue"]).round(4)

    # === 按渠道 KPI ===
    channel_rev = merged.groupby(["month", "channel"]).agg(
        revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum")
    ).reset_index()
    channel_rev["gross_margin_pct"] = (channel_rev["gross_profit"] / channel_rev["revenue"]).round(4)

    # === 广告 ROAS ===
    ad_by_market = merged.groupby(["month", "market"]).agg(revenue=("revenue", "sum")).reset_index()
    ad_by_market = ad_by_market.merge(ad_expense, on=["month", "market"], how="left")
    ad_by_market["ad_roas"] = np.where(
        ad_by_market["ad_expense"] > 0,
        (ad_by_market["revenue"] / ad_by_market["ad_expense"]).round(2),
        0
    )

    # === 库存周转 ===
    inv_monthly = inventory.groupby(["month", "market"]).agg(
        stock_value=("stock_value", "sum"),
        turnover_days=("turnover_days", "mean"),
    ).reset_index()

    # === 保存 ===
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly.round(4).to_csv(output_dir / "kpi_monthly.csv", index=False)
    by_market.round(4).to_csv(output_dir / "kpi_by_market.csv", index=False)
    product_rev.round(4).to_csv(output_dir / "kpi_by_product.csv", index=False)
    channel_rev.round(4).to_csv(output_dir / "kpi_by_channel.csv", index=False)
    ad_by_market.round(4).to_csv(output_dir / "kpi_ad_roas.csv", index=False)
    inv_monthly.round(4).to_csv(output_dir / "kpi_inventory.csv", index=False)

    return {
        "monthly": monthly,
        "by_market": by_market,
        "by_product": product_rev,
        "by_channel": channel_rev,
        "ad_roas": ad_by_market,
        "inventory": inv_monthly,
    }
