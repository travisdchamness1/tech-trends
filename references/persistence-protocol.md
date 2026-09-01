# GitHub persistence protocol

## Authority and idempotency

Immutable run JSON files are the system of record. The history index and visual are derived artifacts.

Use the scheduled occurrence timestamp as `scheduled_for`. A retry must reuse the same `run_id` and paths. Before research or persistence, check `data/trend-history.json` and the expected immutable path. If that occurrence already succeeded, verify it and stop without adding another run.

## Read phase

1. Read the `main` branch HEAD commit and tree.
2. Read and validate the history index, category registry, latest successful immutable run, and all event fingerprints needed for duplicate detection.
3. Set `window_start` to the previous successful run's `window_end`. If no valid run exists, use and document an explicit fallback.
4. Set `window_end` to the current observation cutoff.

## Build and validate phase

Build the immutable run JSON, immutable HTML report, complete replacement history index, and complete replacement visual without writing GitHub state.

Validate:

- exact schema version and required fields;
- one to five material findings;
- one assessment for every canonical category and no extra categories;
- unique `finding_id`, `event_key`, `run_id`, and `scheduled_for` values where required;
- nonempty evidence for `up`, `down`, and `flat`; empty evidence for `unknown`;
- safe source URL schemes and escaped HTML;
- run/report/index linkage;
- the current occurrence appears exactly once.

## Preferred atomic write

When Git data tools are available:

1. Create blobs for all changed files.
2. Create one tree from the previously read base tree.
3. Create one commit whose parent is the previously read `main` HEAD.
4. Update `main` to that commit without force.
5. If the ref update is rejected because `main` changed, discard the proposed ref update, re-read current state, check idempotency, re-merge, and retry at most twice.

Never force-update `main`.

## Fallback two-phase write

Use only when the scheduled runtime lacks the preferred Git data operations:

1. Create the immutable run JSON and report if absent.
2. Re-read state. If either exists, verify exact content before continuing.
3. Update the history index as the commit point using its exact current blob SHA.
4. Update the derived visual.
5. On a later retry, resume the same `scheduled_for` occurrence instead of creating a new run.

The task must report partial completion precisely. A visual lag does not invalidate a committed ledger run, but must be repaired before the next new run.

## Recovery

If the derived history is invalid, preserve its exact bytes under `data/recovery/` and rebuild it only from validated immutable run files. If any ledger file is invalid or the set cannot be enumerated completely, stop and request human review. Never reconstruct missing facts from memory.

## Verification

Re-read the final branch HEAD and committed tree. Confirm the immutable paths exist, the history contains the occurrence once, the report link resolves, and the visual contains the new run ID. Return the commit SHA and URL on success.
