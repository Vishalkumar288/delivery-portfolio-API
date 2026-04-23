from datetime import datetime

def format_date_to_iso(date_str):
    if not date_str or str(date_str).strip() in ["", "—", "-", "TBD", "N/A"]:
        return "TBD"
    formats = ["%d-%b-%y", "%d %b %Y", "%Y-%m-%d", "%b %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return str(date_str)

def apply_common_filters(data, project, status, stream, owner, all_projects=None):
    filtered = data
    if (owner or stream) and all_projects:
        allowed = {
            p["displayName"].lower() for p in all_projects
            if (not owner or p.get("owner", "").lower() == owner.lower())
            and (not stream or p.get("stream", "").lower() == stream.lower())
        }
        filtered = [i for i in filtered if i.get("project", "").lower() in allowed]
    elif owner or stream:
        if owner:
            filtered = [i for i in filtered if i.get("owner", "").lower() == owner.lower()]
        if stream:
            filtered = [i for i in filtered if i.get("stream", "").lower() == stream.lower()]

    if project and project != "all":
        filtered = [i for i in filtered if project.lower() in i.get("name", "").lower()]
    if status:
        filtered = [i for i in filtered if i.get("status", "").lower() == status.lower()]
    return filtered