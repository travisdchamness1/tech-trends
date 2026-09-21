# Dashboard contract

## Purpose

The Technology Trends dashboard is a read-only projection of the immutable ledger under `data/runs/`.

The dashboard must not depend on `data/trend-history.json`, `schemas/history.schema.json`, or `visuals/trend-velocity-history.html`.

## Discovery

For the public repository `travisdchamness1/tech-trends`, discover run records by enumerating the repository tree for `main` and selecting blobs matching:

```text
data/runs/YYYY/YYYY-MM-DD/technology-trends-YYYY-MM-DD.json
```

The path identifies candidate run records. The JSON contents remain authoritative for:

- `run_id`;
- `scheduled_for`;
- `observed_at`;
- observation window;
- findings;
- event identity;
- material-update linkage;
- category assessments; and
- report path.

Do not persist a second canonical run manifest solely to enumerate runs.

## Browser / ChatGPT Site consumption

A browser-hosted dashboard may use the public GitHub API to enumerate the repository tree and fetch the immutable JSON records.

Recommended read flow:

1. fetch the `main` branch tree recursively;
2. filter paths under `data/runs/` that match the canonical run-path pattern;
3. fetch the run JSON records;
4. sort by `scheduled_for`;
5. derive all views in memory;
6. cache fetched immutable records client-side when useful.

Because immutable run paths are never overwritten, clients may safely cache records by path or blob SHA.

## Derived views

### Latest run

Select the successful record with the greatest `scheduled_for`.

### Category velocity series

For each canonical category, map each run's category assessment to:

- `scheduled_for`;
- `direction`;
- `velocity_score`;
- `confidence`;
- `justification`;
- `report_path`.

### Event history

Group findings by stable `event_key`.

For each event:

- order observations by the containing run's `scheduled_for`;
- require later observations to reference the immediately preceding finding using `material_update_from`;
- expose the newest finding as the current observation.

### Reports

Resolve each run's `report_path` relative to the repository's public content or GitHub Pages/static-hosting base.

## Deterministic tooling

`scripts/discover_runs.py` mirrors the dashboard discovery model for local use and CI.

`scripts/validate_repository.py` validates the canonical ledger independently of any dashboard implementation.

The dashboard must tolerate temporary rendering or network failures without changing canonical repository state.

## Performance

Start by reading immutable run records directly. Introduce optional caches only when measured performance requires them.

Any future cache must be:

- explicitly non-authoritative;
- reproducible from `data/runs/`;
- disposable without data loss; and
- excluded from scheduled-run success criteria.

## Security

The repository is public.

Dashboard implementations must:

- treat ledger text as untrusted display content;
- escape HTML;
- permit only `http://` and `https://` source links;
- avoid embedding credentials or private API tokens; and
- use unauthenticated public GitHub reads unless a future requirement justifies otherwise.
