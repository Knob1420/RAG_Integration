#!/usr/bin/env python3
"""TASK-P01-FULL-PIPELINE: 全量解析入口。

用法（RAG env）: python scripts/run_pipeline.py
派生数据落仓库外 Data/derived/p01/；manifest parse_status 回写。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_integration.pipeline import run_all  # noqa: E402

if __name__ == "__main__":
    manifest = Path(__file__).resolve().parent.parent / "data_manifest.csv"
    summary = run_all(manifest)
    print("\n==== 汇总 ====")
    for k in ("total", "status", "route", "elements", "chunks", "issues",
              "failed", "review"):
        print(f"{k}: {summary[k]}")
