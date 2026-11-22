from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas import ErrorResponse, LinkAnalysisRequest, LinkAnalysisResponse
from app.services.analysis_service import run_analysis
from app.services.llm_service import LLMError, get_llm_client
from app.services.website_extractor import FetchError, fetch_and_extract

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("link_analysis")

app = FastAPI(
    title="AI-Powered Website Link Analysis API",
    description=(
        "Fetches a website, analyzes it with an LLM, and returns competitor, "
        "SEO, search-query, services, and target-audience insights."
    ),
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def link_analysis(payload: LinkAnalysisRequest):
    url = str(payload.url)

    try:
        website = await fetch_and_extract(url)
    except FetchError as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error=str(exc)).model_dump(),
        )

    try:
        llm = get_llm_client()
    except LLMError as exc:
        logger.error("LLM client unavailable: %s", exc)
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(error=f"LLM provider unavailable: {exc}").model_dump(),
        )

    try:
        result = await run_analysis(website, llm)
    except LLMError as exc:
        logger.error("LLM analysis failed for %s: %s", url, exc)
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(error=f"Analysis failed: {exc}").model_dump(),
        )

    return result


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error").model_dump(),
    )
