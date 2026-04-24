from app.services.google_sheets import get_worksheet_data, spreadsheet
from app.utils.filters import format_date_to_iso, apply_common_filters
from datetime import date, datetime, timedelta
from typing import Optional

STATUS_MAP = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}


def get_high_level_data():
    raw_data = get_worksheet_data(0)
    transformed = []
    for index, row in enumerate(raw_data, start=1):
        clean = {
            k.lower().replace(" ", "_").replace("%", "percent"): v
            for k, v in row.items()
        }
        project_display = clean.get("project_name", "Unknown")
        transformed.append(
            {
                "id": index,
                "name": str(project_display).lower().replace(" ", "-"),
                "displayName": project_display,
                "project": project_display,
                "stream": clean.get("stream", "N/A"),
                "status": STATUS_MAP.get(clean.get("rag"), "On hold"),
                "progress": (
                    int(clean.get("percent_completed", 0))
                    if str(clean.get("percent_completed", 0)).isdigit()
                    else (
                        clean.get("percent_completed", 0)
                        if clean.get("percent_completed", 0)
                        else 0
                    )
                ),
                "budget": {
                    "used": clean.get("budget_used", 0),
                    "total": clean.get("budget_total", 0),
                },
                "type": clean.get("type"),
                "eta": format_date_to_iso(clean.get("project_end_date")),
                "startDate": format_date_to_iso(clean.get("project_start_date")),
                "owner": clean.get("delivery_manager", "N/A"),
                "updatedOn": format_date_to_iso(clean.get("status_moved_from")),
                "blocker": clean.get("blocker", "NIL"),
                "critical_blockers": clean.get("critical_blockers", "NIL"),
                "margin": clean.get("percentmargin", 0),
            }
        )
    return transformed


def get_milestones_and_risk_data():
    try:
        raw_data = get_worksheet_data(3)
        return [
            {
                "id": i,
                "due_date": format_date_to_iso(r.get("Due Date")),
                "milestone": r.get("Milestone") or "Untitled Milestone",
                "project": r.get("Project") or "Untitled Project",
                "status": STATUS_MAP.get(r.get("Status"), "PENDING"),
                "raw_status": r.get("Status"),
            }
            for i, r in enumerate(raw_data, 1)
        ]
    except:
        return []


def get_filtered_milestones(
    project: Optional[str] = None,
    status: Optional[str] = None,
    stream: Optional[str] = None,
    owner: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    all_projects = get_high_level_data()
    filtered_data = apply_common_filters(
        get_milestones_and_risk_data(),
        project,
        status,
        stream,
        owner,
        all_projects=all_projects,
    )

    if from_date or to_date:
        valid_items = []
        for item in filtered_data:
            try:
                item_dt = datetime.strptime(item["date"], "%Y-%m-%d").date()
                if (not from_date or item_dt >= from_date) and (
                    not to_date or item_dt <= to_date
                ):
                    valid_items.append(item)
            except (ValueError, KeyError):
                continue
        return valid_items
    return filtered_data


def get_sorted_risks(
    project: Optional[str] = None,
    status: Optional[str] = None,
    stream: Optional[str] = None,
    owner: Optional[str] = None,
):
    all_projects = get_high_level_data()
    filtered = apply_common_filters(
        get_milestones_and_risk_data(),
        project,
        status,
        stream,
        owner,
        all_projects=all_projects,
    )

    risk_data = [
        m for m in filtered if m.get("raw_status", "").lower() in ("red", "amber")
    ]

    def sort_key(item):
        priority = 0 if item["raw_status"].lower() == "red" else 1
        try:
            dt = datetime.strptime(item["date"], "%Y-%m-%d")
        except:
            dt = datetime.max
        return (priority, dt)

    return [
        {
            "level": "Critical" if m["raw_status"].lower() == "red" else "At Risk",
            "text": m["milestone"],
            "owner": m.get("project", "Unknown Project"),
        }
        for m in sorted(risk_data, key=sort_key)
    ]


def get_project_progress_stats():
    data = get_high_level_data()

    today = datetime.now().date()
    last_week_start = today - timedelta(days=7)

    status_counts = {"on track": [], "at risk": [], "critical": []}
    unique_streams = {
        i["stream"] for i in data if i.get("stream") and i["stream"] != "N/A"
    }

    for i in data:
        stat = i.get("status", "").lower()
        if stat in status_counts:
            status_counts[stat].append(i)

    recent_ontrack_count = 0
    for p in status_counts["on track"]:
        update_str = p.get("updatedOn")
        if update_str:
            try:
                update_date = datetime.strptime(update_str, "%Y-%m-%d").date()
                if last_week_start <= update_date <= today:
                    recent_ontrack_count += 1
            except (ValueError, TypeError):
                continue

    elt_needed_projects = [
        i.get("displayName")
        for i in status_counts["at risk"]
        if "nil" not in str(i.get("blocker", "")).lower()
    ]

    escalated_projects = [
        {"name": i.get("displayName"), "updatedOn": i.get("updatedOn")}
        for i in status_counts["critical"]
        if str(i.get("blocker", "")) != "NIL"
    ]

    return {
        "projects": {
            "total_projects": len(data),
            "active_streams": len(unique_streams),
        },
        "project_status": {
            "onTrack": {
                "total_ontrack": len(status_counts["on track"]),
                "recent_ontrack": recent_ontrack_count,
            },
            "atRisk": {
                "total_atRisk": len(status_counts["at risk"]),
                "elt_needed": elt_needed_projects,
            },
            "critical": {
                "total_critical": len(status_counts["critical"]),
                "escalated": escalated_projects,
            },
        },
    }


def get_project_details(target_project: str):
    """
    Fetches comprehensive details for a specific project by its name/slug.
    """
    slug = target_project.lower().replace(" ", "-")
    detailed = get_worksheet_data("Detailed Level")
    project_main = next(
        (
            r
            for r in detailed
            if str(r.get("Project Name")).lower().replace(" ", "-") == slug
        ),
        None,
    )

    if not project_main:
        return None

    actual_name = project_main.get("Project Name")
    team_rows = get_worksheet_data("Team Allocation")
    milestone_rows = get_worksheet_data("Milestone")

    STATUS_MAP = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}

    last_seen, project_team = "", []
    for t in team_rows:
        val = str(t.get("Project Name", "")).strip()
        last_seen = val if val else last_seen
        if last_seen == actual_name:
            project_team.append(
                {
                    "name": t.get("Name"),
                    "role": t.get("Role"),
                    "skills": t.get("Skills"),
                    "experience": t.get("Experience"),
                    "allocation": t.get("Allocation"),
                }
            )

    return {
        "project": actual_name,
        "details": {
            "stream": project_main.get("Stream"),
            "director": project_main.get("Project Director"),
            "owner": project_main.get("Project Owner"),
            "team_size": project_main.get("Team Size"),
            "tenure": project_main.get("Tenure"),
            "type": project_main.get("Project Type"),
        },
        "status_metrics": {
            "rag": project_main.get("RAG"),
            "label": STATUS_MAP.get(project_main.get("RAG"), "On hold"),
            "percent_complete": project_main.get("% Completed"),
            "eta": format_date_to_iso(project_main.get("ETA")),
        },
        "blockers": {
            "summary": project_main.get("Blocker"),
            "critical_items": project_main.get("Critical Blockers", ""),
        },
        "financials": {
            "margin": project_main.get("Margin"),
            "pending_invoice": project_main.get("Pending to Invoice"),
            "invoiced": project_main.get("Invoiced"),
            "revenue": project_main.get("Revenue Overall"),
        },
        "team": project_team,
        "milestones": [
            {
                "due_date": format_date_to_iso(m.get("Due Date")),
                "milestone": m.get("Milestone"),
                "completion": m.get("% Completion"),
                "status": STATUS_MAP.get(m.get("Status"), "Unknown"),
            }
            for m in milestone_rows
            if m.get("Project") == actual_name
        ],
    }


def get_delivery_filter_options():
    all_data = get_high_level_data()
    keys = ["name", "status", "stream", "owner"]
    sets = {k: set() for k in keys}

    for item in all_data:
        for k in keys:
            val = item.get(k)
            if val and val != "N/A":
                sets[k].add(val)

    def format_opt(s):
        return sorted(
            [{"name": v, "displayName": v} for v in s], key=lambda x: x["displayName"]
        )

    return {k + ("s" if k != "status" else "es"): format_opt(sets[k]) for k in keys}
