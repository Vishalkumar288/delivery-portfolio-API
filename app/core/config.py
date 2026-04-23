import os
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv("API_KEY")
SHEET_ID = os.getenv("SHEET_ID") 
GOOGLE_SERVICE_ACCOUNT = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT"))
origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in origins_raw.split(",")]