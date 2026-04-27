from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any, Callable, Awaitable

from mcp_server.backend_client import BackendApiClient
from mcp_server.tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from mcp_server.tools.quota import QUOTA_CALENDAR_TOOL_DEFINITION


JsonDict = dict[str, Any]
ToolHandler = Callable[[BackendApiClient, JsonDict], Awaitable[JsonDict]]


class McpServer:
    def __init__(self) -> None:
        self._tool_definitions = TOOL_DEFINITIONS + [QUOTA_CALENDAR_TOOL_DEFINITION]
        self._tool_registry: dict[str, ToolHandler] = dict(TOOL_REGISTRY)
        self._tool_registry["get_doctor_quota_calendar"] = TOOL_REGISTRY["get_doctor_quota"]

    def serve_forever(self) -> None:
        while True:
            request = self._read_message()
            if request is None:
                return
            response = asyncio.run(self.handle_request(request))
            if response is not None:
                self._write_message(response)

    async def handle_request(self, request: JsonDict, *, auth_header: str | None = None) -> JsonDict | None:
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {}) or {}

        try:
            if method == "initialize":
                return self._success(
                    request_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "ihrs-backend-mcp", "version": "0.1.0"},
                        "capabilities": {"tools": {"listChanged": False}},
                    },
                )

            if method == "notifications/initialized":
                return None

            if method == "ping":
                return self._success(request_id, {})

            if method == "tools/list":
                return self._success(request_id, {"tools": self._tool_definitions})

            if method == "tools/call":
                tool_name = str(params.get("name", "") or "").strip()
                arguments = params.get("arguments", {}) or {}
                handler = self._tool_registry.get(tool_name)
                if handler is None:
                    return self._error(request_id, -32602, f"Unknown tool: {tool_name}")

                result = await handler(self._build_client(auth_header), arguments)
                return self._success(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False),
                            }
                        ],
                        "structuredContent": result,
                    },
                )

            return self._error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # pragma: no cover - defensive server boundary
            traceback.print_exc(file=sys.stderr)
            return self._error(request_id, -32000, f"{type(exc).__name__}: {exc}")

    def _build_client(self, auth_header: str | None = None) -> BackendApiClient:
        return BackendApiClient(auth_header=auth_header)

    def _read_message(self) -> JsonDict | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            header_line = line.decode("utf-8").strip()
            if ":" in header_line:
                name, value = header_line.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))
        if content_length <= 0:
            return None

        payload = sys.stdin.buffer.read(content_length)
        return json.loads(payload.decode("utf-8"))

    def _write_message(self, message: JsonDict) -> None:
        encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8"))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()

    def _success(self, request_id: Any, result: JsonDict) -> JsonDict:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str) -> JsonDict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def main() -> None:
    McpServer().serve_forever()


if __name__ == "__main__":
    main()
