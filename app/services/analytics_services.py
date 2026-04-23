from app.services.google_sheets import get_worksheet_values
from app.utils.filters import format_date_to_iso
from collections import defaultdict
from datetime import datetime

def get_issue_analytics():
    try:
        data = get_worksheet_values("Testing")
        headers, rows = data[1], [dict(zip(data[1], r)) for r in data[2:]]
        
        client_stats, rca_stats, all_months = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int)), set()

        for r in rows:
            iso_date = format_date_to_iso(r.get("Raised On"))
            if iso_date == "TBD": continue
            m_y = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%b %Y")
            all_months.add(m_y)
            
            if r.get("Client"): client_stats[m_y][r.get("Client").strip()] += 1
            if r.get("Root Cause"): rca_stats[r.get("Root Cause").strip()][m_y] += 1

        return {
            "monthly_client_data": client_stats,
            "monthly_rca_data": rca_stats,
            "timeline": sorted(list(all_months), key=lambda x: datetime.strptime(x, "%b %Y"))
        }
    except: return {"error": "Failed to analyze data"}
    
def get_recent_issues_log(target_project=None, page=1, page_size=10):
    """
    Paginated log of recent issues including root cause category and resolution dates.
    """
    all_data = get_worksheet_values("Testing")
    if len(all_data) < 2: 
        return {"data": [], "page": page, "has_more": False, "total_count": 0}
     
    headers = all_data[1]
    rows = [dict(zip(headers, r)) for r in all_data[2:]]
     
    filtered = (
        [r for r in rows if str(r.get("Project Name")).lower() == target_project.lower()] 
        if target_project else rows
    )
     
    start, end = (page - 1) * page_size, page * page_size

    return {
        "data": [
            {
                "id": r.get("PCD Number"),
                "env": r.get("Environment"),
                "severity": r.get("Severity"),
                "title": r.get("Issue Description"),
                "category": r.get("Root Cause"), 
                "status": r.get("Status"),
                "raised": format_date_to_iso(r.get("Raised On")),
                "resolved": format_date_to_iso(r.get("Resolved On")), 
            } 
            for r in filtered[start:end]
        ],
        "page": page,
        "total_count": len(filtered),
        "has_more": end < len(filtered)
    }