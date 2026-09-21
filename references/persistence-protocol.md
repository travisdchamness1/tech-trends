# GitHub persistence protocol

## Authority and idempotency

Immutable run JSON files under `data/runs/` are the historical system of record.

The repository layout is the run index. Do not require or maintain a second canonical run identifier index.

Use the scheduled occurrence timestamp as `scheduled_for`. A retry must reuse the same `run_id` and paths. Before research or persistence:

1. enumerate immutable run records under `data/runs/`;
2. validate the ledger sufficiently to identify the latest successful run;
3. check the expected immutable path for the requested occurrence; and
4. if that `scheduled_for` already succeeded, verify it and stop without adding another run.

Legacy files `data/trend-history.json` and `visuals/trend-velocity-history.html` are non-authoritative and are not part of the scheduled persistence transaction.

## Read phase

1. Read the current `main` branch HEAD.
2. Read `SKILL.md`, this protocol, `data/category-registry.json`, and `schemas/run.schema.json`.
3. Discover immutable run paths directly from `data/runs/`.
4. Read the latest successful immutable run and enough prior findings to enforce stable event identity and material-update linkage.
5. Set `window_start` to the previous successful run's `window_end`. If no valid run exists, use and document an explicit fallback.
6. Set `window_end` to the current observation cutoff.

## Build and validate phase

Build the immutable run JSON and immutable HTML report without writing GitHub state.

Validate:

- exact schema version and required fields;
- one to five material findings;
- one assessment for every canonical category and no extra categories;
- globally unique `finding_id` values;
- unique `run_id` and `scheduled_for` values;
- stable `event_key` reuse only for a material update;
- repeated `event_key` observations link to the prior observation with `material_update_from`;
- nonempty evidence for `up`, `down`, and `flat`; empty evidence for `unknown`;
- safe source URL schemes and escaped HTML;
- run/report linkage; and
- the current occurrence appears exactly once in the immutable ledger.

## Preferred atomic write

When Git data tools are available:

1. create blobs for the immutable run JSON and report;
2. create one tree from the previously read base tree;
3. create one commit whose parent is the previously read `main` HEAD;
4. update `main` to that commit without force; and
5. if the ref update is rejected because `main` changed, discard the proposed ref update, re-read current state, check idempotency, re-merge, and retry at most twice.

Never force-update `main`.

## Contents API fallback

Use only when the scheduled runtime lacks the preferred Git data operations.

1. Create the immutable run JSON if absent.
2. Re-read and verify its exact contents.
3. Create the immutable HTML report if absent.
4. Re-read and verify its exact contents.
5. If either file already exists, verify that it exactly matches the proposed occurrence before continuing.
6. Report partial completion precisely if only one immutable artifact persisted.

A later retry must resume the same `scheduled_for` occurrence instead of creating a new run.

## Derived views

Historical summaries are projections, not persistence dependencies.

- Dashboard clients discover run records directly from the public repository tree.
- Event history and category velocity series are derived from immutable run records at read/build time.
- `scripts/discover_runs.py` provides deterministic local/CI discovery.
- `scripts/validate_repository.py` validates the immutable ledger.
- `references/dashboard-contract.md` defines the dashboard data-consumption contract.
- A GitHub Action validates repository state after pushes and pull requests.

No successful scheduled run may be marked failed solely because a dashboard or legacy derived artifact is stale.

## Recovery

If a legacy derived artifact is invalid, ignore it for canonical operations. Reconstruct any needed view only from validated immutable run files.

If any immutable ledger file is invalid or the ledger cannot be enumerated completely, stop and request human review. Never reconstruct missing facts from memory.

## Verification

After persistence:

1. re-read the final branch HEAD or committed immutable files;
2. confirm the immutable run path exists exactly once;
3. confirm the committed `scheduled_for` matches the requested occurrence;
4. confirm the report path resolves;
5. run repository validation when available; and
6. return every resulting commit SHA and URL.

The scheduled task does not update a global history index or longitudinal HTML visual.
