import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("生活可視化のためのダッシュボード")

# ==========[Layout]==========
tab_selection = st.sidebar.radio("タブ切り替え", ["総合", "習慣"])

if tab_selection == "習慣":
    st.write("習慣タブ")

elif tab_selection == "総合":
    left, center = st.columns([3, 4])

    # ---------------------------
    # 左カラム：円・レーダー・棒
    # ---------------------------
    with left:
        st.subheader("睡眠時間分布")
        df_sleep = pd.read_csv('sleep_data_31days_full.csv')
        
        mean_val = df_sleep['sleep_duration_hour'].mean()
        std_val = df_sleep['sleep_duration_hour'].std()
        
        c1, c2 = st.columns([3, 1])
        with c1:
            hist_fig = px.histogram(df_sleep, x="sleep_duration_hour", nbins=10)
            hist_fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(hist_fig, use_container_width=True)
        with c2:
            st.metric("Mean", f"{mean_val:.2f}")
            st.metric("Std", f"{std_val:.2f}")

        st.subheader("歩数分布")
        dummy_data = pd.DataFrame({
            '日付': ["10/21", "10/22", "10/23", "10/24", "10/25", "10/26", "10/27"],
            '歩数': np.random.randint(2000, 10001, size=7)
        })
        bar_fig = px.bar(dummy_data, x='日付', y='歩数')
        st.plotly_chart(bar_fig, use_container_width=True)

    # ---------------------------
    # 中央：折れ線 + KPI + ドーナツ
    # ---------------------------
    with center:
        st.subheader("睡眠時間傾向")
        df_trend = pd.read_csv('sleep_data_31days_full.csv')
        df_trend = df_trend.rename(columns={'day': 'Day'})
        df_weather = pd.read_csv('tokyo_humidity_2025_10.csv')
        df_merged = pd.merge(df_trend, df_weather, on='Day', how='left')

        metric = st.selectbox("比較するデータ", ["なし", "平均湿度", "平均気温"])

        fig = go.Figure()

        # Primary Axis: Sleep Time (Line)
        fig.add_trace(go.Scatter(
            x=df_merged['Day'],
            y=df_merged['sleep_duration_hour'],
            name='睡眠時間',
            mode='lines+markers',
            line=dict(color='#5276A7')
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


        # Heatmap
        st.subheader("集中力ヒートマップ")
        np.random.seed(42)
        heatmap_data = np.random.randint(1, 6, size=(3, 7))
        x_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        y_labels = ['午前', '午後', '夜間']
        
        fig_heatmap = px.imshow(heatmap_data,
                                labels=dict(x="Day of Week", y="Category", color="Intensity"),
                                x=x_labels,
                                y=y_labels,
                                aspect="auto",
                                color_continuous_scale='OrRd')
        st.plotly_chart(fig_heatmap, use_container_width=True)
