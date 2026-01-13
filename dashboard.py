import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import gspread
from google.oauth2.service_account import Credentials

def add_cumulative_sleep_debt(df, actual_col, target_sleep_hours, mode="offset", output_col="sleep_debt_cum"):
    """
    Calculates cumulative sleep debt.
    Reference: sleep_debt_calc_new.py
    """
    out = df.copy()
    actual = pd.to_numeric(out[actual_col], errors="coerce")
    balance = target_sleep_hours - actual

    if mode == "offset":
        debt = []
        running = 0.0
        for x in balance:
            if pd.isna(x):
                debt.append(np.nan)
                continue
            running = max(0.0, running + x)
            debt.append(running)
        out[output_col] = debt
    else:
        # Simple accumulation (no offset)
        out[output_col] = balance.clip(lower=0).cumsum()
        
    return out

# Load the dataset
# Adjust the path if necessary, but assuming it's in the same directory as per user usage
DATA_FILE = 'data_tent.csv'
SPREADSHEET_ID = "1-cB-5Cs02wkfPMVg9s0pDhSgoYxALS9iOt2GeZOyNHk"

@st.cache_data(ttl=600)
def load_data_from_sheet():
    """Load data from Google Spreadsheet."""
    try:
        if "gcp_service_account" not in st.secrets:
            # Fallback to CSV
            return pd.read_csv(DATA_FILE)

        creds_info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        
        ws = client.open_by_key(SPREADSHEET_ID).worksheet("フォームの回答 1")
        data = ws.get_all_values()
        
        if not data:
            return pd.DataFrame()
            
        headers = data[0]
        rows = data[1:]
        return pd.DataFrame(rows, columns=headers)
        
    except Exception as e:
        st.sidebar.error(f"Sheet Error: {e}, falling back to CSV")
        try:
            return pd.read_csv(DATA_FILE)
        except:
            return pd.DataFrame()

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

def time_to_minutes(time_str):
    try:
        t = pd.to_datetime(time_str, format='%H:%M:%S')
        return t.hour * 60 + t.minute
    except:
        return None

def minutes_to_time(minutes):
    h = int(minutes // 60) % 24
    m = int(minutes % 60)
    return f"{h}:{m:02d}:00"

def fill_missing_archives(df):
    if df.empty or '日付' not in df.columns:
        return df
        
    df_filled = df.copy()
    df_filled['date_dt'] = pd.to_datetime(df_filled['日付'], format='%Y/%m/%d')
    df_filled = df_filled.sort_values('date_dt')
    
    min_date = df_filled['date_dt'].min()
    max_date = df_filled['date_dt'].max()
    
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    existing_dates = set(df_filled['date_dt'])
    
    missing_dates = [d for d in all_dates if d not in existing_dates]
    
    if not missing_dates:
        return df_filled
    
    new_rows = []
    
    # Needs to handle iterative filling? 
    # Current request: "Use average of past 1 week".
    # If we have [Data] [Gap 1] [Gap 2] ...
    # Gap 1 uses [Data]. Gap 2 uses [Data] + [Gap 1 (Filled)].
    # So we should iterate through all dates in order.
    
    # Re-build DataFrame date by date
    
    # Create a dict for faster access
    current_data = df_filled.set_index('date_dt').to_dict('index')
    
    filled_data_list = []
    
    for d in all_dates:
        row = None
        is_missing_record = False
        
        if d in current_data:
            row = current_data[d]
            row['date_dt'] = d # Ensure date_dt is kept
        else:
            is_missing_record = True
            row = {
                '日付': d.strftime('%Y/%m/%d'),
                'date_dt': d,
                '就寝時間': None,
                '起床時間': None,
                '昼寝の時間': None,
                '寝つきの良さ': 0,
                '寝起きの良さ': 0,
                '日中の眠気': 0,
                '目が覚めた回数': 0,
                'is_auto_filled': True # Marker
            }
        
        # Check for missing values in this row (whether new or existing)
        # Fields to check/fill
        fields_to_fill = ['就寝時間', '起床時間', '昼寝の時間']
        needs_fill = False
        for f in fields_to_fill:
            if f not in row or pd.isna(row[f]) or str(row[f]).strip() == '':
                 needs_fill = True
                 break
        
        if needs_fill:
            # Calculate Averages from past 7 days
            past_records = [r for r in filled_data_list if (d - r['date_dt']).days <= 7 and (d - r['date_dt']).days > 0]
            
            avg_bed_mins = []
            avg_wake_mins = []
            avg_nap_mins = []
            
            for r in past_records:
                if '就寝時間' in r and pd.notna(r['就寝時間']):
                    bm = time_to_minutes(r['就寝時間'])
                    if bm is not None:
                        if bm < 12 * 60: 
                            bm += 24 * 60
                        avg_bed_mins.append(bm)
                        
                if '起床時間' in r and pd.notna(r['起床時間']):
                     wm = time_to_minutes(r['起床時間'])
                     if wm is not None:
                         # Wake Time logic: just raw minutes usually ok?
                         # Or handle cross-day? Assuming wake is 4:00-15:00.
                         if wm < 12 * 60: 
                             wm += 24 * 60 # To be safe and consistent with logic below?
                             # In previous implementation I did: if wm < 12*60: wm+=24*60.
                             # But actually simply averaging raw minutes is risky if some are 23:00 and some are 01:00.
                             # For Wake time, it's usually morning. 
                             # Let's simple-average raw minutes for wake time assuming no midnight crossing for wake.
                             # Wait, look at previous code I replaced. 
                             # I had logic `if wm < 12*60: ... pass`. I didn't actually change wm.
                             # So I was just using raw `time_to_minutes`.
                             # BUT for Bedtime I did `bm += 24*60`.
                             pass
                     avg_wake_mins.append(time_to_minutes(r['起床時間']))

                if '昼寝の時間' in r and pd.notna(r['昼寝の時間']):
                     nm = time_to_minutes(r['昼寝の時間'])
                     if nm is not None:
                         avg_nap_mins.append(nm)

            # Fill missing fields
            if '就寝時間' not in row or pd.isna(row['就寝時間']) or str(row['就寝時間']).strip() == '':
                 if avg_bed_mins:
                    mean_bed = sum(avg_bed_mins) / len(avg_bed_mins)
                    mean_bed = mean_bed % (24 * 60)
                    row['就寝時間'] = minutes_to_time(mean_bed)
                 else:
                    row['就寝時間'] = '0:00:00' # Default
            
            if '起床時間' not in row or pd.isna(row['起床時間']) or str(row['起床時間']).strip() == '':
                 # Filter None
                 avg_wake_mins = [x for x in avg_wake_mins if x is not None]
                 if avg_wake_mins:
                     mean_wake = sum(avg_wake_mins) / len(avg_wake_mins)
                     row['起床時間'] = minutes_to_time(mean_wake)
                 else:
                     row['起床時間'] = '0:00:00'
            
            if '昼寝の時間' not in row or pd.isna(row['昼寝の時間']) or str(row['昼寝の時間']).strip() == '':
                 avg_nap_mins = [x for x in avg_nap_mins if x is not None]
                 if avg_nap_mins:
                     mean_nap = sum(avg_nap_mins) / len(avg_nap_mins)
                     row['昼寝の時間'] = minutes_to_time(mean_nap)
                 else:
                     row['昼寝の時間'] = '0:00:00'
                     
            if is_missing_record:
                row['is_auto_filled'] = True
            else:
                 row['is_partial_filled'] = True # Marker for debug if needed

        filled_data_list.append(row)
            
    # Reconstruct DF
    df_result = pd.DataFrame(filled_data_list)
    # Drop temp column
    if 'date_dt' in df_result.columns:
        # Keep it if needed, or drop. The usage later re-creates it.
        pass
        
    return df_result

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
    page = st.sidebar.radio("メニュー", ["ダッシュボード", "データ比較", "設定", "データ入力"])

    import datetime

    # Defaults
    default_start = datetime.time(23, 0)
    default_end = datetime.time(6, 30)

    # --- Settings Logic ---
    # We need values for calculation regardless of current page
    # Use session state to persist or defaults if not set
    if "target_start_time" not in st.session_state:
        st.session_state.target_start_time = default_start
    if "target_end_time" not in st.session_state:
        st.session_state.target_end_time = default_end
    if "target_sleep_duration" not in st.session_state:
        st.session_state.target_sleep_duration = 7.5

    if page == "設定":
        st.subheader("睡眠時間帯設定")
        st.write("理想の睡眠時間帯を設定してください。")
        
        # Update session state via widget keys
        # Set value kwarg even with key to ensure default applies if key is new
        st.time_input("理想の睡眠開始時間", value=default_start, key="target_start_time")
        st.time_input("理想の睡眠終了時間", value=default_end, key="target_end_time")
        
        st.subheader("目標睡眠時間設定")
        st.write("ここで設定した時間を基準に、毎日の睡眠負債を算出します。")
        val = st.number_input("理想の睡眠時間", min_value=4.0, max_value=12.0, value=7.5, step=0.25, key="target_sleep_duration", help="睡眠負債の計算やグラフの目標線に使用されます。")
        # Display formatted conversion
        total_minutes = int(round(val * 60))
        h_val = total_minutes // 60
        m_val = total_minutes % 60
        st.write(f"設定値: **{h_val}時間 {m_val:02d}分**")

    if page == "データ入力":
        st.subheader("データアップロード")
        st.write("CSVファイルをアップロードしてデータを更新します。形式は下部から入力するものと同じである必要があります。")
        
        # Download Button
        with open(DATA_FILE, "rb") as file:
            st.download_button(
                label="現在のCSVデータをダウンロード",
                data=file,
                file_name="data_tent_updated.csv",
                mime="text/csv"
            )

        uploaded_file = st.file_uploader("CSVファイルをドラッグ＆ドロップ", type="csv")
        
        if uploaded_file is not None:
            try:
                # Try reading the uploaded CSV
                new_df = pd.read_csv(uploaded_file)
                
                # Validation: Check for required columns
                # We base this on the structure of data_tent.csv
                # It seems minimal requirements are '就寝時間' and '起床時間' for calculations,
                # but let's check for a few key ones to ensure it's the right format.
                required_cols = ['タイムスタンプ', '日付', '就寝時間', '起床時間']
                
                if all(col in new_df.columns for col in required_cols):
                    # Save the file
                    new_df.to_csv(DATA_FILE, index=False)
                    st.success(f"データが正常に更新されました: {DATA_FILE}")
                    st.write("プレビュー:")
                    st.dataframe(new_df.head())
                else:
                    st.error(f"エラー: 必要なカラムが見つかりません。以下のカラムが必要です: {', '.join(required_cols)}")
                    st.write("アップロードされたカラム:", new_df.columns.tolist())
                    
            except Exception as e:
                st.error(f"ファイルの読み込みまたは保存中にエラーが発生しました: {e}")

        # --- Manual Data Entry Form ---
        st.write("---")
        st.subheader("データ入力")
        st.write("日々のデータを手動で追加します。")

        with st.form("manual_entry_form"):
            col_date, col_bed, col_wake, col_nap = st.columns(4)
            with col_date:
                input_date = st.date_input("日付", value=datetime.date.today())
            with col_bed:
                input_bedtime = st.time_input("就寝時間", value=datetime.time(23, 30))
            with col_wake:
                input_waketime = st.time_input("起床時間", value=datetime.time(7, 30))
            with col_nap:
                input_naptime = st.time_input("昼寝の時間", value=datetime.time(0, 0))

            col_q1, col_q2, col_q3, col_count = st.columns(4)
            with col_q1:
                input_onset = st.slider("寝つきの良さ (1-5)", 1, 5, 3)
            with col_q2:
                input_wake_quality = st.slider("寝起きの良さ (1-5)", 1, 5, 3)
            with col_q3:
                input_drowsiness = st.slider("日中の眠気 (1-5)", 1, 5, 3)
            with col_count:
                input_wake_count = st.number_input("目が覚めた回数", min_value=0, value=0, step=1)

            submitted = st.form_submit_button("データを追加")

            if submitted:
                # Prepare data
                timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                date_str = input_date.strftime("%Y/%m/%d")
                bedtime_str = input_bedtime.strftime("%H:%M:%S")
                waketime_str = input_waketime.strftime("%H:%M:%S")
                naptime_str = input_naptime.strftime("%H:%M:%S")

                new_data = {
                    'タイムスタンプ': [timestamp],
                    '日付': [date_str],
                    '就寝時間': [bedtime_str],
                    '起床時間': [waketime_str],
                    '昼寝の時間': [naptime_str],
                    '寝つきの良さ': [input_onset],
                    '寝起きの良さ': [input_wake_quality],
                    '日中の眠気': [input_drowsiness],
                    '目が覚めた回数': [input_wake_count]
                }
                
                new_row_df = pd.DataFrame(new_data)
                
                try:
                    # Append to existing CSV
                    # Read existing to check columns or just append
                    # If file exists, append without header. If not, write with header.
                    # But we trust DATA_FILE exists.
                    new_row_df.to_csv(DATA_FILE, mode='a', header=False, index=False)
                    st.success(f"データを追加しました: {date_str}")
                    
                    # Show the added data
                    st.write("追加されたデータ:")
                    st.dataframe(new_row_df)

                except Exception as e:
                    st.error(f"データの保存中にエラーが発生しました: {e}")

    # Get current values for calculation
    target_start_str = st.session_state.target_start_time.strftime("%H:%M")
    target_end_str = st.session_state.target_end_time.strftime("%H:%M")

    # Only load data and show dashboard if on dashboard page
    # However, for simplicity and to avoid reloading data issues if architecture changes,
    # we can load data always or just for dashboard.
    # Let's load data always for now to safe check columns etc if needed, 
    # but only render dashboard if page == "ダッシュボード"

    if page == "データ比較":
        st.subheader("データ比較")
        try:
            df = load_data_from_sheet()
            
            # Apply Auto-Filling for missing dates if needed
            df = fill_missing_archives(df)
            
            # Preprocess
            if '日付' in df.columns:
                df['date_dt'] = pd.to_datetime(df['日付'], format='%Y/%m/%d')
            
            # Calculate sleep duration if needed
            if '就寝時間' in df.columns and '起床時間' in df.columns:
                 df['sleep_duration_hour'] = df.apply(calculate_sleep_duration, axis=1)
            
            # Calculate nap duration
            if '昼寝の時間' in df.columns:
                def calc_nap(row):
                    try:
                        return time_to_minutes(row['昼寝の時間']) / 60.0
                    except:
                        return 0.0
                df['nap_duration_hour'] = df.apply(calc_nap, axis=1).fillna(0)
            else:
                df['nap_duration_hour'] = 0.0

            # Calculate total sleep (Night + Nap)
            if 'sleep_duration_hour' in df.columns:
                 df['total_sleep_hour'] = df['sleep_duration_hour'].fillna(0) + df['nap_duration_hour']
            
            # --- Date Selection ---
            if 'date_dt' in df.columns and not df.empty:
                min_date = df['date_dt'].min().date()
                max_date = df['date_dt'].max().date()
                
                # Default to last 14 days
                default_start = max(min_date, max_date - datetime.timedelta(days=13))
                
                st.write("### 期間選択")
                date_range = st.date_input(
                    "比較する期間を選択してください",
                    value=(default_start, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                # Filter Data
                if len(date_range) == 2:
                    start_sel, end_sel = date_range
                    # Convert to datetime for comparison
                    start_sel_dt = pd.Timestamp(start_sel)
                    end_sel_dt = pd.Timestamp(end_sel)
                    
                    # Split into Selected and Others
                    mask_selected = (df['date_dt'] >= start_sel_dt) & (df['date_dt'] <= end_sel_dt)
                    df_selected = df[mask_selected].copy()
                    df_others = df[~mask_selected].copy()
                else:
                    st.warning("開始日と終了日を選択してください。")
                    df_selected = df.copy()
                    df_others = pd.DataFrame()
            else:
                st.info("データがありません。")
                df_selected = pd.DataFrame()
                df_others = pd.DataFrame()


            def create_reference_sleep_chart_for_df(target_df, chart_title, compact_view=False):
                # Visualize sleep with Base 19:00 for a specific dataframe
                
                if target_df.empty or 'date_dt' not in target_df.columns or '就寝時間' not in target_df.columns or '起床時間' not in target_df.columns:
                    return None

                df_sorted = target_df.sort_values('date_dt').copy()
                
                dates = []
                bases = []
                heights = []
                
                # Data for Updatemenus
                metrics_list = ["指定なし", "寝起きの良さ", "寝つきの良さ", "日中の眠気", "目が覚めた回数"]
                metrics_data = {m: {'colors': [], 'texts': []} for m in metrics_list}
                
                BASE_HOUR = 19
                
                def adjust_hour(h):
                    # Map 0..24 to 19..43 range
                    if h < BASE_HOUR:
                        return h + 24.0
                    return h
                
                # Pre-calculate target range for gap bar
                gap_base = BASE_HOUR
                gap_height = 24.0
                
                if "target_start_time" in st.session_state and "target_end_time" in st.session_state:
                    ts_val = st.session_state.target_start_time
                    te_val = st.session_state.target_end_time
                    
                    ts_raw = ts_val.hour + ts_val.minute/60.0
                    te_raw = te_val.hour + te_val.minute/60.0
                    
                    ts_adj = adjust_hour(ts_raw)
                    te_adj = adjust_hour(te_raw)
                    
                    if te_adj < ts_adj:
                        te_adj += 24.0
                        
                    gap_base = ts_adj
                    gap_height = te_adj - ts_adj

                # Iterate to build data, inserting gap if needed
                prev_date = None
                
                for _, row in df_sorted.iterrows():
                    current_date = row['date_dt']
                    
                    # Detect Gap (Only for compact view where we want to show a customized separator)
                    if compact_view and prev_date is not None:
                        delta = (current_date - prev_date).days
                        if delta > 1:
                            # Insert Separator
                            dates.append("GAP") # Marker
                            bases.append(gap_base)
                            heights.append(gap_height)
                            for m in metrics_list:
                                metrics_data[m]['colors'].append('#9E9E9E')
                                metrics_data[m]['texts'].append("期間外 (省略)")
                    
                    prev_date = current_date

                    try:
                        # Parse decimal hours
                        b_dt = pd.to_datetime(row['就寝時間'], format='%H:%M:%S')
                        w_dt = pd.to_datetime(row['起床時間'], format='%H:%M:%S')
                        
                        b_raw = b_dt.hour + b_dt.minute/60.0
                        w_raw = w_dt.hour + w_dt.minute/60.0
                        
                        b_adj = adjust_hour(b_raw)
                        w_adj = adjust_hour(w_raw)
                        
                        if w_adj < b_adj:
                            w_adj += 24.0
                        
                        limit = BASE_HOUR + 24.0

                        # Pre-calc Logic for ALL metrics
                        current_colors = {}
                        current_texts = {}
                        
                        for m in metrics_list:
                            c_code = '#FF9800' # Default Orange
                            t_str = f"{row['就寝時間']} - {row['起床時間']}"
                            
                            if m != "指定なし":
                                c_code = '#9E9E9E' # Default Grey
                                val_label = "-"
                                if m in row:
                                    try:
                                        val = float(row[m])
                                        val_label = str(val).rstrip('0').rstrip('.') if val % 1 == 0 else f"{val:.1f}"
                                        
                                        if val <= 0.1: c_code = '#9E9E9E'
                                        elif val < 1.5: c_code = '#FFE0B2'
                                        elif val < 2.5: c_code = '#FFCC80'
                                        elif val < 3.5: c_code = '#FFB74D'
                                        elif val < 4.5: c_code = '#FFA726'
                                        else: c_code = '#F57C00'
                                    except:
                                        pass
                                t_str = f"{row['就寝時間']} - {row['起床時間']}<br>{m}: {val_label}"
                            
                            current_colors[m] = c_code
                            current_texts[m] = t_str
                        
                        if w_adj <= limit:
                            dates.append(current_date)
                            bases.append(b_adj)
                            heights.append(w_adj - b_adj)
                            for m in metrics_list:
                                metrics_data[m]['colors'].append(current_colors[m])
                                metrics_data[m]['texts'].append(current_texts[m])
                        else:
                            # Split
                            dates.append(current_date)
                            bases.append(b_adj)
                            heights.append(limit - b_adj)
                            for m in metrics_list:
                                metrics_data[m]['colors'].append(current_colors[m])
                                metrics_data[m]['texts'].append(current_texts[m])
                            
                            dates.append(next_date)
                            bases.append(BASE_HOUR) 
                            heights.append(w_adj - 24.0 - BASE_HOUR) 
                            for m in metrics_list:
                                metrics_data[m]['colors'].append(current_colors[m])
                                metrics_data[m]['texts'].append(current_texts[m])
                            
                    except Exception:
                        continue
                
                # Process X-values
                x_vals = []
                if compact_view:
                    xaxis_config = dict(
                        title='日付',
                        type='category',
                        tickangle=-45
                    )
                    # Convert dates to strings, handling GAP
                    unique_dates = []
                    # Plotly bar charts group by X. If we have duplicate dates (split bars), it handles them.
                    # But "GAP" string might be duplicated if we have multiple gaps? 
                    # User likely selects one range -> 2 chunks of data -> 1 GAP.
                    # If user selects middle, we have [Before] [GAP] [After].
                    
                    for d in dates:
                        if d == "GAP":
                            x_vals.append("...期間...")
                        elif isinstance(d, pd.Timestamp):
                            x_vals.append(d.strftime('%m/%d'))
                        else:
                             x_vals.append(str(d))
                             
                else:
                     x_vals = dates
                     xaxis_config = dict(
                        title='日付',
                        tickformat='%m/%d',
                        tickangle=-45,
                        range=None
                     )
                     if not df_sorted.empty:
                         first_date = df_sorted['date_dt'].min() - pd.Timedelta(days=0.5)
                         last_date = df_sorted['date_dt'].max() + pd.Timedelta(days=0.5)
                         xaxis_config['range'] = [first_date, last_date]

                fig = go.Figure()
                
                # Add Legend for Colors (Optional but helpful)
                # Since we color bars individually, we don't have a built-in legend for values.
                # We can add dummy traces for legend?
                # Let's keep it simple first as requested. Only bars change color.

                # Add Recommended Time Highlight (Background)
                # Note: Background shape on categorical axis might behave differently?
                # Shapes use xref='paper' for full width or 'x' for coordinates.
                # If we use 'paper' (0 to 1), it covers the whole width regardless of axis type.
                # So highlighting the Y-range across all X is fine.
                
                if "target_start_time" in st.session_state and "target_end_time" in st.session_state:
                    ts_val = st.session_state.target_start_time
                    te_val = st.session_state.target_end_time
                    
                    ts_raw = ts_val.hour + ts_val.minute/60.0
                    te_raw = te_val.hour + te_val.minute/60.0
                    
                    ts_adj = adjust_hour(ts_raw)
                    te_adj = adjust_hour(te_raw)
                    
                    if te_adj < ts_adj:
                        te_adj += 24.0
                    
                    fig.add_shape(
                       type="rect",
                       x0=0, x1=1, xref="paper",
                       y0=ts_adj, y1=te_adj, yref="y",
                       fillcolor="rgba(135, 206, 235, 0.3)",
                       line_width=0,
                       layer="below"
                    )

                fig.add_trace(go.Bar(
                    x=x_vals,
                    y=heights,
                    base=bases,
                    marker_color=metrics_data['指定なし']['colors'],
                    hovertext=metrics_data['指定なし']['texts'],
                    hovertemplate='日付: %{x}<br>時間: %{hovertext}<extra></extra>'
                ))

                tick_vals = list(range(BASE_HOUR, BASE_HOUR + 18))
                tick_text = [str(t % 24) + ":00" for t in tick_vals]
                
                # Updatemenus
                buttons = []
                for m in metrics_list:
                    buttons.append(dict(
                        method='restyle',
                        label=m,
                        visible=True,
                        args=[{
                            'marker.color': [metrics_data[m]['colors']],
                            'hovertext': [metrics_data[m]['texts']]
                        }]
                    ))
                
                updatemenus = [dict(
                    buttons=buttons,
                    direction='down',
                    pad={'r': 10, 't': 10},
                    showactive=True,
                    x=1,
                    xanchor='right',
                    y=1.15,
                    yanchor='top',
                    bgcolor='white',
                    bordercolor='#ddd',
                    font=dict(size=11)
                )]
                
                fig.update_layout(
                    title=dict(
                        text=chart_title,
                        font=dict(size=24)
                    ),
                    yaxis=dict(
                        title='時間',
                        range=[BASE_HOUR + 17, BASE_HOUR], 
                        tickmode='array',
                        tickvals=tick_vals,
                        ticktext=tick_text,
                        dtick=1
                    ),
                    xaxis=xaxis_config,
                    showlegend=False,
                    updatemenus=updatemenus,
                    margin=dict(t=80) 
                )
                
                fig = update_chart_layout(fig)
                
                if not compact_view:
                     fig.update_layout(height=690)
                else:
                     # User requested to match size with Selected Period
                     fig.update_layout(height=690)

                return fig

            def create_sleep_trend_chart_for_df(target_df, chart_title, compact_view=False):
                # Visualize sleep duration trend for a specific dataframe
                
                if target_df.empty or 'date_dt' not in target_df.columns or 'sleep_duration_hour' not in target_df.columns:
                    return None

                df_sorted = target_df.sort_values('date_dt').copy()
                
                dates = []
                durations = []
                texts = []
                
                # Iterate to build data, inserting gap if needed
                prev_date = None
                
                for _, row in df_sorted.iterrows():
                    current_date = row['date_dt']
                    duration = row['sleep_duration_hour']
                    
                    # Detect Gap (Only for compact view)
                    if compact_view and prev_date is not None:
                        delta = (current_date - prev_date).days
                        if delta > 1:
                            dates.append("GAP")
                            durations.append(None) # Break the line
                            texts.append("期間外")
                    
                    prev_date = current_date
                    dates.append(current_date)
                    durations.append(duration)
                    texts.append(f"{duration:.1f}h")
                
                # Process X-values
                x_vals = []
                if compact_view:
                    xaxis_config = dict(
                        title='日付',
                        type='category',
                        tickangle=-45
                    )
                    
                    for d in dates:
                        if d == "GAP":
                            x_vals.append("...期間...")
                        elif isinstance(d, pd.Timestamp):
                            x_vals.append(d.strftime('%m/%d'))
                        else:
                             x_vals.append(str(d))
                             
                else:
                     x_vals = dates
                     xaxis_config = dict(
                        title='日付',
                        tickformat='%m/%d',
                        tickangle=-45
                     )

                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=durations,
                    mode='lines+markers',
                    name='睡眠時間',
                    marker=dict(color='#FF9800'),
                    line=dict(color='#FF9800'),
                    hovertext=texts,
                    hovertemplate='日付: %{x}<br>睡眠時間: %{hovertext}<extra></extra>'
                ))

                fig.update_layout(
                    title=chart_title,
                    yaxis=dict(
                        title='睡眠時間 (h)',
                        dtick=1,
                        range=[5, 10]
                    ),
                    xaxis=xaxis_config,
                    showlegend=False,
                    height=340
                )
                
                fig = update_chart_layout(fig)
                fig.update_layout(height=340)

                return fig

            # Layout for Comparison
            c_sel, c_other = st.columns(2)
            
            with c_sel:
                st.write("#### 選択期間")
                fig_sel = create_reference_sleep_chart_for_df(df_selected, "睡眠チャート (選択期間)", compact_view=False)
                if fig_sel:
                    st.plotly_chart(fig_sel, use_container_width=True)
                else:
                    st.info("データがありません")
                    
                fig_trend_sel = create_sleep_trend_chart_for_df(df_selected, "睡眠時間推移 (選択期間)", compact_view=False)
                if fig_trend_sel:
                     st.plotly_chart(fig_trend_sel, use_container_width=True)

            with c_other:
                st.write("#### その他の期間")
                # Detect gaps for compact view
                fig_other = create_reference_sleep_chart_for_df(df_others, "睡眠チャート (他の期間)", compact_view=True)
                if fig_other:
                     st.plotly_chart(fig_other, use_container_width=True)
                else:
                    st.info("データがありません")
                    
                fig_trend_other = create_sleep_trend_chart_for_df(df_others, "睡眠時間推移 (他の期間)", compact_view=True)
                if fig_trend_other:
                     st.plotly_chart(fig_trend_other, use_container_width=True)

        except Exception as e:
            st.error(f"ファイル読み込みエラー: {e}")

    if page == "ダッシュボード":
        try:
            df = load_data_from_sheet()
            
            # Calculate sleep_duration_hour if it doesn't exist but the source columns do
            if 'sleep_duration_hour' not in df.columns:
                if '就寝時間' in df.columns and '起床時間' in df.columns:
                    df['sleep_duration_hour'] = df.apply(calculate_sleep_duration, axis=1)

            # Calculate nap duration
            if '昼寝の時間' in df.columns:
                def calc_nap(row):
                    try:
                        return time_to_minutes(row['昼寝の時間']) / 60.0
                    except:
                        return 0.0
                df['nap_duration_hour'] = df.apply(calc_nap, axis=1).fillna(0)
            else:
                df['nap_duration_hour'] = 0.0

            # Calculate total sleep (Night + Nap)
            if 'sleep_duration_hour' in df.columns:
                df['total_sleep_hour'] = df['sleep_duration_hour'].fillna(0) + df['nap_duration_hour']

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
                    
                    # Prepare Data
                    dates = recent_data['date_label']
                    night_sleep = recent_data['sleep_duration_hour']
                    
                    # Calculate Nap Hours
                    nap_hours = []
                    for _, row in recent_data.iterrows():
                        nh = 0.0
                        if '昼寝の時間' in row and pd.notna(row['昼寝の時間']):
                            nm = time_to_minutes(row['昼寝の時間'])
                            if nm is not None:
                                nh = nm / 60.0
                        nap_hours.append(nh)
                    
                    recent_data['nap_hours'] = nap_hours
                    recent_data['total_sleep'] = recent_data['sleep_duration_hour'] + recent_data['nap_hours']
                    
                    # Calculate new average (Total)
                    avg_total = recent_data['total_sleep'].mean()
                    avg_total_str = format_hours(avg_total)
                    
                    # Format strings for hover
                    night_texts = recent_data['sleep_duration_hour'].apply(format_hours)
                    nap_texts = recent_data['nap_hours'].apply(format_hours)
                    total_texts = recent_data['total_sleep'].apply(format_hours)

                    fig = go.Figure()
                    
                    # 1. Nap (Bottom) - Modified per user request to be at bottom
                    fig.add_trace(go.Bar(
                        x=dates,
                        y=nap_hours,
                        name='昼寝',
                        marker_color='#26A69A', # Teal/Greenish
                        text=nap_texts, # Show nap text if non-zero
                        textposition='auto',
                        hovertemplate='日付: %{x}<br>昼寝: %{text}<extra></extra>',
                        marker_cornerradius=15
                    ))
                    
                    # 2. Night Sleep (Top)
                    fig.add_trace(go.Bar(
                        x=dates,
                        y=night_sleep,
                        name='夜間睡眠',
                        marker_color='#FF9800', # Vibrant Orange
                        text=night_texts,
                        textposition='auto', # Show text inside if space allows
                        hovertemplate='日付: %{x}<br>夜間睡眠: %{text}<extra></extra>',
                        marker_cornerradius=15
                    ))
                    
                    # Update layout for stacking
                    fig.update_layout(
                        title=f'週間睡眠時間 (昼寝含む)<br>平均: {avg_total_str}',
                        barmode='stack',
                        yaxis_title='睡眠時間 (時間)',
                        xaxis_title=None,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    # Add horizontal line for target sleep
                    target_sleep = st.session_state.target_sleep_duration
                    fig.add_hline(y=target_sleep, line_dash="dash", line_color="#555555")
                    
                    # Apply common layout
                    return update_chart_layout(fig)

                def display_current_status_metrics():
                    # Get data sorted by date
                    df_sorted = df.sort_values('date_dt')
                    
                    # Need at least 1 day for current
                    if df_sorted.empty:
                        return

                    # Current Week (Last 7 days)
                    current_week_data = df_sorted.tail(7)
                    
                    # Previous Week (7 days before current)
                    # Use iloc: [-14:-7]
                    prev_week_data = pd.DataFrame()
                    if len(df_sorted) >= 14:
                         prev_week_data = df_sorted.iloc[-14:-7]
                    
                    st.write("### 週間統計")
                    
                    # Create a 2-column layout for Weekly Stats (Average & SD) - Modified per user request
                    c_avg, c_std = st.columns(2)
                    
                    # 1. Average Sleep Duration (Night Sleep)
                    with c_avg:
                        if 'sleep_duration_hour' in current_week_data.columns:
                            current_avg = current_week_data['sleep_duration_hour'].mean()
                            avg_sleep_str = format_hours(current_avg)
                            
                            delta_val = None
                            if not prev_week_data.empty and 'sleep_duration_hour' in prev_week_data.columns:
                                prev_avg = prev_week_data['sleep_duration_hour'].mean()
                                diff = current_avg - prev_avg
                                delta_val = f"{diff:+.2f}h (先週比)"
                            
                            st.metric(label="平均夜間睡眠", value=avg_sleep_str, delta=delta_val, help="過去7日間の平均睡眠時間 vs 先週の平均")

                    # 2. Standard Deviation (Consistency)
                    with c_std:
                        if 'sleep_duration_hour' in current_week_data.columns and len(current_week_data) > 1:
                            current_std = current_week_data['sleep_duration_hour'].std()
                            
                            delta_std_val = None
                            if not prev_week_data.empty and 'sleep_duration_hour' in prev_week_data.columns and len(prev_week_data) > 1:
                                prev_std = prev_week_data['sleep_duration_hour'].std()
                                diff_std = current_std - prev_std
                                # For consistency, Lower is Better.
                                # Streamlit delta: Positive (Green) / Negative (Red) by default.
                                # If std INCREASED (Positive diff), it's BAD -> Red.
                                # If std DECREASED (Negative diff), it's GOOD -> Green.
                                # default usage: delta_color="inverse" makes positive Red, negative Green.
                                delta_std_val = f"{diff_std:+.2f}h (先週比)"
                            
                            st.metric(label="睡眠時間のばらつき", value=f"{current_std:.2f}h", delta=delta_std_val, delta_color="inverse", help="標準偏差。値が小さいほど一定。先週との差を表示。")
                        else:
                             st.metric(label="ばらつき", value="--")
                    
                    # 3. Current Sleep Debt (Moved below Weekly Stats)
                    st.write("### 睡眠負債")
                    target_sleep = st.session_state.target_sleep_duration
                    
                    # Calculate cumulative debt using ALL data
                    # Use Total Sleep (Night + Nap) for debt calculation ONLY
                    full_df_sorted = df.sort_values('date_dt')
                    
                    if 'total_sleep_hour' in full_df_sorted.columns and not full_df_sorted.empty:
                        df_cum = add_cumulative_sleep_debt(
                            full_df_sorted, 
                            actual_col="total_sleep_hour", 
                            target_sleep_hours=target_sleep, 
                            mode="offset"
                        )
                        latest_debt = df_cum.iloc[-1]['sleep_debt_cum']
                        debt_str = format_hours(latest_debt)
                        
                        st.metric(label="現在の睡眠負債 (累積)", value=debt_str, help=f"累積睡眠負債 ({target_sleep}h基準・超過返済あり・昼寝含む)")
                    
                    #      st.info("スコア計算中...")
                    
                    st.empty() # Placeholder if needed, or just end function


                    


                def create_sleep_debt_chart():
                    target_sleep = st.session_state.target_sleep_duration
                    df_sorted = df.sort_values('date_dt')
                    
                    # Calculate Cumulative Debt (using Total Sleep including Nap)
                    df_cum = add_cumulative_sleep_debt(
                        df_sorted, 
                        actual_col="total_sleep_hour", 
                        target_sleep_hours=target_sleep, 
                        mode="offset"
                    )
                    
                    # Create a temporary DF for plotting
                    plot_df = pd.DataFrame({
                        'date_label': df_sorted['date_label'],
                        'debt': df_cum['sleep_debt_cum']
                    })
                    plot_df['formatted_debt'] = plot_df['debt'].apply(format_hours)
                    
                    fig = px.area(plot_df, x='date_label', y='debt',
                                  title=f'睡眠負債の推移 (理想: {target_sleep}時間・昼寝含む)',
                                  labels={'date_label': '日付', 'debt': '累積睡眠負債 (時間)'},
                                  custom_data=['formatted_debt']) # Pass formatted data
                    # Red/Salmon is already warm, keeping it as it represents "Debt/Warning"
                    fig.update_traces(line_color='#E64A19', fillcolor='rgba(255, 87, 34, 0.3)') # Darker Orange/Red
                    # Update hover to use formatted debt
                    fig.update_traces(hovertemplate='日付: %{x}<br>睡眠負債: %{customdata[0]}')
                    fig.update_xaxes(title=None)
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
                    
                    fig.update_xaxes(title=None)
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
                    
                    fig.update_xaxes(title=None)
                    return update_chart_layout(fig)

                def create_sleep_schedule_chart():
                     # Visualize sleep intervals: X=Date, Y=Time (Range)
                     if 'date_dt' not in df.columns or '就寝時間' not in df.columns or '起床時間' not in df.columns:
                         return None

                     df_sorted = df.sort_values('date_dt').tail(14).copy() # Last 2 weeks
                     
                     # Prepare data for floating bars
                     dates = []
                     starts = []
                     durations = []
                     colors = []
                     texts = []
                     
                     # Base date for Y-axis normalization (e.g., 2000-01-01 16:00 to 2000-01-02 16:00)
                     BASE_Y_DATE = pd.Timestamp("2000-01-01")
                     
                     for _, row in df_sorted.iterrows():
                         try:
                             # Parse times
                             bt = pd.to_datetime(row['就寝時間'], format='%H:%M:%S').time()
                             wt = pd.to_datetime(row['起床時間'], format='%H:%M:%S').time()
                             
                             # Normalize to 24h+ timeline
                             # Cut-off is 16:00.
                             # If time >= 16:00, it's Day 1.
                             # If time < 16:00, it's Day 2.
                             
                             if bt.hour >= 16:
                                 start_dt = pd.Timestamp.combine(BASE_Y_DATE, bt)
                             else:
                                 start_dt = pd.Timestamp.combine(BASE_Y_DATE + pd.Timedelta(days=1), bt)
                                 
                             if wt.hour >= 16:
                                 end_dt = pd.Timestamp.combine(BASE_Y_DATE, wt)
                             else:
                                 end_dt = pd.Timestamp.combine(BASE_Y_DATE + pd.Timedelta(days=1), wt)
                             
                             # Adjustment for wrap-around cases
                             # If normalized end < start, it means mapped incorrectly or duration is negative.
                             # We assume valid sleep duration wraps to next day if needed.
                             if end_dt < start_dt:
                                  end_dt += pd.Timedelta(days=1)

                             dates.append(row['date_label'])
                             starts.append(start_dt)
                             # Duration in milliseconds
                             durations.append((end_dt - start_dt).total_seconds() * 1000)
                             
                             colors.append('#FF9800')
                             
                             # Hover text
                             sleep_time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                             texts.append(sleep_time_str)
                             
                         except Exception:
                             continue

                     fig = go.Figure()
                     
                     fig.add_trace(go.Bar(
                         x=dates,
                         y=durations,
                         base=starts,
                         marker_color=colors,
                         hovertext=texts,
                         hovertemplate='日付: %{x}<br>時間: %{hovertext}<extra></extra>',
                         opacity=0.8,
                         width=0.6
                     ))

                     # Configure Y axis to show time
                     # Range: 16:00 (Day 1) to 16:00 (Day 2)
                     range_start = BASE_Y_DATE + pd.Timedelta(hours=16)
                     range_end = BASE_Y_DATE + pd.Timedelta(hours=16+24) # Next day 16:00
                     
                     fig.update_layout(
                         title='睡眠スケジュール (過去14日間)',
                         yaxis=dict(
                             title='時間',
                             tickformat='%H:%M',
                             range=[range_start, range_end]
                         ),
                         xaxis=dict(title='日付'),
                         showlegend=False
                     )
                     
                     return update_chart_layout(fig)

                def create_reference_sleep_chart(color_metric='寝起きの良さ'):
                     # Visualize sleep with Base 19:00 (19:00 Top -> 19:00 Next Day Bottom)
                     # Logic:
                     # Map hours to 19..43 range.
                     # h < 19 -> h + 24 (e.g., 01:00 -> 25.0)
                     # h >= 19 -> h     (e.g., 23:00 -> 23.0)
                     # Split if bar crosses 19:00 (43.0).
                     
                     if 'date_dt' not in df.columns or '就寝時間' not in df.columns or '起床時間' not in df.columns:
                         return None
            
                     df_sorted = df.sort_values('date_dt').copy()
                     
                     dates = []
                     bases = []
                     heights = []
                     
                     # Data for Updatemenus
                     metrics_list = ["指定なし", "寝起きの良さ", "寝つきの良さ", "日中の眠気", "目が覚めた回数"]
                     metrics_data = {m: {'colors': [], 'texts': []} for m in metrics_list}
                     
                     BASE_HOUR = 19
                     
                     def adjust_hour(h):
                         # Map 0..24 to 19..43 range
                         if h < BASE_HOUR:
                             return h + 24.0
                         return h
                     
                     for _, row in df_sorted.iterrows():
                         try:
                             # Parse decimal hours
                             b_dt = pd.to_datetime(row['就寝時間'], format='%H:%M:%S')
                             w_dt = pd.to_datetime(row['起床時間'], format='%H:%M:%S')
                             
                             b_raw = b_dt.hour + b_dt.minute/60.0
                             w_raw = w_dt.hour + w_dt.minute/60.0
                             
                             b_adj = adjust_hour(b_raw)
                             w_adj = adjust_hour(w_raw)
                             
                             current_date = row['date_dt']
                             next_date = current_date + pd.Timedelta(days=1)
                             
                             # Handle wrap-around for duration
                             # If w_adj < b_adj (e.g., Bed 18:00 [42], Wake 20:00 [20]), 
                             # then Waketime is next cycle [20+24=44].
                             if w_adj < b_adj:
                                 w_adj += 24.0
                             
                             # Does it cross the 43.0 (19:00 next day) boundary?
                             # In standard view 19..43, boundary is 43.
                             # If w_adj > BASE_HOUR + 24 (43.0):
                             # Split!
                             

                             
                             limit = BASE_HOUR + 24.0

                             # Pre-calc Logic for ALL metrics
                             # Store temporarily
                             current_colors = {}
                             current_texts = {}
                             
                             metrics_list = ["指定なし", "寝起きの良さ", "寝つきの良さ", "日中の眠気", "目が覚めた回数"]
                             
                             for m in metrics_list:
                                 c_code = '#FF9800' # Default
                                 t_str = f"{row['就寝時間']} - {row['起床時間']}"
                                 
                                 if m != "指定なし":
                                     c_code = '#9E9E9E' # Default Grey
                                     val_label = "-"
                                     if m in row:
                                         try:
                                             val = float(row[m])
                                             val_label = str(val).rstrip('0').rstrip('.') if val % 1 == 0 else f"{val:.1f}"
                                             
                                             if val <= 0.1: c_code = '#9E9E9E'
                                             elif val < 1.5: c_code = '#FFE0B2'
                                             elif val < 2.5: c_code = '#FFCC80'
                                             elif val < 3.5: c_code = '#FFB74D'
                                             elif val < 4.5: c_code = '#FFA726'
                                             else: c_code = '#F57C00'
                                         except:
                                             pass
                                     t_str = f"{row['就寝時間']} - {row['起床時間']}<br>{m}: {val_label}"
                                 
                                 current_colors[m] = c_code
                                 current_texts[m] = t_str

                             # Add to global lists (Split logic)
                             if w_adj <= limit:
                                 dates.append(current_date)
                                 bases.append(b_adj)
                                 heights.append(w_adj - b_adj)
                                 for m in metrics_list:
                                     metrics_data[m]['colors'].append(current_colors[m])
                                     metrics_data[m]['texts'].append(current_texts[m])
                             else:
                                 # Split 1
                                 dates.append(current_date)
                                 bases.append(b_adj)
                                 heights.append(limit - b_adj)
                                 for m in metrics_list:
                                     metrics_data[m]['colors'].append(current_colors[m])
                                     metrics_data[m]['texts'].append(current_texts[m])
                                 
                                 # Split 2
                                 dates.append(next_date)
                                 bases.append(BASE_HOUR)
                                 heights.append(w_adj - 24.0 - BASE_HOUR)
                                 for m in metrics_list:
                                     metrics_data[m]['colors'].append(current_colors[m])
                                     metrics_data[m]['texts'].append(current_texts[m])
                         except Exception:
                             continue

                     fig = go.Figure()
                     
                     # Add Recommended Time Highlight (Background)
                     # Get target times from session state (defaults are set in main)
                     if "target_start_time" in st.session_state and "target_end_time" in st.session_state:
                         ts_val = st.session_state.target_start_time
                         te_val = st.session_state.target_end_time
                         
                         ts_raw = ts_val.hour + ts_val.minute/60.0
                         te_raw = te_val.hour + te_val.minute/60.0
                         
                         ts_adj = adjust_hour(ts_raw)
                         te_adj = adjust_hour(te_raw)
                         
                         # Ensure te_adj > ts_adj (handle basic wrap if needed, though adjust_hour usually handles day wrap for <19h)
                         if te_adj < ts_adj:
                             te_adj += 24.0
                         
                         # Add the shape
                         fig.add_shape(
                            type="rect",
                            x0=0, x1=1, xref="paper",
                            y0=ts_adj, y1=te_adj, yref="y",
                            fillcolor="rgba(135, 206, 235, 0.3)", # Light Sky Blue, transparent
                            line_width=0,
                            layer="below"
                         )

                     
                     fig.add_trace(go.Bar(
                         x=dates,
                         y=heights,
                         base=bases,
                         marker_color=metrics_data['指定なし']['colors'],
                         hovertext=metrics_data['指定なし']['texts'],
                         hovertemplate='日付: %{x|%m/%d}<br>時間: %{hovertext}<extra></extra>'
                     ))


                     # Create tick labels 19, 20... 12 (next day)
                     # Range 19..36 (17 hours)
                     tick_vals = list(range(BASE_HOUR, BASE_HOUR + 18)) # 19 to 36 inclusive
                     tick_text = [str(t % 24) + ":00" for t in tick_vals]
                     
                     # Determine default range (last 14 days)
                     if not df_sorted.empty:
                         last_date = df_sorted['date_dt'].max()
                         start_date = last_date - pd.Timedelta(days=13) # Show 14 days total including last
                         # Add slight buffer to end date if needed, or just let it be exact
                         range_x = [start_date, last_date + pd.Timedelta(days=0.5)] # small buffer
                     else:
                         range_x = None

                     
                     # Updatemenus
                     buttons = []
                     for m in metrics_list:
                         buttons.append(dict(
                             method='restyle',
                             label=m,
                             visible=True,
                             args=[{
                                 'marker.color': [metrics_data[m]['colors']],
                                 'hovertext': [metrics_data[m]['texts']]
                             }]
                         ))
                     
                     updatemenus = [dict(
                         buttons=buttons,
                         direction='down',
                         pad={'r': 10, 't': 10},
                         showactive=True,
                         x=1,
                         xanchor='right',
                         y=1.15,
                         yanchor='top',
                         bgcolor='white',
                         bordercolor='#ddd',
                         font=dict(size=11)
                     )]

                     # Apply common layout first (which sets default height=320)
                     fig = update_chart_layout(fig)
                     
                     # Then overwrite with specific settings
                     # Then overwrite with specific settings
                     fig.update_layout(
                         title=dict(
                             text='睡眠チャート',
                             font=dict(size=24) # Increase font size
                         ),
                         # Annotation removed as requested
                         yaxis=dict(
                             title='時間',
                             range=[BASE_HOUR + 17, BASE_HOUR], # 36 (Bottom) -> 19 (Top)
                             tickmode='array',
                             tickvals=tick_vals,
                             ticktext=tick_text,
                             dtick=1
                         ),
                         xaxis=dict(
                             title='日付',
                             tickformat='%m/%d',
                             tickangle=-45,
                             range=range_x # Set initial zoom
                         ),
                         updatemenus=updatemenus,
                         showlegend=False,
                         margin=dict(t=80),
                         height=690
                     )
                     
                     return fig

                # --- NEW LAYOUT (Updated) ---
                
                # Row 1: Weekly Chart (Left) + Current Status Metrics (Right)
                c_r1_1, c_r1_2 = st.columns(2)
                
                with c_r1_1:
                    if 'date_dt' in df.columns:
                        st.plotly_chart(create_weekly_bar_chart(), use_container_width=True)
                    else:
                        st.plotly_chart(create_plot("Weekly"), use_container_width=True)

                with c_r1_2:
                     with st.container():
                          display_current_status_metrics()

                st.write("---")

                # Row 2: Stacked Charts (Left) vs Tall Reference Chart (Right)
                c_main_left, c_main_right = st.columns(2)
                
                with c_main_left:
                    # 1. Sleep Debt Chart
                    if 'date_dt' in df.columns:
                        st.plotly_chart(create_sleep_debt_chart(), use_container_width=True)
                    else:
                        st.plotly_chart(create_plot("Debt"), use_container_width=True)
                        
                    st.write("") # Spacer
                    
                    # 2. Sleep Histogram
                    st.plotly_chart(create_sleep_histogram(), use_container_width=True)

                with c_main_right:
                    # Tall Reference Chart (800px)
                    if 'date_dt' in df.columns:
                         st.plotly_chart(create_reference_sleep_chart(), use_container_width=True)
                    else:
                         st.write("データ不足")

                st.write("---")
                
                # Bottom: Monthly Trend
                st.plotly_chart(create_monthly_sleep_trend(), use_container_width=True)

            else:
                st.error(f"'{DATA_FILE}' に 'sleep_duration_hour' カラムが見つからないか計算できませんでした")
                st.write("利用可能なカラム:", df.columns.tolist())

        except FileNotFoundError:
            st.error(f"ファイルが見つかりませんでした: {DATA_FILE}")

if __name__ == '__main__':
    main()
