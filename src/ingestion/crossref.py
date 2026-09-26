from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    import re

    records = []
    items = payload.get("message", {}).get("items", [])

    for item in items:
        # Extract DOI (paper_id)
        doi = item.get("DOI", "")
        if not doi:
            continue

        # Extract title
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            continue

        # Extract abstract (remove JATS XML tags)
        abstract = item.get("abstract", "")
        if abstract:
            # Remove JATS XML tags like <jats:p>, </jats:p>, etc.
            abstract = re.sub(r"<[^>]+>", "", abstract)
            abstract = re.sub(r"\s+", " ", abstract).strip()

        # Extract authors
        authors_data = item.get("author", [])
        authors = []
        for author in authors_data:
            given = author.get("given", "")
            family = author.get("family", "")
            if family:
                name = f"{given} {family}".strip() if given else family
                authors.append(name)

        # Extract categories
        subjects = item.get("subject", [])
        categories = subjects if subjects else []
        primary_category = categories[0] if categories else ""

        # Extract dates
        published_date = item.get("published", {})
        published = _parse_date_from_parts(published_date)

        updated_date = item.get("created", {})
        updated = _parse_date_from_datetime(updated_date)

        # Extract URLs
        url = item.get("URL", "")
        abs_url = f"https://doi.org/{doi}" if doi else ""

        # Extract comment (container-title as proxy)
        container_title = item.get("container-title", [])
        comment = container_title[0] if container_title else ""

        record = PaperRecord(
            paper_id=doi,
            title=title.strip(),
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=url,
            comment=comment,
        )
        records.append(record)

    return records


def _parse_date_from_parts(date_dict: dict) -> str:
    """Parse date from {'date-parts': [[year, month, day]]} format."""
    date_parts = date_dict.get("date-parts", [])
    if date_parts and date_parts[0]:
        parts = date_parts[0]
        year = parts[0] if len(parts) > 0 else 2024
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    return "2024-01-01"


def _parse_date_from_datetime(date_dict: dict) -> str:
    """Parse date from {'date-time': 'YYYY-MM-DDTHH:MM:SSZ'} format."""
    date_time = date_dict.get("date-time", "")
    if date_time:
        # Extract YYYY-MM-DD from ISO format
        return date_time[:10]
    return "2024-01-01"


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records.

    Fallback ve local snapshot neu API that bai.
    """
    import requests

    # Try to fetch from Crossref API
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    api_url = "https://api.crossref.org/works"

    try:
        response = requests.get(api_url, params=params, timeout=30)

        if response.status_code == 200:
            payload = response.json()
        elif response.status_code == 429:
            # Rate limited - use local fallback
            print(f"API rate limited (429), falling back to local snapshot")
            payload = _load_local_snapshot(settings.paths.raw_api_response)
        else:
            print(f"API error ({response.status_code}), falling back to local snapshot")
            payload = _load_local_snapshot(settings.paths.raw_api_response)
    except requests.RequestException as e:
        print(f"Network error: {e}, falling back to local snapshot")
        payload = _load_local_snapshot(settings.paths.raw_api_response)

    # Save raw response
    from core.utils import write_json
    write_json(settings.paths.raw_api_response, payload)

    # Parse to records
    records = parse_crossref_payload(payload)

    # Save records
    records_data = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, records_data)

    return records


def _load_local_snapshot(path) -> dict:
    """Load local Crossref response snapshot."""
    from core.utils import read_json
    if path.exists():
        return read_json(path)
    raise FileNotFoundError(f"No local snapshot found at {path}")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    from core.utils import read_json

    data = read_json(path)
    records = []

    for item in data:
        record = PaperRecord(
            paper_id=item["paper_id"],
            title=item["title"],
            summary=item["summary"],
            authors=item["authors"],
            categories=item["categories"],
            primary_category=item["primary_category"],
            published=item["published"],
            updated=item["updated"],
            abs_url=item["abs_url"],
            pdf_url=item["pdf_url"],
            comment=item["comment"],
        )
        records.append(record)

    return records
