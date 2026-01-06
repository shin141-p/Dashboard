import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_client():
    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES
    )
    return gspread.authorize(creds)

gc = get_client()

SPREADSHEET_ID = "1-cB-5Cs02wkfPMVg9s0pDhSgoYxALS9iOt2GeZOyNHk"
worksheet_name = "フォームの回答 1"

ws = gc.open_by_key(SPREADSHEET_ID).worksheet(worksheet_name)

data = ws.get_all_values()
st.write(data)
