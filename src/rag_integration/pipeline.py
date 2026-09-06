"""TASK-P01-FULL-PIPELINE: 管线编排。

manifest 驱动：探测 → 路由 → 解析 → 质量门 → chunk → JSONL 落盘（仓库外）
+ manifest parse_status 回写。JSONL 每行一个模型的 to_json()。
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from . import parse_doc, parse_docx, parse_pdf, parse_xlsx
from .chunking import make_chunks
from .models import (DocumentElement, IssueCode, ParseRun, ParseStatus,
                     QualityIssue, RouteId, Severity)
from .probe import probe
from .quality import check
from .routing import decide

DATA_ROOT = Path("/home/zjlab/Documents/build_LLMs/NLP_course_hf/RAG/Data")
CORPUS = DATA_ROOT / "x100研制 - 副本"
OUT_DIR = DATA_ROOT / "derived" / "p01"
FILES = {"elements": "elements.jsonl", "chunks": "chunks.jsonl",
         "runs": "runs.jsonl", "issues": "issues.jsonl"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_one(root: Path, source_id: str, rel_path: str,
              prev_stats: dict | None) -> dict:
    """单文件全流程。返回 {run, elements, chunks, issues}（不落盘）。"""
    path = root / rel_path
    pr = probe(path)
    route, reason = decide(pr)
    run = ParseRun(source_id=source_id, parser_name="-", parser_version="-",
                   route=route, route_reason=reason, started_at=_now(),
                   status=ParseStatus.IN_PROGRESS)
    issues: list[QualityIssue] = []
    elements: list[DocumentElement] = []
    xlsx_stats = None
    try:
        if route is RouteId.R9:
            raise RuntimeError(f"unsupported: {reason}")
        if route in (RouteId.R1, RouteId.R2, RouteId.R3):
            elements, _ = parse_pdf.parse_pdf(
                path, source_id, route, reason, pr.page_types)
        elif route in (RouteId.R4, RouteId.R5):
            elements = parse_docx.parse_docx(path, source_id, route, reason)
        elif route is RouteId.R6:
            elements = parse_doc.parse_doc(path, source_id, reason)
        elif route in (RouteId.R7, RouteId.R8):
            elements, xlsx_stats = parse_xlsx.parse_xlsx(
                path, source_id, route, reason)
        elif route is RouteId.R10:
            raise RuntimeError("R10 ppt not enabled (no ppt in corpus)")
        run.parser_name = elements[0].provenance.parser_name if elements else "-"
        run.parser_version = elements[0].provenance.parser_version if elements else "-"
        qr = check(elements, source_id, run.run_id, route,
                   xlsx_stats=xlsx_stats, prev_stats=prev_stats)
        issues.extend(qr.issues)
        run.status = qr.status
        run.stats = qr.stats
    except Exception as e:  # 解析器异常 → FAILED（附原始错误，不含正文）
        run.status = ParseStatus.FAILED
        issues.append(QualityIssue(
            source_id=source_id, run_id=run.run_id, code=IssueCode.PARSE_ERROR,
            severity=Severity.BLOCKING,
            message=f"{type(e).__name__}: {str(e)[:150]}"))
    run.finished_at = _now()
    run.element_count = len(elements)
    chunks = (make_chunks(elements, source_id)
              if run.status is ParseStatus.DONE else [])
    return {"run": run, "elements": elements, "chunks": chunks,
            "issues": issues}


def _load_prev_stats(runs_path: Path) -> dict[str, dict]:
    prev: dict[str, dict] = {}
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                prev[r["source_id"]] = r.get("stats") or {}
    return prev


def run_all(manifest_csv: Path, out_dir: Path = OUT_DIR,
            corpus: Path = CORPUS) -> dict:
    """全量解析 + JSONL 落盘 + manifest parse_status 回写。返回汇总。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_path = out_dir / FILES["runs"]
    prev = _load_prev_stats(runs_path)
    rows = list(csv.DictReader(open(manifest_csv, encoding="utf-8")))
    summary = {"total": len(rows), "status": {}, "route": {}, "failed": [],
               "review": [], "elements": 0, "chunks": 0, "issues": 0}
    # runs 追加（保留历史供漂移比对）；elements/chunks/issues 重写（反映最新全量）
    handles = {k: open(out_dir / f, "a" if k == "runs" else "w",
                       encoding="utf-8")
               for k, f in FILES.items()}
    try:
        for row in rows:
            sid, rel = row["source_id"], row["relative_path"]
            res = parse_one(corpus, sid, rel, prev.get(sid))
            run, els, chunks, issues = (res["run"], res["elements"],
                                        res["chunks"], res["issues"])
            handles["runs"].write(run.to_json() + "\n")
            for e in els:
                handles["elements"].write(e.to_json() + "\n")
            for c in chunks:
                handles["chunks"].write(c.to_json() + "\n")
            for i in issues:
                handles["issues"].write(i.to_json() + "\n")
            row["parse_status"] = run.status.value
            summary["status"][run.status.value] = \
                summary["status"].get(run.status.value, 0) + 1
            summary["route"][run.route.value] = \
                summary["route"].get(run.route.value, 0) + 1
            summary["elements"] += len(els)
            summary["chunks"] += len(chunks)
            summary["issues"] += len(issues)
            if run.status is ParseStatus.FAILED:
                summary["failed"].append(sid)
            elif run.status is ParseStatus.PENDING_REVIEW:
                summary["review"].append(sid)
            print(f"{sid} {run.route.value} {run.status.value} "
                  f"els={len(els)} chunks={len(chunks)}", flush=True)
    finally:
        for h in handles.values():
            h.close()
    with open(manifest_csv, "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return summary
