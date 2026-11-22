"""Post-processing helpers specific to the competitor analysis section."""
from __future__ import annotations

from app.schemas import CompetitorAnalysis

MIN_COMPETITORS = 3


def enforce_competitor_minimum(competitor_analysis: CompetitorAnalysis) -> CompetitorAnalysis:
    """Flag when the LLM could not identify enough reliable competitors.

    The spec asks for a minimum of 3 competitors "where reliable information
    is available" — we don't fabricate extra ones to hit the count, we just
    make the shortfall explicit so the API consumer knows the data is thin.
    """
    if len(competitor_analysis.competitors) < MIN_COMPETITORS:
        competitor_analysis.opportunities.append(
            f"Limited reliable competitor data available "
            f"({len(competitor_analysis.competitors)} identified; "
            f"{MIN_COMPETITORS} recommended). Consider manual competitor research."
        )
    return competitor_analysis
