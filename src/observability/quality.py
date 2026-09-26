from __future__ import annotations

from typing import Any
import json
from datetime import datetime

import pandas as pd

from core.config import Settings
from core.utils import ensure_parent


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks su dung Great Expectations 1.x.

    4 Expectations thiết yếu:
    1. ExpectTableRowCountToBeBetween (row count)
    2. ExpectColumnValuesToNotBeNull (paper_id, title)
    3. ExpectColumnValuesToBeUnique (paper_id)
    4. ExpectColumnValueLengthsToBeBetween (summary length)
    """
    # Use simple pandas-based expectations without complex GX API
    results = []

    # 1. ExpectTableRowCountToBeBetween (expect between 20 and 30 rows)
    row_count = len(df)
    results.append({
        "expectation": "table_row_count",
        "success": bool(20 <= row_count <= 30),
        "details": {"actual": int(row_count)}
    })

    # 2. ExpectColumnValuesToNotBeNull (paper_id)
    paper_id_nulls = int(df["paper_id"].isnull().sum() + (df["paper_id"] == "").sum())
    results.append({
        "expectation": "paper_id_not_null",
        "success": bool(paper_id_nulls == 0),
        "details": {"null_count": paper_id_nulls}
    })

    # 3. ExpectColumnValuesToNotBeNull (title)
    title_nulls = int(df["title"].isnull().sum() + (df["title"] == "").sum())
    results.append({
        "expectation": "title_not_null",
        "success": bool(title_nulls == 0),
        "details": {"null_count": title_nulls}
    })

    # 4. ExpectColumnValuesToBeUnique (paper_id)
    unique_count = int(df["paper_id"].nunique())
    total_count = len(df)
    results.append({
        "expectation": "paper_id_unique",
        "success": bool(unique_count == total_count),
        "details": {"unique": unique_count, "total": int(total_count)}
    })

    # 5. ExpectColumnValueLengthsToBeBetween (summary >= 50 chars)
    short_summaries = int((df["summary"].str.len() < 50).sum()) if "summary" in df.columns else 0
    results.append({
        "expectation": "summary_length",
        "success": bool(short_summaries == 0),
        "details": {"short_count": short_summaries}
    })

    # Determine overall success
    all_success = bool(all(r["success"] for r in results))

    # Save report
    report_data = {
        "report_name": report_name,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "success": all_success,
    }

    report_path = settings.paths.quality_dir / f"quality_check_{report_name}.json"
    ensure_parent(report_path)
    report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return report_data


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report.

    Freshness SLA:
    - Cảnh báo is_fresh=False nếu tỷ lệ bài báo có age_days > 180 vượt quá 25%.
    """
    # Find latest and oldest published date
    df["published_date"] = pd.to_datetime(df["published"], errors="coerce")

    latest_published = df["published_date"].max().strftime("%Y-%m-%d") if pd.notna(df["published_date"].max()) else None
    oldest_published = df["published_date"].min().strftime("%Y-%m-%d") if pd.notna(df["published_date"].min()) else None

    # Count stale rows (age_days > threshold)
    threshold = settings.freshness_threshold_days
    total_rows = len(df)
    stale_rows = len(df[df["age_days"] > threshold])
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0

    # Is fresh if stale ratio <= 25%
    is_fresh = stale_ratio <= 0.25

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": int(stale_rows),
        "total_rows": int(total_rows),
        "stale_ratio": round(stale_ratio, 3),
        "threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    # Save report
    ensure_parent(report_path)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return payload
