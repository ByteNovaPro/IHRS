from __future__ import annotations

from typing import Any

from mcp_server.backend_client import BackendApiClient


TOOL_NAME = "get_doctor_quota"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": "Get remaining quota for one doctor on one date and time slot.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "doctor_id": {"type": "integer"},
            "appointment_date": {"type": "string", "format": "date"},
            "time_slot": {"type": "string"},
        },
        "required": ["doctor_id", "appointment_date", "time_slot"],
    },
}

QUOTA_CALENDAR_TOOL_NAME = "get_doctor_quota_calendar"
QUOTA_CALENDAR_TOOL_DEFINITION = {
    "name": QUOTA_CALENDAR_TOOL_NAME,
    "description": "Get a quota calendar for a set of doctors over a date range.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "doctor_ids": {
                "type": "array",
                "items": {"type": "integer"},
            },
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
        },
        "required": ["doctor_ids", "start_date", "end_date"],
    },
}


async def call(client: BackendApiClient, arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments.get("doctor_ids") is not None:
        return await call_quota_calendar(client, arguments)

    result = await client.get_doctor_quota(
        doctor_id=int(arguments["doctor_id"]),
        appointment_date=str(arguments["appointment_date"]),
        time_slot=str(arguments["time_slot"]),
    )
    payload = {
        "doctor_id": result.get("doctorId"),
        "appointment_date": result.get("appointmentDate"),
        "time_slot": result.get("timeSlot"),
        "reserved_count": result.get("reservedCount"),
        "remaining_count": result.get("remainingCount"),
        "capacity": result.get("capacity"),
    }
    return {
        **payload,
        "count": 1,
        "returned": 1,
        "total": 1,
    }


async def call_quota_calendar(client: BackendApiClient, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.get_doctor_quota_calendar(
        doctor_ids=[int(item) for item in arguments.get("doctor_ids", [])],
        start_date=str(arguments["start_date"]),
        end_date=str(arguments["end_date"]),
    )
    items = result.get("quotas", []) if isinstance(result, dict) else []
    normalized_items = [
        {
            "doctor_id": item.get("doctorId"),
            "appointment_date": item.get("appointmentDate"),
            "time_slot": item.get("timeSlot"),
            "reserved_count": item.get("reservedCount"),
            "remaining_count": item.get("remainingCount"),
            "capacity": item.get("capacity"),
        }
        for item in items
    ]
    returned_count = len(normalized_items)
    return {
        "items": normalized_items,
        "quotas": normalized_items,
        "count": returned_count,
        "returned": returned_count,
        "total": returned_count,
    }
