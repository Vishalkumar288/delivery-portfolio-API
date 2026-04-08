from fastapi import Header, HTTPException
from config import API_KEY

def verify_api_key(x_api_key: str = Header(None, alias="x-api-key")):
    print("Received API key:", x_api_key)
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")