# AI-Powered Website Link Analysis API

FastAPI service that fetches a website, analyzes its content with an LLM, and
returns structured competitor, SEO, search-query, services, and target-audience
insights.

Built for the Dxora Technologies Python practical test.

## Features

- `POST /link-analysis` — single endpoint, takes `{"url": "..."}`, returns the
  five required analysis sections as structured JSON.
- Minimal static frontend at `GET /` (vanilla HTML/CSS/JS, served by FastAPI)
  for manually testing the endpoint without curl/Swagger — enter a URL, see
  all five sections rendered.
- Real content extraction (title, meta description, headings, nav labels,
  body text) via `httpx` + `BeautifulSoup`, with boilerplate/script/style
  stripped before anything reaches the LLM.
- SSRF protection: rejects non-http(s) schemes, resolves DNS and blocks
  private/loopback/link-local/metadata addresses, and re-validates after
  every redirect hop.
- Provider-agnostic LLM layer (`app/services/llm_service.py`) — switch
  between **Anthropic Claude**, **OpenAI**, and **Google Gemini** with one
  env var, no code changes.
- One consolidated LLM call per analysis (not five), with strict JSON-schema
  validation on the response and a single corrective retry if the model's
  output doesn't parse/validate.
- Graceful error handling for invalid URLs, unreachable sites, blocked
  targets, and LLM/provider failures — never a raw 500 for an expected
  failure mode.

## Project Structure

```
app/
  main.py                      # FastAPI app, /link-analysis route, static frontend
  config.py                    # env-driven settings
  schemas.py                   # Pydantic request/response models
  services/
    website_extractor.py       # fetch + SSRF guard + HTML -> clean text
    llm_service.py              # Anthropic/OpenAI/Gemini client wrapper
    analysis_service.py        # prompt building, LLM call, validation, retry
    competitor_service.py      # competitor-section post-processing
  utils/
    validators.py              # URL + SSRF validation
  static/
    index.html, style.css, script.js   # minimal frontend for manual testing
tests/
  test_link_analysis.py        # mocked happy path + error-path tests
.env.example
requirements.txt
```

## Setup

```bash
git clone <this-repo>
cd link-analysis-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key
```

Run the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Frontend (manual testing UI): http://localhost:4000/
API docs: http://localhost:4000/docs

Run tests (LLM and HTTP calls are mocked, no API key required):

```bash
pytest tests/ -v
```

## Sample Request

```bash
curl -s -X POST http://localhost:4000/link-analysis \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com"}'
```

## Sample Response (shape)

```json
{
  "success": true,
  "website": "https://example.com",
  "brand": {
    "name": "ABC Technologies",
    "category": "Technology Services",
    "summary": "A technology company providing digital solutions."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "...",
      "main_business_category": "Technology Services",
      "main_products_services": ["Web Development"],
      "competitors": [
        {"name": "XYZ Technologies", "description": "...", "strengths": [], "weaknesses": [], "source_note": "ai_generated"}
      ],
      "your_competitive_advantages": [],
      "opportunities": []
    },
    "target_search_queries": [
      {"query": "Best web development company", "platforms": ["Google"], "intent": "Service Search", "business_relevance": "...", "target_audience": "..."}
    ],
    "seo_improvements": {
      "primary_keyword": "Web Development",
      "secondary_keywords": [],
      "long_tail_keywords": [],
      "business_keywords": [],
      "recommended_title": "...",
      "meta_description": "...",
      "supporting_content": []
    },
    "top_services": [
      {"service_name": "Web Development", "description": "...", "target_industry": "...", "target_customer": "...", "main_benefit": "...", "inferred": false}
    ],
    "target_audience": {
      "primary_audience": [],
      "secondary_audience": [],
      "industries": [],
      "business_types": [],
      "customer_needs": [],
      "customer_interests": [],
      "location_focus": "",
      "recommended_segments": []
    }
  }
}
```

### Error responses

| Scenario | Status | Example |
|---|---|---|
| Invalid URL | 422 | FastAPI validation error on `url` |
| SSRF-blocked target (private/internal IP) | 400 | `{"success": false, "error": "Resolved address ... is not a public address"}` |
| Unreachable / non-HTML site | 400 | `{"success": false, "error": "Could not reach website: ..."}` |
| LLM provider misconfigured or call failed | 502 | `{"success": false, "error": "LLM provider unavailable: ..."}` |

### Verified local run (no LLM key configured in this sandbox)

```
$ curl -s http://localhost:4000/health
{"status":"ok"}

$ curl -s -X POST http://localhost:4000/link-analysis -d '{"url":"https://example.com"}'
{"success":false,"error":"LLM provider unavailable: ANTHROPIC_API_KEY is not configured"}

$ curl -s -X POST http://localhost:4000/link-analysis -d '{"url":"http://169.254.169.254/latest/meta-data/"}'
{"success":false,"error":"Target host is not allowed"}

$ curl -s -X POST http://localhost:4000/link-analysis -d '{"url":"not-a-url"}'
{"detail":[{"type":"url_parsing","loc":["body","url"],"msg":"Input should be a valid URL, relative URL without a base", ...}]}

$ pytest tests/ -v
5 passed in 0.31s
```

This confirms the full pipeline — routing, URL validation, SSRF blocking,
website fetch/extraction, and error handling — end to end. The LLM call
itself (`/link-analysis` on a real public site with a valid API key) should
be re-verified by whoever runs this with live credentials; a full
successful-run log/screenshot should be added here once a provider key is
supplied.

---

## LLM Platform & Model Research

### A. Comparison

Pricing below is per published provider rate cards (per 1M tokens, text
input/output) as of this writeup; always re-check current pricing pages
before relying on these numbers in production, as providers change pricing
frequently.

| Provider | Model | Input $/1M | Output $/1M | Context Window | JSON Support | Notes |
|---|---|---|---|---|---|---|
| Anthropic | Claude Haiku 4.5 | ~$1 | ~$5 | 200K tokens | Strong (tool-use / strict instruction-following) | Best balance of cost/speed/quality for this task; very reliable at following "JSON only" instructions |
| OpenAI | GPT-4o-mini | ~$0.15 | ~$0.60 | 128K tokens | Native `response_format: json_object` / `json_schema` | Cheapest of the three; native structured-output mode makes malformed JSON rare |
| Google | Gemini 1.5 Flash | ~$0.075 (≤128K) | ~$0.30 (≤128K) | 1M tokens | Native `response_mime_type: application/json` | Cheapest overall, huge context window (useful if sending more raw HTML instead of trimming it) |
| Anthropic | Claude Sonnet 4.5 | ~$3 | ~$15 | 200K tokens | Strong | Reserve for cases needing deeper competitor/market reasoning, not the default path |

Response speed is not independently benchmarked in this sandbox (no API
key available at build time — see note above). Published typical latency
for all three "small/fast" tiers (Haiku, GPT-4o-mini, Gemini Flash) on a
~2–6K token prompt is in the low single-digit seconds; treat any specific
number here as a vendor-reported estimate, not a measurement, until
re-tested with real credentials.

### B. Best Model Selection

**Recommendation: Google Gemini 1.5 Flash or OpenAI GPT-4o-mini as the
primary model, with Anthropic Claude Haiku as a quality-focused fallback.**

Reasoning:
- This task is extraction + structured synthesis over a few thousand
  tokens of website text — not deep multi-step reasoning. The "flagship"
  tier (Sonnet/GPT-4/Gemini Pro) is unnecessary cost for this workload.
- Both GPT-4o-mini and Gemini Flash have **native JSON-mode / schema
  enforcement**, which materially reduces the "LLM returned invalid JSON"
  failure path this API already has to defend against.
- Claude Haiku is included as the default in this implementation because
  it has excellent instruction-following for "return ONLY JSON, no
  preamble" even without a dedicated JSON mode, and is a reasonable
  middle ground on cost — but for a cost-sensitive production deployment,
  GPT-4o-mini or Gemini Flash is the stronger choice on raw $/request.

### C. Cost Optimization (implemented in this codebase)

- **One consolidated prompt**, not five separate calls per section —
  cuts fixed per-call overhead (system prompt, instructions) by ~5x.
- **Content trimming before the LLM ever sees it**: `website_extractor.py`
  strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<svg>`, `<iframe>`,
  collapses whitespace, and the final context is hard-capped at
  `MAX_CONTENT_CHARS_FOR_LLM` (default 6000 chars ≈ 1.5K tokens) before
  being sent — most of a raw page's HTML is markup/boilerplate, not
  content.
- **Byte cap on the raw fetch** (`MAX_HTML_BYTES`) so a large page doesn't
  even get fully downloaded and parsed before trimming.
- **Capped output tokens** (`LLM_MAX_OUTPUT_TOKENS`) to bound worst-case
  output cost per call.
- **Smaller/faster model tier by default** (Haiku / mini / Flash class)
  rather than a flagship model, since this task doesn't need flagship
  reasoning depth.
- **Single corrective retry, not a full re-run**, when JSON validation
  fails — avoids paying for the entire analysis twice on a formatting slip.
- Not yet implemented, recommended for production: **response caching
  keyed by normalized URL** (e.g. Redis, TTL of a day/week) so repeated
  analysis requests for the same site don't re-trigger fetch + LLM cost.

### D. Final Recommendation

| Field | Value |
|---|---|
| Recommended provider | Google Gemini (cost-optimized) or OpenAI (balanced) |
| Recommended model | Gemini 1.5 Flash / GPT-4o-mini |
| Default in this repo | Anthropic Claude Haiku 4.5 (per user instruction for this build) |
| Estimated input tokens/analysis | ~1,500–2,000 (trimmed website content + schema instructions) |
| Estimated output tokens/analysis | ~800–1,500 (5 structured sections) |
| Estimated cost/analysis (Gemini Flash) | roughly $0.0002–$0.0005 |
| Estimated cost/analysis (GPT-4o-mini) | roughly $0.0008–$0.0013 |
| Estimated cost/analysis (Claude Haiku) | roughly $0.006–$0.009 |
| Expected response time | low single-digit seconds (vendor-typical for these tiers; not independently benchmarked here — see note above) |
| Alternative/fallback model | If the primary provider errors or rate-limits, fall back to the next provider in `LLM_PROVIDER` — the `llm_service.py` abstraction makes this a config change, not a code change |
| Balancing approach | Default to the cheapest model with native JSON mode (Gemini Flash / GPT-4o-mini) for this extraction-and-synthesis workload; escalate to a larger model only if a client explicitly requests deeper competitor/market analysis beyond what site content alone supports |

**Important caveat:** cost estimates above are computed from published
per-token pricing times estimated token counts for this workload, not
measured bills from live runs — mark them as estimates, not benchmarks,
until tested against a real account. Response-time figures are
vendor-typical, not locally measured, for the same reason (no API key was
available in the build environment).

## Notes on Scope / Honesty

- Competitor data is clearly marked `"source_note": "ai_generated"` unless
  backed by site content itself — per the test's instruction not to present
  AI-generated competitor claims as verified fact.
- The service never invents search-volume or ranking numbers; `target_search_queries`
  returns query/platform/intent only, as instructed.
- `top_services` entries are flagged `"inferred": true` when the model
  deduced a service rather than finding it explicitly stated on the page.
