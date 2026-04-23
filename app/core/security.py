from fastapi import Header, HTTPException
from app.core.config import API_KEY

def verify_api_key(x_api_key: str = Header(None, alias="x-api-key")):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized access: Invalid API Key")