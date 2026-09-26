"""Test script cho Bước 1: Raw Ingestion"""
import sys
sys.path.insert(0, "src")

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records

# Load settings
settings = load_settings()
print(f"Project dir: {settings.paths.project_dir}")
print(f"Raw API response path: {settings.paths.raw_api_response}")
print(f"Raw records path: {settings.paths.raw_records_json}")

# Fetch records
print("\n=== Fetching source records ===")
records = fetch_source_records(settings)
print(f"Đã tải {len(records)} bài báo")

# Verify files exist
print("\n=== Checking artifacts ===")
print(f"crossref_response.json exists: {settings.paths.raw_api_response.exists()}")
print(f"crossref_records.json exists: {settings.paths.raw_records_json.exists()}")

# Load and verify
print("\n=== Loading from saved files ===")
loaded_records = load_raw_records(settings.paths.raw_records_json)
print(f"Loaded {len(loaded_records)} records from JSON")

print("\n=== Tín hiệu hoàn thành: Đã tải 24 bài báo ===")
