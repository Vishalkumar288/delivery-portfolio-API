from fastapi import FastAPI, Depends, Query
from auth import verify_api_key
from sheets import (
    get_sheet_data,
    get_milestone_sheet_data,
    get_project_details,
    get_kpi_summary,
    get_recent_issues_log,
    get_issue_analytics,
)
from utils import apply_common_filters
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date
from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "API running"}


@app.get("/projects")
def fetch_data(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    stream: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    all_data = get_sheet_data()
    filtered_data = apply_common_filters(all_data, project, status, stream, owner)
    return {"data": filtered_data}


@app.get("/milestones")
def get_milestones(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    stream: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    # Fetch Milestone data
    all_milestones = get_milestone_sheet_data()
    # Fetch Project Master data (for the lookup)
    all_projects = get_sheet_data()

    # 1. Apply common filters (passing both datasets)
    filtered_data = apply_common_filters(
        all_milestones, project, status, stream, owner, all_projects=all_projects
    )

    # 2. Apply Date Filtering
    if from_date or to_date:
        final_list = []
        for item in filtered_data:
            try:
                # Ensure we handle the date string correctly
                item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                if from_date and item_date < from_date:
                    continue
                if to_date and item_date > to_date:
                    continue
                final_list.append(item)
            except Exception:
                continue
        filtered_data = final_list

    return {"data": filtered_data}


@app.get("/risks")
def get_risks(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    stream: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key),
):
    all_milestones = get_milestone_sheet_data()
    all_projects = get_sheet_data()

    # 1. Apply common filters (passing both datasets)
    filtered_data = apply_common_filters(
        all_milestones, project, status, stream, owner, all_projects=all_projects
    )

    # 2. Filter for risks only (Red/Amber)
    risk_data = [
        m for m in filtered_data if m["raw_status"].lower() in ["red", "amber"]
    ]

    # 3. Sort logic
    def sort_logic(item):
        priority = 0 if item["raw_status"].lower() == "red" else 1
        try:
            dt = datetime.strptime(item["date"], "%Y-%m-%d")
        except:
            dt = datetime.max
        return (priority, dt)

    sorted_risks = sorted(risk_data, key=sort_logic)

    # 4. Final format for UI
    final_format = [
        {
            "level": "Critical" if m["raw_status"].lower() == "red" else "At Risk",
            "text": m["milestone"],
            "owner": m.get("project", "Unknown Project"),
        }
        for m in sorted_risks
    ]

    return {"data": final_format}


@app.get("/projects-progress")
def get_projects_progress(api_key: str = Depends(verify_api_key)):
    data = get_sheet_data()
    total_projects = len(data)
    unique_streams = len({item["stream"] for item in data if item["stream"] != "N/A"})

    on_track_list = [i for i in data if i["status"].lower() == "on track"]
    at_risk_list = [i for i in data if i["status"].lower() == "at risk"]
    critical_list = [i for i in data if i["status"].lower() == "critical"]

    elt_needed_count = len(
        [i for i in at_risk_list if not "NIL" in str(i.get("blocker", "")).lower()]
    )
    escalated_count = len([i for i in critical_list if i.get("blocker") != "NIL"])

    recent_ontrack = "--"

    return {
        "data": {
            "projects": {
                "total_projects": total_projects,
                "active_streams": unique_streams,
            },
            "project_status": {
                "onTrack": {
                    "total_ontrack": len(on_track_list),
                    "recent_ontrack": recent_ontrack,
                },
                "atRisk": {
                    "total_atRisk": len(at_risk_list),
                    "elt_needed": elt_needed_count,
                },
                "critical": {
                    "total_critical": len(critical_list),
                    "escalated": escalated_count,
                },
            },
        }
    }


@app.get("/projects/{project_name}")
def fetch_project_by_id(project_name: str, api_key: str = Depends(verify_api_key)):
    data = get_project_details(project_name)

    return {"data": data}


@app.get("/ticket/issues-summary")
def fetch_project_kpis(
    project_name: Optional[str] = None, api_key: str = Depends(verify_api_key)
):
    """
    Query Param: ?project_name=MyProject
    If no project_name is provided, it returns aggregated stats for all projects.
    """
    data = get_kpi_summary(project_name)

    return {"data": data}


@app.get("/ticket/issues-log")
def fetch_project_issues_log(
    project_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    api_key: str = Depends(verify_api_key),
):
    """
    Query Param: ?project_name=MyProject&page=1&page_size=10
    """
    log_data = get_recent_issues_log(project_name, page, page_size)

    return {
        "data": log_data["data"],
        "meta": {
            "current_page": log_data["page"],
            "has_more": log_data["has_more"],
            "total_records": log_data["total_count"],
        },
    }


@app.get("/ticket/rca-summary")
def fetch_project_issues_Analytics(api_key: str = Depends(verify_api_key)):
    log_data = get_issue_analytics()

    return {
        "data": log_data,
    }


@app.get("/filters/delivery-portfolio")
def get_filter_options(api_key: str = Depends(verify_api_key)):
    all_data = get_sheet_data()

    # Using sets to collect unique values efficiently
    unique_projects = set()
    unique_statuses = set()
    unique_streams = set()
    unique_owners = set()

    for item in all_data:
        if item["name"]:
            unique_projects.add(item["name"])
        if item["status"]:
            unique_statuses.add(item["status"])
        if item["stream"]:
            unique_streams.add(item["stream"])
        if item["owner"]:
            unique_owners.add(item["owner"])

    # Helper function to format for the Frontend DropDown component
    def format_options(unique_set):
        # Sorting ensures the dropdown looks organized
        return sorted(
            [
                {"name": val, "displayName": val}
                for val in unique_set
                if val and val != "N/A"
            ],
            key=lambda x: x["displayName"],
        )

    return {
        "data": {
            "projects": format_options(unique_projects),
            "status": format_options(unique_statuses),
            "stream": format_options(unique_streams),
            "owner": format_options(unique_owners),
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
