#!/usr/bin/env python3
"""Finance BI Multi-Agent Copilot - Streamlit Dashboard"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 加载环境变量：优先 Streamlit Cloud secrets，其次本地 .env
if hasattr(st, 'secrets'):
    for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]:
        if key in st.secrets:
            os.environ.setdefault(key, str(st.secrets[key]))

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data" / "raw"

st.set_page_config(page_title="Finance BI Copilot", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ==================== 深色主题样式 ====================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .main .block-container { padding-top: 1.2rem; max-width: 1400px; }
    section[data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background: #161b22; padding: 16px; border-radius: 10px; border: 1px solid #30363d; }
    .stMetric label { color: #8b949e !important; font-size: 0.8rem !important; }
    .stMetric [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 1.6rem !important; }
    .stMetric [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }
    h1 { color: #e6edf3 !important; font-size: 1.8rem !important; }
    h2, .stSubheader { color: #c9d1d9 !important; font-size: 1.15rem !important; margin-top: 1.2rem; }
    h3 { color: #c9d1d9 !important; }
    p, span, label, .stMarkdown { color: #c9d1d9; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
    div[data-testid="stExpander"] summary { color: #c9d1d9; }
    .stSelectbox label, .stMultiSelect label { color: #c9d1d9 !important; }
    hr { border-color: #30363d !important; }
    .insight-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 12px 0; }
    .insight-card.warning { border-left: 4px solid #f85149; }
    .insight-card.warning h3 { color: #f85149 !important; }
    .insight-card.success { border-left: 4px solid #3fb950; }
    .insight-card.success h3 { color: #3fb950 !important; }
    .insight-card.info { border-left: 4px solid #58a6ff; }
    .insight-card.info h3 { color: #58a6ff !important; }
    .insight-card h3 { margin: 0 0 8px 0; font-size: 1rem; }
    .insight-card p { color: #c9d1d9; margin: 0 0 10px 0; line-height: 1.6; }
    .insight-card .rec { color: #8b949e; font-size: 0.85rem; }
    .report-box strong.warn { color: #f85149 !important; }
    .report-box strong.good { color: #3fb950 !important; }
    .report-box strong.neutral { color: #58a6ff !important; }
    .report-box { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 24px 28px; }
    .report-box h1, .report-box h2, .report-box h3 { color: #e6edf3 !important; }
    .report-box p, .report-box li { color: #c9d1d9; line-height: 1.7; }
    .report-box strong { color: #58a6ff; }
    .dq-item { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; margin: 6px 0; display: flex; align-items: center; gap: 10px; }
    .dq-item.pass { border-left: 3px solid #3fb950; }
    .dq-item.fail { border-left: 3px solid #f85149; }
    .anomaly-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 18px; margin: 8px 0; }
    .anomaly-high { border-left: 4px solid #f85149; }
    .anomaly-medium { border-left: 4px solid #d29922; }
    .anomaly-low { border-left: 4px solid #3fb950; }
</style>
""", unsafe_allow_html=True)

# Plotly 深色模板
DARK_LAYOUT = dict(
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
    font=dict(color="#c9d1d9"),
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    margin=dict(t=30, b=30, l=60, r=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b949e")),
)
COLORS = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#f0883e", "#79c0ff"]


# ==================== 数据加载 ====================
@st.cache_data
def load_data():
    data = {}
    for name in ["kpi_monthly", "kpi_by_market", "kpi_by_product", "kpi_by_channel", "kpi_ad_roas", "kpi_inventory"]:
        path = OUTPUT_DIR / f"{name}.csv"
        if path.exists():
            df = pd.read_csv(path)
            # 计算净利润率
            if "net_profit" in df.columns and "revenue" in df.columns and "net_profit_pct" not in df.columns:
                df["net_profit_pct"] = df["net_profit"] / df["revenue"]
            data[name] = df
    for name in ["data_quality_report", "anomaly_events", "budget_variance_report", "ai_insights"]:
        path = OUTPUT_DIR / f"{name}.json"
        if path.exists():
            data[name] = json.loads(path.read_text())
    report_path = OUTPUT_DIR / "management_report.md"
    if report_path.exists():
        data["management_report"] = report_path.read_text()
    return data


data = load_data()


# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("### Finance BI Copilot")
    st.caption("Multi-Agent Financial Analysis")
    st.divider()
    page = st.radio("导航", [
        "AI Insight Center",
        "Executive Overview",
        "Market Performance",
        "Product Profitability",
        "Budget Variance",
    ], label_visibility="collapsed")
    st.divider()
    if st.button("Run Pipeline", use_container_width=True, type="primary"):
        with st.spinner("Running..."):
            import subprocess
            result = subprocess.run([sys.executable, "src/pipeline.py", "--month", "2026-04"], capture_output=True, text=True, cwd=str(BASE_DIR))
            if result.returncode == 0:
                st.success("Done!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(result.stderr[:500])


def fmt_c(v):
    if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"


def fmt_p(v): return f"{v*100:.1f}%"


def dark_fig(fig, height=350):
    fig.update_layout(**DARK_LAYOUT, height=height)
    return fig


def insight(text, icon="💡"):
    st.markdown(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 16px;margin:8px 0;font-size:0.9rem;color:#8b949e;">{icon} {text}</div>', unsafe_allow_html=True)


# ==================== Page 1: Executive Overview ====================
if page == "Executive Overview":
    st.title("Executive Overview")

    monthly = data.get("kpi_monthly")
    dq = data.get("data_quality_report", {})
    budget = data.get("budget_variance_report", {})

    if monthly is not None and len(monthly) > 0:
        latest = monthly.iloc[-1]
        prev = monthly.iloc[-2] if len(monthly) > 1 else latest
        # 去年同期（如果有的话）
        yoy = monthly.iloc[-13] if len(monthly) > 12 else None

        # KPI 卡片
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        rev_mom = (latest['revenue']/prev['revenue']-1)*100
        rev_yoy = f"{(latest['revenue']/yoy['revenue']-1)*100:+.1f}% YoY" if yoy is not None else None
        c1.metric("Revenue", fmt_c(latest["revenue"]), delta=f"{rev_mom:+.1f}% MoM", help=rev_yoy)

        gp_mom = (latest['gross_profit']/prev['gross_profit']-1)*100
        c2.metric("Gross Profit", fmt_c(latest["gross_profit"]), delta=f"{gp_mom:+.1f}% MoM")

        gm_delta = (latest['gross_margin_pct'] - prev['gross_margin_pct']) * 100
        c3.metric("Gross Margin", fmt_p(latest['gross_margin_pct']), delta=f"{gm_delta:+.1f}pp MoM")

        np_mom = (latest['net_profit']/prev['net_profit']-1)*100 if prev['net_profit'] != 0 else 0
        c4.metric("Net Profit", fmt_c(latest["net_profit"]), delta=f"{np_mom:+.1f}% MoM")

        er_delta = (latest['expense_ratio'] - prev['expense_ratio']) * 100
        c5.metric("Expense Ratio", fmt_p(latest['expense_ratio']), delta=f"{er_delta:+.1f}pp MoM", delta_color="inverse")

        ba = latest.get('budget_achievement_pct', 0)
        c6.metric("Budget Achievement", fmt_p(ba), delta=f"目标 100%", delta_color="off")

        # 趋势图
        st.subheader("Revenue & Profit Trend")
        rev_trend = "上升" if latest["revenue"] > prev["revenue"] else "下降"
        insight(f"收入{rev_trend} {abs(latest['revenue']/prev['revenue']-1)*100:.1f}%，净利润率 {latest['net_profit']/latest['revenue']*100:.1f}%")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["revenue"], name="Revenue", line=dict(color=COLORS[0], width=2.5), fill="tozeroy", fillcolor="rgba(88,166,255,0.08)"))
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["gross_profit"], name="Gross Profit", line=dict(color=COLORS[1], width=2)))
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["net_profit"], name="Net Profit", line=dict(color=COLORS[2], width=2)))
        dark_fig(fig, 350)
        st.plotly_chart(fig, use_container_width=True)

        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Gross Margin Trend")
            gm_avg = monthly["gross_margin_pct"].mean()
            gm_trend = "改善" if latest["gross_margin_pct"] > monthly.iloc[-3]["gross_margin_pct"] else "承压"
            insight(f"毛利率均值 {gm_avg*100:.1f}%，近期呈{gm_trend}态势")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=monthly["month"], y=monthly["gross_margin_pct"], mode="lines+markers",
                                      line=dict(color=COLORS[0], width=2.5), marker=dict(size=6), fill="tozeroy", fillcolor="rgba(88,166,255,0.1)"))
            fig2.update_layout(yaxis_tickformat=".0%")
            dark_fig(fig2, 280)
            st.plotly_chart(fig2, use_container_width=True)

        with c_b:
            st.subheader("Data Quality Score")
            score = dq.get("health_score", 0)
            dq_status = "健康" if score >= 80 else "需关注" if score >= 50 else "风险"
            insight(f"数据质量评分 {score:.0f}/100，状态：{dq_status}")
            color = "#3fb950" if score >= 80 else "#d29922" if score >= 50 else "#f85149"
            fig3 = go.Figure(go.Indicator(mode="gauge+number", value=score, title={"text": "Health Score", "font": {"color": "#8b949e"}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                       "steps": [{"range": [0, 50], "color": "#2d1b1b"}, {"range": [50, 80], "color": "#2d2b1b"}, {"range": [80, 100], "color": "#1b2d1b"}]}))
            dark_fig(fig3, 280)
            st.plotly_chart(fig3, use_container_width=True)

        # 市场利润排名
        by_market = data.get("kpi_by_market")
        if by_market is not None:
            st.subheader("Market Profit Ranking")
            lm = by_market["month"].max()
            mk = by_market[by_market["month"] == lm].sort_values("gross_profit", ascending=True)
            top_mkt = mk.iloc[-1]
            insight(f"利润最高市场：{top_mkt['market']}（{fmt_c(top_mkt['gross_profit'])}），占总利润 {top_mkt['gross_profit']/mk['gross_profit'].sum()*100:.1f}%")
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(x=mk["gross_profit"], y=mk["market"], orientation="h",
                                  marker_color=[COLORS[i % len(COLORS)] for i in range(len(mk))],
                                  text=[fmt_c(v) for v in mk["gross_profit"]], textposition="outside"))
            dark_fig(fig4, 300)
            fig4.update_layout(yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig4, use_container_width=True)


# ==================== Page 2: Market Performance ====================
elif page == "Market Performance":
    st.title("Market Performance")

    by_market = data.get("kpi_by_market")
    ad_roas = data.get("kpi_ad_roas")

    if by_market is not None and len(by_market) > 0:
        markets = sorted(by_market["market"].unique().tolist())
        selected = st.multiselect("Markets", markets, default=markets[:4])
        filtered = by_market[by_market["market"].isin(selected)]

        st.subheader("Revenue by Market")
        latest_mkt = filtered[filtered["month"] == filtered["month"].max()]
        top_rev = latest_mkt.sort_values("revenue", ascending=False).iloc[0]
        insight(f"最新月收入最高：{top_rev['market']}（{fmt_c(top_rev['revenue'])}），共 {len(selected)} 个市场")
        fig = px.line(filtered, x="month", y="revenue", color="market", markers=True, color_discrete_sequence=COLORS)
        dark_fig(fig, 350)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Gross Margin by Market")
            gm_latest = filtered[filtered["month"] == filtered["month"].max()]
            best_gm = gm_latest.sort_values("gross_margin_pct", ascending=False).iloc[0]
            insight(f"毛利率最高：{best_gm['market']}（{best_gm['gross_margin_pct']*100:.1f}%）")
            fig2 = px.line(filtered, x="month", y="gross_margin_pct", color="market", markers=True, color_discrete_sequence=COLORS)
            fig2.update_layout(yaxis_tickformat=".0%")
            dark_fig(fig2, 300)
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            st.subheader("Net Margin by Market")
            if "net_profit_pct" in filtered.columns:
                nm_latest = filtered[filtered["month"] == filtered["month"].max()]
                best_nm = nm_latest.sort_values("net_profit_pct", ascending=False).iloc[0]
                insight(f"净利率最高：{best_nm['market']}（{best_nm['net_profit_pct']*100:.1f}%）")
                fig3 = px.line(filtered, x="month", y="net_profit_pct", color="market", markers=True, color_discrete_sequence=COLORS)
                fig3.update_layout(yaxis_tickformat=".0%")
                dark_fig(fig3, 300)
                st.plotly_chart(fig3, use_container_width=True)

    if ad_roas is not None and len(ad_roas) > 0:
        st.subheader("Ad ROAS by Market")
        f_roas = ad_roas[ad_roas["market"].isin(selected)] if selected else ad_roas
        roas_latest = f_roas[f_roas["month"] == f_roas["month"].max()]
        below_threshold = len(roas_latest[roas_latest["ad_roas"] < 3.0])
        insight(f"ROAS 低于阈值 3.0 的市场：{below_threshold} 个，需优化广告投放")
        fig4 = px.line(f_roas, x="month", y="ad_roas", color="market", markers=True, color_discrete_sequence=COLORS)
        fig4.add_hline(y=3.0, line_dash="dash", line_color="#f85149", annotation_text="ROAS Threshold 3.0", annotation_font_color="#f85149")
        dark_fig(fig4, 300)
        st.plotly_chart(fig4, use_container_width=True)

    by_channel = data.get("kpi_by_channel")
    if by_channel is not None and len(by_channel) > 0:
        st.subheader("Channel Mix")
        lm = by_channel["month"].max()
        ch = by_channel[by_channel["month"] == lm]
        top_ch = ch.sort_values("revenue", ascending=False).iloc[0]
        insight(f"最大渠道：{top_ch['channel']}（占比 {top_ch['revenue']/ch['revenue'].sum()*100:.1f}%）")
        fig5 = go.Figure(go.Pie(labels=ch["channel"], values=ch["revenue"], hole=0.45,
                                marker=dict(colors=COLORS), textfont=dict(color="#c9d1d9")))
        dark_fig(fig5, 350)
        st.plotly_chart(fig5, use_container_width=True)


# ==================== Page 3: Product Profitability ====================
elif page == "Product Profitability":
    st.title("Product Profitability")

    by_product = data.get("kpi_by_product")

    if by_product is not None and len(by_product) > 0:
        lm = by_product["month"].max()
        prod = by_product[by_product["month"] == lm].sort_values("revenue", ascending=False)

        st.subheader("Product Revenue")
        insight(f"Top 产品：{prod.iloc[0]['product']}（{fmt_c(prod.iloc[0]['revenue'])}），共 {len(prod)} 个 SKU")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=prod["product"], y=prod["revenue"],
                             marker_color=[COLORS[i % len(COLORS)] for i in range(len(prod))],
                             text=[fmt_c(v) for v in prod["revenue"]], textposition="outside"))
        dark_fig(fig, 350)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Gross Margin by Product")
            best_margin = prod.sort_values("gross_margin_pct", ascending=False).iloc[0]
            insight(f"毛利率最高：{best_margin['product']}（{best_margin['gross_margin_pct']*100:.1f}%）")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=prod["product"], y=prod["gross_margin_pct"],
                                  marker_color=[COLORS[i % len(COLORS)] for i in range(len(prod))],
                                  text=[fmt_p(v) for v in prod["gross_margin_pct"]], textposition="outside"))
            fig2.update_layout(yaxis_tickformat=".0%")
            dark_fig(fig2, 300)
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            st.subheader("Volume vs Profit")
            insight("气泡大小代表收入规模，右上角为高销量高利润产品")
            fig3 = go.Figure()
            for i, (_, row) in enumerate(prod.iterrows()):
                fig3.add_trace(go.Scatter(x=[row["quantity"]], y=[row["gross_profit"]], mode="markers+text",
                                          marker=dict(size=max(10, row["revenue"]/prod["revenue"].max()*40), color=COLORS[i % len(COLORS)]),
                                          text=[row["product"]], textposition="top center", showlegend=False))
            dark_fig(fig3, 300)
            st.plotly_chart(fig3, use_container_width=True)

        # 产品趋势
        st.subheader("Product Revenue Trend")
        prods = sorted(by_product["product"].unique().tolist())
        sel_p = st.multiselect("Products", prods, default=prods[:3])
        insight(f"已选择 {len(sel_p)} 个产品，查看收入趋势变化")
        pf = by_product[by_product["product"].isin(sel_p)]
        fig4 = px.line(pf, x="month", y="revenue", color="product", markers=True, color_discrete_sequence=COLORS)
        dark_fig(fig4, 350)
        st.plotly_chart(fig4, use_container_width=True)

    # 库存周转
    inventory = data.get("kpi_inventory")
    if inventory is not None and len(inventory) > 0:
        st.subheader("Inventory Turnover Days")
        avg_turnover = inventory["turnover_days"].mean()
        over_threshold = len(inventory[inventory["turnover_days"] > 120])
        insight(f"平均周转天数 {avg_turnover:.0f} 天，超阈值（>120天）的市场：{over_threshold} 个")
        fig5 = go.Figure()
        for i, mkt in enumerate(sorted(inventory["market"].unique())):
            m_data = inventory[inventory["market"] == mkt]
            fig5.add_trace(go.Box(y=m_data["turnover_days"], name=mkt, marker_color=COLORS[i % len(COLORS)]))
        fig5.add_hline(y=120, line_dash="dash", line_color="#f85149", annotation_text="Threshold 120d", annotation_font_color="#f85149")
        dark_fig(fig5, 350)
        st.plotly_chart(fig5, use_container_width=True)


# ==================== Page 4: Budget Variance ====================
elif page == "Budget Variance":
    st.title("Budget Variance")

    budget = data.get("budget_variance_report", {})

    if budget:
        summary = budget.get("summary", {})
        actual_rev = summary.get("total_actual_revenue", 0)
        budget_rev = summary.get("total_budget_revenue", 0)
        achievement = summary.get("revenue_achievement_pct", 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Actual Revenue", fmt_c(actual_rev), delta=f"达成率 {achievement:.1f}%")
        c2.metric("Budget Revenue", fmt_c(budget_rev), delta="年度目标", delta_color="off")
        var = summary.get("revenue_variance", 0)
        c3.metric("Revenue Variance", fmt_c(var), delta=f"{achievement - 100:+.1f}% vs Budget")
        profit_var = summary.get("profit_variance", 0)
        profit_var_pct = (profit_var / (actual_rev - var)) * 100 if (actual_rev - var) != 0 else 0
        c4.metric("Profit Variance", fmt_c(profit_var), delta=f"{profit_var_pct:+.1f}% vs Budget")

        by_mkt = budget.get("by_market", [])
        if by_mkt:
            st.subheader("Budget vs Actual by Market")
            mdf = pd.DataFrame(by_mkt)
            total_actual = mdf["actual_revenue"].sum()
            total_budget = mdf["budget_revenue"].sum()
            insight(f"总收入达成率 {(total_actual/total_budget*100):.1f}%，{'超额完成' if total_actual > total_budget else '未达预算'}")
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Actual", x=mdf["market"], y=mdf["actual_revenue"], marker_color=COLORS[0]))
            fig.add_trace(go.Bar(name="Budget", x=mdf["market"], y=mdf["budget_revenue"], marker_color="#30363d"))
            fig.update_layout(barmode="group")
            dark_fig(fig, 350)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Variance % by Market")
            over_markets = len(mdf[mdf["revenue_variance_pct"] < 0])
            insight(f"{over_markets} 个市场未达预算，需关注 {mdf.sort_values('revenue_variance_pct').iloc[0]['market']}")
            fig2 = go.Figure()
            colors_var = [COLORS[1] if v >= 0 else COLORS[3] for v in mdf["revenue_variance_pct"]]
            fig2.add_trace(go.Bar(x=mdf["market"], y=mdf["revenue_variance_pct"], marker_color=colors_var,
                                  text=[f"{v:+.1f}%" for v in mdf["revenue_variance_pct"]], textposition="outside"))
            fig2.add_hline(y=0, line_color="#484f58", line_width=1)
            dark_fig(fig2, 300)
            st.plotly_chart(fig2, use_container_width=True)

        over = budget.get("top_over_budget", [])
        if over:
            st.subheader("Over-Budget Items")
            odf = pd.DataFrame(over)
            st.dataframe(odf, use_container_width=True, hide_index=True)

    detail_path = OUTPUT_DIR / "budget_variance_detail.csv"
    if detail_path.exists():
        with st.expander("Full Budget Detail"):
            st.dataframe(pd.read_csv(detail_path).head(50), use_container_width=True, hide_index=True)


# ==================== Page 5: AI Insight Center ====================
elif page == "AI Insight Center":
    st.title("AI Insight Center")

    # --- 1. 经营月报（最前面） ---
    report = data.get("management_report")
    if report:
        st.subheader("Management Report")

        import re
        warn_kw = ["超支", "失控", "恶化", "侵蚀", "威胁", "下降", "亏损", "风险", "警告", "异常", "失灵", "未达", "压力", "承压", "挤压", "缺口", "拖累", "令人担忧", "严峻", "失速"]
        good_kw = ["达成", "超额", "增长", "改善", "健康", "优化", "提升", "达标", "盈利", "完成", "亮眼", "良好", "优秀", "强劲"]

        def colorize_strong(match):
            text = match.group(1)
            if any(k in text for k in warn_kw):
                return f'<strong class="warn">{text}</strong>'
            elif any(k in text for k in good_kw):
                return f'<strong class="good">{text}</strong>'
            else:
                return f'<strong class="neutral">{text}</strong>'

        colored_report = re.sub(r'<strong>(.*?)</strong>', colorize_strong, report)

        # 对正文中非 strong 包裹的关键词也进行着色
        warn_phrases = [
            "增收不增利", "增收减利", "利润承压", "利润缺口", "严重超支", "费用失控",
            "毛利率承压", "盈利下滑", "利润反向偏离", "利润大幅低于预算", "利润未达预算",
            "费用超支", "超预算", "利润率下降", "费用率过高", "盈利表现不佳",
            "未达目标", "核心风险", "系统性", "复发性", "立即核查", "立即关注",
            "紧急", "高度关注"
        ]
        good_phrases = [
            "超额完成", "表现亮眼", "增长质量良好", "表现最为健康", "高质量的增收",
            "预算达成率", "大幅超越", "收入增长强劲", "执行情况优秀", "增长平稳"
        ]

        # 为关键词添加颜色标记
        for phrase in warn_phrases:
            if phrase in colored_report and f'<span' not in colored_report.split(phrase)[0][-50:]:
                colored_report = colored_report.replace(phrase, f'<span style="color:#f85149;font-weight:600">{phrase}</span>')
        for phrase in good_phrases:
            if phrase in colored_report and f'<span' not in colored_report.split(phrase)[0][-50:]:
                colored_report = colored_report.replace(phrase, f'<span style="color:#3fb950;font-weight:600">{phrase}</span>')

        st.markdown(f'<div class="report-box">{colored_report}</div>', unsafe_allow_html=True)
    else:
        st.info("Run Pipeline with LLM_API_KEY to generate report")

    st.divider()

    # --- 2. AI 洞察 ---
    insights = data.get("ai_insights", [])
    if insights:
        st.subheader("AI Insights")
        # 关键词判断语义
        warn_keywords = ["超支", "失控", "恶化", "侵蚀", "威胁", "下降", "亏损", "风险", "警告", "异常", "失灵"]
        good_keywords = ["达成", "超额", "增长", "改善", "健康", "优化", "提升", "达标", "盈利"]

        for ins in insights:
            title = ins.get("title", "Insight")
            summary = ins.get("summary", "")
            recs = ins.get("recommendations", [])
            rec_html = "".join(f"<li>{r}</li>" for r in recs)

            # 根据标题和摘要判断类型
            text_to_check = title + summary
            is_warning = any(k in text_to_check for k in warn_keywords)
            is_good = any(k in text_to_check for k in good_keywords)
            card_type = "warning" if is_warning else ("success" if is_good else "info")

            st.markdown(f"""
            <div class="insight-card {card_type}">
                <h3>{title}</h3>
                <p>{summary}</p>
                {"<p class='rec'><b>Action Items:</b></p><ul class='rec'>" + rec_html + "</ul>" if recs else ""}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Run Pipeline with LLM_API_KEY to generate insights")

    st.divider()

    # --- 3. 异常事件 ---
    anomalies = data.get("anomaly_events", [])
    if anomalies:
        st.subheader(f"Anomaly Events ({len(anomalies)})")
        sev_order = {"high": 0, "medium": 1, "low": 2}
        sorted_a = sorted(anomalies, key=lambda x: sev_order.get(x.get("severity", "low"), 2))
        for a in sorted_a[:12]:
            sev = a.get("severity", "low")
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
            st.markdown(f"""
            <div class="anomaly-card anomaly-{sev}">
                <b>{icon} [{sev.upper()}]</b> {a.get('description', a.get('type', ''))}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- 4. 数据质量报告（最后） ---
    dq = data.get("data_quality_report", {})
    if dq:
        st.subheader("Data Quality Report")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Checks", dq.get("total_checks", 0))
        c2.metric("Passed", dq.get("passed", 0))
        c3.metric("Failed", dq.get("failed", 0))

        for check in dq.get("checks", []):
            passed = check["status"] == "passed"
            icon = "✅" if passed else "❌"
            st.markdown(f"""
            <div class="dq-item {'pass' if passed else 'fail'}">
                <span>{icon}</span>
                <span><b>{check['check_name']}</b> — {check.get('issue_count', 0)} issues</span>
            </div>
            """, unsafe_allow_html=True)
            if check.get("recommendation"):
                st.caption(f"  💡 {check['recommendation']}")
