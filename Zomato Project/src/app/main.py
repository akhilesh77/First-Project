"""FastAPI application entry point."""

from __future__ import annotations

import logging

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api.routes import router
from app.api.schemas import ErrorResponse
from app.config import get_cors_origins

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zomato Restaurant Recommendation API",
        version="0.1.0",
        description="AI-powered restaurant recommendations (Phase 3: filter + stub explanations).",
    )

    origins = get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
            msg = first.get("msg", "Validation error")
            detail = f"{loc}: {msg}" if loc else str(msg)
        else:
            detail = "Validation error"
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(detail=detail).model_dump(),
        )

    app.include_router(router)
    return app


app = create_app()
