import streamlit as st
import pandas as pd
import altair as alt

def main():
    st.title('生活の可視化')
    
    st.divider()
    
    # タブの作成
    tab_sleep, tab_exercise = st.tabs(["睡眠時間", "運動習慣"])
    
    # セッション状態の初期化 (共通)
    if 'sleep_time_val' not in st.session_state:
        st.session_state.sleep_time_val = 7.0 # 7.0 hours
    


    with tab_sleep:
        st.subheader("睡眠データの分析")
        
        # データの読み込み
        try:
            df_sleep = pd.read_csv('dummy_sleep_data.csv')
            df_weather = pd.read_csv('tokyo_humidity_2025_10.csv')
            
            # データの結合
            df_merged = pd.merge(df_sleep, df_weather, on='Day', how='left')
            
            # 統計量の計算
            mean_sleep = df_sleep['Sleep_Time'].mean()
            std_sleep = df_sleep['Sleep_Time'].std()

            # CSS styling for stat boxes
            st.markdown("""
                <style>
                .stat-box {
                    border-radius: 10px;
                    padding: 15px;
                    background-color: #f0f2f6;
                    margin-bottom: 10px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
                }
                .stat-label {
                    font-size: 14px;
                    color: #555;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #000;
                    text-align: right;
                }
                </style>
            """, unsafe_allow_html=True)

            st.subheader("睡眠統計と分布 (直近1ヶ月)")
            col_hist, col_stats = st.columns([2, 1])
            
            with col_hist:
                # ヒストグラム
                hist = alt.Chart(df_sleep).mark_bar().encode(
                    alt.X("Sleep_Time", bin=alt.Bin(step=0.5), title="睡眠時間 (時間)"),
                    y=alt.Y('count()', title='頻度'),
                    tooltip=['count()']
                ).properties(
                    title='睡眠時間の分布 (30分区切り)'
                )
                st.altair_chart(hist, use_container_width=True)

            with col_stats:
                st.write("統計データ")
                
                st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">平均睡眠時間</div>
                        <div class="stat-value">{mean_sleep:.2f} 時間</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">標準偏差</div>
                        <div class="stat-value">{std_sleep:.2f} 時間</div>
                    </div>
                """, unsafe_allow_html=True)

            st.divider()

            # 比較データの選択
            compare_metric = st.selectbox("比較するデータ", ["なし", "平均湿度", "平均気温"])
            
            # 基本チャート (睡眠時間)
            base = alt.Chart(df_merged).encode(x=alt.X('Day', title='日'))
            
            bar_sleep = base.mark_bar(opacity=0.7, color='#5276A7').encode(
                y=alt.Y('Sleep_Time', title='睡眠時間 (時間)', scale=alt.Scale(domain=[0, 10])),
                tooltip=['Day', 'Sleep_Time']
            )
            
            if compare_metric == "なし":
                st.altair_chart(bar_sleep, use_container_width=True)
            else:
                if compare_metric == "平均湿度":
                    y2_col = 'Avg_Humidity'
                    y2_title = '平均湿度 (%)'
                    y2_color = '#F18727'
                    y2_domain = [0, 100]
                else: # 平均気温
                    y2_col = 'Avg_Temperature'
                    y2_title = '平均気温 (℃)'
                    y2_color = '#F18727'
                    y2_domain = [0, 35]
                
                bar_compare = base.mark_line(color=y2_color).encode(
                    y=alt.Y(y2_col, title=y2_title, scale=alt.Scale(domain=y2_domain)),
                    tooltip=['Day', y2_col]
                )
                
                # 2軸チャートの作成
                chart_dual = alt.layer(bar_sleep, bar_compare).resolve_scale(
                    y='independent'
                ).properties(
                    title=f'睡眠時間と{compare_metric}の関係'
                )
                
                st.altair_chart(chart_dual, use_container_width=True)

        except FileNotFoundError as e:
            st.warning(f"データファイルが見つかりません: {e.filename}")
            

    with tab_exercise:
        st.subheader("運動習慣の記録")
        step_count = st.number_input("歩数", min_value=0, step=1000)
        
        if st.button("運動データを保存", key="save_exercise"):
            st.success(f"運動データを保存しました: 歩数: {step_count}")

if __name__ == "__main__":
    main()