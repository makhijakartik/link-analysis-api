"""Pydantic request/response models for the /link-analysis endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class LinkAnalysisRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public website URL to analyze")


class BrandInfo(BaseModel):
    name: str
    category: str
    summary: str


class CompetitorEntry(BaseModel):
    name: str
    description: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    source_note: str = Field(
        default="ai_generated",
        description="'ai_generated' unless backed by a verifiable source",
    )


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    main_business_category: str
    main_products_services: list[str] = Field(default_factory=list)
    competitors: list[CompetitorEntry] = Field(default_factory=list)
    your_competitive_advantages: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


class TargetSearchQuery(BaseModel):
    query: str
    platforms: list[str] = Field(default_factory=list)
    intent: str
    business_relevance: str = ""
    target_audience: str = ""


class SeoImprovements(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str] = Field(default_factory=list)
    long_tail_keywords: list[str] = Field(default_factory=list)
    business_keywords: list[str] = Field(default_factory=list)
    recommended_title: str
    meta_description: str
    supporting_content: list[str] = Field(default_factory=list)


class ServiceEntry(BaseModel):
    service_name: str
    description: str
    target_industry: str = ""
    target_customer: str = ""
    main_benefit: str = ""
    inferred: bool = Field(
        default=False, description="True if not explicitly found in site content"
    )


class TargetAudience(BaseModel):
    primary_audience: list[str] = Field(default_factory=list)
    secondary_audience: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    business_types: list[str] = Field(default_factory=list)
    customer_needs: list[str] = Field(default_factory=list)
    customer_interests: list[str] = Field(default_factory=list)
    location_focus: str = ""
    recommended_segments: list[str] = Field(default_factory=list)


class AnalysisSections(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[TargetSearchQuery]
    seo_improvements: SeoImprovements
    top_services: list[ServiceEntry]
    target_audience: TargetAudience


class LinkAnalysisResponse(BaseModel):
    success: bool = True
    website: str
    brand: BrandInfo
    analysis: AnalysisSections


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
