import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID
from datetime import datetime
from typing import Optional
from collections import Counter, defaultdict

scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_file("service_account.json", scopes=scope)

client = gspread.authorize(creds)


def transform_sheet_data(data):
    transformed = []
    status_map = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}

    for index, row in enumerate(data, start=1):
        clean_row = {
            k.lower().replace(" ", "_").replace("%", "percent"): v
            for k, v in row.items()
        }

        project_display = clean_row.get("project_name", "Unknown")

        # 'name' is for the URL (e.g., "hsbc-banking")
        # 'displayName' is for the UI (e.g., "HSBC Banking")
        new_item = {
            "id": index,
            "name": str(project_display).lower().replace(" ", "-"),
            "displayName": project_display,
            "project": project_display,  # Keeping this for compatibility
            "stream": clean_row.get("stream", "N/A"),
            "status": status_map.get(clean_row.get("rag"), "On hold"),
            "progress": int(clean_row.get("percent_completed", 0)),
            "budget": {
                "used": clean_row.get("budget_used", 0),
                "total": clean_row.get("budget_total", 0),
            },
            "eta": clean_row.get("eta", "TBD"),
            "owner": clean_row.get("owner", "N/A"),
            "blocker": clean_row.get("blocker", "NIL"),
            "critical_blockers": clean_row.get("critical_blockers", "NIL"),
            "margin": clean_row.get("percentmargin", 0),
        }

        transformed.append(new_item)

    return transformed


def get_sheet_data():
    sheet = client.open_by_key(SHEET_ID).get_worksheet(0)
    data = sheet.get_all_records()
    return transform_sheet_data(data)


def transform_milestone_data(data):
    transformed = []
    status_map = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}

    for index, row in enumerate(data, start=1):
        clean_row = {k.lower().strip().replace(" ", "_"): v for k, v in row.items()}
        raw_date = str(clean_row.get("due_date", ""))
        display_date = "TBD"
        standardized_date = raw_date  # Keep original as fallback

        if raw_date:
            try:
                # MATCHES: '01 Jan 2025'
                date_obj = datetime.strptime(raw_date, "%d %b %Y")
                display_date = date_obj.strftime("%b %d")  # e.g., "Jan 01"
                # Standardize to YYYY-MM-DD for easier filtering in the API
                standardized_date = date_obj.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                # Attempt fallback for ISO format just in case
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
                    display_date = date_obj.strftime("%b %d")
                    standardized_date = raw_date
                except:
                    display_date = raw_date

        new_item = {
            "id": index,
            "due_date": standardized_date,
            "milestone": clean_row.get("milestone") or "Untitled Milestone",
            "project": clean_row.get("project") or "Untitled Project",
            "status": status_map.get(clean_row.get("status"), "PENDING"),
            "raw_status": clean_row.get("status"),
        }
        transformed.append(new_item)
    return transformed


def get_milestone_sheet_data():
    try:
        # open_by_key returns the Spreadsheet; get_worksheet(1) gets the second tab
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.get_worksheet(3)  # Index 0 is sheet1, Index 1 is sheet2

        data = sheet.get_all_records()
        return transform_milestone_data(data)
    except Exception as e:
        print(f"Error accessing Sheet2: {e}")
        return []


def get_project_details(target_project: str):
    spreadsheet = client.open_by_key(SHEET_ID)

    # 1. Fetch raw data from all tabs
    detailed_rows = spreadsheet.worksheet("Detailed Level").get_all_records()
    team_rows = spreadsheet.worksheet("Team Allocation").get_all_records()
    milestone_rows = spreadsheet.worksheet("Milestone").get_all_records()

    # 2. Forward Fill Logic for Team Allocation (Fixing Merged Cells)
    last_seen_project = ""
    filled_team_data = []
    for row in team_rows:
        val = str(row.get("Project Name", "")).strip()
        if val != "":
            last_seen_project = val
        else:
            row["Project Name"] = last_seen_project
        filled_team_data.append(row)

    # 3. Find the specific project metadata
    project_main = next(
        (
            r
            for r in detailed_rows
            if str(r.get("Project Name")).lower().replace(" ", "-")
            == target_project.lower().replace(" ", "-")
        ),
        None,
    )

    if not project_main:
        return None

    # Mapping status colors to human-readable text
    status_map = {"Green": "On track", "Amber": "At risk", "Red": "Critical"}
    actual_p_name = project_main.get("Project Name")

    # 4. Filter and Transform Team
    project_team = [
        {
            "name": t.get("Name"),
            "role": t.get("Role"),
            "skills": t.get("Skills"),
            "experience": t.get("Experience"),
            "allocation": t.get("Allocation"),
        }
        for t in filled_team_data
        if t.get("Project Name") == actual_p_name
    ]

    # 5. Filter and Transform Milestones
    project_milestones = [
        {
            "due_date": m.get("Due Date"),
            "milestone": m.get("Milestone"),
            "completion": m.get("% Completion"),
            "status": status_map.get(m.get("Status"), "Unknown"),
        }
        for m in milestone_rows
        if m.get("Project") == actual_p_name
    ]

    # 6. Final Data Assembly
    return {
        "project": actual_p_name,
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
            "label": status_map.get(project_main.get("RAG"), "On hold"),
            "percent_complete": project_main.get("% Completed"),
            "eta": project_main.get("ETA"),
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
        "milestones": project_milestones,
    }


def get_kpi_summary(target_project: Optional[str] = None):
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Testing")

    all_data = worksheet.get_all_values()
    if len(all_data) < 2:
        return None

    headers = all_data[1]
    raw_rows = all_data[2:]

    all_rows = []
    for row in raw_rows:
        record = {
            headers[i]: row[i] for i in range(len(headers)) if headers[i].strip() != ""
        }
        all_rows.append(record)
    print(target_project)
    # 1. Filter Logic
    if target_project:
        rows = [
            r
            for r in all_rows
            if str(r.get("Client")).lower() == target_project.lower()
        ]
    else:
        rows = all_rows

    if not rows:
        return None

    # 2. Metric Calculations
    total_count = len(rows)

    prod_issues = [r for r in rows if str(r.get("Environment")).upper() == "PROD"]
    test_issues = [r for r in rows if str(r.get("Environment")).upper() == "TEST"]

    unresolved_prod = len(
        [r for r in prod_issues if str(r.get("Status")).lower() != "closed"]
    )
    resolved_total = len([r for r in rows if str(r.get("Status")).lower() == "closed"])

    res_rate = round((resolved_total / total_count) * 100) if total_count > 0 else 0

    raw_categories = [r.get("Issue Category") for r in rows if r.get("Issue Category")]
    category_counts = Counter(raw_categories)

    # 2. Define your expected UI labels and map them to sheet values
    # If the sheet value is "Model accuracy", it counts towards that label
    categories_to_track = [
        "Model accuracy",
        "Hallucination",
        "Latency / performance",
        "Data pipeline",
        "Bias / fairness",
        "Integration / API",
    ]

    category_metrics = []
    other_count = 0

    # Loop through tracked categories to build the metrics list
    for cat in categories_to_track:
        count = category_counts.get(cat, 0)
        percent = round((count / total_count) * 100) if total_count > 0 else 0
        category_metrics.append({"label": cat, "value": count, "percentage": percent})

    # 3. Handle "Other" (anything not in the list above)
    tracked_total = sum(category_counts.get(cat, 0) for cat in categories_to_track)
    other_count = total_count - tracked_total
    category_metrics.append(
        {
            "label": "Other",
            "value": max(0, other_count),
            "percentage": (
                round((max(0, other_count) / total_count) * 100)
                if total_count > 0
                else 0
            ),
        }
    )

    # Helper for Severity counts & percentages
    def get_sev_data(label, sheet_val):
        count = len([r for r in rows if r.get("Severity") == sheet_val])
        percent = round((count / total_count) * 100) if total_count > 0 else 0
        return {"label": label, "value": count, "percentage": percent}

    # 3. Final Mapped Output
    return {
        # This maps to your top 4 KPI cards
        "summary_cards": [
            {
                "label": "Total issues",
                "value": total_count,
                "trend": "Across all Env" if not target_project else target_project,
            },
            {
                "label": "Critical / high",
                "value": len(
                    [
                        r
                        for r in rows
                        if r.get("Severity") in ["Critical", "Blocker", "High"]
                    ]
                ),
                "trend": f"{unresolved_prod} unresolved in prod",
            },
            {
                "label": "Avg resolution time",
                "value": "--d",
                "trend": "-- vs last sprint",
            },  # Mocked if not in sheet
            {
                "label": "Resolution rate",
                "value": f"{res_rate}%",
                "trend": "-- vs last sprint",
            },
        ],
        # This maps to your "Environment Zones" (Blue and Red boxes)
        "environments": [
            {
                "type": "test",
                "header": {"title": "Test Environment", "count": len(test_issues)},
                "metrics": [
                    {
                        "label": "Open Issues",
                        "value": len(
                            [r for r in test_issues if r.get("Status") == "Open"]
                        ),
                    },
                    {
                        "label": "In Progress",
                        "value": len(
                            [r for r in test_issues if r.get("Status") == "In Progress"]
                        ),
                    },
                    {
                        "label": "Resolved",
                        "value": len(
                            [r for r in test_issues if r.get("Status") == "Closed"]
                        ),
                    },
                ],
                "badge_metric": {"label": "Detection Rate", "value": "0%"},
            },
            {
                "type": "prod",
                "header": {
                    "title": "Production Environment",
                    "count": len(prod_issues),
                },
                "metrics": [
                    {
                        "label": "Open Issues",
                        "value": len(
                            [r for r in prod_issues if r.get("Status") == "Open"]
                        ),
                    },
                    {
                        "label": "In Progress",
                        "value": len(
                            [r for r in prod_issues if r.get("Status") == "In Progress"]
                        ),
                    },
                    {
                        "label": "Resolved",
                        "value": len(
                            [r for r in prod_issues if r.get("Status") == "Closed"]
                        ),
                    },
                ],
                "badge_metric": {
                    "label": "Unresolved in Prod",
                    "value": unresolved_prod,
                },
            },
        ],
        "issue_category_analysis": {
            "title": "Issues by category",
            "metrics": category_metrics,  # This now matches the structure you need!
        },
        # This maps to your Progress Bar sections
        "severity_analysis": {
            "title": "Issues by severity",
            "metrics": [
                get_sev_data("Critical", "Blocker"),
                get_sev_data("High", "High"),
                get_sev_data("Medium", "Medium"),
                get_sev_data("Low", "Low"),
            ],
            # Data for the stepped progress bar at the bottom
            "resolution_by_env": [
                {
                    "label": "Production",
                    "percentage": (
                        round(
                            (
                                len(
                                    [
                                        r
                                        for r in prod_issues
                                        if r.get("Status") == "Closed"
                                    ]
                                )
                                / len(prod_issues)
                                * 100
                            )
                        )
                        if prod_issues
                        else 0
                    ),
                },
                {
                    "label": "Testing",
                    "percentage": (
                        round(
                            (
                                len(
                                    [
                                        r
                                        for r in test_issues
                                        if r.get("Status") == "Closed"
                                    ]
                                )
                                / len(test_issues)
                                * 100
                            )
                        )
                        if test_issues
                        else 0
                    ),
                },
            ],
        },
    }


def format_sheet_date(date_str: str) -> str:
    """Helper to convert various sheet date formats to YYYY-MM-DD"""
    if not date_str or date_str.strip() in ["", "—", "-"]:
        return ""

    try:
        # Matches format like '19-Apr-26'
        # Adjust '%d-%b-%y' if your sheet uses '19-04-2026' (%d-%m-%Y)
        dt = datetime.strptime(date_str.strip(), "%d-%b-%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # Fallback: if the format is slightly different or already formatted
        return date_str


def get_recent_issues_log(
    target_project: Optional[str] = None, page: int = 1, page_size: int = 10
):
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Testing")

    all_data = worksheet.get_all_values()
    if len(all_data) < 2:
        return {"data": [], "page": page, "has_more": False, "total_count": 0}

    headers = all_data[1]
    raw_rows = all_data[2:]

    all_rows = []
    for row in raw_rows:
        record = {
            headers[i]: row[i] for i in range(len(headers)) if headers[i].strip() != ""
        }
        all_rows.append(record)

    if target_project:
        filtered_rows = [
            r
            for r in all_rows
            if str(r.get("Project Name")).lower() == target_project.lower()
        ]
    else:
        filtered_rows = all_rows

    start = (page - 1) * page_size
    end = start + page_size
    paginated_rows = filtered_rows[start:end]

    transformed = [
        {
            "id": r.get("PCD Number"),
            "env": r.get("Environment"),
            "severity": r.get("Severity"),
            "title": r.get("Issue Description"),
            "category": r.get("Root Cause"),
            "status": r.get("Status"),
            "raised": format_sheet_date(
                r.get("Raised On")
            ),  # Formatting Raised Date too
            "resolved": format_sheet_date(r.get("Resolved On")),  # Added and formatted
        }
        for r in paginated_rows
    ]

    return {
        "data": transformed,
        "page": page,
        "has_more": end < len(filtered_rows),
        "total_count": len(filtered_rows),
    }


def get_issue_analytics():
    try:
        # Connect to sheet
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet("Testing")
        all_data = worksheet.get_all_values()
    except NameError:
        return {"error": "Google Sheets 'client' is not initialized globally."}
    except Exception as e:
        return {"error": f"Failed to access sheet: {str(e)}"}

    # Headers are on Row 2 (index 1); Data starts on Row 3 (index 2)
    headers = all_data[1]
    rows = all_data[2:]

    # Map rows to dictionaries based on header names
    data_rows = [dict(zip(headers, row)) for row in rows]

    # Initialize data structures
    client_monthly_stats = defaultdict(lambda: defaultdict(int))
    rca_monthly_stats = defaultdict(lambda: defaultdict(int))
    all_months = set()

    for r in data_rows:
        # 1. Extract and Parse Date (Format: 15-Apr-26)
        date_str = r.get("Raised On", "").strip()
        if not date_str or date_str in ["—", ""]:
            continue

        try:
            # %d-%b-%y matches '15-Apr-26'
            dt = datetime.strptime(date_str, "%d-%b-%y")
            month_year = dt.strftime("%b %Y")
        except ValueError:
            # Fallback for inconsistent formats
            month_year = date_str if "202" in date_str else "Jan 2026"

        all_months.add(month_year)

        # 2. Extract Dimensions
        # IMPORTANT: Ensure these keys match your Sheet headers exactly
        client_name = r.get("Client", "").strip()
        rca_category = r.get("Root Cause", "").strip()

        # 3. Aggregate Data for Chart 1 (Monthly counts per Client)
        if client_name:
            client_monthly_stats[month_year][client_name] += 1

        # 4. Aggregate Data for Chart 2 (Monthly counts per RCA)
        if rca_category:
            rca_monthly_stats[rca_category][month_year] += 1

    # Sort timeline chronologically (e.g., Aug 2025 -> Dec 2025 -> Jan 2026)
    try:
        sorted_timeline = sorted(
            list(all_months), key=lambda x: datetime.strptime(x, "%b %Y")
        )
    except:
        sorted_timeline = sorted(list(all_months))

    return {
        "monthly_client_data": client_monthly_stats,
        "monthly_rca_data": rca_monthly_stats,
        "timeline": sorted_timeline,
    }
