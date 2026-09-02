"""TASK-P00-004 测试: 问题池建池与校验."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "eval" / "questions"))

from scripts.validate_question_pool import validate  # noqa: E402


def _make_manifest(tmp_path, ids):
    p = tmp_path / "m.csv"
    p.write_text("source_id\n" + "".join(f"{i}\n" for i in ids), encoding="utf-8")
    return p


def test_real_pool_validates():
    r = validate(Path("eval/questions/question_pool.csv"), Path("data_manifest.csv"))
    assert r["problems"] == [], r["problems"]
    assert r["stats"]["total"] >= 30


def test_unknown_source_id_fails(tmp_path):
    bad = tmp_path / "bad.csv"
    fields = ["question_id", "question", "task_type", "business_context",
              "related_source_ids", "evidence_locations", "answerable",
              "requires_multiple_sources", "version_or_time_constraint",
              "status_constraint", "required_claims", "forbidden_claims",
              "value_score", "difficulty", "generation_method", "review_status"]
    row = ["Q-999", "q?", "parameter_lookup", "ctx", "SRC-NOPE", "somewhere",
           "answerable", "False", "", "", "claim", "fb", "1", "easy",
           "profile_anchor", "machine_draft"]
    with bad.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fields)
        w.writerow(row)
    r = validate(bad, _make_manifest(tmp_path, ["SRC-OK"]))
    assert any("不在 manifest" in p for p in r["problems"])


def test_user_confirmed_rejected(tmp_path):
    bad = tmp_path / "bad2.csv"
    fields = ["question_id"] + ["f"] * 14  # 简化: 只验证该单条规则触达
    # 用与真实池同构的最小行, 但 review_status=user_confirmed
    row = {"question_id": "Q-998", "question": "q", "task_type": "parameter_lookup",
           "business_context": "c", "related_source_ids": "SRC-OK",
           "evidence_locations": "loc", "answerable": "answerable",
           "requires_multiple_sources": "False", "version_or_time_constraint": "",
           "status_constraint": "", "required_claims": "c1", "forbidden_claims": "f1",
           "value_score": "1", "difficulty": "easy", "generation_method": "x",
           "review_status": "user_confirmed"}
    with bad.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)
    r = validate(bad, _make_manifest(tmp_path, ["SRC-OK"]))
    assert any("user_confirmed" in p for p in r["problems"])
