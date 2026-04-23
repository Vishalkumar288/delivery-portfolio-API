from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.api import deps
from app.services import ticket_services as service

router = APIRouter(prefix="/tickets", tags=["Ticket Tracker"])

@router.get("/summary")
def get_ticket_summary(
    project_name: Optional[str] = Query(None),
    api_key: str = Depends(deps.verify_api_key)
):
    """
    Fetches KPI cards and environment-specific metrics.
    If project_name is omitted, returns global stats.
    """
    data = service.get_ticket_kpi_summary(project_name)
    return {"data": data}

