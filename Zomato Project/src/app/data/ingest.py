"""Orchestrate dataset download, transform, and SQLite load."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_database_path, get_hf_dataset_id
from app.data.repository import RestaurantRepository
from app.data.transform import load_raw_dataframe, summarize_dataframe, transform_dataframe

logger = logging.getLogger(__name__)


def run_ingestion(
    *,
    dataset_id: Optional[str] = None,
    db_path: Optional[Path] = None,
    run_samples: bool = True,
) -> Dict[str, Any]:
    """
    Full Phase 1 pipeline: load HF data → transform → persist → report.

    Returns a report dict suitable for logging or JSON export.
    """
    dataset_id = dataset_id or get_hf_dataset_id()
    db_path = db_path or get_database_path()
    repo = RestaurantRepository(db_path)

    logger.info("Loading dataset %s", dataset_id)
    raw_df = load_raw_dataframe(dataset_id)
    raw_count = len(raw_df)

    logger.info("Transforming %s raw rows", raw_count)
    canonical_df = transform_dataframe(raw_df)
    dedupe_removed = int(canonical_df.attrs.get("dedupe_removed", 0))
    transform_summary = summarize_dataframe(canonical_df)

    if canonical_df.empty:
        raise RuntimeError(
            "No rows remained after transformation. Check dataset schema and mapping."
        )

    logger.info("Writing %s rows to %s", len(canonical_df), db_path)
    inserted = repo.replace_all(canonical_df)
    db_stats = repo.get_stats()

    report: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "database_path": str(db_path),
        "raw_row_count": raw_count,
        "canonical_row_count": inserted,
        "dedupe_removed": dedupe_removed,
        "transform_summary": transform_summary,
        "database_stats": db_stats,
    }

    if run_samples:
        report["sample_queries"] = repo.run_sample_queries()

    logger.info("Ingestion complete: %s", json.dumps(report, indent=2, default=str))
    return report
