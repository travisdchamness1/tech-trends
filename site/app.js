const OWNER = "travisdchamness1";
const REPO = "tech-trends";
const BRANCH = "main";
const API = `https://api.github.com/repos/${OWNER}/${REPO}`;
const RAW = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}`;
const BLOB = `https://github.com/${OWNER}/${REPO}/blob/${BRANCH}`;

const runPathPattern = /^data\/runs\/\d{4}\/\d{4}-\d{2}-\d{2}\/technology-trends-\d{4}-\d{2}-\d{2}\.json$/;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDateTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit"
  }).format(date);
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  return response.json();
}

async function loadRun(entry) {
  const cacheKey = `technology-trends:${entry.sha}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    try { return JSON.parse(cached); } catch {}
  }
  const run = await getJson(`${RAW}/${entry.path}`);
  try { localStorage.setItem(cacheKey, JSON.stringify(run)); } catch {}
  return run;
}

function scoreLabel(assessment) {
  if (assessment.direction === "unknown") return "Unknown";
  const score = assessment.velocity_score;
  return `${assessment.direction} ${score > 0 ? "+" : ""}${score}`;
}

function renderSummary(runs) {
  const latest = runs.at(-1);
  const totalFindings = runs.reduce((sum, run) => sum + run.findings.length, 0);
  const events = new Set(runs.flatMap(run => run.findings.map(f => f.event_key)));
  document.querySelector("#summary").innerHTML = [
    ["Latest run", latest.scheduled_for.slice(0, 10)],
    ["Immutable runs", runs.length],
    ["Material findings", totalFindings],
    ["Tracked events", events.size],
  ].map(([label, value]) => `
    <article class="stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>
  `).join("");
}

function renderFindings(latest) {
  const root = document.querySelector("#findings");
  root.innerHTML = latest.findings.map(finding => `
    <article class="finding">
      <div class="rank">${finding.rank}</div>
      <div>
        <h3>${escapeHtml(finding.headline)}</h3>
        <p>${escapeHtml(finding.summary)}</p>
        <p class="why"><strong>Why it matters:</strong> ${escapeHtml(finding.why_it_matters)}</p>
        <div class="chips">
          ${finding.category_ids.map(id => `<span>${escapeHtml(id)}</span>`).join("")}
        </div>
      </div>
    </article>
  `).join("");

  const report = document.querySelector("#latest-report");
  report.href = `${BLOB}/${latest.report_path}`;
}

function renderCategories(runs, registry) {
  const latest = runs.at(-1);
  const names = Object.fromEntries(registry.categories.map(c => [c.category_id, c.category_name]));
  const latestById = Object.fromEntries(latest.category_assessments.map(a => [a.category_id, a]));

  const seriesById = {};
  for (const run of runs) {
    for (const assessment of run.category_assessments) {
      (seriesById[assessment.category_id] ??= []).push({
        date: run.scheduled_for.slice(0, 10),
        score: assessment.velocity_score,
        direction: assessment.direction,
      });
    }
  }

  document.querySelector("#categories").innerHTML = registry.categories.map(category => {
    const a = latestById[category.category_id];
    const series = seriesById[category.category_id] ?? [];
    const points = series.map(item => {
      const cls = item.direction === "unknown" ? "unknown" : item.score > 0 ? "up" : item.score < 0 ? "down" : "flat";
      const title = `${item.date}: ${item.direction} ${item.score}`;
      return `<span class="spark ${cls}" title="${escapeHtml(title)}"></span>`;
    }).join("");
    return `
      <article class="category-card">
        <div class="category-top">
          <div>
            <span class="category-id">${escapeHtml(category.category_id)}</span>
            <h3>${escapeHtml(names[category.category_id])}</h3>
          </div>
          <strong class="velocity ${escapeHtml(a.direction)}">${escapeHtml(scoreLabel(a))}</strong>
        </div>
        <p>${escapeHtml(a.justification)}</p>
        <div class="sparkline" aria-label="Historical category velocity">${points}</div>
      </article>
    `;
  }).join("");
}

function renderRuns(runs) {
  document.querySelector("#runs").innerHTML = [...runs].reverse().map(run => `
    <tr>
      <td><strong>${escapeHtml(run.scheduled_for.slice(0, 10))}</strong><br><span class="muted">${escapeHtml(run.run_id)}</span></td>
      <td>${run.findings.length}</td>
      <td>${escapeHtml(formatDateTime(run.window_start))}<br><span class="muted">to ${escapeHtml(formatDateTime(run.window_end))}</span></td>
      <td><a href="${BLOB}/${encodeURI(run.report_path)}" target="_blank" rel="noopener noreferrer">Report</a></td>
    </tr>
  `).join("");
}

async function main() {
  const status = document.querySelector("#status");
  try {
    const [tree, registry] = await Promise.all([
      getJson(`${API}/git/trees/${BRANCH}?recursive=1`),
      getJson(`${RAW}/data/category-registry.json`),
    ]);

    const entries = tree.tree
      .filter(item => item.type === "blob" && runPathPattern.test(item.path))
      .sort((a, b) => a.path.localeCompare(b.path));

    if (!entries.length) throw new Error("No immutable run records found.");

    const runs = (await Promise.all(entries.map(loadRun)))
      .filter(run => run.status === "success")
      .sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for));

    renderSummary(runs);
    renderFindings(runs.at(-1));
    renderCategories(runs, registry);
    renderRuns(runs);

    status.textContent = `Live · ${runs.length} runs · ${runs.at(-1).scheduled_for.slice(0, 10)}`;
    status.classList.add("ok");
  } catch (error) {
    console.error(error);
    status.textContent = "Unable to load ledger";
    status.classList.add("error");
    document.querySelector("#summary").innerHTML =
      `<p class="error-box">${escapeHtml(error.message)}</p>`;
  }
}

main();
