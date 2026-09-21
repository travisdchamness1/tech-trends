# ChatGPT Site implementation specification

## 1. Purpose

Build a read-only **Technology Trends** dashboard as a ChatGPT Site.

The Site is a presentation layer over the public GitHub repository `travisdchamness1/tech-trends`. GitHub remains the canonical data source. The Site must not introduce a second authoritative database, run manifest, history index, or event index.

The Site should make the longitudinal experiment easy to inspect without changing the scheduled-run persistence model.

## 2. Architectural principles

1. **Immutable ledger is authoritative.**
   - Canonical records live under `data/runs/`.
   - Human-readable immutable reports live under `reports/`.

2. **Repository structure is the run index.**
   - Discover run files from the GitHub tree.
   - Do not maintain a canonical list of run identifiers elsewhere.

3. **Derived views are ephemeral.**
   - Category history, event timelines, summaries, counts, and charts are derived in memory from immutable run records.
   - Optional caches are disposable and never authoritative.

4. **Read-only Site.**
   - The Site must not write to GitHub.
   - The Site must not mutate scheduled task state.
   - The Site must not require GitHub credentials for the public repository.

5. **Fail visibly, never invent data.**
   - Partial API failures must be shown clearly.
   - Missing or malformed run records must not be silently approximated.

## 3. Canonical repository inputs

The Site must read:

- `data/category-registry.json`
- immutable run records matching:
  `data/runs/YYYY/YYYY-MM-DD/technology-trends-YYYY-MM-DD.json`

The Site may link to:

- `reports/YYYY/YYYY-MM-DD/technology-trend-update-technology-trends-YYYY-MM-DD.html`

The Site must not use these legacy files as authoritative inputs:

- `data/trend-history.json`
- `schemas/history.schema.json`
- `visuals/trend-velocity-history.html`

The canonical data-consumption rules are defined in `references/dashboard-contract.md`.

## 4. Data discovery

### 4.1 Repository

- Owner: `travisdchamness1`
- Repository: `tech-trends`
- Branch: `main`
- Repository visibility: public

### 4.2 GitHub API discovery

Preferred browser read sequence:

1. Fetch the recursive tree for `main`:
   `GET https://api.github.com/repos/travisdchamness1/tech-trends/git/trees/main?recursive=1`
2. Filter blobs whose paths match:
   `^data/runs/\d{4}/\d{4}-\d{2}-\d{2}/technology-trends-\d{4}-\d{2}-\d{2}\.json$`
3. Sort candidate paths lexically for deterministic fetch ordering.
4. Fetch each immutable run from:
   `https://raw.githubusercontent.com/travisdchamness1/tech-trends/main/<path>`
5. Keep only records with `status == "success"`.
6. Sort records by `scheduled_for` ascending.
7. Fetch `data/category-registry.json`.
8. Derive all dashboard views in memory.

### 4.3 Caching

Immutable run files may be cached client-side by Git blob SHA.

Recommended cache key:

`technology-trends:<blob-sha>`

Requirements:

- cache failure must not prevent a network retry;
- malformed cached JSON must be discarded;
- cache content is non-authoritative;
- no cache is required for correctness.

## 5. Information architecture

The first release should contain five primary views.

### 5.1 Overview

Purpose: answer "What is happening now?"

Show:

- latest successful run date;
- observation window;
- number of immutable runs;
- total material findings;
- unique tracked event count;
- latest five-or-fewer material findings;
- category velocity snapshot;
- link to the latest immutable report.

Each finding card should include:

- rank;
- headline;
- summary;
- why it matters;
- category labels;
- source links;
- whether it is a material update;
- prior finding link when `material_update_from` is non-null.

### 5.2 Category trends

Purpose: answer "Which technology areas are accelerating, slowing, flat, or uncertain?"

For each canonical category, show:

- category name;
- latest direction;
- latest velocity score;
- confidence;
- justification;
- complete historical series by run date.

Required visual treatment:

- a compact sparkline or point series;
- `unknown` visually distinct from `flat`;
- hover/tap details showing date, score, direction, confidence, and justification.

Do not interpolate missing values.

### 5.3 Event timeline

Purpose: answer "How has a specific development evolved?"

Derive events by grouping findings on stable `event_key`.

For each event:

- first observation;
- latest observation;
- number of material updates;
- chronological observation chain;
- headline and summary for each observation;
- source links;
- `material_update_from` linkage.

Validation behavior:

- if a repeated `event_key` does not point to the immediately preceding finding, show a visible integrity warning rather than repairing it client-side.

### 5.4 Run history

Purpose: answer "What did each scheduled assessment contain?"

Show one row/card per run:

- date;
- run ID;
- observation window;
- finding count;
- category velocity summary;
- immutable report link.

Allow newest-first sorting.

Optional filtering:

- category;
- direction;
- event key;
- date range.

### 5.5 Methodology / system status

Purpose: answer "How should I interpret this dashboard?"

Show concise explanations of:

- immutable-ledger architecture;
- materiality threshold;
- `scheduled_for` idempotency;
- `event_key`;
- `material_update_from`;
- meaning of velocity scores;
- distinction between `unknown` and `flat`;
- GitHub as canonical source;
- timestamp of the last successful client refresh.

Provide links to:

- repository;
- `SKILL.md`;
- `references/persistence-protocol.md`;
- `references/dashboard-contract.md`.

## 6. Visual design

Use the existing `site/` implementation as a starting point, but adapt it to ChatGPT Sites conventions if needed.

Design goals:

- information-dense but readable;
- restrained visual hierarchy;
- desktop and mobile responsive;
- no decorative animation required;
- clear distinction between data, interpretation, and integrity state.

Recommended semantic colors:

- up: positive/green treatment;
- down: negative/red treatment;
- flat: neutral/gray treatment;
- unknown: amber/yellow treatment.

Color must never be the only carrier of meaning. Always include text labels.

## 7. Interaction requirements

### Required

- open immutable report;
- open source link;
- inspect category history;
- inspect event chain;
- browse prior runs;
- refresh GitHub data;
- responsive mobile layout.

### Preferred

- category filter;
- event search;
- date-range filter;
- shareable deep-link state if Sites routing permits.

### Not required for v1

- authentication;
- write-back to GitHub;
- comments;
- user accounts;
- private data;
- Python backend;
- database;
- WebSocket/live polling.

## 8. Source-link behavior

Only render source links whose URL scheme is `http://` or `https://`.

All external links should:

- open safely;
- use `rel="noopener noreferrer"` where applicable;
- display a human-readable source title;
- never render arbitrary HTML from ledger text.

All text from the ledger must be escaped before injection into HTML.

## 9. Error and integrity behavior

### GitHub unavailable

Show:

- "Unable to load ledger";
- last successfully rendered cached data if available;
- visible indication that it is cached/stale;
- retry control.

### One run fails to parse

Show:

- a visible integrity warning;
- path of the invalid record;
- do not include that run in calculated trends;
- do not silently infer its content.

### Category registry unavailable

Fail the category views explicitly. Do not guess category names.

### Empty ledger

Show a valid empty state. Do not fabricate placeholder findings.

### Event-link inconsistency

Show a warning on the affected event timeline.

## 10. Performance target

For the current repository size, direct ledger reads are acceptable.

Initial target:

- first meaningful dashboard content within approximately 3 seconds on a typical broadband connection;
- avoid refetching immutable runs whose SHA is already cached;
- no backend required for v1.

If performance becomes unacceptable, add a generated cache only after measurement. Any cache remains disposable and non-authoritative.

## 11. Accessibility

Minimum requirements:

- semantic headings;
- keyboard-accessible links and controls;
- visible focus states;
- adequate text contrast;
- category status communicated with text, not color only;
- tables usable on narrow screens;
- meaningful ARIA labels for charts or visual series;
- no interaction that requires hover only.

## 12. ChatGPT Sites runtime assumptions

The Site should be implemented as a client-side application using capabilities supported by the ChatGPT Sites runtime.

Do not assume:

- arbitrary long-running Python processes;
- a persistent server filesystem;
- background workers;
- private server-side secrets;
- a relational database.

The v1 architecture intentionally avoids those dependencies.

If Sites provides a supported server-side fetch/runtime abstraction, it may be used as an optimization, but canonical behavior must remain equivalent to the public GitHub read model above.

## 13. Existing frontend

The repository currently contains:

- `site/index.html`
- `site/app.js`
- `site/styles.css`

The existing frontend already:

- discovers run files from the GitHub tree;
- fetches immutable run JSON;
- caches immutable runs by SHA;
- renders latest findings;
- renders category velocity;
- renders run history.

The Sites implementation should reuse this logic where practical rather than re-creating the data model.

The implementation should extend it with:

- event timelines;
- source links on finding cards;
- explicit material-update display;
- integrity warnings;
- methodology/system-status view;
- refresh state;
- better chart accessibility.

## 14. Acceptance criteria

The ChatGPT Site is complete when all of the following pass:

1. It loads data directly from `travisdchamness1/tech-trends` without a private credential.
2. It discovers every valid immutable run currently under `data/runs/`.
3. The latest run shown matches the run with greatest `scheduled_for`.
4. Latest findings match the immutable latest run exactly.
5. Exactly the canonical categories from `data/category-registry.json` are shown.
6. Category histories are derived from immutable run assessments.
7. Repeated events are grouped by `event_key`.
8. Material-update chains honor `material_update_from`.
9. Every report link resolves to the corresponding immutable report.
10. Legacy `data/trend-history.json` is not read.
11. Legacy `visuals/trend-velocity-history.html` is not read.
12. A GitHub/network failure produces a visible error or stale-data state rather than fabricated values.
13. The interface is usable on mobile.
14. The Site is read-only.
15. No GitHub token or other secret is embedded in client code.

## 15. Validation checklist for handoff

Before publishing:

- compare latest Site run ID with `python scripts/discover_runs.py . --latest`;
- compare latest finding count with immutable run JSON;
- verify all eight category cards;
- inspect the known NASA Roman material-update chain;
- verify at least one immutable report link;
- test with local storage cleared;
- test with network temporarily unavailable;
- test narrow mobile viewport;
- confirm the browser network log never requests `data/trend-history.json`;
- confirm no secret/token is present in Site source.

## 16. Suggested ChatGPT Work / Sites build prompt

Use this prompt when handing the repository to Work/Sites:

> Build a ChatGPT Site for the Technology Trends dashboard using the public GitHub repository `travisdchamness1/tech-trends`. Treat `references/chatgpt-site-spec.md` as the implementation specification and `references/dashboard-contract.md` as the authoritative data-consumption contract. GitHub is the canonical data source. Discover immutable runs directly from `data/runs/`; do not use `data/trend-history.json` or the legacy longitudinal visual as authoritative inputs. Reuse the existing `site/` frontend where practical. Implement Overview, Category Trends, Event Timeline, Run History, and Methodology/System Status views. Keep the Site read-only, unauthenticated, responsive, and safe for public data. Derive all histories in memory from immutable run records. Validate the finished Site against the acceptance criteria in the specification before presenting it for publication.

## 17. Future extensions

Not part of v1:

- GitHub Pages mirror;
- authenticated private datasets;
- notification controls;
- annotations;
- cross-category correlation views;
- machine-generated weekly/monthly rollups;
- export to CSV/JSON;
- query/search using embeddings;
- comparison against market or investment data.

Any future feature must preserve the invariant that immutable records under `data/runs/` are the historical source of truth.
