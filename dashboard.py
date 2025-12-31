import streamlit as st
import pandas as pd
import plotly.express as px

# Load the dataset
# Adjust the path if necessary, but assuming it's in the same directory as per user usage
DATA_FILE = 'data_tent.csv'

def calculate_sleep_duration(row):
    try:
        bedtime = pd.to_datetime(row['就寝時間'], format='%H:%M:%S')
        waketime = pd.to_datetime(row['起床時間'], format='%H:%M:%S')
        
        # If wake time is earlier than bedtime, assume it's the next day
        if waketime < bedtime:
            waketime += pd.Timedelta(days=1)
            
        duration = (waketime - bedtime).total_seconds() / 3600
        return duration
    except Exception as e:
        return None

def format_hours(hours):
    """Convert decimal hours to XhYm format."""
    if pd.isna(hours):
        return ""
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h{m}m"

def hhmm_to_min(time_str):
    """Convert HH:MM:SS or HH:MM to minutes from 00:00."""
    if pd.isna(time_str):
        return 0
    parts = list(map(int, str(time_str).split(":")))
    return parts[0] * 60 + parts[1]

def interval_overlap(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))

def calculate_sleep_fit_score(row, target_start="23:30", target_end="07:30"):
    """
    Calculate how well the sleep fits into the target window.
    Score = (Overlap Duration / Actual Sleep Duration) * 100
    """
    ts = hhmm_to_min(target_start)
    te = hhmm_to_min(target_end)
    
    # Normalize target window to "Noon-to-Noon" timeline (Day defined as 12:00 to 12:00+24h)
    # If time < 12:00 (720 min), add 1440.
    if ts < 720: ts += 1440
    if te < 720: te += 1440
    if te <= ts: te += 1440 # Ensure end is after start if not already handled by normalization
    
    bs = hhmm_to_min(row['就寝時間'])
    we = hhmm_to_min(row['起床時間'])
    
    if bs < 720: bs += 1440
    if we < 720: we += 1440
    if we <= bs: we += 1440
    
    actual = we - bs
    overlap = interval_overlap(bs, we, ts, te)
    
    if actual == 0:
        return 0
    
    return min(100, (overlap / actual) * 100)

def update_chart_layout(fig):
    """Apply common layout settings."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#333333",
        title_font_size=22,
        height=320,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def main():
    st.set_page_config(layout="wide")

    st.markdown("""
<style>
/* カード風コンテナ */
.card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 14px;          /* 角を丸く */
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);  /* 影を柔らかく */
    margin-bottom: 20px;
}

/* Plotlyチャートのコンテナにカードスタイルを適用 */
[data-testid="stPlotlyChart"] {
    background-color: #ffffff;
    border-radius: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    padding: 10px;
}

/* KPI 用 */
.metric-card {
    background-color: #FAFAFA;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

/* 見出しを少し軽く */
h1, h2, h3 {
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

    st.title('睡眠時間ダッシュボード')

    # Sidebar Navigation
    page = st.sidebar.radio("メニュー", ["ダッシュボード", "設定"])

    import datetime

    # Defaults
    default_start = datetime.time(23, 30)
    default_end = datetime.time(7, 30)

    # --- Settings Logic ---
    # We need values for calculation regardless of current page
    # Use session state to persist or defaults if not set
    if "target_start_time" not in st.session_state:
        st.session_state.target_start_time = default_start
    if "target_end_time" not in st.session_state:
        st.session_state.target_end_time = default_end

    if page == "設定":
        st.subheader("睡眠スコア設定")
        st.write("推奨される睡眠時間帯を設定してください。")
        
        # Update session state via widget keys
        # Set value kwarg even with key to ensure default applies if key is new
        st.time_input("睡眠開始目標時間 (Target Start)", value=default_start, key="target_start_time")
        st.time_input("睡眠終了目標時間 (Target End)", value=default_end, key="target_end_time")

    # Get current values for calculation
    target_start_str = st.session_state.target_start_time.strftime("%H:%M")
    target_end_str = st.session_state.target_end_time.strftime("%H:%M")

    # Only load data and show dashboard if on dashboard page
    # However, for simplicity and to avoid reloading data issues if architecture changes,
    # we can load data always or just for dashboard.
    # Let's load data always for now to safe check columns etc if needed, 
    # but only render dashboard if page == "ダッシュボード"

    if page == "ダッシュボード":
        try:
            df = pd.read_csv(DATA_FILE)
            
            # Calculate sleep_duration_hour if it doesn't exist but the source columns do
            if 'sleep_duration_hour' not in df.columns:
                if '就寝時間' in df.columns and '起床時間' in df.columns:
                    df['sleep_duration_hour'] = df.apply(calculate_sleep_duration, axis=1)

            # Parse date and add weekday
            if '日付' in df.columns:
                df['date_dt'] = pd.to_datetime(df['日付'], format='%Y/%m/%d')
                weekday_map = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}
                df['weekday'] = df['date_dt'].dt.dayofweek.map(weekday_map)
                df['date_label'] = df['date_dt'].dt.strftime('%m/%d') + ' (' + df['weekday'] + ')'
            
            # Check if the required column exists (either originally or calculated)
            if 'sleep_duration_hour' in df.columns:
                # Calculate sleep fit score using SETTINGS values
                if '就寝時間' in df.columns and '起床時間' in df.columns:
                    # Use lambda to pass the dynamic target times
                    df['sleep_fit_score'] = df.apply(
                        lambda row: calculate_sleep_fit_score(row, target_start=target_start_str, target_end=target_end_str), 
                        axis=1
                    )

                # Create a function to generate the plot
                def create_plot(title_suffix=""):
                    valid_data = df['sleep_duration_hour'].dropna()
                    # Warm color for histogram, outline only
                    fig = px.histogram(valid_data, x="sleep_duration_hour",
                                       title=f'睡眠時間の分布 {title_suffix}',
                                       labels={'sleep_duration_hour': '睡眠時間 (時間)'})
                    
                    # 30 min bins, transparent fill, colored edge
                    fig.update_traces(xbins=dict(size=0.5),
                                      marker_color='rgba(0,0,0,0)',
                                      marker_line_color='#EF6C00',
                                      marker_line_width=3)
                                      
                    fig.update_layout(bargap=0, yaxis_title='頻度')
                    return update_chart_layout(fig)

                def create_weekly_bar_chart():
                    # Get last 7 days
                    df_sorted = df.sort_values('date_dt') # Ensure sorted
                    recent_data = df_sorted.tail(7).copy() # Use copy to avoid SettingWithCopyWarning
                    
                    # Calculate average
                    avg_sleep = recent_data['sleep_duration_hour'].mean()
                    avg_sleep_str = format_hours(avg_sleep)
                    
                    # Add formatted string column
                    recent_data['formatted_sleep'] = recent_data['sleep_duration_hour'].apply(format_hours)

                    # Warm color for bars
                    fig = px.bar(recent_data, x='date_label', y='sleep_duration_hour',
                                 title=f'睡眠時間 (過去7日間)<br>平均: {avg_sleep_str}',
                                 text='formatted_sleep',
                                 labels={'date_label': '日付', 'sleep_duration_hour': '睡眠時間 (時間)', 'formatted_sleep': '時間'})
                    # Add rounded corners (marker_cornerradius)
                    # Border color changed to inner color (#FF9800)
                    fig.update_traces(textposition='outside', marker_color='#FF9800', marker_line_color='#FF9800', marker_line_width=1.5, marker_cornerradius=15) # Vibrant Orange
                    
                    # Add horizontal line for average sleep
                    fig.add_hline(y=avg_sleep, line_dash="dash", line_color="#555555")
                    
                    # Update hover template to show formatted time
                    fig.update_traces(hovertemplate='日付: %{x}<br>睡眠時間: %{text}')
                    return update_chart_layout(fig)

                def display_weekly_quality_metrics():
                    # Get last 7 days
                    df_sorted = df.sort_values('date_dt')
                    recent_data = df_sorted.tail(7)
                    
                    # Calculate averages
                    # Columns: 寝つきの良さ, 寝起きの良さ, 日中の眠気
                    avg_onset = recent_data['寝つきの良さ'].mean()
                    avg_wake = recent_data['寝起きの良さ'].mean()
                    avg_drowsiness = recent_data['日中の眠気'].mean()
                    
                    st.write("### 週間平均 (過去7日間)")
                    
                    # Display metrics vertically
                    st.metric(label="寝つきの良さ (Sleep Onset Quality)", value=f"{avg_onset:.2f}")
                    st.metric(label="寝起きの良さ (Wake Up Quality)", value=f"{avg_wake:.2f}")
                    st.metric(label="日中の眠気 (Daytime Drowsiness)", value=f"{avg_drowsiness:.2f}")

                def create_sleep_debt_chart():
                    # Calculate debt: 7.5 - sleep_duration. If < 0 (surplus), set to 0.
                    df_sorted = df.sort_values('date_dt')
                    
                    # Calculate debt
                    debt_series = 7.5 - df_sorted['sleep_duration_hour']
                    debt_series = debt_series.apply(lambda x: max(0, x))
                    
                    # Create a temporary DF for plotting
                    plot_df = pd.DataFrame({
                        'date_label': df_sorted['date_label'],
                        'debt': debt_series
                    })
                    plot_df['formatted_debt'] = plot_df['debt'].apply(format_hours)
                    
                    fig = px.area(plot_df, x='date_label', y='debt',
                                  title='睡眠負債の推移 (理想: 7.5時間)',
                                  labels={'date_label': '日付', 'debt': '睡眠負債 (時間)'},
                                  custom_data=['formatted_debt']) # Pass formatted data
                    # Red/Salmon is already warm, keeping it as it represents "Debt/Warning"
                    fig.update_traces(line_color='#E64A19', fillcolor='rgba(255, 87, 34, 0.3)') # Darker Orange/Red
                    # Update hover to use formatted debt
                    fig.update_traces(hovertemplate='日付: %{x}<br>睡眠負債: %{customdata[0]}')
                    return update_chart_layout(fig)

                def create_sleep_histogram():
                    valid_data = df['sleep_duration_hour'].dropna()
                    # Warm color for histogram, outline only
                    fig = px.histogram(valid_data, x="sleep_duration_hour",
                                       title='睡眠時間の分布',
                                       labels={'sleep_duration_hour': '睡眠時間 (時間)'})
                    
                    # 30 min bins, transparent fill, colored edge
                    fig.update_traces(xbins=dict(size=0.5),
                                      marker_color='rgba(0,0,0,0)',
                                      marker_line_color='#EF6C00',
                                      marker_line_width=3)
                                      
                    fig.update_layout(bargap=0, yaxis_title='頻度')
                    return update_chart_layout(fig)

                def create_monthly_sleep_trend():
                    # Get last 30 days
                    df_sorted = df.sort_values('date_dt')
                    recent_data = df_sorted.tail(30).copy()
                    
                    # Add formatted string column
                    recent_data['formatted_sleep'] = recent_data['sleep_duration_hour'].apply(format_hours)
                    
                    fig = px.line(recent_data, x='date_label', y='sleep_duration_hour',
                                  title='睡眠時間の推移 (過去30日間)',
                                  markers=True,
                                  labels={'date_label': '日付', 'sleep_duration_hour': '睡眠時間 (時間)'},
                                  custom_data=['formatted_sleep'])
                    
                    # Style line and markers
                    fig.update_traces(line_color='#FF9800', line_width=3, 
                                      marker_size=8, marker_color='white', marker_line_color='#FF9800', marker_line_width=2,
                                      hovertemplate='日付: %{x}<br>睡眠時間: %{customdata[0]}')
                    
                    return update_chart_layout(fig)

                def create_sleep_score_trend():
                    # Get last 30 days
                    df_sorted = df.sort_values('date_dt')
                    recent_data = df_sorted.tail(30).copy()
                    
                    # Check if score exists
                    if 'sleep_fit_score' not in recent_data.columns:
                        return None

                    fig = px.line(recent_data, x='date_label', y='sleep_fit_score',
                                  title='推奨時間との一致度 (過去30日間)',
                                  markers=True,
                                  labels={'date_label': '日付', 'sleep_fit_score': '一致度 (%)'})
                    
                    # Style line and markers
                    fig.update_traces(line_color='#FFB74D', line_width=3, 
                                      marker_size=8, marker_color='white', marker_line_color='#FFB74D', marker_line_width=2,
                                      hovertemplate='日付: %{x}<br>一致度: %{y:.1f}%')
                    
                    # Set y-axis range 0-100 for percentage
                    fig.update_layout(yaxis_range=[0, 105])
                    
                    return update_chart_layout(fig)

                # Create 3 rows of 2 columns
                # Row 1
                c1, c2 = st.columns(2)
                with c1:
                    if 'date_dt' in df.columns:
                        st.plotly_chart(create_weekly_bar_chart(), use_container_width=True)
                    else:
                        st.plotly_chart(create_plot("(1)"), use_container_width=True)
                with c2:
                    # Check if quality columns exist
                    if all(col in df.columns for col in ['寝つきの良さ', '寝起きの良さ', '日中の眠気']):
                        # Use a container for metric card styling
                        with st.container():
                             display_weekly_quality_metrics()
                    else:
                         st.plotly_chart(create_plot("(2)"), use_container_width=True)

                # Row 2
                c3, c4 = st.columns(2)
                with c3:
                    if 'date_dt' in df.columns:
                        st.plotly_chart(create_sleep_debt_chart(), use_container_width=True)
                    else:
                        st.plotly_chart(create_plot("(3)"), use_container_width=True)
                with c4:
                    # SWAPPED: Sleep Score Trend is now mostly here (Position 4)
                    st.plotly_chart(create_sleep_score_trend(), use_container_width=True)
                
                # Row 3
                c5, c6 = st.columns(2)
                with c5:
                    st.plotly_chart(create_monthly_sleep_trend(), use_container_width=True)
                with c6:
                    # SWAPPED: Histogram is now here (Position 6)
                    st.plotly_chart(create_sleep_histogram(), use_container_width=True)

            else:
                st.error(f"'{DATA_FILE}' に 'sleep_duration_hour' カラムが見つからないか計算できませんでした")
                st.write("利用可能なカラム:", df.columns.tolist())

        except FileNotFoundError:
            st.error(f"ファイルが見つかりませんでした: {DATA_FILE}")

if __name__ == '__main__':
    main()
