from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from mcp_server.server import McpServer


app = FastAPI(title="IHRS MCP Server", version="0.1.0")
server = McpServer()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "mcp-server", "status": "UP"}


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - invalid client request boundary
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    if isinstance(payload, list):
        responses = await _handle_batch(payload, authorization=authorization)
        if not responses:
            return Response(status_code=204)
        return JSONResponse(content=responses)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON-RPC payload must be an object or array.")

    response = await server.handle_request(payload, auth_header=authorization)
    if response is None:
        return Response(status_code=204)
    return JSONResponse(content=response)


async def _handle_batch(payload: list[Any], *, authorization: str | None) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            responses.append(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid Request"},
                }
            )
            continue
        response = await server.handle_request(item, auth_header=authorization)
        if response is not None:
            responses.append(response)
    return responses
