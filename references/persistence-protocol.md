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

## Publication request handoff

The scheduled task must submit a complete request rather than writing canonical paths on `main`.

1. Build `run.json` and `report.html` locally and validate them against this protocol.
2. Add `publication-request/run.json`, `publication-request/report.html`, and
   `publication-request/mode.txt` to one Git commit based on current `main`.
   Set `mode.txt` to exactly `publish` (or `dry-run` for a harmless validation).
3. Create a new `publication-requests/<name>` branch at that commit. The branch
   creation triggers `.github/workflows/publish-trend-run.yml`. Git data tools
   can create both blobs, one tree, one commit, and then the branch. Never use a
   sequence of Contents API writes to canonical paths on `main`.
4. If Git data operations are unavailable, prepare the same complete request
   through another branch or workflow-dispatch handoff. If no complete handoff
   is possible, return the proposed artifacts and report that publication did
   not occur.

The request branch is staging only. It is not part of the canonical ledger.

## Publication gate

The publication workflow has `contents: write` and serializes all requests
through one concurrency group. It reads the request at the triggering commit,
checks out fresh `main`, and runs `scripts/publish_run.py`. The publisher
validates the schema, canonical category coverage, unique occurrence and paths,
event linkage, and report linkage. It refuses overwrites, materializes both
files locally, and runs repository validation. The workflow then commits both
paths once, re-fetches `main` immediately before pushing, and uses a normal
non-force push. If `main` advanced, it fails; rebuild and resubmit the
request after checking idempotency against the new ledger.

`validate.yml` remains strict and read-only. GitHub does not automatically
trigger a second workflow from a `GITHUB_TOKEN` push, so the publication
workflow itself runs the same repository validator before and after push.

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
6. return the single publication commit SHA, request branch commit SHA, and
   workflow URL and result.

The scheduled task does not update a global history index or longitudinal HTML visual.

