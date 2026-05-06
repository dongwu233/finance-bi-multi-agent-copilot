"""Report Agent - LLM Agent，生成经营月报"""

import json
from pathlib import Path
from src.llm.base import chat as llm_chat

SYSTEM_PROMPT = """你是一名资深财务分析师，负责撰写月度经营报告。

要求：
1. 报告面向管理层，语言精炼、专业
2. 只基于提供的数据，不要编造
3. 总字数控制在 1000-1500 字
4. 使用中文输出
5. 使用 Markdown 格式
6. 报告结构必须包含以下章节"""

REPORT_STRUCTURE = """
1. 本月经营概览
2. 收入与利润表现
3. 市场表现分析
4. 产品盈利分析
5. 预算执行分析
6. 费用异常分析
7. 库存与现金流风险
8. AI 发现的重点异常
9. 下月行动建议
"""


def run(output_dir: Path, kpi_summary: dict, anomaly_events: list, budget_report: dict, ai_insights: list) -> str:
    """生成经营月报"""
    month = kpi_summary.get("month", "未知")

    user_prompt = f"""请基于以下数据撰写 {month} 的经营月报。

## 报告结构
{REPORT_STRUCTURE}

## KPI 摘要
{json.dumps(kpi_summary, indent=2, ensure_ascii=False)}

## 预算偏差
{json.dumps(budget_report.get('summary', {}), indent=2, ensure_ascii=False)}
按市场: {json.dumps(budget_report.get('by_market', []), indent=2, ensure_ascii=False)}

## 异常事件
{json.dumps(anomaly_events[:5], indent=2, ensure_ascii=False)}

## AI 洞察
{json.dumps(ai_insights[:3], indent=2, ensure_ascii=False)}

请直接输出 Markdown 格式的月报，不要加任何解释。"""

    try:
        report = llm_chat(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        report = f"""# {month} 经营月报

## 1. 本月经营概览
LLM 服务不可用，无法自动生成月报。请查看 AI 洞察和预算偏差报告获取关键信息。

## 2. 关键数据
- 总收入: {kpi_summary.get('revenue', 'N/A')}
- 毛利率: {kpi_summary.get('gross_margin_pct', 'N/A')}
- 净利润: {kpi_summary.get('net_profit', 'N/A')}

---
*本报告因 LLM 服务异常自动生成兜底版本*
"""

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "management_report.md").write_text(report, encoding="utf-8")

    return report
