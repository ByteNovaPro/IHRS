from __future__ import annotations

from typing import Any

from mcp_server.backend_client import BackendApiClient


TOOL_NAME = "search_hospitals"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": "Search hospitals by keyword, city hint, and level using the Spring Boot catalog API.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string"},
            "city_hint": {"type": "string"},
            "level": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
    },
}


async def call(client: BackendApiClient, arguments: dict[str, Any]) -> dict[str, Any]:
    keyword = str(arguments.get("keyword", "") or "").strip().lower()
    city_hint = str(arguments.get("city_hint", "") or "").strip().lower()
    level = str(arguments.get("level", "") or "").strip().lower()
    limit = max(1, min(int(arguments.get("limit", 10) or 10), 50))
    city_hints = [
        token.strip()
        for token in city_hint.replace("/", ",").replace("，", ",").split(",")
        if token.strip()
    ]

    hospitals = await client.list_hospitals()
    filtered: list[dict[str, Any]] = []
    for item in hospitals:
        searchable_text = " ".join(
            str(item.get(field, "") or "")
            for field in ("name", "level", "location", "shortIntro", "detailIntro")
        ).lower()
        if keyword and keyword not in searchable_text:
            continue
        if city_hints and not any(hint in searchable_text for hint in city_hints):
            continue
        if level and level not in str(item.get("level", "") or "").lower():
            continue
        filtered.append(
            {
                "hospital_id": item.get("id"),
                "hospital_name": item.get("name"),
                "level": item.get("level"),
                "location": item.get("location"),
                "short_intro": item.get("shortIntro"),
                "detail_intro": item.get("detailIntro"),
            }
        )

    returned_items = filtered[:limit]
    returned_count = len(returned_items)
    total_count = len(filtered)
    return {
        "hospitals": returned_items,
        "count": returned_count,
        "returned": returned_count,
        "total": total_count,
    }
