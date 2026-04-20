def apply_common_filters(data, project, status, stream, owner, all_projects=None):
    filtered = data

    if (owner or stream) and all_projects:
        allowed_project_names = {
            p["displayName"].lower()
            for p in all_projects
            if (not owner or p.get("owner", "").lower() == owner.lower())
            and (not stream or p.get("stream", "").lower() == stream.lower())
        }

        filtered = [
            i for i in filtered if i.get("project", "").lower() in allowed_project_names
        ]

    elif owner or stream:
        if owner:
            filtered = [
                i for i in filtered if i.get("owner", "").lower() == owner.lower()
            ]
        if stream:
            filtered = [
                i for i in filtered if i.get("stream", "").lower() == stream.lower()
            ]

    # 3. DIRECT FILTERS (Project Dropdown & Status)
    if project and project != "all":
        filtered = [i for i in filtered if project.lower() in i.get("name", "").lower()]

    if status:
        filtered = [
            i for i in filtered if i.get("status", "").lower() == status.lower()
        ]

    return filtered
