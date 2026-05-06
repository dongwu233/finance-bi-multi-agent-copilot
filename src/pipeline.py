#!/usr/bin/env python3
"""Finance BI Multi-Agent Pipeline - 流水线编排"""

import argparse
import sys
import os
import json
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import data_quality_agent, metric_agent, anomaly_agent, budget_agent, insight_agent, report_agent


def run_pipeline(target_month: str):
    """运行完整分析流水线"""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / "raw"
    output_dir = base_dir / "outputs"

    print("=" * 60)
    print(f"🚀 Finance BI Multi-Agent Pipeline")
    print(f"📅 目标月份: {target_month}")
    print("=" * 60)

    # Step 1: 数据质量检查
    print("\n🔍 [1/6] Data Quality Agent...")
    dq_report = data_quality_agent.run(data_dir, output_dir)
    print(f"   ✅ 健康度: {dq_report['health_score']}% ({dq_report['passed']}/{dq_report['total_checks']} passed)")

    # Step 2: 指标计算
    print("\n📊 [2/6] Metric Agent...")
    metrics = metric_agent.run(data_dir, output_dir)
    print(f"   ✅ 计算完成: {len(metrics['monthly'])} 个月度指标")

    # Step 3: 异常检测
    print("\n⚠️  [3/6] Anomaly Agent...")
    anomaly_events = anomaly_agent.run(data_dir, output_dir, metrics)
    print(f"   ✅ 发现 {len(anomaly_events)} 个异常事件")

    # Step 4: 预算分析
    print("\n💰 [4/6] Budget Agent...")
    budget_report = budget_agent.run(data_dir, output_dir)
    print(f"   ✅ 预算达成率: {budget_report['summary']['revenue_achievement_pct']}%")

    # 准备 KPI 摘要（给 LLM 用）
    latest_month = metrics["monthly"]["month"].max()
    latest_kpi = metrics["monthly"][metrics["monthly"]["month"] == latest_month].iloc[0]
    kpi_summary = {
        "month": target_month,
        "revenue": round(latest_kpi["revenue"], 2),
        "gross_margin_pct": round(latest_kpi["gross_margin_pct"], 4),
        "net_profit": round(latest_kpi["net_profit"], 2),
        "net_profit_pct": round(latest_kpi["net_profit_pct"], 4),
        "expense_ratio": round(latest_kpi["expense_ratio"], 4),
        "budget_achievement_pct": round(latest_kpi.get("budget_achievement_pct", 0), 4),
    }

    # Step 5: AI 洞察
    print("\n🧠 [5/6] Insight Agent (LLM)...")
    api_key = os.getenv("LLM_API_KEY", "")
    if api_key:
        ai_insights = insight_agent.run(output_dir, anomaly_events, budget_report, kpi_summary)
        print(f"   ✅ 生成 {len(ai_insights)} 条洞察")
    else:
        print("   ⚠️  LLM_API_KEY 未设置，跳过 AI 洞察生成")
        ai_insights = []

    # Step 6: 经营月报
    print("\n📝 [6/6] Report Agent (LLM)...")
    if api_key:
        report = report_agent.run(output_dir, kpi_summary, anomaly_events, budget_report, ai_insights)
        print(f"   ✅ 月报已生成 ({len(report)} 字符)")
    else:
        print("   ⚠️  LLM_API_KEY 未设置，跳过月报生成")

    # 汇总
    print("\n" + "=" * 60)
    print("✅ Pipeline 完成！")
    print("=" * 60)
    print(f"\n📁 输出文件:")
    for f in sorted(output_dir.glob("*")):
        size = f.stat().st_size
        print(f"   {f.name} ({size:,} bytes)")

    return {
        "data_quality": dq_report,
        "metrics": kpi_summary,
        "anomalies": anomaly_events,
        "budget": budget_report,
        "insights": ai_insights,
    }


def main():
    parser = argparse.ArgumentParser(description="Finance BI Multi-Agent Pipeline")
    parser.add_argument("--month", type=str, default="2026-04", help="目标分析月份 (YYYY-MM)")
    args = parser.parse_args()

    run_pipeline(args.month)


if __name__ == "__main__":
    main()
