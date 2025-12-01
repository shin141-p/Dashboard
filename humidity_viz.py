import streamlit as st
import pandas as pd
import altair as alt
from streamlit_elements import elements, mui, html, dashboard
import json

def main():
    st.set_page_config(layout="wide", page_title="生活の可視化")
    
    # Draw 1445x650 border
    st.markdown("""
        <style>
        .fixed-border {
            width: 1445px;
            height: 650px;
            border: 2px solid #333;
            position: absolute;
            top: 60px; /* Adjust based on header height */
            left: 50%;
            transform: translateX(-50%);
            pointer-events: none;
            z-index: 0;
        }
        </style>
        <div class="fixed-border"></div>
    """, unsafe_allow_html=True)

    st.divider()
    
    if 'sleep_time_val' not in st.session_state:
        st.session_state.sleep_time_val = 7.0
    
    try:
        df_sleep = pd.read_csv('dummy_sleep_data.csv')
        df_weather = pd.read_csv('tokyo_humidity_2025_10.csv')
        df_merged = pd.merge(df_sleep, df_weather, on='Day', how='left')
        
        # Initialize dashboard layout for 3x3 grid
        # 12 columns total. 3 columns -> 4 units width each.
        # Height: Try to fit 650px. If rowHeight is default (~30-50px?), maybe h=4 or 5 per item?
        # Let's assume h=4 for now. 3 rows * 4 = 12 units height.
        if "layout" not in st.session_state:
            st.session_state.layout = [
                dashboard.Item("chart1", 0, 0, 4, 2),
                dashboard.Item("chart2", 4, 0, 4, 2),
                dashboard.Item("chart3", 8, 0, 4, 2),
                dashboard.Item("chart4", 0, 2, 4, 2),
                dashboard.Item("chart5", 4, 2, 4, 2),
                dashboard.Item("chart6", 8, 2, 4, 2),

            ]

        with elements("dashboard"):
            # Load Vega libraries inside the iframe context
            html.script(src="https://cdn.jsdelivr.net/npm/vega@5")
            html.script(src="https://cdn.jsdelivr.net/npm/vega-lite@5")
            html.script(src="https://cdn.jsdelivr.net/npm/vega-embed@6")

            def render_altair(chart, uid):
                spec = chart.to_dict()
                with html.div(style={'width': '100%', 'height': '100%'}):
                    html.div(id=uid, style={'width': '100%', 'height': '100%'})
                    html.script(f"""
                        (function() {{
                            const spec = {json.dumps(spec)};
                            const embed = () => {{
                                if (window.vegaEmbed) {{
                                    window.vegaEmbed('#{uid}', spec, {{actions: false}});
                                }} else {{
                                    setTimeout(embed, 100);
                                }}
                            }};
                            embed();
                        }})();
                    """)

            with dashboard.Grid(st.session_state.layout):
                
                # Helper to create a card with a chart
                def create_chart_card(key, title, chart):
                    with mui.Card(key=key, sx={"display": "flex", "flexDirection": "column", "height": "100%"}):
                        mui.CardHeader(title=title, titleTypographyProps={"variant": "subtitle1"})
                        with mui.CardContent(sx={"flex": 1, "minHeight": 0, "padding": "8px"}):
                            render_altair(chart.properties(width='container', height='container'), f"vis_{key}")

                # Chart Definitions
                base = alt.Chart(df_merged).encode(x=alt.X('Day', title='日'))
                
                # 1. Histogram
                # 1. Histogram
                hist = alt.Chart(df_sleep).mark_bar().encode(
                    alt.X("Sleep_Time", bin=alt.Bin(step=0.5), title="睡眠時間", axis=alt.Axis(format='.1f')),
                    y=alt.Y('count()', title='頻度'),
                    tooltip=[alt.Tooltip("Sleep_Time", bin=True, title="睡眠時間 (範囲)"), 'count()']
                )
                create_chart_card("chart1", "睡眠時間分布", hist)

                # 2. Sleep Time Bar
                bar_sleep = base.mark_bar(color='#5276A7').encode(y=alt.Y('Sleep_Time', title='睡眠時間'))
                create_chart_card("chart2", "ダミーデータ", bar_sleep)

                # 3. Humidity Line
                line_hum = base.mark_line(color='#F18727').encode(y=alt.Y('Avg_Humidity', title='湿度'))
                create_chart_card("chart3", "ダミーデータ", line_hum)

                # 4. Temperature Line
                line_temp = base.mark_line(color='#C0392B').encode(y=alt.Y('Avg_Temperature', title='気温'))
                create_chart_card("chart4", "ダミーデータ", line_temp)

                # 5. Scatter Sleep vs Humidity
                scatter_hum = alt.Chart(df_merged).mark_circle().encode(
                    x=alt.X('Avg_Humidity', title='湿度'),
                    y=alt.Y('Sleep_Time', title='睡眠時間')
                )
                create_chart_card("chart5", "ダミーデータ", scatter_hum)

                # 6. Scatter Sleep vs Temp
                scatter_temp = alt.Chart(df_merged).mark_circle().encode(
                    x=alt.X('Avg_Temperature', title='気温'),
                    y=alt.Y('Sleep_Time', title='睡眠時間')
                )
                create_chart_card("chart6", "ダミーデータ", scatter_temp)



    except FileNotFoundError as e:
        st.warning(f"データファイルが見つかりません: {e.filename}")

if __name__ == "__main__":
    main()
