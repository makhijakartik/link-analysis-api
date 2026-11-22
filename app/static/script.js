const form = document.getElementById("analysis-form");
const urlInput = document.getElementById("url-input");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function tagList(items) {
  if (!items || items.length === 0) return "<p>-</p>";
  return `<ul class="tag-list">${items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
}

function setStatus(message, kind) {
  statusEl.className = `status ${kind}`;
  statusEl.textContent = message;
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  statusEl.classList.add("hidden");
  statusEl.textContent = "";
}

function renderResults(data) {
  const { brand, analysis } = data;

  const competitorsRows = (analysis.competitor_analysis.competitors || [])
    .map(
      (c) => `
      <tr>
        <td>${escapeHtml(c.name)}</td>
        <td>${escapeHtml((c.strengths || []).join(", "))}</td>
        <td>${escapeHtml((c.weaknesses || []).join(", "))}</td>
      </tr>`
    )
    .join("");

  const queriesRows = (analysis.target_search_queries || [])
    .map(
      (q) => `
      <tr>
        <td>${escapeHtml(q.query)}</td>
        <td>${escapeHtml((q.platforms || []).join(", "))}</td>
        <td>${escapeHtml(q.intent)}</td>
      </tr>`
    )
    .join("");

  const servicesRows = (analysis.top_services || [])
    .map(
      (s) => `
      <tr>
        <td>${escapeHtml(s.service_name)}${s.inferred ? '<span class="badge">inferred</span>' : ""}</td>
        <td>${escapeHtml(s.description)}</td>
        <td>${escapeHtml(s.target_customer)}</td>
      </tr>`
    )
    .join("");

  resultsEl.innerHTML = `
    <div class="card">
      <h2>Brand Overview</h2>
      <p><strong>${escapeHtml(brand.name)}</strong> &middot; ${escapeHtml(brand.category)}</p>
      <p class="brand-summary">${escapeHtml(brand.summary)}</p>
    </div>

    <div class="card">
      <h2>1. Competitor vs Your Brand</h2>
      <p>${escapeHtml(analysis.competitor_analysis.brand_overview)}</p>
      <h3>Main Products / Services</h3>
      ${tagList(analysis.competitor_analysis.main_products_services)}
      <h3>Competitors</h3>
      <table>
        <thead><tr><th>Name</th><th>Strengths</th><th>Weaknesses</th></tr></thead>
        <tbody>${competitorsRows || '<tr><td colspan="3">No reliable competitor data found</td></tr>'}</tbody>
      </table>
      <h3>Your Competitive Advantages</h3>
      ${tagList(analysis.competitor_analysis.your_competitive_advantages)}
      <h3>Opportunities</h3>
      ${tagList(analysis.competitor_analysis.opportunities)}
    </div>

    <div class="card">
      <h2>2. Top 5 Target Search Queries</h2>
      <table>
        <thead><tr><th>Query</th><th>Platforms</th><th>Intent</th></tr></thead>
        <tbody>${queriesRows}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>3. SEO Improvement</h2>
      <h3>Primary Keyword</h3>
      <p>${escapeHtml(analysis.seo_improvements.primary_keyword)}</p>
      <h3>Secondary Keywords</h3>
      ${tagList(analysis.seo_improvements.secondary_keywords)}
      <h3>Long-tail Keywords</h3>
      ${tagList(analysis.seo_improvements.long_tail_keywords)}
      <h3>Recommended SEO Title</h3>
      <p>${escapeHtml(analysis.seo_improvements.recommended_title)}</p>
      <h3>Meta Description</h3>
      <p>${escapeHtml(analysis.seo_improvements.meta_description)}</p>
      <h3>Suggested Supporting Content</h3>
      ${tagList(analysis.seo_improvements.supporting_content)}
    </div>

    <div class="card">
      <h2>4. Top Services</h2>
      <table>
        <thead><tr><th>Service</th><th>Description</th><th>Target Customer</th></tr></thead>
        <tbody>${servicesRows}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>5. Target Audience</h2>
      <h3>Primary Audience</h3>
      ${tagList(analysis.target_audience.primary_audience)}
      <h3>Secondary Audience</h3>
      ${tagList(analysis.target_audience.secondary_audience)}
      <h3>Industries</h3>
      ${tagList(analysis.target_audience.industries)}
      <h3>Customer Needs</h3>
      ${tagList(analysis.target_audience.customer_needs)}
      <h3>Recommended Segments</h3>
      ${tagList(analysis.target_audience.recommended_segments)}
    </div>
  `;
  resultsEl.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  resultsEl.classList.add("hidden");
  resultsEl.innerHTML = "";
  setStatus("Analyzing website... this can take a few seconds.", "loading");
  submitBtn.disabled = true;

  try {
    const response = await fetch("/link-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await response.json();

    if (!response.ok || data.success === false) {
      setStatus(data.error || "Analysis failed.", "error");
      return;
    }

    clearStatus();
    renderResults(data);
  } catch (err) {
    setStatus("Network error: could not reach the API.", "error");
  } finally {
    submitBtn.disabled = false;
  }
});
