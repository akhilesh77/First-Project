"""CLI entry point: python -m scripts.ingest"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.data.ingest import run_ingestion  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Zomato Hugging Face dataset into SQLite (Phase 1)."
    )
    parser.add_argument(
        "--dataset",
        help="Hugging Face dataset id (default: env HF_DATASET or ManikaSaini/...)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="SQLite database file path (default: from DATABASE_URL)",
    )
    parser.add_argument(
        "--no-samples",
        action="store_true",
        help="Skip running sample verification queries",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write JSON ingestion report to this path",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        report = run_ingestion(
            dataset_id=args.dataset,
            db_path=args.db,
            run_samples=not args.no_samples,
        )
    except Exception as exc:
        logging.error("Ingestion failed: %s", exc)
        return 1

    print(json.dumps(report, indent=2, default=str))

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"Report written to {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
