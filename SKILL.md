---
name: technology-trends
description: Produce and persist the weekday Technology Trend Update, including material technology findings, immutable run records, category velocity history, and the longitudinal report visual. Use for scheduled or manual Technology Trends runs; do not use for investment advice or generic news summaries.
---

# Technology Trends

Produce a materiality-first technology update covering commercialization, deployment, manufacturing capacity, infrastructure, strategic partnerships, geographic expansion, regulatory approval, and meaningful technical milestones.

## Required behavior

- Use the canonical categories in `data/category-registry.json`.
- Rank by signal strength, not popularity. Prefer primary company, government, regulatory, and research-institution sources.
- Return up to five findings. Do not add filler when fewer than five clear the materiality threshold.
- Do not repeat an event unless it materially changed. Use a stable `event_key`; give each observation a unique `finding_id`; link material updates with `material_update_from`.
- Determine the observation window from the previous successful run. Record `scheduled_for`, `window_start`, and `window_end` explicitly.
- Treat immutable files under `data/runs/` as the authoritative ledger. `data/trend-history.json` and `visuals/trend-velocity-history.html` are rebuildable derivatives.
- Escape untrusted text before generating HTML and allow only `https://` or `http://` source links.

Before any persistence operation, read `references/persistence-protocol.md` and validate against `schemas/run.schema.json` and `schemas/history.schema.json`.

## Failure boundary

Never claim persistence without re-reading the resulting Git commit. If the ledger is malformed and cannot be rebuilt solely from validated immutable run files, fail closed and return the human-readable report plus the exact proposed run JSON.
