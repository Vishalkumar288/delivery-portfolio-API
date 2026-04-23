import gspread
from google.oauth2.service_account import Credentials
from app.core.config import SHEET_ID, GOOGLE_SERVICE_ACCOUNT

scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_info(GOOGLE_SERVICE_ACCOUNT, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

def get_worksheet_data(name_or_index):
    sheet = spreadsheet.get_worksheet(name_or_index) if isinstance(name_or_index, int) else spreadsheet.worksheet(name_or_index)
    return sheet.get_all_records()

def get_worksheet_values(name):
    return spreadsheet.worksheet(name).get_all_values()