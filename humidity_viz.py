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
    
    # 共通の日付入力
    st.header('日次データ入力')
    date = st.date_input("日付")

    with tab_sleep:
        st.subheader("睡眠データの分析")
        
        # データの読み込み
        try:
            df_sleep = pd.read_csv('dummy_sleep_data.csv')
            df_weather = pd.read_csv('tokyo_humidity_2025_10.csv')
            
            # データの結合
            df_merged = pd.merge(df_sleep, df_weather, on='Day', how='left')
            
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
            
        st.divider()
        st.subheader("睡眠記録")
        
        # 睡眠時間: カスタムUI
        st.write("睡眠時間")
        col_minus, col_disp, col_plus = st.columns([1, 2, 1])
        
        with col_minus:
            if st.button("－", key="sleep_minus"):
                st.session_state.sleep_time_val = max(0.0, st.session_state.sleep_time_val - 0.25)
                
        with col_plus:
            if st.button("＋", key="sleep_plus"):
                st.session_state.sleep_time_val = min(24.0, st.session_state.sleep_time_val + 0.25)
                
        with col_disp:
            h = int(st.session_state.sleep_time_val)
            m = int((st.session_state.sleep_time_val - h) * 60)
            st.markdown(f"#### {h}h {m:02d}m")

        sleep_quality = st.slider("睡眠の質 (1-5)", min_value=1, max_value=5, value=3)
        
        if st.button("睡眠データを保存", key="save_sleep"):
            h_save = int(st.session_state.sleep_time_val)
            m_save = int((st.session_state.sleep_time_val - h_save) * 60)
            formatted_time = f"{h_save}h {m_save:02d}m"
            st.success(f"睡眠データを保存しました: {date}, 時間: {formatted_time}, 質: {sleep_quality}")

    with tab_exercise:
        st.subheader("運動習慣の記録")
        step_count = st.number_input("歩数", min_value=0, step=1000)
        
        if st.button("運動データを保存", key="save_exercise"):
            st.success(f"運動データを保存しました: {date}, 歩数: {step_count}")

if __name__ == "__main__":
    main()
