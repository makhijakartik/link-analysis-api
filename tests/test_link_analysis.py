from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.website_extractor import ExtractedWebsite

client = TestClient(app)

_VALID_LLM_RESPONSE = {
    "brand": {
        "name": "ABC Technologies",
        "category": "Technology Services",
        "summary": "A technology company providing digital solutions.",
    },
    "competitor_analysis": {
        "brand_overview": "Provides web development services.",
        "main_business_category": "Technology Services",
        "main_products_services": ["Web Development"],
        "competitors": [
            {"name": "Comp A", "description": "", "strengths": [], "weaknesses": [], "source_note": "ai_generated"},
            {"name": "Comp B", "description": "", "strengths": [], "weaknesses": [], "source_note": "ai_generated"},
            {"name": "Comp C", "description": "", "strengths": [], "weaknesses": [], "source_note": "ai_generated"},
        ],
        "your_competitive_advantages": ["Affordable pricing"],
        "opportunities": ["Improve visibility"],
    },
    "target_search_queries": [
        {"query": "best web development company", "platforms": ["Google"], "intent": "Service Search", "business_relevance": "", "target_audience": ""}
        for _ in range(5)
    ],
    "seo_improvements": {
        "primary_keyword": "Web Development",
        "secondary_keywords": [],
        "long_tail_keywords": [],
        "business_keywords": [],
        "recommended_title": "ABC Technologies - Web Development",
        "meta_description": "Affordable web development services.",
        "supporting_content": [],
    },
    "top_services": [
        {"service_name": "Web Development", "description": "", "target_industry": "", "target_customer": "", "main_benefit": "", "inferred": False}
    ],
    "target_audience": {
        "primary_audience": ["Small Businesses"],
        "secondary_audience": [],
        "industries": [],
        "business_types": [],
        "customer_needs": [],
        "customer_interests": [],
        "location_focus": "",
        "recommended_segments": [],
    },
}

_FAKE_WEBSITE = ExtractedWebsite(
    final_url="https://example.com",
    title="ABC Technologies",
    meta_description="Web development services",
    headings=["Welcome"],
    body_text="We build websites for small businesses.",
    internal_links=["Home", "Services"],
)


def test_link_analysis_happy_path():
    with patch(
        "app.main.fetch_and_extract", new=AsyncMock(return_value=_FAKE_WEBSITE)
    ), patch("app.main.get_llm_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.generate_json = AsyncMock(return_value=_VALID_LLM_RESPONSE)
        mock_get_client.return_value = mock_client

        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["brand"]["name"] == "ABC Technologies"
    assert len(body["analysis"]["target_search_queries"]) == 5
    assert len(body["analysis"]["competitor_analysis"]["competitors"]) >= 3


def test_link_analysis_invalid_url():
    response = client.post("/link-analysis", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_link_analysis_ssrf_blocked():
    response = client.post("/link-analysis", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_link_analysis_unreachable_site():
    from app.services.website_extractor import FetchError

    with patch(
        "app.main.fetch_and_extract",
        new=AsyncMock(side_effect=FetchError("Could not reach website: timeout")),
    ):
        response = client.post("/link-analysis", json={"url": "https://this-domain-should-not-exist-xyz123.com"})

    assert response.status_code == 400
    assert response.json()["success"] is False


def test_link_analysis_llm_failure():
    from app.services.llm_service import LLMError

    with patch(
        "app.main.fetch_and_extract", new=AsyncMock(return_value=_FAKE_WEBSITE)
    ), patch("app.main.get_llm_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.generate_json = AsyncMock(side_effect=LLMError("boom"))
        mock_get_client.return_value = mock_client

        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert response.json()["success"] is False
