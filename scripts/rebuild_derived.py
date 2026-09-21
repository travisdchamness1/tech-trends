#!/usr/bin/env python3
"""Deprecated compatibility entry point.

The canonical architecture no longer persists a global history index or
regenerates the longitudinal HTML visual after every run. Historical views are
derived directly from immutable records under data/runs/.

This script intentionally performs no writes.
"""

from __future__ import annotations


def main() -> int:
    print(
        "DEPRECATED: no files changed. "
        "Discover runs with scripts/discover_runs.py and build dashboard views "
        "directly from the immutable ledger. See references/dashboard-contract.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
