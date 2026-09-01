#!/usr/bin/env python3
"""Validate the Technology Trends ledger and its derived artifacts."""

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
    require(parsed.scheme in {"http", "https"} and bool(parsed.netloc), f"{location}: unsafe or invalid URL")


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
    require(isinstance(findings, list) and 1 <= len(findings) <= 5, f"{where}: findings must contain 1-5 items")
    require(run.get("methodology", {}).get("finding_count") == len(findings), f"{where}: finding_count mismatch")

    finding_ids: set[str] = set()
    event_keys: set[str] = set()
    expected_ranks = list(range(1, len(findings) + 1))
    require([item.get("rank") for item in findings] == expected_ranks, f"{where}: finding ranks must be consecutive")
    for index, finding in enumerate(findings):
        location = f"{where}: findings[{index}]"
        finding_id = finding.get("finding_id")
        event_key = finding.get("event_key")
        require(isinstance(finding_id, str) and finding_id, f"{location}: missing finding_id")
        require(isinstance(event_key, str) and event_key, f"{location}: missing event_key")
        require(finding_id not in finding_ids, f"{location}: duplicate finding_id")
        require(event_key not in event_keys, f"{location}: duplicate event_key within run")
        finding_ids.add(finding_id)
        event_keys.add(event_key)
        finding_categories = finding.get("category_ids")
        require(isinstance(finding_categories, list) and bool(finding_categories), f"{location}: category_ids must be nonempty")
        require(set(finding_categories) <= category_ids, f"{location}: unknown category_id")
        sources = finding.get("source_links")
        require(isinstance(sources, list) and bool(sources), f"{location}: source_links must be nonempty")
        for source_index, source in enumerate(sources):
            safe_url(source.get("url", ""), f"{location}: source_links[{source_index}]")

    assessments = run.get("category_assessments")
    require(isinstance(assessments, list) and len(assessments) == len(category_ids), f"{where}: assessments must cover every category once")
    assessment_ids = [item.get("category_id") for item in assessments]
    require(set(assessment_ids) == category_ids and len(set(assessment_ids)) == len(assessment_ids), f"{where}: category coverage mismatch")
    for index, assessment in enumerate(assessments):
        location = f"{where}: category_assessments[{index}]"
        direction = assessment.get("direction")
        evidence = assessment.get("evidence")
        require(direction in {"up", "down", "flat", "unknown"}, f"{location}: invalid direction")
        require(isinstance(evidence, list), f"{location}: evidence must be a list")
        if direction == "unknown":
            require(not evidence and assessment.get("velocity_score") == 0, f"{location}: unknown requires empty evidence and zero velocity")
        else:
            require(bool(evidence), f"{location}: {direction} requires evidence")
        for evidence_index, item in enumerate(evidence):
            evidence_location = f"{location}: evidence[{evidence_index}]"
            if item.get("finding_id") is not None:
                require(item["finding_id"] in finding_ids, f"{evidence_location}: unknown finding_id")
            safe_url(item.get("source_url", ""), evidence_location)

    report_path = run.get("report_path", "")
    require(report_path.startswith("reports/") and (root / report_path).is_file(), f"{where}: report_path does not resolve")
    return run


def validate_repository(root: Path) -> None:
    for schema_path in sorted((root / "schemas").glob("*.json")):
        load_json(schema_path)

    registry = load_json(root / "data/category-registry.json")
    categories = registry.get("categories")
    require(isinstance(categories, list) and len(categories) == 8, "category registry must contain exactly eight categories")
    category_ids = {item.get("category_id") for item in categories}
    require(None not in category_ids and len(category_ids) == 8, "category registry contains missing or duplicate IDs")

    run_paths = sorted((root / "data/runs").glob("*/*/*.json"))
    require(bool(run_paths), "ledger must contain at least one immutable run")
    runs = [validate_run(root, path, category_ids) for path in run_paths]
    run_by_id = {run["run_id"]: run for run in runs}
    require(len(run_by_id) == len(runs), "duplicate run_id in ledger")
    scheduled_values = [run["scheduled_for"] for run in runs]
    require(len(set(scheduled_values)) == len(scheduled_values), "duplicate scheduled_for in ledger")

    history = load_json(root / "data/trend-history.json")
    require(history.get("schema_version") == "1.0", "history: unsupported schema_version")
    require(history.get("record_type") == "technology_trend_history_index", "history: wrong record_type")
    indexed_runs = history.get("runs")
    require(isinstance(indexed_runs, list), "history: runs must be a list")
    indexed_ids = [item.get("run_id") for item in indexed_runs]
    require(set(indexed_ids) == set(run_by_id) and len(indexed_ids) == len(run_by_id), "history: run index must exactly match ledger")
    for entry in indexed_runs:
        run = run_by_id[entry["run_id"]]
        require(entry.get("scheduled_for") == run["scheduled_for"], f"history: scheduled_for mismatch for {entry['run_id']}")
        require(entry.get("run_record_path") == next(path.relative_to(root).as_posix() for path in run_paths if path.stem == entry["run_id"]), f"history: run path mismatch for {entry['run_id']}")
        require(entry.get("report_path") == run["report_path"], f"history: report path mismatch for {entry['run_id']}")
        require(entry.get("finding_count") == len(run["findings"]), f"history: finding_count mismatch for {entry['run_id']}")

    latest = max(runs, key=lambda item: item["scheduled_for"])["run_id"]
    require(history.get("latest_successful_run_id") == latest, "history: latest_successful_run_id mismatch")

    observations = history.get("category_observations")
    require(isinstance(observations, list), "history: category_observations must be a list")
    expected_observations = {(run["run_id"], category_id) for run in runs for category_id in category_ids}
    actual_observations = {(item.get("run_id"), item.get("category_id")) for item in observations}
    require(actual_observations == expected_observations and len(observations) == len(expected_observations), "history: category observations must cover every run/category once")
    for item in observations:
        require((root / item.get("report_path", "")).is_file(), "history: observation report_path does not resolve")

    all_findings = {finding["finding_id"] for run in runs for finding in run["findings"]}
    events = history.get("finding_events")
    require(isinstance(events, list), "history: finding_events must be a list")
    event_keys = [item.get("event_key") for item in events]
    require(len(set(event_keys)) == len(event_keys), "history: duplicate event_key")
    for item in events:
        require(item.get("latest_finding_id") in all_findings, f"history: unknown latest_finding_id for {item.get('event_key')}")
        require(item.get("first_seen_run_id") in run_by_id and item.get("last_seen_run_id") in run_by_id, f"history: invalid event run link for {item.get('event_key')}")
        for url in item.get("source_urls", []):
            safe_url(url, f"history: {item.get('event_key')}")

    visual_path = root / "visuals/trend-velocity-history.html"
    require(visual_path.is_file(), "missing history visual")
    visual = visual_path.read_text(encoding="utf-8")
    for run_id in run_by_id:
        require(run_id in visual, f"visual: missing {run_id}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        validate_repository(root)
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"VALIDATION PASSED: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
