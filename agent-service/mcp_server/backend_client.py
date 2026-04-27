from __future__ import annotations

import os
from typing import Any

import httpx


class BackendApiClient:
    """Thin async wrapper around the existing Spring Boot REST APIs."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        auth_header: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_BASE_URL", "http://backend:8080")).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(os.getenv("BACKEND_TIMEOUT_SECONDS", "15").strip())
        self.auth_header = str(
            auth_header if auth_header is not None else os.getenv("MCP_BACKEND_AUTH_HEADER", "")
        ).strip()

    async def list_hospitals(self) -> list[dict[str, Any]]:
        return await self._get_json("/api/catalog/hospitals")

    async def list_rooms(self, hospital_id: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if hospital_id is not None:
            params["hospitalId"] = hospital_id
        return await self._get_json("/api/catalog/rooms", params=params)

    async def list_doctors(
        self,
        *,
        hospital_id: int | None = None,
        room_id: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if hospital_id is not None:
            params["hospitalId"] = hospital_id
        if room_id is not None:
            params["roomId"] = room_id
        return await self._get_json("/api/catalog/doctors", params=params)

    async def get_doctor_quota(
        self,
        *,
        doctor_id: int,
        appointment_date: str,
        time_slot: str,
    ) -> dict[str, Any]:
        return await self._get_json(
            "/api/appointments/quota",
            params={
                "doctorId": doctor_id,
                "appointmentDate": appointment_date,
                "timeSlot": time_slot,
            },
        )

    async def get_doctor_quota_calendar(
        self,
        *,
        doctor_ids: list[int],
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = [
            ("startDate", start_date),
            ("endDate", end_date),
        ]
        params.extend(("doctorIds", str(doctor_id)) for doctor_id in doctor_ids)
        return await self._get_json("/api/appointments/quota-calendar", params=params)

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, str]] | None = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}{path}", params=params, headers=headers)
            response.raise_for_status()
            return response.json()
