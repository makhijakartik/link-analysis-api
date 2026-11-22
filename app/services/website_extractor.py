"""Fetches a website and extracts clean, LLM-ready text content."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.utils.validators import UnsafeURLError, validate_public_url

_NOISE_TAGS = ("script", "style", "noscript", "svg", "iframe", "nav", "footer")
_USER_AGENT = "LinkAnalysisBot/1.0 (+https://github.com/; contact via repository)"


class FetchError(Exception):
    pass


class ExtractedWebsite:
    def __init__(
        self,
        final_url: str,
        title: str,
        meta_description: str,
        headings: list[str],
        body_text: str,
        internal_links: list[str],
    ) -> None:
        self.final_url = final_url
        self.title = title
        self.meta_description = meta_description
        self.headings = headings
        self.body_text = body_text
        self.internal_links = internal_links

    def to_llm_context(self, max_chars: int) -> str:
        parts = [
            f"URL: {self.final_url}",
            f"Title: {self.title}",
            f"Meta Description: {self.meta_description}",
            f"Headings: {' | '.join(self.headings[:20])}",
            f"Navigation/Link labels: {', '.join(self.internal_links[:30])}",
            "Body content:",
            self.body_text,
        ]
        context = "\n".join(parts)
        return context[:max_chars]


async def fetch_and_extract(url: str) -> ExtractedWebsite:
    settings = get_settings()

    try:
        validate_public_url(url)
    except UnsafeURLError as exc:
        raise FetchError(str(exc)) from exc

    headers = {"User-Agent": _USER_AGENT}
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=5,
            timeout=settings.request_timeout_seconds,
            headers=headers,
        ) as client:
            async with client.stream("GET", url) as response:
                # Re-validate the final (post-redirect) target before trusting it.
                final_url = str(response.url)
                try:
                    validate_public_url(final_url)
                except UnsafeURLError as exc:
                    raise FetchError(str(exc)) from exc

                if response.status_code >= 400:
                    raise FetchError(f"Website returned HTTP {response.status_code}")

                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    raise FetchError(f"Unsupported content type: {content_type or 'unknown'}")

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > settings.max_html_bytes:
                        break
                    chunks.append(chunk)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="ignore")
    except httpx.TimeoutException as exc:
        raise FetchError("Website request timed out") from exc
    except httpx.TransportError as exc:
        raise FetchError(f"Could not reach website: {exc}") from exc

    return _parse_html(html, final_url)


def _parse_html(html: str, final_url: str) -> ExtractedWebsite:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = (meta_desc_tag.get("content", "") if meta_desc_tag else "").strip()

    headings = [
        h.get_text(strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    ]

    link_labels = [
        a.get_text(strip=True)
        for a in soup.find_all("a")
        if a.get_text(strip=True) and len(a.get_text(strip=True)) < 60
    ]
    # de-dupe while preserving order
    seen: set[str] = set()
    internal_links = []
    for label in link_labels:
        key = label.lower()
        if key not in seen:
            seen.add(key)
            internal_links.append(label)

    body = soup.body or soup
    text = body.get_text(separator=" ", strip=True)
    # collapse repeated whitespace
    body_text = " ".join(text.split())

    if not body_text and not title:
        raise FetchError("No readable content found on the page")

    return ExtractedWebsite(
        final_url=final_url,
        title=title,
        meta_description=meta_description,
        headings=headings,
        body_text=body_text,
        internal_links=internal_links,
    )
