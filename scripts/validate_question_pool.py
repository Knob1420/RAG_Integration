#!/usr/bin/env python3
"""TASK-P00-004: 问题池格式与配额校验.

检查: 字段完整、source_id 可回链 manifest(含 MANIFEST 特殊引用)、枚举合法、
配额达标(总数/各类型/证据位置/多来源/不可回答)。退出码 0/1。
"""

import csv
import sys
from pathlib import Path

POOL_FIELDS = [
    "question_id", "question", "task_type", "business_context",
    "related_source_ids", "evidence_locations", "answerable",
    "requires_multiple_sources", "version_or_time_constraint",
    "status_constraint", "required_claims", "forbidden_claims",
    "value_score", "difficulty", "generation_method", "review_status",
]
TASK_TYPES = {
    "parameter_lookup", "interface_lookup", "test_result_lookup",
    "design_decision_lookup", "meeting_action_lookup", "cross_document_trace",
    "time_or_version_compare", "conflict_detection", "insufficient_evidence",
    "document_discovery",
}
ANSWERABLE = {"answerable", "partially_answerable", "unanswerable"}

# 通过标准配额（TASK-P00-004）
QUOTAS = {
    "total_min": 30,
    "evidence_min": 20,          # 有明确证据位置(含真实 source_id 且位置非空)
    "multi_min": 5,              # requires_multiple_sources
    "unanswerable_min": 3,       # 冲突/资料不足/不可回答
}


def validate(pool_csv: Path, manifest_csv: Path = Path("data_manifest.csv")) -> dict:
    problems = []
    manifest_ids = {r["source_id"] for r in csv.DictReader(manifest_csv.open(encoding="utf-8"))}
    rows = list(csv.DictReader(pool_csv.open(encoding="utf-8")))

    ids = [r.get("question_id", "") for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("question_id 重复")
    for r in rows:
        qid = r.get("question_id", "?")
        for f in POOL_FIELDS:
            if not r.get(f, "").strip():
                problems.append(f"{qid} 字段为空: {f}")
        if r.get("task_type") not in TASK_TYPES:
            problems.append(f"{qid} 非法 task_type")
        if r.get("answerable") not in ANSWERABLE:
            problems.append(f"{qid} 非法 answerable")
        if r.get("requires_multiple_sources") not in ("True", "False"):
            problems.append(f"{qid} requires_multiple_sources 非布尔")
        if r.get("review_status") == "user_confirmed":
            problems.append(f"{qid} 模型生成问题不得自动标记 user_confirmed")
        for sid in r.get("related_source_ids", "").split(";"):
            if sid.strip() and sid.strip() != "MANIFEST" and sid.strip() not in manifest_ids:
                problems.append(f"{qid} source_id 不在 manifest: {sid}")

    n_multi = sum(r["requires_multiple_sources"] == "True" for r in rows)
    n_unans = sum(r["answerable"] in ("partially_answerable", "unanswerable") for r in rows)
    n_evidence = sum(
        bool(any(s.strip() and s.strip() != "MANIFEST" for s in r["related_source_ids"].split(";")))
        and bool(r["evidence_locations"].strip())
        for r in rows
    )
    stats = {
        "total": len(rows),
        "multi_source": n_multi,
        "partial_or_unanswerable": n_unans,
        "with_evidence": n_evidence,
        "by_task_type": {},
        "by_answerable": {},
    }
    for r in rows:
        stats["by_task_type"][r["task_type"]] = stats["by_task_type"].get(r["task_type"], 0) + 1
        stats["by_answerable"][r["answerable"]] = stats["by_answerable"].get(r["answerable"], 0) + 1

    if len(rows) < QUOTAS["total_min"]:
        problems.append(f"总数 {len(rows)} < {QUOTAS['total_min']}")
    if n_evidence < QUOTAS["evidence_min"]:
        problems.append(f"有证据位置问题 {n_evidence} < {QUOTAS['evidence_min']}")
    if n_multi < QUOTAS["multi_min"]:
        problems.append(f"多来源问题 {n_multi} < {QUOTAS['multi_min']}")
    if n_unans < QUOTAS["unanswerable_min"]:
        problems.append(f"部分可答/不可答 {n_unans} < {QUOTAS['unanswerable_min']}")

    return {"stats": stats, "problems": problems}


def main(argv=None) -> int:
    pool = Path(argv[0] if argv else "eval/questions/question_pool.csv")
    r = validate(pool)
    s = r["stats"]
    print(f"总数 {s['total']} | 有证据 {s['with_evidence']} | 多来源 {s['multi_source']} "
          f"| 部分/不可答 {s['partial_or_unanswerable']}")
    print("按类型:", {k: v for k, v in sorted(s["by_task_type"].items())})
    print("按可答性:", s["by_answerable"])
    if r["problems"]:
        print(f"问题 {len(r['problems'])} 项:")
        for p in r["problems"]:
            print("  -", p)
        return 1
    print("校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
