from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.services import analytics_services as service
from typing import Optional

router = APIRouter(prefix="/analytics", tags=["RCA Analytics"])

@router.get("/rca-summary")
def get_rca_analytics(api_key: str = Depends(deps.verify_api_key)):
    """
    Returns monthly breakdown of issues by Client and Root Cause.
    """
    data = service.get_issue_analytics()
    return {"data": data}

@router.get("/log")
def get_ticket_log(
    project_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    api_key: str = Depends(deps.verify_api_key)
):
    """
    Paginated log of recent issues.
    """
    log_data = service.get_recent_issues_log(project_name, page, page_size)
    return {
        "data": log_data["data"],
        "meta": {
            "current_page": page,
            "has_more": log_data["has_more"],
            "total_records": log_data["total_count"],
        }
    }
