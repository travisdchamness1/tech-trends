---
name: technology-trends
description: Produce and persist the weekday Technology Trend Update using an immutable GitHub ledger, with deterministic validation and a dashboard that derives history directly from ledger records.
---

# Technology Trends

Produce a materiality-first technology update covering commercialization, deployment, manufacturing capacity, infrastructure, strategic partnerships, geographic expansion, regulatory approval, and meaningful technical milestones.

## Required behavior

- Use the canonical categories in `data/category-registry.json`.
- Rank by signal strength, not popularity. Prefer primary company, government, regulatory, and research-institution sources.
- Return up to five findings. Do not add filler when fewer than five clear the materiality threshold.
- Do not repeat an event unless it materially changed. Use a stable `event_key`; give each observation a unique `finding_id`; link material updates with `material_update_from`.
- Discover runs directly from immutable files under `data/runs/`. The repository layout is the run index; do not maintain a second canonical run index.
- Determine the observation window from the latest successful immutable run. Record `scheduled_for`, `window_start`, and `window_end` explicitly.
- Treat immutable files under `data/runs/` as the sole historical system of record.
- Treat `data/trend-history.json` and `visuals/trend-velocity-history.html` as legacy derived artifacts. Scheduled runs must not read, rewrite, or depend on them.
- Dashboard history, event timelines, and category series must be derived from the immutable ledger at read/build time. See `references/dashboard-contract.md`.
- Escape untrusted text before generating HTML and allow only `https://` or `http://` source links.

Before any persistence operation, read `references/persistence-protocol.md` and validate the proposed immutable run against `schemas/run.schema.json`.

## Persistence boundary

A scheduled run is complete when:

1. the immutable run JSON and immutable HTML report are committed;
2. the committed run is re-read from GitHub;
3. its report path resolves; and
4. repository validation succeeds or any validation limitation is reported precisely.

No history-index rewrite or dashboard regeneration is part of the scheduled-run transaction.

## Failure boundary

Never claim persistence without re-reading the resulting Git commit or committed files. If the immutable ledger is malformed or cannot be enumerated completely, fail closed and return the human-readable report plus the exact proposed run JSON.
