from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.utils import ensure_parent


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set 10 cau hoi tu cleaned dataframe.

    Question types:
    - summary: hoi ve noi dung tom tat
    - authors: hoi ve tac gia
    - date: hoi ve ngay xuat ban
    - categories: hoi ve the loai

    Each question includes:
    - id
    - question_type
    - question
    - ground_truth
    - ground_truth_doc_ids
    """
    test_set = []
    question_id = 1

    # Check minimum documents
    if len(df) < 3:
        raise ValueError(f"Need at least 3 documents, got {len(df)}")

    # Sample papers for different question types
    papers = df.to_dict("records")

    # Generate summary questions (3 questions)
    for _, paper in enumerate(papers[:3]):
        test_set.append({
            "id": f"q{question_id}",
            "question_type": "summary",
            "question": f"What is the main contribution or abstract of the paper titled '{paper['title']}'?",
            "ground_truth": paper["summary"],
            "ground_truth_doc_ids": [paper["paper_id"]],
        })
        question_id += 1

    # Generate author questions (3 questions)
    for _, paper in enumerate(papers[:3]):
        test_set.append({
            "id": f"q{question_id}",
            "question_type": "authors",
            "question": f"Who are the authors of papers published in '{paper['published']}'?",
            "ground_truth": paper["authors_joined"],
            "ground_truth_doc_ids": [paper["paper_id"]],
        })
        question_id += 1

    # Generate date questions (2 questions)
    for _, paper in enumerate(papers[:2]):
        test_set.append({
            "id": f"q{question_id}",
            "question_type": "date",
            "question": f"When was the paper titled '{paper['title']}' published?",
            "ground_truth": paper["published"],
            "ground_truth_doc_ids": [paper["paper_id"]],
        })
        question_id += 1

    # Generate categories questions (2 questions)
    for _, paper in enumerate(papers[:2]):
        test_set.append({
            "id": f"q{question_id}",
            "question_type": "categories",
            "question": f"What are the research categories of the paper titled '{paper['title']}'?",
            "ground_truth": paper["categories_joined"],
            "ground_truth_doc_ids": [paper["paper_id"]],
        })
        question_id += 1

    # Save to file
    ensure_parent(output_path)
    output_path.write_text(
        json.dumps(test_set, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return test_set
