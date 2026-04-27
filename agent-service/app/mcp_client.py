from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import httpx


class McpClientError(RuntimeError):
    """Raised when the MCP server cannot satisfy a request."""


class BackendMcpClient:
    """Async MCP client for explicit orchestration inside agent-service."""

    def __init__(
        self,
        command: list[str] | None = None,
        auth_header: str | None = None,
        server_url: str | None = None,
    ) -> None:
        self.server_url = str(server_url or os.getenv("MCP_SERVER_URL", "")).strip()
        self.command = command or self._default_command()
        self.auth_header = str(auth_header or "").strip()
        self.timeout_seconds = float(os.getenv("MCP_SERVER_TIMEOUT_SECONDS", "20").strip())
        self._process: asyncio.subprocess.Process | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._initialized = False
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._request("tools/list", {})
        return list(result.get("tools", []))

    async def search_hospitals(
        self,
        *,
        keyword: str = "",
        city_hint: str = "",
        level: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        return await self.call_tool(
            "search_hospitals",
            {
                "keyword": keyword,
                "city_hint": city_hint,
                "level": level,
                "limit": limit,
            },
        )

    async def list_rooms(self, *, hospital_id: int) -> dict[str, Any]:
        return await self.call_tool("list_rooms", {"hospital_id": hospital_id})

    async def list_doctors(
        self,
        *,
        hospital_id: int | None = None,
        room_id: int | None = None,
        keyword: str = "",
        work_time_slot: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "keyword": keyword,
            "work_time_slot": work_time_slot,
            "limit": limit,
        }
        if hospital_id is not None:
            payload["hospital_id"] = hospital_id
        if room_id is not None:
            payload["room_id"] = room_id
        return await self.call_tool("list_doctors", payload)

    async def get_doctor_quota(
        self,
        *,
        doctor_id: int,
        appointment_date: str,
        time_slot: str,
    ) -> dict[str, Any]:
        return await self.call_tool(
            "get_doctor_quota",
            {
                "doctor_id": doctor_id,
                "appointment_date": appointment_date,
                "time_slot": time_slot,
            },
        )

    async def get_doctor_quota_calendar(
        self,
        *,
        doctor_ids: list[int],
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        return await self.call_tool(
            "get_doctor_quota_calendar",
            {
                "doctor_ids": doctor_ids,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        structured_content = result.get("structuredContent")
        if isinstance(structured_content, dict):
            return structured_content

        content = result.get("content", [])
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                return json.loads(first["text"])

        raise McpClientError(f"Tool {name} did not return structured content.")

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        if self._process is not None:
            if self._process.stdin:
                self._process.stdin.close()
            await self._process.wait()
            self._process = None

        self._initialized = False

    async def _ensure_started(self) -> None:
        if self.server_url:
            await self._ensure_http_client()
            return

        if self._process is not None:
            return

        env = dict(os.environ)
        if self.auth_header:
            env["MCP_BACKEND_AUTH_HEADER"] = self.auth_header

        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        await self._initialize_via_stdio()

    async def _ensure_http_client(self) -> None:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout_seconds)
        if self._initialized:
            return
        response = await self._send_http_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "agent-service", "version": "0.1.0"},
                    "capabilities": {},
                },
            }
        )
        if response.get("id") != 0 or "error" in response:
            error_message = response.get("error", {}).get("message", "MCP initialize failed")
            raise McpClientError(str(error_message))
        await self._send_http_message(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
            expect_response=False,
        )
        self._initialized = True

    async def _initialize_via_stdio(self) -> None:
        await self._write_stdio_message(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "agent-service", "version": "0.1.0"},
                    "capabilities": {},
                },
            }
        )
        response = await self._read_stdio_message()
        if response.get("id") != 0 or "error" in response:
            error_message = response.get("error", {}).get("message", "MCP initialize failed")
            raise McpClientError(str(error_message))
        await self._write_stdio_message(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            await self._ensure_started()
            self._request_id += 1
            request_id = self._request_id
            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }

            if self.server_url:
                response = await self._send_http_message(message)
            else:
                await self._write_stdio_message(message)
                response = await self._read_stdio_message()

            if response.get("id") != request_id:
                raise McpClientError(f"Unexpected MCP response id: {response.get('id')}")
            if "error" in response:
                error = response["error"]
                raise McpClientError(str(error.get("message", "Unknown MCP error")))
            return dict(response.get("result", {}))

    async def _send_http_message(
        self,
        message: dict[str, Any],
        *,
        expect_response: bool = True,
    ) -> dict[str, Any]:
        assert self._http_client is not None
        headers: dict[str, str] = {}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        response = await self._http_client.post(self.server_url, json=message, headers=headers)
        response.raise_for_status()
        if not expect_response or response.status_code == 204:
            return {}
        return dict(response.json())

    async def _write_stdio_message(self, message: dict[str, Any]) -> None:
        assert self._process is not None and self._process.stdin is not None
        encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
        payload = f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8") + encoded
        self._process.stdin.write(payload)
        await self._process.stdin.drain()

    async def _read_stdio_message(self) -> dict[str, Any]:
        assert self._process is not None and self._process.stdout is not None

        headers: dict[str, str] = {}
        while True:
            line = await self._process.stdout.readline()
            if not line:
                stderr = await self._drain_stderr()
                raise McpClientError(f"MCP server closed unexpectedly. stderr={stderr}")
            if line in (b"\r\n", b"\n"):
                break
            header_line = line.decode("utf-8").strip()
            if ":" in header_line:
                name, value = header_line.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))
        if content_length <= 0:
            raise McpClientError("Invalid MCP content length.")

        payload = await self._process.stdout.readexactly(content_length)
        return json.loads(payload.decode("utf-8"))

    async def _drain_stderr(self) -> str:
        assert self._process is not None and self._process.stderr is not None
        try:
            data = await asyncio.wait_for(self._process.stderr.read(), timeout=0.2)
        except asyncio.TimeoutError:
            return ""
        return data.decode("utf-8", errors="ignore").strip()

    def _default_command(self) -> list[str]:
        custom = os.getenv("MCP_SERVER_COMMAND", "").strip()
        if custom:
            return custom.split()
        return [sys.executable, "-m", "mcp_server.server"]
