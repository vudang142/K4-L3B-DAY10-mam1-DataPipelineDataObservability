from __future__ import annotations

import json
from datetime import datetime, timedelta

import pandas as pd

from core.utils import ensure_parent


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 dang data corruption.

    Corruption scenarios:
    1. Drop latest records (mất 20% bản ghi mới nhất)
    2. Blank summary (xóa rỗng tóm tắt)
    3. Inject noise (chèn ký tự rác vào tóm tắt)
    4. Truncate title (cắt ngắn tiêu đề < 8 ký tự)
    5. Stale date (lùi ngày xuất bản về quá khứ)
    6. Duplicate rows (nhân bản dữ liệu)
    """
    import random

    corruption_log = {
        "timestamp": datetime.now().isoformat(),
        "original_rows": len(df),
        "corruptions": [],
    }

    df_corrupted = df.copy()

    # 1. Drop latest records (mất 20% bản ghi mới nhất)
    n_drop = max(1, len(df_corrupted) // 5)  # 20%
    if len(df_corrupted) > 0:
        df_corrupted = df_corrupted.iloc[n_drop:].reset_index(drop=True)
        corruption_log["corruptions"].append({
            "type": "drop_latest_records",
            "description": f"Dropped {n_drop} latest records (20%)",
            "count": n_drop,
        })

    if len(df_corrupted) == 0:
        # Restore if too aggressive
        df_corrupted = df.copy()
        corruption_log["corruptions"].append({
            "type": "drop_latest_records",
            "description": "Restored - too aggressive, keeping all",
            "count": 0,
        })

    # 2. Blank summary (xóa rỗng tóm tắt ở 2-3 dong)
    n_blank = min(3, len(df_corrupted))
    blank_indices = random.sample(range(len(df_corrupted)), n_blank)
    for idx in blank_indices:
        df_corrupted.at[idx, "summary"] = ""
        df_corrupted.at[idx, "summary_chars"] = 0
    corruption_log["corruptions"].append({
        "type": "blank_summary",
        "description": f"Blanked {n_blank} summaries",
        "count": n_blank,
        "indices": blank_indices,
    })

    # 3. Inject noise (chèn ký tự rác vào tóm tắt)
    noise_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~\n\r\t"
    n_noise = min(2, len(df_corrupted))
    noise_indices = random.sample(range(len(df_corrupted)), n_noise)
    for idx in noise_indices:
        original = df_corrupted.at[idx, "summary"]
        noise = "".join(random.choices(noise_chars, k=20))
        df_corrupted.at[idx, "summary"] = noise + original[:100]
        df_corrupted.at[idx, "summary_chars"] = len(df_corrupted.at[idx, "summary"])
    corruption_log["corruptions"].append({
        "type": "inject_noise",
        "description": f"Injected noise into {n_noise} summaries",
        "count": n_noise,
        "indices": noise_indices,
    })

    # 4. Truncate title (cắt ngắn tiêu đề < 8 ký tự)
    n_truncate = min(2, len(df_corrupted))
    truncate_indices = random.sample(range(len(df_corrupted)), n_truncate)
    for idx in truncate_indices:
        original = df_corrupted.at[idx, "title"]
        df_corrupted.at[idx, "title"] = original[:5]  # Truncate to 5 chars
    corruption_log["corruptions"].append({
        "type": "truncate_title",
        "description": f"Truncated {n_truncate} titles to < 5 chars",
        "count": n_truncate,
        "indices": truncate_indices,
    })

    # 5. Stale date (lùi ngày xuất bản về quá khứ)
    n_stale = min(3, len(df_corrupted))
    stale_indices = random.sample(range(len(df_corrupted)), n_stale)
    for idx in stale_indices:
        try:
            original_date = datetime.strptime(df_corrupted.at[idx, "published"], "%Y-%m-%d")
            new_date = original_date - timedelta(days=random.randint(365, 730))  # 1-2 years back
            df_corrupted.at[idx, "published"] = new_date.strftime("%Y-%m-%d")
            df_corrupted.at[idx, "age_days"] = (datetime.now() - new_date).days
        except (ValueError, TypeError):
            pass
    corruption_log["corruptions"].append({
        "type": "stale_date",
        "description": f"Made {n_stale} dates stale (1-2 years back)",
        "count": n_stale,
        "indices": stale_indices,
    })

    # 6. Duplicate rows (nhân bản dữ liệu)
    n_dup = min(2, len(df_corrupted))
    dup_indices = random.sample(range(len(df_corrupted)), n_dup)
    dup_rows = df_corrupted.iloc[dup_indices].copy()
    for i, idx in enumerate(dup_indices):
        new_row = dup_rows.iloc[i].copy()
        new_row["paper_id"] = new_row["paper_id"] + "_dup"
        df_corrupted = pd.concat([df_corrupted, new_row.to_frame().T], ignore_index=True)
    corruption_log["corruptions"].append({
        "type": "duplicate_rows",
        "description": f"Added {n_dup} duplicate rows",
        "count": n_dup,
        "indices": dup_indices,
    })

    # Rebuild text_for_embedding for corrupted rows
    df_corrupted = _rebuild_embedding_text(df_corrupted)

    corruption_log["final_rows"] = len(df_corrupted)
    corruption_log["duplicates"] = len(df_corrupted) - (len(df) - n_drop)

    # Save corruption log
    ensure_parent(output_log_path)
    output_log_path.write_text(
        json.dumps(corruption_log, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return df_corrupted


def _rebuild_embedding_text(df: pd.DataFrame) -> pd.DataFrame:
    """Rebuild text_for_embedding sau khi corrupt."""
    for idx in df.index:
        title = df.at[idx, "title"]
        summary = df.at[idx, "summary"]
        authors = df.at[idx, "authors_joined"]
        categories = df.at[idx, "categories_joined"]
        published = df.at[idx, "published"]

        text = (
            f"Title: {title}\n\n"
            f"Authors: {authors}\n\n"
            f"Published: {published}\n\n"
            f"Categories: {categories}\n\n"
            f"Abstract: {summary}"
        )
        df.at[idx, "text_for_embedding"] = text

    return df
