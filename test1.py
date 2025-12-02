import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from streamlit_elements import elements, mui, dashboard

st.set_page_config(layout="wide")
st.title("ダッシュボード（ダミーデータ入り）")

# =====================
# ダミーデータ作成
# =====================

# Trend 折れ線
trend_df = px.data.stocks().head(50)

# Catalog Distribution 円グラフ
catalog_df = px.data.tips()
catalog_pie = catalog_df["day"].value_counts().reset_index()
catalog_pie.columns = ["day", "count"]

# Department Radar
dept_labels = ["A", "B", "C", "D", "E"]
dept_values = [70, 50, 60, 90, 80]

# Data Sampling 棒グラフ
sample_df = px.data.tips().groupby("day").size().reset_index(name="count")

# Donut data
donut_values = [75, 25]
donut_labels = ["Success", "Fail"]

# KPI ダミー
kpi_dummy = {
    "KPI 1": 850000,
    "KPI 2": 750000,
    "KPI 3": 650000,
    "KPI 4": 550000,
}

# =====================
# レイアウト設定
# =====================

layout = [
    dashboard.Item("catalog_dist",      x=0,  y=0,  w=3, h=4),
    dashboard.Item("department_radar",  x=0,  y=4,  w=3, h=4),
    dashboard.Item("data_sampling",     x=0,  y=8,  w=3, h=4),

    dashboard.Item("trend",             x=3,  y=0,  w=6, h=5),

    dashboard.Item("kpi_1",             x=3,  y=5,  w=3, h=2),
    dashboard.Item("kpi_2",             x=6,  y=5,  w=3, h=2),
    dashboard.Item("kpi_3",             x=3,  y=7,  w=3, h=2),
    dashboard.Item("kpi_4",             x=6,  y=7,  w=3, h=2),

    dashboard.Item("donut_1",           x=3,  y=9,  w=3, h=4),
    dashboard.Item("donut_2",           x=6,  y=9,  w=3, h=4),

    dashboard.Item("release",           x=9,  y=0,  w=3, h=3),
    dashboard.Item("catalog_status",    x=9,  y=3,  w=3, h=4),
    dashboard.Item("interface_rank",    x=9,  y=7,  w=3, h=6),
]

# =====================
# 表示
# =====================

with elements("dashboard"):
    with dashboard.Grid(layout, draggableHandle=".draggable"):

        # --- Catalog Distribution ---
        pie_fig = px.pie(catalog_pie, values="count", names="day", hole=0.3)
        with mui.Paper(key="catalog_dist", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(pie_fig, use_container_width=True)

        # --- Department Radar ---
        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=dept_values,
            theta=dept_labels,
            fill='toself'
        ))
        radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True)))
        with mui.Paper(key="department_radar", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(radar_fig, use_container_width=True)

        # --- Data Sampling ---
        bar_fig = px.bar(sample_df, x="day", y="count")
        with mui.Paper(key="data_sampling", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(bar_fig, use_container_width=True)

        # --- Trend (折れ線) ---
        line_fig = px.line(trend_df, x="date", y="GOOG")
        with mui.Paper(key="trend", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(line_fig, use_container_width=True)

        # --- KPI ---
        for key_id, (label, value) in zip(
            ["kpi_1", "kpi_2", "kpi_3", "kpi_4"], 
            kpi_dummy.items()
        ):
            with mui.Paper(key=key_id, className="draggable", elevation=3, sx={"padding": "20px", "textAlign": "center"}):
                mui.Typography(f"{label}")
                mui.Typography(f"{value:,}")

        # --- Donut Charts ---
        donut_fig1 = px.pie(values=donut_values, names=donut_labels, hole=0.5)
        donut_fig2 = px.pie(values=[63, 37], names=["Fail", "Other"], hole=0.5)

        with mui.Paper(key="donut_1", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(donut_fig1, use_container_width=True)

        with mui.Paper(key="donut_2", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(donut_fig2, use_container_width=True)

        # --- 右側 Release ---
        with mui.Paper(key="release", className="draggable", elevation=3, sx={"padding": "15px"}):
            mui.Typography("Release Info (Dummy)")
            mui.Typography("Version 1.0")
            mui.Typography("Status: Stable")

        # --- Catalog Status ---
        with mui.Paper(key="catalog_status", className="draggable", elevation=3, sx={"padding": "15px"}):
            mui.Typography("Catalog Status Dummy")
            mui.Typography("OK: 120 / NG: 20")

        # --- Interfaces Rank ---
        rank_fig = px.bar(x=["UI", "API", "Batch"], y=[80, 65, 45])
        with mui.Paper(key="interface_rank", className="draggable", elevation=3, sx={"padding": "10px"}):
            st.plotly_chart(rank_fig, use_container_width=True)