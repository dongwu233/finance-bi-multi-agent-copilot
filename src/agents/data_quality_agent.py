"""Data Quality Agent - 规则型，不调用 LLM"""

import pandas as pd
from pathlib import Path


def run(data_dir: Path, output_dir: Path) -> dict:
    """执行数据质量检查"""
    checks = []

    # 加载数据
    sales = pd.read_csv(data_dir / "fact_sales.csv")
    cost = pd.read_csv(data_dir / "fact_cost.csv")
    expense = pd.read_csv(data_dir / "fact_expense.csv")
    products = pd.read_csv(data_dir / "dim_product.csv")
    fx = pd.read_csv(data_dir / "fx_rates.csv")

    # 1. SKU 映射检查
    valid_products = set(products["product_name"])
    invalid_sales = sales[~sales["product"].isin(valid_products)]
    if len(invalid_sales) > 0:
        checks.append({
            "check_name": "SKU mapping check",
            "status": "failed",
            "issue_count": len(invalid_sales),
            "impact_amount": round(invalid_sales["revenue"].sum(), 2),
            "recommendation": f"补充新品 SKU 主数据（{', '.join(invalid_sales['product'].unique())}），检查产品维表维护流程。",
        })
    else:
        checks.append({"check_name": "SKU mapping check", "status": "passed", "issue_count": 0})

    # 2. 市场/渠道缺失检查
    for col, table_name in [("market", "fact_sales"), ("channel", "fact_sales")]:
        missing = sales[sales[col].isna() | (sales[col] == "")]
        status = "failed" if len(missing) > 0 else "passed"
        checks.append({
            "check_name": f"{col} completeness in {table_name}",
            "status": status,
            "issue_count": len(missing),
        })

    # 3. 异常负值检查
    for col in ["revenue", "quantity"]:
        neg = sales[sales[col] < 0]
        if len(neg) > 0:
            checks.append({
                "check_name": f"negative {col} check",
                "status": "failed",
                "issue_count": len(neg),
                "impact_amount": round(neg[col].sum(), 2),
            })

    neg_cost = cost[cost["product_cost"] < 0]
    if len(neg_cost) > 0:
        checks.append({
            "check_name": "negative cost check",
            "status": "failed",
            "issue_count": len(neg_cost),
        })

    # 4. 汇率缺失检查
    months_in_sales = sales["month"].unique()
    currencies = ["USD", "EUR", "GBP"]
    missing_fx = []
    for m in months_in_sales:
        for c in currencies:
            if len(fx[(fx["month"] == m) & (fx["currency"] == c)]) == 0:
                missing_fx.append({"month": m, "currency": c})
    if missing_fx:
        checks.append({
            "check_name": "FX rate completeness",
            "status": "failed",
            "issue_count": len(missing_fx),
            "details": missing_fx,
            "recommendation": f"补充缺失汇率数据: {', '.join([f'{d['month']} {d['currency']}' for d in missing_fx])}",
        })
    else:
        checks.append({"check_name": "FX rate completeness", "status": "passed", "issue_count": 0})

    # 5. 重复导入检查
    dup_cols = ["month", "market", "channel", "product"]
    duplicates = sales[sales.duplicated(subset=dup_cols, keep=False)]
    dup_groups = len(duplicates) // 2 if len(duplicates) > 0 else 0
    checks.append({
        "check_name": "duplicate import check",
        "status": "failed" if dup_groups > 0 else "passed",
        "issue_count": dup_groups,
    })

    # 6. 毛利率合理性检查
    merged = sales.merge(
        cost.groupby(["month", "market", "channel", "product"])[
            ["product_cost", "freight_cost", "tariff_cost"]
        ].sum().reset_index(),
        on=["month", "market", "channel", "product"],
        how="left",
    )
    merged["cogs"] = merged["product_cost"].fillna(0) + merged["freight_cost"].fillna(0) + merged["tariff_cost"].fillna(0)
    merged["gross_margin"] = (merged["revenue"] - merged["cogs"]) / merged["revenue"]
    abnormal_gm = merged[(merged["gross_margin"] < 0) | (merged["gross_margin"] > 0.8)]
    checks.append({
        "check_name": "gross margin range check",
        "status": "failed" if len(abnormal_gm) > 0 else "passed",
        "issue_count": len(abnormal_gm),
    })

    # 汇总
    failed = [c for c in checks if c.get("status") == "failed"]
    report = {
        "total_checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "health_score": round((len(checks) - len(failed)) / len(checks) * 100, 1),
        "checks": checks,
    }

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    import json
    (output_dir / "data_quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )

    return report
