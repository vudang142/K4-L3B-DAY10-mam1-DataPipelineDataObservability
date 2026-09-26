# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Vũ Hải Đăng |
| MSSV | 2A202602821 |
| Khóa/Lớp | K4 / Lớp B |
| Tên nhóm | mam1 |
| Vai trò chính | Nhóm trưởng / Full-stack |
| Repository | https://github.com/vudang142/K4-L3B-DAY10-mam1-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

*(Nhóm 1 thành viên - hoàn thành toàn bộ pipeline)*

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw Ingestion | `src/ingestion/crossref.py` | Crossref API / Local JSON | `crossref_records.json` (24 records) | Hoàn thành |
| Data Cleaning | `src/ingestion/cleaning.py` | Raw records | `papers_clean.json` (24 dòng) | Hoàn thành |
| Quality Checks | `src/observability/quality.py` | Clean DataFrame | Quality + Freshness reports | Hoàn thành |
| Evaluation Test Set | `src/evaluation/testset.py` | Clean DataFrame | `test_set.json` (10 câu) | Hoàn thành |
| Corruption Scenarios | `src/ingestion/corruption.py` | Clean DataFrame | Corrupted data + log | Hoàn thành |
| Pipeline Orchestration | `src/pipelines/phase1.py`, `corruption_flow.py` | Tất cả modules | Metrics + Reports | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Hỗ trợ debug] | [Tên] | [Kết quả] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement Crossref API fetch | `crossref.py` | `crossref_records.json` (24 records) | Chạy fetch, verify 24 bài báo |
| Implement data cleaning | `cleaning.py` | `papers_clean.json` (24 dòng) | Chạy clean, verify len(df)=24 |
| Implement quality checks | `quality.py` | `quality_check_baseline.json` | `success=True` |
| Implement freshness report | `quality.py` | `freshness_report.json` | `is_fresh=True`, stale=0/24 |
| Implement test set generator | `testset.py` | `test_set.json` (10 câu) | 4 question types |
| Implement 6 corruption scenarios | `corruption.py` | `corruption_log.json` | 6 scenarios logged |
| Implement baseline pipeline | `phase1.py` | `baseline_metrics.json` | Metrics file created |
| Implement corruption flow | `corruption_flow.py` | `corruption_report.md` | 3-state comparison |

**Một output cụ thể:** `data/quality/quality_check_baseline.json` - Chứa kết quả 5 quality expectations, tất cả đều PASS.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần xử lý dữ liệu từ Crossref API, làm sạch, đánh giá chất lượng, và mô phỏng/restore khi có corruption.

### Cách triển khai

**Crossref Ingestion:**
- Fetch với retry logic cho 429/503 errors
- Fallback sang local snapshot khi network fail
- Parse payload với JATS XML tag removal

**Data Cleaning:**
- Normalize text với whitespace handling
- Build `text_for_embedding` 5-part format
- Calculate `age_days` từ published date
- Deduplicate theo paper_id (DOI)

**Quality Checks:**
- 5 expectations: row count, null checks, uniqueness, summary length
- Freshness: is_fresh=False nếu >25% papers có age_days > 180

**Corruption Scenarios:**
- 6 scenarios: drop, blank, noise, truncate, stale, duplicate
- Random selection để đảm bảo diversity

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Crossref API response hoặc local JSON |
| Output | Clean DataFrame, quality reports, metrics |
| Module phụ thuộc | `core.config`, `core.utils` |
| Module sử dụng output | `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | API 429/503, missing fields, empty strings |

### Cách xác minh

```bash
python -c "from ingestion.crossref import fetch_source_records; records = fetch_source_records(settings); print(len(records))"
python -c "from observability.quality import run_data_quality_checks; result = run_data_quality_checks(df, settings, 'baseline'); print(result['success'])"
```

- **Kết quả mong đợi:** `True` cho cả hai
- **Kết quả thực tế:** [Mô tả]
- **Artifact/log:** `data/quality/quality_check_baseline.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Great Expectations 1.x API phức tạp, Batch/Validator objects có interface không tương thích
- **Các phương án đã cân nhắc:**
  1. Dùng GX native API với Checkpoint/Validator
  2. Pandas-based implementation đơn giản
  3. Mock GX results để pass requirement
- **Phương án đã chọn:** Pandas-based implementation
- **Lý do:** Đơn giản, hoạt động ổn định, không phụ thuộc version-specific API
- **Bằng chứng quyết định phù hợp:** Quality checks chạy thành công với success=True

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `AttributeError: 'EphemeralDataContext' object has no attribute 'validators'`   
- **Lệnh hoặc bước tái hiện:** Chạy `run_data_quality_checks()` với GX 1.x
- **Nguyên nhân gốc:** GX 1.x API khác với documentation, ephemeral context không có validators attribute
- **Cách xử lý:** Thay vì dùng GX objects phức tạp, implement pandas-based checks tương đương
- **Cách xác minh sau khi sửa:** Chạy lại, output `success=True`
- **Điều học được:** GX 1.x API thay đổi nhanh, documentation có thể không cập nhật. Luôn test trước khi commit.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API → raw JSON → parsed records → cleaned DataFrame → text_for_embedding → MiniLM embeddings → ChromaDB collection

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Test set chứa câu hỏi + ground_truth + doc_ids. Retrieval hit rate đo có trả về đúng doc hay không. Token F1 đo overlap giữa answer và ground truth.

3. **Quality checks khác freshness monitoring ở điểm nào?**
   Quality checks đo schema integrity (null, unique, length). Freshness đo temporal aspect (age of data).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo so sánh metrics chỉ phản ánh data change, không phải test set change.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Metrics trở về baseline (retrieval_hit_rate, mean_token_f1). Quality checks PASS. Freshness restored.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 70.00% | 0.00% | 70.00% | Corruption làm hit rate về 0 |
| `mean_token_f1` | 27.40% | 1.52% | 27.40% | F1 giảm 95% sau corruption |
| `judge_accuracy` | 20.00% | 0.00% | 20.00% | Judge không đánh giá đúng nào |
| `mean_judge_score` | 1.80 | 1.10 | 1.80 | Score giảm rõ rệt |
| Quality checks | PASS | FAIL | PASS | Quality gates phát hiện corruption |
| Freshness status | Fresh | Fresh | Fresh | Data vẫn còn mới |

### Kết luận từ số liệu

1. **Data corruption** → **summary blank + truncate title** → **embedding quality giảm** → **retrieval_hit_rate giảm từ 70.00% xuống 0.00%**

2. **Repair từ raw** → **quality restored** → **metrics trở về baseline** → **retrieval_hit_rate phục hồi 70.00%**

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Blank summary và truncate title ảnh hưởng rõ nhất vì trực tiếp thay đổi content dùng để tạo embeddings. Khi summary bị xóa rỗng hoặc title bị cắt ngắn, text_for_embedding trở nên vô nghĩa → vector embedding sai → retrieval không tìm được đúng document.

**Kết quả nào khác với kỳ vọng?**
Judge accuracy baseline chỉ đạt 20% (1.80/5 điểm) thay vì kỳ vọng cao hơn. Nguyên nhân: mock LLM không có khả năng reasoning thực sự, chỉ trả về response cố định.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data quality gate là critical checkpoint** - Phát hiện corruption trước khi ảnh hưởng users
2. **Repair phải từ raw source** - Clean data đã qua transformations có thể không đáng tin cậy
3. **GX 1.x API thay đổi nhanh** - Documentation không always sync với code

### Nếu có thêm thời gian

Thêm deterministic corruption với random seed để reproducibility. Implement auto-repair trigger khi quality check fail.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Hải Đăng
**Ngày xác nhận:** 2026-09-26
