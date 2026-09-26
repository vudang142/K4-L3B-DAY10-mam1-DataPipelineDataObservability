from __future__ import annotations

from datetime import datetime, timezone

from core.config import load_settings
from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report
from evaluation.metrics import evaluate_pipeline
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corruption -> Evaluate -> Repair -> Compare flow."""
    settings = load_settings()
    print("=== CORRUPTION FLOW ===")

    # Step 1: Load baseline clean data
    print("1. Loading baseline data...")
    import pandas as pd
    baseline_df = read_json(settings.paths.clean_json)
    df_baseline = pd.DataFrame(baseline_df)
    print(f"   Baseline rows: {len(df_baseline)}")

    # Step 2: Create corrupted data
    print("2. Creating corrupted data...")
    df_corrupted = corrupt_clean_dataframe(df_baseline.copy(), settings.paths.corruption_log)
    print(f"   Corrupted rows: {len(df_corrupted)}")

    # Step 3: Save corrupted artifacts
    print("3. Saving corrupted artifacts...")
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    print(f"   Saved: {settings.paths.corrupted_clean_json}")

    # Step 4: Build corrupted index and evaluate
    print("4. Evaluating corrupted data...")
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    # Run quality checks on corrupted
    print("5. Quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    print(f"   Corrupted quality: {'PASS' if corrupted_quality['success'] else 'FAIL'}")

    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.corrupted_quality_report)
    print(f"   Corrupted freshness: is_fresh={corrupted_freshness['is_fresh']}")

    # Evaluate corrupted
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"   Corrupted hit rate: {corrupted_bundle.summary['retrieval_hit_rate']:.2%}")
    print(f"   Corrupted mean F1: {corrupted_bundle.summary['mean_token_f1']:.2%}")

    # Step 6: Repair from raw source
    print("6. Repairing from raw source...")
    records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(timezone.utc)
    df_repaired = build_clean_dataframe(records, run_date)
    print(f"   Repaired rows: {len(df_repaired)}")

    # Save repaired artifacts
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)

    # Step 7: Build repaired index and evaluate
    print("7. Evaluating repaired data...")
    index_repaired = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # Run quality checks on repaired
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    print(f"   Repaired quality: {'PASS' if repaired_quality['success'] else 'FAIL'}")

    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.freshness_report)
    print(f"   Repaired freshness: is_fresh={repaired_freshness['is_fresh']}")

    # Evaluate repaired
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"   Repaired hit rate: {repaired_bundle.summary['retrieval_hit_rate']:.2%}")
    print(f"   Repaired mean F1: {repaired_bundle.summary['mean_token_f1']:.2%}")

    # Load baseline metrics
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # Step 8: Generate comparison report
    print("8. Generating comparison report...")
    baseline_metrics['quality_success'] = True
    baseline_metrics['is_fresh'] = True
    baseline_metrics['stale_rows'] = 0

    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"   Report: {settings.paths.comparison_report}")

    print("\n=== CORRUPTION FLOW COMPLETE ===")
    print(f"Comparison report: {settings.paths.comparison_report}")


if __name__ == "__main__":
    main()
