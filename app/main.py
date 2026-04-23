from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import delivery, tickets, analytics
from app.core.config import ALLOWED_ORIGINS  
app = FastAPI(title="Project Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  
    allow_credentials=True,         
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registering the Feature Routers
app.include_router(delivery.router)
app.include_router(tickets.router)
app.include_router(analytics.router)

@app.get("/")
def health_check():
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)