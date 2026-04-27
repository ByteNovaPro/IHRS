from __future__ import annotations

from typing import Any

from mcp_server.backend_client import BackendApiClient


TOOL_NAME = "list_rooms"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": "List clinic rooms for a given hospital.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "hospital_id": {"type": "integer"},
        },
        "required": ["hospital_id"],
    },
}


async def call(client: BackendApiClient, arguments: dict[str, Any]) -> dict[str, Any]:
    hospital_id = int(arguments["hospital_id"])
    rooms = await client.list_rooms(hospital_id=hospital_id)
    normalized_rooms = [
        {
            "room_id": item.get("id"),
            "hospital_id": item.get("hospitalId"),
            "hospital_name": item.get("hospitalName"),
            "room_name": item.get("name"),
            "floor": item.get("floor"),
            "short_intro": item.get("shortIntro"),
            "detail_intro": item.get("detailIntro"),
        }
        for item in rooms
    ]
    return {
        "rooms": normalized_rooms,
        "count": len(normalized_rooms),
        "returned": len(normalized_rooms),
        "total": len(normalized_rooms),
    }
