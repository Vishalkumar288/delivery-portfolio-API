from app.services.google_sheets import get_worksheet_values
from app.utils.filters import format_date_to_iso
from collections import Counter
from typing import Optional

def get_ticket_kpi_summary(target_project: Optional[str] = None):
    # Fetch data using your new worksheet helper
    all_data = get_worksheet_values("Testing")
    if len(all_data) < 2:
        return None

    headers, raw_rows = all_data[1], all_data[2:]
    all_rows = [
        {headers[i]: row[i] for i in range(len(headers)) if headers[i].strip()}
        for row in raw_rows
    ]

    # Filter by project if provided
    rows = (
        [r for r in all_rows if str(r.get("Client")).lower() == target_project.lower()]
        if target_project
        else all_rows
    )
    
    if not rows:
        return None

    total = len(rows)
    prod_issues = [r for r in rows if str(r.get("Environment")).upper() == "PROD"]
    test_issues = [r for r in rows if str(r.get("Environment")).upper() == "TEST"]
    unresolved_prod = len([r for r in prod_issues if str(r.get("Status")).lower() != "closed"])
    
    # Calculate Resolution Rate
    closed_count = len([r for r in rows if str(r.get("Status")).lower() == "closed"])
    res_rate = round((closed_count / total) * 100) if total > 0 else 0

    # Category Analysis
    categories = ["Model accuracy", "Hallucination", "Latency / performance", "Data pipeline", "Bias / fairness", "Integration / API"]
    counts = Counter([r.get("Issue Category") for r in rows])
    cat_metrics = [
        {
            "label": c,
            "value": counts.get(c, 0),
            "percentage": round((counts.get(c, 0) / total) * 100) if total > 0 else 0,
        }
        for c in categories
    ]
    other_val = max(0, total - sum(counts.get(c, 0) for c in categories))
    cat_metrics.append({
        "label": "Other",
        "value": other_val,
        "percentage": round((other_val / total) * 100) if total > 0 else 0
    })

    # Helper for Severity
    def get_sev(label, sheet_values):
        c = len([r for r in rows if r.get("Severity") in sheet_values])
        return {
            "label": label,
            "value": c,
            "percentage": round((c / total) * 100) if total > 0 else 0,
        }

    return {
        "summary_cards": [
            {"label": "Total issues", "value": total, "trend": "Across all Env"},
            {
                "label": "Critical / high", 
                "value": len([r for r in rows if r.get("Severity") in ["Critical", "Blocker", "High"]]), 
                "trend": f"{unresolved_prod} unresolved in prod"
            },
            {"label": "Avg resolution time", "value": "--d", "trend": "-- vs last sprint"},
            {"label": "Resolution rate", "value": f"{res_rate}%", "trend": "-- vs last sprint"}
        ],
        "environments": [
            {
                "type": "test",
                "header": {"title": "Test Environment", "count": len(test_issues)},
                "metrics": [
                    {"label": s, "value": len([r for r in test_issues if r.get("Status") == s])}
                    for s in ["Open", "In Progress", "Closed"]
                ],
                "badge_metric": {"label": "Detection Rate", "value": "0%"}
            },
            {
                "type": "prod",
                "header": {"title": "Production Environment", "count": len(prod_issues)},
                "metrics": [
                    {"label": s, "value": len([r for r in prod_issues if r.get("Status") == s])}
                    for s in ["Open", "In Progress", "Closed"]
                ],
                "badge_metric": {"label": "Unresolved in Prod", "value": unresolved_prod}
            }
        ],
        "issue_category_analysis": {
            "title": "Issues by category",
            "metrics": cat_metrics
        },
        "severity_analysis": {
            "title": "Issues by severity",
            "metrics": [
                get_sev("Critical", ["Blocker", "Critical"]),
                get_sev("High", ["High"]),
                get_sev("Medium", ["Medium"]),
                get_sev("Low", ["Low"]),
            ],
            "resolution_by_env": [
                {
                    "label": "Production",
                    "percentage": round((len([r for r in prod_issues if r.get("Status") == "Closed"]) / len(prod_issues)) * 100) if prod_issues else 0
                },
                {
                    "label": "Testing",
                    "percentage": round((len([r for r in test_issues if r.get("Status") == "Closed"]) / len(test_issues)) * 100) if test_issues else 0
                }
            ]
        }
    }