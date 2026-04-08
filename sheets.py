import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID
from datetime import datetime
import os
import json 

# Load the JSON string from environment variables
service_account_info = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT"))

scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)

client = gspread.authorize(creds)


def transform_sheet_data(data):
    transformed = []
    status_map = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}
    for index, row in enumerate(data, start=1):
        clean_row = {
            k.lower().replace(" ", "_").replace("%", "percent"): v
            for k, v in row.items()
        }
        new_item = {
            "id": index,
            "project": clean_row.get("project_name", "Unknown"),
            "stream": clean_row.get("stream", "N/A"),
            "status": status_map.get(clean_row.get("rag"), "On hold"),
            "progress": int(clean_row.get("percent_completed", 0)),
            "budget": {
                "used": clean_row.get("budget_used", 0),
                "total": clean_row.get("budget_total", 0),
            },
            "eta": clean_row.get("eta", "TBD"),
            "owner": clean_row.get("owner", "N/A"),
            "blocker": clean_row.get("blocker", "NIL"),
            "margin": clean_row.get("percentmargin", 0),
        }

        transformed.append(new_item)

    return transformed


def get_sheet_data():
    sheet = client.open_by_key(SHEET_ID).sheet1
    data = sheet.get_all_records()
    return transform_sheet_data(data)


def transform_milestone_data(data):
    transformed = []
    status_map = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}

    for index, row in enumerate(data, start=1):
        clean_row = {k.lower().strip().replace(" ", "_"): v for k, v in row.items()}

        raw_date = str(clean_row.get("date", ""))
        display_date = "TBD"
        standardized_date = raw_date  # Keep original as fallback

        if raw_date:
            try:
                # MATCHES: '01 Jan 2025'
                date_obj = datetime.strptime(raw_date, "%d %b %Y")
                display_date = date_obj.strftime("%b %d")  # e.g., "Jan 01"
                # Standardize to YYYY-MM-DD for easier filtering in the API
                standardized_date = date_obj.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # Attempt fallback for ISO format just in case
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
                    display_date = date_obj.strftime("%b %d")
                    standardized_date = raw_date
                except:
                    display_date = raw_date

        new_item = {
            "id": index,
            "date": standardized_date,  # This is what the API will filter on
            "display_date": display_date,
            "title": clean_row.get("milestone") or "Untitled Milestone",
            "project": clean_row.get("project") or "Untitled Milestone",
            "status": status_map.get(clean_row.get("status"), "PENDING"),
            "raw_status": clean_row.get("status"),
        }
        transformed.append(new_item)
    return transformed


def get_milestone_sheet_data():
    try:
        # open_by_key returns the Spreadsheet; get_worksheet(1) gets the second tab
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.get_worksheet(1)  # Index 0 is sheet1, Index 1 is sheet2

        data = sheet.get_all_records()
        return transform_milestone_data(data)
    except Exception as e:
        print(f"Error accessing Sheet2: {e}")
        return []
