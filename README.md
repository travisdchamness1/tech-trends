# Technology Trends

Persistent, auditable artifacts for the weekday **Technology Trend Update** scheduled task.

The repository is public. Reports and run records must not contain secrets, private account data, or unpublished personal information.

## Canonical data model

- `data/runs/YYYY/YYYY-MM-DD/<run_id>.json` — authoritative immutable run ledger
- `reports/YYYY/YYYY-MM-DD/technology-trend-update-<run_id>.html` — immutable human-readable report
- `schemas/run.schema.json` — canonical run contract
- `data/category-registry.json` — canonical category registry
- `references/persistence-protocol.md` — transaction, idempotency, retry, and recovery rules
- `references/dashboard-contract.md` — dashboard discovery and rendering contract
- `references/chatgpt-site-spec.md` — ChatGPT Site implementation and acceptance specification

The repository tree itself is the run index. Consumers discover immutable run files directly under `data/runs/`; no second canonical run-index file is required.

## Scheduled task responsibility

The ChatGPT scheduled task owns only the immutable production write:

1. discover the latest successful run directly from `data/runs/`;
2. research and validate the next occurrence;
3. commit one immutable run JSON and one immutable HTML report;
4. re-read and verify the committed artifacts.

The task does **not** rewrite longitudinal history or regenerate a dashboard.

## Deterministic validation

GitHub Actions runs `python scripts/validate_repository.py .` after pushes and on pull requests.

The validator checks the immutable ledger, report linkage, category coverage, global finding identity, scheduled-occurrence uniqueness, and material-update event linkage.

Run discovery can be inspected locally with:

```bash
python scripts/discover_runs.py .
```

## Dashboard architecture

A dashboard or ChatGPT Site should discover run files from the public GitHub repository tree and derive:

- latest run;
- category velocity series;
- event timelines;
- material-update chains; and
- report links.

These views are projections of the immutable ledger and may be recomputed at any time. See `references/dashboard-contract.md`.

## Legacy derived artifacts

`data/trend-history.json`, `schemas/history.schema.json`, and `visuals/trend-velocity-history.html` are retained only as legacy artifacts from the earlier architecture.

They are **not authoritative**, are **not updated by scheduled runs**, and are **not validation dependencies**. New integrations must not use them as the source of truth.

## Core invariants

1. Immutable run and report paths are never overwritten.
2. `scheduled_for` is the idempotency key: at most one successful run per scheduled occurrence.
3. The repository layout under `data/runs/` is sufficient to discover all runs.
4. A repeated `event_key` must represent a material update and link to the preceding observation through `material_update_from`.
5. A changed branch HEAD causes a re-read and bounded retry, never a forced update.
6. Derived views can always be reconstructed from the immutable ledger.
