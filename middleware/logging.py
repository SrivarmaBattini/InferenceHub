import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from logger import log, request_id_var


# In-memory metrics counters
_endpoint_counts: dict[str, int] = defaultdict(int)
_endpoint_errors: dict[str, int] = defaultdict(int)
_endpoint_latency: dict[str, list] = defaultdict(list)

def get_endpoint_metrics():
    return {
        endpoint: {
            "requests": _endpoint_counts[endpoint],
            "errors": _endpoint_errors[endpoint],
            "avg_latency_ms": round(
                sum(_endpoint_latency[endpoint]) / len(_endpoint_latency[endpoint]), 2
            ) if _endpoint_latency[endpoint] else 0,
        }
        for endpoint in _endpoint_counts
    }


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Wraps every request with:
    - A unique request ID (generated or taken from X-Request-ID header)
    - Structured log at request start
    - Structured log at request end with status code + latency
    - Tracks endpoint counts, latencies, and errors in memory
    - X-Request-ID header on the response
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Generate or inherit request ID
        request_id = (
            request.headers.get("X-Request-ID")
            or str(uuid.uuid4())[:8]
        )

        token = request_id_var.set(request_id)
        start_ns = time.perf_counter_ns()

        log.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) or None,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
            
            # Record metric for error
            key = f"{request.method} {request.url.path}"
            _endpoint_counts[key] += 1
            _endpoint_latency[key].append(latency_ms)
            _endpoint_errors[key] += 1

            log.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 3),
                exc_info=True,
            )
            raise
        finally:
            request_id_var.reset(token)

        latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        
        # Record metric for success
        key = f"{request.method} {request.url.path}"
        _endpoint_counts[key] += 1
        _endpoint_latency[key].append(latency_ms)
        if response.status_code >= 400:
            _endpoint_errors[key] += 1

        log_fn = log.warning if response.status_code >= 400 else log.info
        log_fn(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 3),
        )

        response.headers["X-Request-ID"] = request_id
        return response
