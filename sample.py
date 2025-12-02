import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("固定レイアウト・ダッシュボード（Streamlit標準版）")

# ==========[Layout]==========
left, center, right = st.columns([3, 4, 2])

# ---------------------------
# 左カラム：円・レーダー・棒
# ---------------------------
with left:
    st.subheader("睡眠時間分布")
    df_sleep = pd.read_csv('dummy_sleep_data.csv')
    
    mean_val = df_sleep['Sleep_Time'].mean()
    std_val = df_sleep['Sleep_Time'].std()
    
    c1, c2 = st.columns([3, 1])
    with c1:
        hist_fig = px.histogram(df_sleep, x="Sleep_Time", nbins=10)
        hist_fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(hist_fig, use_container_width=True)
    with c2:
        st.metric("Mean", f"{mean_val:.2f}")
        st.metric("Std", f"{std_val:.2f}")

    st.subheader("Department Radar")
    radar_fig = go.Figure()
    radar_fig.add_trace(go.Scatterpolar(
        theta=["A","B","C","D","E"],
        r=[70,50,60,90,80],
        fill='toself'
    ))
    radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True)))
    st.plotly_chart(radar_fig, use_container_width=True)

    st.subheader("Data Sampling")
    bar_fig = px.bar(x=["Mon","Tue","Wed","Thu"], y=[10,20,15,30])
    st.plotly_chart(bar_fig, use_container_width=True)

# ---------------------------
# 中央：折れ線 + KPI + ドーナツ
# ---------------------------
with center:
    st.subheader("睡眠時間傾向")
    df_trend = pd.read_csv('dummy_sleep_data.csv')
    df_weather = pd.read_csv('tokyo_humidity_2025_10.csv')
    df_merged = pd.merge(df_trend, df_weather, on='Day', how='left')

    metric = st.selectbox("比較するデータ", ["なし", "平均湿度", "平均気温"])

    fig = go.Figure()

    # Primary Axis: Sleep Time (Bar)
    fig.add_trace(go.Bar(
        x=df_merged['Day'],
        y=df_merged['Sleep_Time'],
        name='睡眠時間',
        marker_color='#5276A7'
    ))

    # Secondary Axis: Weather Data (Line)
    y_range = None
    if metric != "なし":
        if metric == "平均湿度":
            y_col = 'Avg_Humidity'
            y_title = '平均湿度 (%)'
            y_color = '#F18727'
            y_range = [0, 120]
        else:
            y_col = 'Avg_Temperature'
            y_title = '平均気温 (℃)'
            y_color = '#F18727'
            y_range = [0, 35]

        fig.add_trace(go.Scatter(
            x=df_merged['Day'],
            y=df_merged[y_col],
            name=metric,
            yaxis='y2',
            mode='lines+markers',
            line=dict(color=y_color)
        ))

    # Layout
    fig.update_layout(
        title=' ',
        yaxis=dict(
            title='睡眠時間 (時間)',
            range=[2, 12]
        ),
        yaxis2=dict(
            title=metric if metric != "なし" else "",
            range=y_range,
            overlaying='y',
            side='right',
            showgrid=False
        ),
        legend=dict(x=0, y=1.1, orientation='h'),
        margin=dict(l=0, r=0, t=40, b=0),
        height=340
    )

    st.plotly_chart(fig, use_container_width=True)


    # ドーナツ
    d1, d2 = st.columns(2)
    with d1:
        donut = px.pie(names=["Success","Fail"], values=[75,25], hole=0.5)
        st.plotly_chart(donut, use_container_width=True)
    with d2:
        donut2 = px.pie(names=["Fail","Other"], values=[63,37], hole=0.5)
        st.plotly_chart(donut2, use_container_width=True)

# ---------------------------
# 右：カード3つ
# ---------------------------
with right:
    st.subheader("Release")
    st.info("Version 1.0\nStable")

    st.subheader("Catalog Status")
    st.success("OK: 120\nNG: 20")

    st.subheader("Ranking")
    rank_fig = px.bar(x=["UI","API","Batch"], y=[80,60,45])
    st.plotly_chart(rank_fig, use_container_width=True)
