#!/usr/bin/env python3
"""Validate and materialize one immutable run and its report together.

The caller owns the Git commit. This script never writes a branch or overwrites
an existing canonical artifact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

from validate_repository import ValidationError, load_json, validate_repository


RUN_ID_RE = re.compile(r"^technology-trends-(\d{4}-\d{2}-\d{2})$")
RUN_PATH_RE = re.compile(
    r"^data/runs/(\d{4})/(\d{4}-\d{2}-\d{2})/"
    r"technology-trends-\2\.json$"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def canonical_paths(run: dict) -> tuple[str, str]:
    run_id = run["run_id"]
    match = RUN_ID_RE.fullmatch(run_id)
    require(match is not None, "invalid run_id")
    day = match.group(1)
    try:
        datetime.fromisoformat(day)
        scheduled = datetime.fromisoformat(run["scheduled_for"])
        require(scheduled.tzinfo is not None, "scheduled_for needs a timezone offset")
        local = scheduled.astimezone(ZoneInfo("America/Los_Angeles"))
        require(local.date().isoformat() == day, "run_id date differs from scheduled_for")
        require(
            scheduled.utcoffset() == local.utcoffset(),
            "scheduled_for offset differs from America/Los_Angeles",
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"invalid run date or scheduled_for: {exc}") from exc

    run_path = f"data/runs/{day[:4]}/{day}/{run_id}.json"
    report_path = f"reports/{day[:4]}/{day}/technology-trend-update-{run_id}.html"
    require(run["report_path"] == report_path, "report_path is not canonical for run_id")
    return run_path, report_path


def validate_proposal(root: Path, run: dict, html: str) -> tuple[str, str]:
    schema = load_json(root / "schemas/run.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(run),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValidationError(f"run schema: {location}: {error.message}")

    run_path, report_path = canonical_paths(run)
    registry = load_json(root / "data/category-registry.json")
    categories = {
        item["category_id"]: item["category_name"] for item in registry["categories"]
    }
    require(len(categories) == len(registry["categories"]), "duplicate registry category")
    assessments = run["category_assessments"]
    require(
        {item["category_id"] for item in assessments} == set(categories),
        "category coverage differs from registry",
    )
    for item in assessments:
        require(
            item["category_name"] == categories[item["category_id"]],
            f"category name mismatch: {item['category_id']}",
        )

    require(bool(html.strip()), "report HTML is empty")
    require(
        "<html" in html.lower() and "</html>" in html.lower(),
        "report HTML must contain an html element",
    )
    require(not (root / run_path).exists(), f"immutable run path exists: {run_path}")
    require(not (root / report_path).exists(), f"immutable report path exists: {report_path}")

    ledger_dir = root / "data/runs"
    for path in sorted(ledger_dir.rglob("*.json")):
        relative = path.relative_to(root).as_posix()
        require(RUN_PATH_RE.fullmatch(relative) is not None, f"unexpected run path: {relative}")
        previous = load_json(path)
        require(previous.get("run_id") != run["run_id"], "run_id already exists")
        require(
            previous.get("scheduled_for") != run["scheduled_for"],
            "scheduled_for already exists",
        )
    return run_path, report_path


def publish_local(
    root: Path, run_source: Path, report_source: Path, dry_run: bool
) -> tuple[str, str, int]:
    run = load_json(run_source)
    try:
        html = report_source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"cannot read report HTML: {exc}") from exc

    run_path, report_path = validate_proposal(root, run, html)
    run_target, report_target = root / run_path, root / report_path
    created: list[Path] = []
    try:
        for target, content in (
            (run_target, run_source.read_bytes()),
            (report_target, html.encode("utf-8")),
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(content)
            created.append(target)

        count, _ = validate_repository(root)
        return run_path, report_path, count
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"cannot materialize publication: {exc}") from exc
    finally:
        if dry_run or sys.exc_info()[0] is not None:
            for target in reversed(created):
                target.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--run-json", required=True, type=Path)
    parser.add_argument("--report-html", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        run_path, report_path, count = publish_local(
            root, args.run_json, args.report_html, args.dry_run
        )
        if args.github_output is not None:
            with args.github_output.open("a", encoding="utf-8") as output:
                output.write(f"run_path={run_path}\nreport_path={report_path}\n")
        print(
            json.dumps(
                {
                    "result": "validated" if args.dry_run else "materialized",
                    "run_path": run_path,
                    "report_path": report_path,
                    "ledger_runs_after_publication": count,
                }
            )
        )
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"PUBLICATION REJECTED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
