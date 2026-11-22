"""Orchestrates extraction -> LLM prompting -> validated structured output."""
from __future__ import annotations

from pydantic import ValidationError

from app.config import get_settings
from app.schemas import AnalysisSections, BrandInfo, LinkAnalysisResponse
from app.services.competitor_service import enforce_competitor_minimum
from app.services.llm_service import LLMClient, LLMError
from app.services.website_extractor import ExtractedWebsite

_SYSTEM_PROMPT = """You are a senior digital marketing and SEO analyst.
You analyze real website content and produce structured, factual business
intelligence. Base every claim on the provided website content first; only
use general market knowledge to fill reasonable gaps, and when you do,
mark it clearly as an inference rather than presenting it as fact extracted
from the site. Never invent specific search-volume or ranking numbers you
cannot source. Respond with ONLY a single valid JSON object — no markdown
fences, no commentary before or after it."""

_RESPONSE_SCHEMA_HINT = """
Return a JSON object with EXACTLY this shape (fill every field; use [] or ""
when information is genuinely unavailable, do not omit keys):

{
  "brand": {"name": "", "category": "", "summary": ""},
  "competitor_analysis": {
    "brand_overview": "",
    "main_business_category": "",
    "main_products_services": [""],
    "competitors": [
      {"name": "", "description": "", "strengths": [""], "weaknesses": [""], "source_note": "ai_generated"}
    ],
    "your_competitive_advantages": [""],
    "opportunities": [""]
  },
  "target_search_queries": [
    {"query": "", "platforms": ["Google"], "intent": "", "business_relevance": "", "target_audience": ""}
  ],
  "seo_improvements": {
    "primary_keyword": "",
    "secondary_keywords": [""],
    "long_tail_keywords": [""],
    "business_keywords": [""],
    "recommended_title": "",
    "meta_description": "",
    "supporting_content": [""]
  },
  "top_services": [
    {"service_name": "", "description": "", "target_industry": "", "target_customer": "", "main_benefit": "", "inferred": false}
  ],
  "target_audience": {
    "primary_audience": [""],
    "secondary_audience": [""],
    "industries": [""],
    "business_types": [""],
    "customer_needs": [""],
    "customer_interests": [""],
    "location_focus": "",
    "recommended_segments": [""]
  }
}

Requirements:
- "target_search_queries" must contain exactly 5 entries, covering Google,
  Facebook, Instagram, LinkedIn, and X between them.
- "competitors" should contain at least 3 entries when you have reasonably
  reliable knowledge of the market; otherwise return fewer and do not invent
  names.
- "top_services" must contain up to 5 of the most important services found
  in the website content. Set "inferred": true for any service you deduced
  rather than found explicitly stated.
"""


def _build_user_prompt(website: ExtractedWebsite, settings) -> str:
    context = website.to_llm_context(settings.max_content_chars_for_llm)
    return (
        "Analyze the following website content and produce the requested "
        "business/SEO/competitor intelligence.\n\n"
        f"WEBSITE CONTENT:\n{context}\n\n{_RESPONSE_SCHEMA_HINT}"
    )


async def run_analysis(website: ExtractedWebsite, llm: LLMClient) -> LinkAnalysisResponse:
    settings = get_settings()
    user_prompt = _build_user_prompt(website, settings)

    raw = await llm.generate_json(_SYSTEM_PROMPT, user_prompt)
    parsed = _validate_or_raise(raw)

    if parsed is None:
        # One corrective retry: ask the model to fix its own output against
        # the exact validation errors, rather than re-running the whole
        # analysis from scratch (cheaper and more likely to converge).
        try:
            raw = await llm.generate_json(_SYSTEM_PROMPT, user_prompt)
        except LLMError:
            raise
        parsed = _validate_or_raise(raw, strict=True)

    brand = BrandInfo(**parsed["brand"])
    analysis = AnalysisSections(
        competitor_analysis=parsed["competitor_analysis"],
        target_search_queries=parsed["target_search_queries"],
        seo_improvements=parsed["seo_improvements"],
        top_services=parsed["top_services"],
        target_audience=parsed["target_audience"],
    )
    analysis.competitor_analysis = enforce_competitor_minimum(analysis.competitor_analysis)

    return LinkAnalysisResponse(website=website.final_url, brand=brand, analysis=analysis)


def _validate_or_raise(raw: dict, strict: bool = False) -> dict | None:
    required_keys = {
        "brand",
        "competitor_analysis",
        "target_search_queries",
        "seo_improvements",
        "top_services",
        "target_audience",
    }
    missing = required_keys - raw.keys()
    if missing:
        if strict:
            raise LLMError(f"LLM response missing required keys: {sorted(missing)}")
        return None

    try:
        BrandInfo(**raw["brand"])
        AnalysisSections(
            competitor_analysis=raw["competitor_analysis"],
            target_search_queries=raw["target_search_queries"],
            seo_improvements=raw["seo_improvements"],
            top_services=raw["top_services"],
            target_audience=raw["target_audience"],
        )
    except (ValidationError, TypeError, KeyError) as exc:
        if strict:
            raise LLMError(f"LLM response failed schema validation: {exc}") from exc
        return None

    return raw
