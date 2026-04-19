from fastapi import FastAPI, Depends
from auth import verify_api_key
from sheets import (
    get_sheet_data,
    get_milestone_sheet_data,
    get_project_details,
    get_kpi_summary,
    get_recent_issues_log,
    get_issue_analytics,
)
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
    filter: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    all_data = get_sheet_data()
    filtered_data = all_data

    if filter == "risk":
        filtered_data = [
            item for item in filtered_data if item["status"].lower() == "at risk"
        ]

    if filter and filter != "risk":
        filtered_data = [
            item for item in filtered_data if item["stream"].lower() == filter.lower()
        ]

    return {"data": filtered_data}


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


@app.get("/milestones")
def get_milestones(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    api_key: str = Depends(verify_api_key),
):
    all_data = get_milestone_sheet_data()
    filtered_data = all_data

    if from_date or to_date:
        final_list = []
        for item in filtered_data:
            try:
                # Since we standardized to %Y-%m-%d in the transform function:
                item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()

                if from_date and item_date < from_date:
                    continue
                if to_date and item_date > to_date:
                    continue
                final_list.append(item)
            except Exception as e:
                # If date is invalid ("TBD"), skip filtering for this item
                print(f"Skipping row due to date error: {e}")
                continue
        filtered_data = final_list

    return {"data": filtered_data}


@app.get("/projects/{project_name}")
def fetch_project_by_id(project_name: str, api_key: str = Depends(verify_api_key)):
    data = get_project_details(project_name)

    return {"data": data}


@app.get("/risks")
def get_risks(api_key: str = Depends(verify_api_key)):

    all_milestones = get_milestone_sheet_data()

    risk_data = [
        m for m in all_milestones if m["raw_status"].lower() in ["red", "amber"]
    ]

    def sort_logic(item):
        priority = 0 if item["raw_status"].lower() == "red" else 1
        try:
            dt = datetime.strptime(item["date"], "%Y-%m-%d")
        except:
            dt = datetime.max
        return (priority, dt)

    sorted_risks = sorted(risk_data, key=sort_logic)

    final_format = []
    for m in sorted_risks:
        final_format.append(
            {
                "level": "Critical" if m["raw_status"].lower() == "red" else "At Risk",
                "text": m["milestone"],
                "owner": m.get("project", "Unknown Project"),
            }
        )

    return {"data": final_format}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
