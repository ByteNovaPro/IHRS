from __future__ import annotations

from typing import Any

from mcp_server.backend_client import BackendApiClient


TOOL_NAME = "list_doctors"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": "List doctors filtered by hospital, room, keyword, and work time slot.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "hospital_id": {"type": "integer"},
            "room_id": {"type": "integer"},
            "keyword": {"type": "string"},
            "work_time_slot": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        },
        "anyOf": [
            {"required": ["hospital_id"]},
            {"required": ["room_id"]},
        ],
    },
}


async def call(client: BackendApiClient, arguments: dict[str, Any]) -> dict[str, Any]:
    hospital_id = arguments.get("hospital_id")
    room_id = arguments.get("room_id")
    keyword = str(arguments.get("keyword", "") or "").strip().lower()
    work_time_slot = str(arguments.get("work_time_slot", "") or "").strip().lower()
    limit = max(1, min(int(arguments.get("limit", 20) or 20), 50))

    if hospital_id is None and room_id is None:
        raise ValueError("list_doctors requires at least one scope field: hospital_id or room_id")

    doctors = await client.list_doctors(
        hospital_id=int(hospital_id) if hospital_id is not None else None,
        room_id=int(room_id) if room_id is not None else None,
    )

    filtered: list[dict[str, Any]] = []
    for item in doctors:
        searchable_text = " ".join(
            str(item.get(field, "") or "")
            for field in (
                "hospitalName",
                "roomName",
                "name",
                "title",
                "specialty",
                "shortIntro",
                "detailIntro",
                "workTimeSlot",
            )
        ).lower()
        if keyword and keyword not in searchable_text:
            continue
        if work_time_slot and work_time_slot not in str(item.get("workTimeSlot", "") or "").lower():
            continue
        filtered.append(
            {
                "doctor_id": item.get("id"),
                "hospital_id": item.get("hospitalId"),
                "hospital_name": item.get("hospitalName"),
                "room_id": item.get("roomId"),
                "room_name": item.get("roomName"),
                "doctor_name": item.get("name"),
                "title": item.get("title"),
                "specialty": item.get("specialty"),
                "work_time_slot": item.get("workTimeSlot"),
                "short_intro": item.get("shortIntro"),
                "detail_intro": item.get("detailIntro"),
            }
        )

    returned_items = filtered[:limit]
    returned_count = len(returned_items)
    total_count = len(filtered)
    return {
        "doctors": returned_items,
        "count": returned_count,
        "returned": returned_count,
        "total": total_count,
    }
