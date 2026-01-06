import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_gspread_client():
    """
    Authenticate and return a gspread client using Streamlit secrets.
    """
    if "gcp_service_account" not in st.secrets:
        st.error("Streamlit secretsに 'gcp_service_account' が設定されていません。")
        return None

    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def load_data_from_spreadsheet(spreadsheet_id, worksheet_name="フォームの回答 1"):
    """
    Fetch data from a Google Spreadsheet and return as a pandas DataFrame.
    """
    client = get_gspread_client()
    if not client:
        return pd.DataFrame()

    try:
        sh = client.open_by_key(spreadsheet_id)
        ws = sh.worksheet(worksheet_name)
        
        # Get all values (list of lists)
        data = ws.get_all_values()
        
        if not data:
            return pd.DataFrame()
            
        # First row is header
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers)
        return df
        
    except Exception as e:
        st.error(f"スプレッドシートの読み込み中にエラーが発生しました: {e}")
        return pd.DataFrame()
