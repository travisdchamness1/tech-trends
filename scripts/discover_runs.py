#!/usr/bin/env python3
"""Discover Technology Trends immutable run records from the repository layout.

This command computes an ephemeral view of the ledger. It does not write or
maintain a persistent run index.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover(root: Path) -> list[dict]:
    records = []
    for path in sorted((root / "data/runs").glob("*/*/*.json")):
        run = read_json(path)
        records.append(
            {
                "run_id": run["run_id"],
                "scheduled_for": run["scheduled_for"],
                "observed_at": run["observed_at"],
                "window_start": run["window_start"],
                "window_end": run["window_end"],
                "status": run["status"],
                "path": path.relative_to(root).as_posix(),
                "report_path": run["report_path"],
                "finding_count": len(run["findings"]),
            }
        )
    return sorted(records, key=lambda item: item["scheduled_for"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--latest", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    records = discover(root)
    if not records:
        raise SystemExit("No immutable runs found")

    payload = records[-1] if args.latest else {
        "count": len(records),
        "latest_run_id": records[-1]["run_id"],
        "runs": records,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
