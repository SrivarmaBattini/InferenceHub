import logging
import sys
from contextvars import ContextVar
from typing import Any
import threading
from collections import deque

import structlog

# Context variable to store the request ID for the current async task
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


# Thread-safe in-memory ring buffer for recent log storage
_log_buffer: deque[dict] = deque(maxlen=20)
_buffer_lock = threading.Lock()


def get_recent_logs() -> list[dict]:
    with _buffer_lock:
        return list(_log_buffer)


def capture_log_event(
    logger: Any,
    method: str,
    event_dict: dict,
) -> dict:
    """Structlog processor — copies every log event into the in-memory buffer."""
    with _buffer_lock:
        _log_buffer.append({**event_dict})
    return event_dict


def inject_request_id(
    logger: Any,
    method: str,
    event_dict: dict,
) -> dict:
    """Structlog processor — adds request_id to every log line."""
    event_dict["request_id"] = request_id_var.get()
    return event_dict


def inject_app_context(
    logger: Any,
    method: str,
    event_dict: dict,
) -> dict:
    """Structlog processor — adds static app metadata."""
    event_dict["app"] = "inferencehub"
    event_dict["version"] = "0.1.0"
    return event_dict


def configure_logging(json_logs: bool = True) -> None:
    """
    Call once at app startup.
    json_logs=True  → JSON output (production)
    json_logs=False → human-readable console output (development)
    """
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        inject_request_id,
        inject_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        processors = shared_processors + [
            capture_log_event,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            capture_log_event,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Module-level logger to import everywhere
log = structlog.get_logger()
