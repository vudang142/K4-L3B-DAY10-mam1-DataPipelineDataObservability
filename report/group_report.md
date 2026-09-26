# Group Report — Day 10: Data Pipeline & Data Observability

> Dùng mẫu này cho báo cáo chung của nhóm 3–5 thành viên.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 / Lớp B              |
| Tên nhóm         | mam1                    |
| Repository         | https://github.com/vudang142/K4-L3B-DAY10-mam1-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Vũ Hải Đăng | 2A202602821 | Nhóm trưởng / Data Ingestion & Cleaning Owner | `crossref.py`, `cleaning.py`, `quality.py`, `testset.py`, `reporting.py`, `corruption.py`, `phase1.py`, `corruption_flow.py` |

*(Nhóm 1 thành viên - hoàn thành toàn bộ pipeline)*

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline từ Crossref API đến so sánh 3 trạng thái (baseline, corrupted, repaired). Baseline pipeline tạo ra 2 raw artifacts (`crossref_response.json`, `crossref_records.json`), 2 clean artifacts (`papers_clean.csv`, `papers_clean.json`), ChromaDB index với 24 documents, và evaluation test set 10 câu hỏi.

Corruption scenarios ảnh hưởng rõ nhất đến data quality là **blank summary** (xóa rỗng tóm tắt) và **truncate title** (cắt ngắn tiêu đề < 8 ký tự), khiến retrieval hit rate giảm đáng kể do embedding quality suy giảm.

Repair từ raw source đã phục hồi thành công các metrics về mức baseline. Blocker còn lại là thời gian chạy Ragas evaluation (cần LLM thực sự).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API / Local Snapshot (fallback khi offline)
    -> crossref_response.json (raw API response)
    -> crossref_records.json (parsed raw records)
    -> papers_clean.csv/json (cleaned, deduplicated)
    -> ChromaDB index (papers-baseline collection)
    -> test_set.json (10 câu hỏi: summary, authors, date, categories)
    -> baseline_metrics.json
    -> quality_check_baseline.json + freshness_report.json
    -> corruption (6 scenarios)
    -> corrupted_metrics.json
    -> repair from raw source
    -> repaired_metrics.json
    -> corruption_report.md (so sánh 3 trạng thái)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref API / Local JSON | Fetch, retry 429, parse payload | `data/raw/crossref_records.json` | [Tên 1] |
| Cleaning | Raw records | Normalize, deduplicate, build text_for_embedding, calculate age_days | `data/clean/papers_clean.json` | [Tên 1] |
| Embedding/index | Clean DataFrame | MiniLM-L6-v2 embeddings, ChromaDB persist | `data/chroma/`, `data/embeddings/` | [Tên 2] |
| Evaluation | ChromaDB index, test set | Retrieval hit rate, token F1, judge scoring | `data/results/baseline_metrics.json` | [Tên 2] |
| Observability | Clean DataFrame | GX quality checks (5 expectations), freshness SLA (180 days) | `data/quality/*.json` | [Tên 2] |
| Corruption/repair | Clean DataFrame, raw records | 6 corruption scenarios, repair from raw | `data/results/corruption_log.json` | [Tên 3] |
| Orchestration | Tất cả modules | phase1.py, corruption_flow.py | `data/reports/*.md` | [Tên 3] |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | mock (fallback) |
| `LLM_MODEL` | gemini-2.5-flash |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 |
| Retrieval`top_k` | 4 |
| Freshness threshold | 180 days |
| Random seed | None (random corruption) |

### Lệnh cài đặt

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | [Thành công] | 2026-09-26 | `data/results/baseline_metrics.json` |
| Corruption flow | [Thành công] | 2026-09-26 | `data/results/corrupted_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (https://api.crossref.org/works) |
| Query/filter | query="agentic retrieval augmented generation large language model", from-pub-date: 180 days ago, has-abstract:true |
| Thời điểm lấy dữ liệu | 2026-09-26 |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Fallback sang local snapshot khi API trả 429/503/error |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | str (DOI) | Có | Unique identifier | Drop nếu trống |
| title | str | Có | Tiêu đề paper | Drop nếu trống |
| summary | str | Không | Abstract đã clean JATS tags | Empty string |
| authors | list[str] | Không | Danh sách tên tác giả | Empty list |
| categories | list[str] | Không | Subject tags | Empty list |
| published | str (YYYY-MM-DD) | Có | Ngày xuất bản | Default 2024-01-01 |
| text_for_embedding | str | Có | 5-part text cho embedding | Auto-generated |
| age_days | int | Có | Số ngày từ published đến now | Calculated |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | ------------------------: | -------------------- |
| Loại bỏ records không có title | Completeness | 0 (24/24 có title) | Verify len(df) == 24 |
| Khử trùng lặp theo paper_id | Uniqueness | 0 (không trùng DOI) | expect_column_values_to_be_unique |
| Xóa JATS XML tags trong abstract | Validity | Tất cả | Regex `<[^>]+>` replacement |
| Chuẩn hóa whitespace | Consistency | Tất cả | re.sub(r"\s+", " ", text) |
| Tính age_days từ published date | Freshness | Tất cả | (run_date - published_date).days |

**Cách tạo `text_for_embedding`:**
```
Title: {title}
Authors: {authors_joined}
Published: {published}
Categories: {categories_joined}
Abstract: {summary}
```

**Cách tạo `paper_id`:** Sử dụng DOI trực tiếp từ Crossref (duy nhất, stable).

**Cách tính `age_days`:** `age_days = (run_date - datetime.strptime(published, "%Y-%m-%d")).days`

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 10 |
| Các`question_type` | summary (3), authors (3), date (2), categories (2) |
| Ground-truth document ID | paper_id (DOI) |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection | ChromaDB, collection: papers-baseline |
| Retrieval`top_k` | 4 |
| LLM provider/model | mock (FakeListChatModel) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

**Giải thích:** Test set được giữ nguyên cho baseline, corrupted và repaired để đảm bảo so sánh có ý nghĩa. Nếu dùng test set khác nhau, sự khác biệt về metrics có thể do test set chứ không phải do data change.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/` | Có | 2 files |
| Cleaned dataset | `data/clean/` | Có | CSV + JSON |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness | `data/quality/` | Có | 2 files |
| Baseline report | `data/reports/phase1_report.md` | Có | |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 70.00% | Tỷ lệ câu hỏi trả về đúng document |
| `mean_token_f1` | 27.40% | Token-level F1 giữa answer và ground truth |
| `judge_accuracy` | 20.00% | Tỷ lệ câu trả lời được judge đánh giá correct |
| `mean_judge_score` | 1.80/5 | Điểm trung bình từ judge (1-5) |
| Ragas | N/A | Chưa chạy (cần real LLM) |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| table_row_count | Completeness | 20-30 rows | [PASS/FAIL], actual=[24] | `quality_check_baseline.json` |
| paper_id_not_null | Completeness | 0 nulls | [PASS/FAIL], nulls=0 | `quality_check_baseline.json` |
| title_not_null | Completeness | 0 nulls | [PASS/FAIL], nulls=0 | `quality_check_baseline.json` |
| paper_id_unique | Uniqueness | all unique | [PASS/FAIL], unique=24/24 | `quality_check_baseline.json` |
| summary_length | Validity | >=50 chars | [PASS/FAIL], short=0 | `quality_check_baseline.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean DataFrame (sau cleaning) |
| Timestamp mới nhất | [Ngày mới nhất từ API] |
| Ngưỡng freshness | 180 days |
| Trạng thái baseline | Fresh |
| Lý do | 0 stale rows (tất cả papers published gần đây) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | --------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | df.iloc[n:] (20%) | ~5 records | Row count giảm | retrieval_hit_rate giảm | Rebuild từ raw |
| blank_summary | df.at[i, "summary"] = "" | 2-3 rows | summary_length fail | embedding sai | Rebuild từ raw |
| inject_noise | Thêm ký tự rác vào summary | 2 rows | summary_length > baseline | F1 giảm | Rebuild từ raw |
| truncate_title | title[:5] | 2 rows | title length < threshold | retrieval giảm | Rebuild từ raw |
| stale_date | published -= 1-2 years | 2-3 rows | age_days tăng, stale tăng | freshness fail | Rebuild từ raw |
| duplicate_rows | pd.concat duplicate | 2 rows | Uniqueness fail | retrieval giảm | Rebuild từ raw |

**Corruption log:** `data/results/corruption_log.json` - Có đầy đủ 6 scenarios và số record bị tác động.

**Giải thích repair:** Repair luôn từ `data/raw/crossref_records.json` - bản raw chưa qua cleaning nên đáng tin cậy hơn clean data đã bị corruption.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: |
| `retrieval_hit_rate` | 70.00% | 0.00% | 70.00% | -70.00% | 100% |
| `mean_token_f1` | 27.40% | 1.52% | 27.40% | -25.88% | 100% |
| `judge_accuracy` | 20.00% | 0.00% | 20.00% | -20.00% | 100% |
| `mean_judge_score` | 1.80 | 1.10 | 1.80 | -0.70 | 100% |
| Quality checks pass/fail | PASS | FAIL | PASS | N/A | 100% |
| Freshness status | Fresh | Fresh | Fresh | N/A | 100% |

**Kết luận có quan hệ nhân quả:**

1. **blank_summary + truncate_title** → `summary_length` check FAIL → embedding quality giảm → `retrieval_hit_rate` giảm → Agent trả lời kém chính xác hơn.

2. **Repair từ raw** → quality checks PASS → freshness restored → metrics trở về baseline → Chứng minh data quality gate + repair strategy hoạt động đúng.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** AttributeError khi dùng GX 1.x API với Batch object không có methods như `expect_table_row_count_to_be_between`
- **Nguyên nhân:** GX 1.x API thay đổi, Batch object có interface khác với documentation
- **Cách xử lý:** Chuyển sang pandas-based implementation cho đơn giản và tương thích
- **Cách xác minh:** Chạy lại quality checks, output `quality_check_baseline.json` với success=True

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| LLM mock (không có real LLM) | Judge scoring không đánh giá thực sự | Dùng Gemini/OpenAI API key |
| Ragas evaluation chưa chạy | Thiếu context_precision, faithfulness | Enable RUN_RAGAS=1 |
| Corruption random, không deterministic | Khó reproduce kết quả | Thêm random_seed |

