import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logger import log


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Adds Server-Timing header to every response so browser devtools
    and monitoring tools can see server-side latency.

    Also logs a warning for slow requests (> threshold_ms).
    """

    def __init__(self, app: ASGIApp, slow_threshold_ms: float = 500.0) -> None:
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        start_ns = time.perf_counter_ns()
        response = await call_next(request)
        latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        # Server-Timing header — visible in browser Network tab
        response.headers["Server-Timing"] = f"total;dur={latency_ms:.1f}"

        # Warn on slow requests
        if latency_ms > self.slow_threshold_ms:
            log.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 3),
                threshold_ms=self.slow_threshold_ms,
            )

        return response
