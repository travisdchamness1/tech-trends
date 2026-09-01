#!/usr/bin/env python3
"""Rebuild compact history and longitudinal HTML from immutable run records."""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    run_paths = sorted((root / "data/runs").glob("*/*/*.json"))
    if not run_paths:
        raise SystemExit("No immutable runs found")
    runs = sorted((read_json(path) for path in run_paths), key=lambda run: run["scheduled_for"])
    old_history_path = root / "data/trend-history.json"
    old_history = read_json(old_history_path) if old_history_path.exists() else {}
    # The scheduled runtime is configured for America/Los_Angeles. Using the
    # host's configured local zone also works on Windows installations that do
    # not bundle the IANA tzdata package.
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    path_by_id = {path.stem: path.relative_to(root).as_posix() for path in run_paths}
    run_index = [{
        "run_id": run["run_id"], "scheduled_for": run["scheduled_for"], "observed_at": run["observed_at"],
        "window_start": run["window_start"], "window_end": run["window_end"], "status": run["status"],
        "run_record_path": path_by_id[run["run_id"]], "report_path": run["report_path"],
        "finding_count": len(run["findings"])
    } for run in runs]

    events: dict[str, dict] = {}
    observations = []
    for run in runs:
        for finding in run["findings"]:
            key = finding["event_key"]
            urls = [source["url"] for source in finding["source_links"]]
            if key not in events:
                events[key] = {
                    "event_key": key, "latest_finding_id": finding["finding_id"],
                    "first_seen_run_id": run["run_id"], "last_seen_run_id": run["run_id"],
                    "source_urls": urls,
                }
            else:
                event = events[key]
                event["latest_finding_id"] = finding["finding_id"]
                event["last_seen_run_id"] = run["run_id"]
                event["source_urls"] = list(dict.fromkeys(event["source_urls"] + urls))
        for assessment in run["category_assessments"]:
            observations.append({
                "run_id": run["run_id"], "scheduled_for": run["scheduled_for"],
                "category_id": assessment["category_id"], "direction": assessment["direction"],
                "velocity_score": assessment["velocity_score"], "confidence": assessment["confidence"],
                "justification": assessment["justification"], "evidence_count": len(assessment["evidence"]),
                "report_path": run["report_path"],
            })

    history = {
        "schema_version": "1.0", "record_type": "technology_trend_history_index",
        "timezone": "America/Los_Angeles", "ledger_authority": "data/runs",
        "created_at": old_history.get("created_at", now), "updated_at": now,
        "latest_successful_run_id": runs[-1]["run_id"], "runs": run_index,
        "finding_events": [events[key] for key in sorted(events)],
        "category_observations": observations,
    }
    write_text(old_history_path, json.dumps(history, indent=2, ensure_ascii=False) + "\n")

    registry = read_json(root / "data/category-registry.json")
    names = {item["category_id"]: item["category_name"] for item in registry["categories"]}
    head = "".join(f"<th>{html.escape(run['scheduled_for'][:10])}</th>" for run in runs)
    rows = []
    by_key = {(item["run_id"], item["category_id"]): item for item in observations}
    for category_id, category_name in names.items():
        cells = []
        for run in runs:
            item = by_key[(run["run_id"], category_id)]
            direction = item["direction"]
            score = item["velocity_score"]
            label = "Unknown" if direction == "unknown" else f"{direction.title()} {score:+d}"
            title = html.escape(f"Confidence {item['confidence']:.2f}. {item['justification']}", quote=True)
            report = html.escape("../" + item["report_path"], quote=True)
            cells.append(f'<td class="{direction}" title="{title}"><a href="{report}">{html.escape(label)}</a></td>')
        rows.append(f"<tr><th>{html.escape(category_name)}</th>{''.join(cells)}</tr>")
    run_markers = " ".join(html.escape(run["run_id"]) for run in runs)
    visual = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Technology Trends — Velocity History</title><style>body{{font:15px/1.45 system-ui,sans-serif;max-width:1200px;margin:36px auto;padding:0 18px;color:#172033}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border:1px solid #d8dfeb;text-align:left}}td.up{{background:#dff6e7}}td.flat{{background:#eef1f5}}td.down{{background:#ffe3e0}}td.unknown{{background:#fff4ce}}a{{color:inherit}}.markers{{display:none}}</style></head><body><h1>Technology Trend Velocity History</h1><p>As of {html.escape(now)}. Unknown means insufficient qualifying evidence; it does not mean flat. Hover a cell for confidence and justification; select it for the dated report.</p><table><thead><tr><th>Category</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table><p class="markers">{run_markers}</p></body></html>'''
    write_text(root / "visuals/trend-velocity-history.html", visual + "\n")
    print(f"Rebuilt history and visual from {len(runs)} run(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
