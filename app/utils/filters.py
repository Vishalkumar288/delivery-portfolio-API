from datetime import datetime


def format_date_to_iso(date_str):
    placeholders = ["", "—", "-", "TBD", "TBC", "TBU", "N/A"]
    normalized = str(date_str).strip() if date_str else ""

    if not date_str or normalized in placeholders:
        return normalized if normalized else "TBD"

    formats = ["%d-%B-%y", "%d-%b-%y", "%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%b %d, %Y"]

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return normalized


def apply_common_filters(data, project, status, stream, owner, all_projects=None):
    filtered = data
    if (owner or stream) and all_projects:
        allowed = {
            p["displayName"].lower()
            for p in all_projects
            if (not owner or p.get("owner", "").lower() == owner.lower())
            and (not stream or p.get("stream", "").lower() == stream.lower())
        }
        filtered = [i for i in filtered if i.get("project", "").lower() in allowed]
    elif owner or stream:
        if owner:
            filtered = [
                i for i in filtered if i.get("owner", "").lower() == owner.lower()
            ]
        if stream:
            filtered = [
                i for i in filtered if i.get("stream", "").lower() == stream.lower()
            ]

    if project and project != "all":
        filtered = [i for i in filtered if project.lower() in i.get("name", "").lower()]
    if status:
        filtered = [
            i for i in filtered if i.get("rag", "").lower() == status.lower()
        ]
    return filtered
