from __future__ import annotations

from datetime import datetime, timezone

from core.config import load_settings
from core.utils import read_json
from ingestion.crossref import load_raw_records, fetch_source_records
from ingestion.cleaning import build_clean_dataframe
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Baseline pipeline end-to-end."""
    settings = load_settings()
    print("=== PHASE 1: BASELINE PIPELINE ===")

    # Step 1: Load/fetch raw records
    print("1. Loading raw records...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"   Loaded {len(records)} records")

    # Step 2: Clean data
    print("2. Cleaning data...")
    run_date = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, run_date)
    print(f"   Cleaned {len(df)} rows")

    # Step 3: Save clean artifacts
    print("3. Saving clean artifacts...")
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    df.to_csv(settings.paths.clean_csv, index=False)
    print(f"   Saved: {settings.paths.clean_json}")
    print(f"   Saved: {settings.paths.clean_csv}")

    # Step 4: Build ChromaDB index
    print("4. Building ChromaDB index...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"   Collection: {index.collection_name}")
    print(f"   Documents: {len(index.documents)}")

    # Step 5: Build evaluation test set
    print("5. Building evaluation test set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
        print(f"   Generated {len(test_set)} test questions")
    else:
        test_data = read_json(settings.paths.eval_testset)
        print(f"   Loaded {len(test_data)} test questions from cache")

    # Step 6: Run quality checks
    print("6. Running quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")
    print(f"   Quality check: {'PASS' if quality['success'] else 'FAIL'}")

    # Step 7: Run freshness report
    print("7. Running freshness report...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"   Is fresh: {freshness['is_fresh']}")
    print(f"   Stale rows: {freshness['stale_rows']}/{freshness['total_rows']}")

    # Step 8: Evaluate pipeline
    print("8. Evaluating baseline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"   Retrieval hit rate: {bundle.summary['retrieval_hit_rate']:.2%}")
    print(f"   Mean token F1: {bundle.summary['mean_token_f1']:.2%}")
    print(f"   Judge accuracy: {bundle.summary['judge_accuracy']:.2%}")
    print(f"   Mean judge score: {bundle.summary['mean_judge_score']:.2f}")

    # Step 9: Generate report
    print("9. Generating phase 1 report...")
    source_summary = {
        "total_records": len(records),
        "cleaned_records": len(df),
        "collection_name": index.collection_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"   Report: {settings.paths.baseline_report}")

    print("\n=== PHASE 1 COMPLETE ===")
    print(f"Baseline metrics saved to: {settings.paths.baseline_metrics}")
    print(f"Phase 1 report: {settings.paths.baseline_report}")


if __name__ == "__main__":
    main()
