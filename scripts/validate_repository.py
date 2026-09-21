#!/usr/bin/env python3
"""Validate the Technology Trends immutable ledger.

Canonical state is the set of immutable run records under data/runs/.
Legacy history and visual projections are intentionally not validation dependencies.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


RUN_ID_RE = re.compile(r"^technology-trends-(\d{4}-\d{2}-\d{2})$")


class ValidationError(Exception):
    pass


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def safe_url(value: str, location: str) -> None:
    parsed = urlparse(value)
    require(
        parsed.scheme in {"http", "https"} and bool(parsed.netloc),
        f"{location}: unsafe or invalid URL",
    )


def validate_run(root: Path, path: Path, category_ids: set[str]) -> dict:
    run = load_json(path)
    where = path.relative_to(root).as_posix()

    require(run.get("schema_version") == "1.0", f"{where}: unsupported schema_version")
    require(run.get("record_type") == "technology_trend_run", f"{where}: wrong record_type")
    require(run.get("status") == "success", f"{where}: only successful ledger records are permitted")

    run_id = run.get("run_id", "")
    match = RUN_ID_RE.fullmatch(run_id)
    require(bool(match), f"{where}: invalid run_id")
    require(path.stem == run_id, f"{where}: filename must match run_id")
    require(path.parent.name == match.group(1), f"{where}: date directory must match run_id")
    require(path.parent.parent.name == match.group(1)[:4], f"{where}: year directory must match run_id")

    findings = run.get("findings")
    require(
        isinstance(findings, list) and 1 <= len(findings) <= 5,
        f"{where}: findings must contain 1-5 items",
    )
    require(
        run.get("methodology", {}).get("finding_count") == len(findings),
        f"{where}: finding_count mismatch",
    )

    finding_ids: set[str] = set()
    event_keys: set[str] = set()
    expected_ranks = list(range(1, len(findings) + 1))
    require(
        [item.get("rank") for item in findings] == expected_ranks,
        f"{where}: finding ranks must be consecutive",
    )

    for index, finding in enumerate(findings):
        location = f"{where}: findings[{index}]"
        finding_id = finding.get("finding_id")
        event_key = finding.get("event_key")
        require(isinstance(finding_id, str) and finding_id, f"{location}: missing finding_id")
        require(isinstance(event_key, str) and event_key, f"{location}: missing event_key")
        require(finding_id not in finding_ids, f"{location}: duplicate finding_id within run")
        require(event_key not in event_keys, f"{location}: duplicate event_key within run")
        finding_ids.add(finding_id)
        event_keys.add(event_key)

        finding_categories = finding.get("category_ids")
        require(
            isinstance(finding_categories, list) and bool(finding_categories),
            f"{location}: category_ids must be nonempty",
        )
        require(set(finding_categories) <= category_ids, f"{location}: unknown category_id")

        sources = finding.get("source_links")
        require(
            isinstance(sources, list) and bool(sources),
            f"{location}: source_links must be nonempty",
        )
        for source_index, source in enumerate(sources):
            safe_url(source.get("url", ""), f"{location}: source_links[{source_index}]")

    assessments = run.get("category_assessments")
    require(
        isinstance(assessments, list) and len(assessments) == len(category_ids),
        f"{where}: assessments must cover every category once",
    )
    assessment_ids = [item.get("category_id") for item in assessments]
    require(
        set(assessment_ids) == category_ids and len(set(assessment_ids)) == len(assessment_ids),
        f"{where}: category coverage mismatch",
    )

    for index, assessment in enumerate(assessments):
        location = f"{where}: category_assessments[{index}]"
        direction = assessment.get("direction")
        evidence = assessment.get("evidence")
        require(direction in {"up", "down", "flat", "unknown"}, f"{location}: invalid direction")
        require(isinstance(evidence, list), f"{location}: evidence must be a list")

        if direction == "unknown":
            require(
                not evidence and assessment.get("velocity_score") == 0,
                f"{location}: unknown requires empty evidence and zero velocity",
            )
        else:
            require(bool(evidence), f"{location}: {direction} requires evidence")

        for evidence_index, item in enumerate(evidence):
            evidence_location = f"{location}: evidence[{evidence_index}]"
            if item.get("finding_id") is not None:
                require(
                    item["finding_id"] in finding_ids,
                    f"{evidence_location}: unknown finding_id",
                )
            safe_url(item.get("source_url", ""), evidence_location)

    report_path = run.get("report_path", "")
    require(
        report_path.startswith("reports/") and (root / report_path).is_file(),
        f"{where}: report_path does not resolve",
    )
    return run


def validate_repository(root: Path) -> tuple[int, str]:
    # Schema files must remain parseable, but only run.schema.json is canonical
    # to the scheduled-run persistence boundary.
    for schema_path in sorted((root / "schemas").glob("*.json")):
        load_json(schema_path)

    registry = load_json(root / "data/category-registry.json")
    categories = registry.get("categories")
    require(
        isinstance(categories, list) and len(categories) == 8,
        "category registry must contain exactly eight categories",
    )
    category_ids = {item.get("category_id") for item in categories}
    require(
        None not in category_ids and len(category_ids) == 8,
        "category registry contains missing or duplicate IDs",
    )

    run_paths = sorted((root / "data/runs").glob("*/*/*.json"))
    require(bool(run_paths), "ledger must contain at least one immutable run")

    runs = [validate_run(root, path, category_ids) for path in run_paths]
    runs = sorted(runs, key=lambda item: item["scheduled_for"])

    run_ids = [run["run_id"] for run in runs]
    require(len(set(run_ids)) == len(run_ids), "duplicate run_id in ledger")

    scheduled_values = [run["scheduled_for"] for run in runs]
    require(
        len(set(scheduled_values)) == len(scheduled_values),
        "duplicate scheduled_for in ledger",
    )

    all_finding_ids: dict[str, str] = {}
    latest_by_event: dict[str, str] = {}

    for run in runs:
        for finding in run["findings"]:
            finding_id = finding["finding_id"]
            event_key = finding["event_key"]
            material_update_from = finding.get("material_update_from")

            require(
                finding_id not in all_finding_ids,
                f"duplicate finding_id across ledger: {finding_id}",
            )

            if event_key in latest_by_event:
                require(
                    material_update_from == latest_by_event[event_key],
                    (
                        f"{run['run_id']}: repeated event_key {event_key} must link "
                        f"material_update_from to {latest_by_event[event_key]}"
                    ),
                )
            else:
                require(
                    material_update_from in {None, ""},
                    (
                        f"{run['run_id']}: first observation of event_key {event_key} "
                        "must not set material_update_from"
                    ),
                )

            all_finding_ids[finding_id] = event_key
            latest_by_event[event_key] = finding_id

    latest = runs[-1]
    return len(runs), latest["run_id"]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        count, latest = validate_repository(root)
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"VALIDATION PASSED: {root}")
    print(f"Immutable runs: {count}")
    print(f"Latest run: {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
