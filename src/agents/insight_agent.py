"""Insight Agent - LLM Agent，将结构化异常转为业务洞察"""

import json
from pathlib import Path
from src.llm.base import chat as llm_chat

SYSTEM_PROMPT = """你是一名资深财务经营分析师，服务于一家欧美市场小家电企业（500人以下）。

你的任务是将结构化的异常数据转化为管理层可理解的经营洞察和行动建议。

规则：
1. 只基于提供的数据进行分析，不要编造数据
2. 每个洞察控制在 150-300 字
3. 给出具体可执行的行动建议（2-3 条）
4. 使用中文输出
5. 输出严格的 JSON 格式"""


def run(output_dir: Path, anomaly_events: list, budget_report: dict, kpi_summary: dict) -> list:
    """为每个异常事件生成 AI 洞察"""
    if not anomaly_events:
        return []

    # 限制只处理 top 5 最严重的异常
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_events = sorted(anomaly_events, key=lambda e: severity_order.get(e.get("severity", "low"), 2))
    top_events = sorted_events[:5]

    user_prompt = f"""请为以下异常事件生成经营洞察。

## 异常事件
{json.dumps(top_events, indent=2, ensure_ascii=False)}

## 预算偏差摘要
{json.dumps(budget_report.get('summary', {}), indent=2, ensure_ascii=False)}

## KPI 摘要
{json.dumps(kpi_summary, indent=2, ensure_ascii=False)}

请输出一个 JSON 数组，每个元素格式如下：
{{
  "event_id": "对应异常事件ID",
  "title": "简短标题（10字以内）",
  "summary": "150-300字的分析摘要",
  "recommendations": ["建议1", "建议2", "建议3"]
}}"""

    try:
        result = llm_chat(SYSTEM_PROMPT, user_prompt)
        # 尝试提取 JSON
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            result = result.rsplit("```", 1)[0]
        insights = json.loads(result)
        if not isinstance(insights, list):
            insights = [insights]
    except Exception as e:
        # LLM 调用失败时生成兜底洞察
        insights = []
        for event in top_events:
            insights.append({
                "event_id": event.get("event_id", ""),
                "title": event.get("description", "")[:10],
                "summary": event.get("description", "") + f"（原始异常：{event.get('metric', '')} 变化 {event.get('change_pct_point', event.get('variance_pct', ''))}）",
                "recommendations": ["请人工复核该异常", "确认数据准确性后制定行动计划"],
            })

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ai_insights.json").write_text(
        json.dumps(insights, indent=2, ensure_ascii=False)
    )

    return insights
