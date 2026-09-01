# Technology Trends

Persistent, auditable artifacts for the weekday **Technology Trend Update** scheduled task.

The repository is public. Reports and run records must not contain secrets, private account data, or unpublished personal information.

## Data model

- `data/runs/YYYY/YYYY-MM-DD/<run_id>.json` — authoritative immutable run ledger
- `reports/YYYY/YYYY-MM-DD/technology-trend-update-<run_id>.html` — immutable human-readable report
- `data/trend-history.json` — compact derived run, event, and category index
- `visuals/trend-velocity-history.html` — rebuildable longitudinal visual
- `schemas/` — machine-readable contracts
- `references/persistence-protocol.md` — transaction, idempotency, retry, and recovery rules

The existing ChatGPT scheduled task owns production writes. It runs Monday through Friday at 8:00 AM in `America/Los_Angeles` and must update this repository using the protocol in this repository.

## Core invariants

1. Immutable run and report paths are never overwritten.
2. `scheduled_for` is the idempotency key: at most one successful run per scheduled occurrence.
3. A production run is committed atomically from an expected branch HEAD when the runtime supports Git data operations.
4. A changed branch HEAD causes a re-read and bounded retry, never a forced update.
5. Derived history can be rebuilt from validated ledger files; the reverse is not authoritative.

Run `python scripts/validate_repository.py .` to validate the repository.

## Growth policy

Keep `data/trend-history.json` compact. It stores run metadata, event fingerprints, and category observations, not complete run objects. If it exceeds 5 MB, archive older category observations by calendar year while keeping the run ledger immutable.
