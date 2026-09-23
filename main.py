# main.py
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from database import lifespan
from fastapi.exceptions import RequestValidationError

from exceptions import InferenceHubError
from routers import auth, users, admin, predict, stream
from dependencies.common import verify_api_version
from dependencies.auth import get_current_user

# Ensure SQLAlchemy models are actively registered to the global Base.metadata 
import models.user        # noqa: F401
import models.prediction  # noqa: F401 
import models.tag         # noqa: F401

def create_app():
    # Configure logging before anything else
    import os
    json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"
    from logger import configure_logging
    configure_logging(json_logs=json_logs)

    app = FastAPI(
        title="InferenceHub",
        version="0.1.0",
        description="ML model serving API with auth, logging, and caching.",
        contact={"name": "Sree", "email": "sree@example.com"},
        license_info={"name": "MIT"},
        dependencies=[Depends(verify_api_version)],
        lifespan=lifespan,
    )

    import os
    from fastapi.staticfiles import StaticFiles

    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    from middleware.logging import LoggingMiddleware
    from middleware.timing import TimingMiddleware
    from fastapi.middleware.cors import CORSMiddleware

    # CORS outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Timing measures total server time
    app.add_middleware(TimingMiddleware, slow_threshold_ms=500.0)

    # Logging generates request ID, logs every request
    app.add_middleware(LoggingMiddleware)

    # Include routers
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(predict.router)
    app.include_router(stream.router)

    # ---- exception handlers ----
    @app.exception_handler(InferenceHubError)
    async def domain_error_handler(
        request: Request, exc: InferenceHubError
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error":   exc.error_code,
                "message": exc.message,
                "detail":  exc.context,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = [
            {
                "field":   " → ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type":    err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error":   "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail":  errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ):
        print(f"UNHANDLED: {exc!r}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error":   "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

    # ---- root routes ----
    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()