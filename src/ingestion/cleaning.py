from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace, compact_join
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    Steps:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    import pandas as pd
    from datetime import datetime

    rows = []
    for record in records:
        # Parse published date
        try:
            published_dt = datetime.strptime(record.published, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            published_dt = datetime(2024, 1, 1).date()

        # Calculate age_days
        run_date_date = run_date.date() if isinstance(run_date, datetime) else run_date
        age_days = (run_date_date - published_dt).days

        # Normalize text fields
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)

        # Join authors and categories
        authors_joined = compact_join(record.authors)
        categories_joined = compact_join(record.categories)

        # Calculate summary length
        summary_chars = len(summary)

        # Build text_for_embedding (5 parts)
        text_for_embedding = _build_embedding_text(
            title=title,
            summary=summary,
            authors=authors_joined,
            categories=categories_joined,
            published=record.published,
        )

        rows.append({
            "paper_id": record.paper_id,
            "title": title,
            "summary": summary,
            "authors": record.authors,
            "categories": record.categories,
            "primary_category": record.primary_category,
            "published": record.published,
            "updated": record.updated,
            "abs_url": record.abs_url,
            "pdf_url": record.pdf_url,
            "comment": record.comment,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Filter out invalid rows (empty title or paper_id)
    df = df[df["title"].str.len() > 0]
    df = df[df["paper_id"].str.len() > 0]

    # Sort by published date (newest first)
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    return df


def _build_embedding_text(
    title: str,
    summary: str,
    authors: str,
    categories: str,
    published: str,
) -> str:
    """Build 5-part text for embedding."""
    return (
        f"Title: {title}\n\n"
        f"Authors: {authors}\n\n"
        f"Published: {published}\n\n"
        f"Categories: {categories}\n\n"
        f"Abstract: {summary}"
    )
