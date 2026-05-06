# Finance BI Multi-Agent Copilot

面向欧美小家电企业的 AI 财务经营分析系统，基于多智能体架构自动完成数据校验、指标计算、异常检测、预算偏差分析和经营月报生成。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成模拟数据
python src/generate_demo_data.py

# 运行分析 Pipeline（不含 LLM）
python src/pipeline.py --month 2026-04

# 启动 Streamlit 仪表盘
streamlit run app.py
```

## 含 LLM 的完整 Pipeline

```bash
# 设置 API Key
export LLM_API_KEY="your_key"
export LLM_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export LLM_MODEL="mimo-v2.5-pro"

# 运行完整 Pipeline
python src/pipeline.py --month 2026-04
```

## 架构

```
模拟数据 CSV
  ↓
规则型 Agent（Python/pandas）
  ├── Data Quality Agent → 数据质量报告
  ├── Metric Agent → KPI 指标表
  ├── Anomaly Agent → 异常事件
  └── Budget Agent → 预算偏差
  ↓
LLM Agent（低成本 API）
  ├── Insight Agent → AI 洞察卡片
  └── Report Agent → 经营月报
  ↓
Streamlit 仪表盘（替代 Power BI）
```

## 仪表盘页面

1. **Executive Overview** — 收入/利润/毛利率总览、趋势图、市场排名
2. **Market Performance** — 各市场收入、毛利率、广告 ROAS、渠道结构
3. **Product Profitability** — 产品收入排名、毛利率、库存周转
4. **Budget Variance** — 实际 vs 预算、偏差率、超预算费用
5. **AI Insight Center** — 数据质量、异常事件、AI 洞察、经营月报

## 预埋异常

数据中预埋了以下异常供演示：
- 美国市场 2026-04 ASP 下降导致毛利率下降
- 德国 Amazon 2025-08 广告费超预算 40%
- 空气炸锅 2026-03 销量上升但利润下降
- 西班牙 2026-02 库存周转天数异常升高
- 2025-11 EUR 汇率缺失
- ~3% SKU 主数据缺失

## 项目结构

```
├── app.py                      # Streamlit 仪表盘
├── requirements.txt
├── config/
│   ├── settings.yaml           # 全局配置
│   └── metrics.yaml            # KPI 定义
├── src/
│   ├── generate_demo_data.py   # 模拟数据生成
│   ├── pipeline.py             # 流水线编排
│   ├── agents/
│   │   ├── data_quality_agent.py
│   │   ├── metric_agent.py
│   │   ├── anomaly_agent.py
│   │   ├── budget_agent.py
│   │   ├── insight_agent.py
│   │   └── report_agent.py
│   └── llm/
│       └── base.py             # LLM 客户端
├── data/
│   ├── raw/                    # 原始 CSV
│   └── powerbi/                # Power BI 用数据
└── outputs/                    # 分析结果
```
