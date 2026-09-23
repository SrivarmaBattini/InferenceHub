import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

def sse_event(
    data:       Any,
    event_type: str | None = None,
    event_id:   int | None = None,
):
    payload = json.dumps(data) if isinstance(data, dict) else str(data)
    lines: list[str] = []
    if event_id   is not None:
        lines.append(f"id: {event_id}")
    if event_type is not None:
        lines.append(f"event: {event_type}")
    lines.append(f"data: {payload}")
    lines.append("")
    return "\n".join(lines) + "\n"

def sse_error(message: str, code: str = "ERROR"):
    return sse_event(
        data       = {"error": code, "message": message},
        event_type = "error",
    )

def sse_done():
    return sse_event(data="[DONE]", event_type="done")

async def keep_alive_generator(
    source:          AsyncGenerator[str, None],
    ping_interval_s: float = 15.0,
):
    last_ping = asyncio.get_event_loop().time()

    async for chunk in source:
        yield chunk
        now = asyncio.get_event_loop().time()
        if now - last_ping > ping_interval_s:
            yield ": ping\n\n"
            last_ping = now
