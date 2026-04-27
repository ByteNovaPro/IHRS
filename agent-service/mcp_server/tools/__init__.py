from __future__ import annotations

from mcp_server.tools import doctors, hospitals, quota, rooms


TOOL_MODULES = (
    hospitals,
    rooms,
    doctors,
    quota,
)

TOOL_DEFINITIONS = [module.TOOL_DEFINITION for module in TOOL_MODULES]
TOOL_REGISTRY = {module.TOOL_NAME: module.call for module in TOOL_MODULES}

