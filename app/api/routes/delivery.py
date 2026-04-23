from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.services import delivery_services as service
from app.utils.filters import apply_common_filters
from datetime import date
from typing import Optional

router = APIRouter(prefix="/delivery", tags=["Delivery Portfolio"])

@router.get("/portfolio")
def get_portfolio(
    project: str = Query(None), status: str = Query(None),
    stream: str = Query(None), owner: str = Query(None),
    api_key: str = Depends(deps.verify_api_key)
):
    data = service.get_high_level_data()
    return {"data": apply_common_filters(data, project, status, stream, owner)}

@router.get("/stats")
def get_stats(api_key: str = Depends(deps.verify_api_key)):
    return {"data": service.get_project_progress_stats()}

@router.get("/milestones")
def get_milestones(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    stream: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    api_key: str = Depends(deps.verify_api_key),
):
    data = service.get_filtered_milestones(
        project, status, stream, owner, from_date, to_date
    )
    return {"data": data}

@router.get("/risks")
def get_risks(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    stream: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    api_key: str = Depends(deps.verify_api_key),
):
    data = service.get_sorted_risks(project, status, stream, owner)
    return {"data": data}

@router.get("/project/{project_name}")
def get_project(project_name: str, api_key: str = Depends(deps.verify_api_key)):
    return {"data": service.get_project_details(project_name)}

@router.get("/filters")
def get_filter_options(api_key: str = Depends(deps.verify_api_key)):
    data = service.get_delivery_filter_options()
    return {"data": data}