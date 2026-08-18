import logging
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.application import seed_database
from app.config import get_settings
from app.database import SessionLocal, create_schema

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = structlog.get_logger()

app = FastAPI(title="AI Technical English Tutor", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup() -> None:
    await create_schema()
    async with SessionLocal() as db:
        await seed_database(db)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", request_id=request_id, path=request.url.path)
        raise
    response.headers["x-request-id"] = request_id
    logger.info("request", request_id=request_id, path=request.url.path, status=response.status_code, latency_ms=round((time.perf_counter()-started)*1000))
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error":{"code":"VALIDATION_ERROR","message":"Please check the submitted information.","details":exc.errors()}})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error":{"code":"INTERNAL_ERROR","message":"Something went wrong. Please try again."}})


@app.get("/health")
async def health() -> dict:
    return {"status":"ok","ai_provider":settings.llm_provider}

