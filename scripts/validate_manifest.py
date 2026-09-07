#!/usr/bin/env python3
"""TASK-P00-003A: 验证 data_manifest.csv 是否满足数据治理与后续解析要求.

只读 CSV，不触文件系统、不解析正文、不调用外部 API。
用法: python scripts/validate_manifest.py [data_manifest.csv]
退出码: 0 通过 / 1 存在问题
"""

import csv
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "source_id", "file_name", "relative_path", "file_extension",
    "file_size", "checksum_sha256", "filesystem_mtime",
]
# 允许 UNKNOWN 的字段（不得伪造值）
UNKNOWN_OK_FIELDS = {
    "title", "document_internal_id", "document_status",
    "security_level", "external_model_allowed",
}
# P01-004 规则预填字段（产出经 docs/reports/P01-metadata-prefill.md 审计，允许非 UNKNOWN 值）
PREFILLED_FIELDS = {
    "document_type", "subsystem", "document_version",
    "effective_version", "doc_family",
}
SUPPORTED_EXTS = {".pdf", ".doc", ".docx", ".xlsx"}
# 已开放人工确认流程的字段及其合法值（2026-09-01 用户定级：内部可用/YES）
CONFIRMED_ENUMS = {
    "security_level": {"UNKNOWN", "公开", "内部可用", "受限", "禁止外发"},
    "external_model_allowed": {"UNKNOWN", "YES", "NO"},
}
PARSE_STATUS_ENUM = {"NOT_STARTED", "PENDING", "IN_PROGRESS", "DONE",
                     "PENDING_OCR", "PENDING_REVIEW", "FAILED"}
SRC_ID_RE = re.compile(r"^SRC-[0-9A-F]{10}$")
MTIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|api[_-]?key\s*[:=]|password\s*[:=]|Bearer\s+\S+)", re.I)


def validate(csv_path: Path) -> dict:
    problems, warnings = [], []
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], [r for r in rows[1:] if r]

    # 表头
    if len(header) != len(set(header)):
        problems.append("表头存在重复列名")
    for col in REQUIRED_FIELDS:
        if col not in header:
            problems.append(f"缺少必需字段: {col}")
    idx = {c: i for i, c in enumerate(header)}
    for col in (UNKNOWN_OK_FIELDS | PREFILLED_FIELDS) - set(header):
        problems.append(f"缺少需显式标 UNKNOWN 的字段: {col}")

    dup_headers = [i for i, r in enumerate(data, 2) if r and r[0] == "source_id"]
    if dup_headers:
        problems.append(f"存在重复表头行: 行号 {dup_headers}")

    ids, checksums = [], []
    for ln, r in enumerate(data, 2):
        cells = dict(zip(header, r))
        if not any(c.strip() for c in r):
            problems.append(f"第{ln}行为空行")
            continue
        if len(r) != len(header):
            problems.append(f"第{ln}行列数不一致: {len(r)} != {len(header)}")
            continue
        if not cells.get("source_id", "").strip():
            problems.append(f"第{ln}行 source_id 为空")
        if cells.get("file_extension", "").lower() not in SUPPORTED_EXTS:
            problems.append(f"第{ln}行扩展名不受支持: {cells.get('file_extension')}")
        rp = cells.get("relative_path", "")
        if rp.startswith("/") or ":\\" in rp:
            problems.append(f"第{ln}行疑似绝对路径: {rp}")
        if not MTIME_RE.match(cells.get("filesystem_mtime", "")):
            problems.append(f"第{ln}行 mtime 格式不统一: {cells.get('filesystem_mtime')}")
        if cells.get("parse_status") not in PARSE_STATUS_ENUM:
            problems.append(f"第{ln}行 parse_status 非法枚举: {cells.get('parse_status')}")
        for col in (UNKNOWN_OK_FIELDS & set(header)) - PREFILLED_FIELDS:
            v = cells.get(col, "")
            if col in CONFIRMED_ENUMS:
                if v not in CONFIRMED_ENUMS[col]:
                    problems.append(f"第{ln}行 {col} 非法取值: {v!r}")
            elif v.strip() and v != "UNKNOWN":
                problems.append(f"第{ln}行 {col} 未确认却填了值: {v!r}")
        for c in r:
            if SECRET_RE.search(c):
                problems.append(f"第{ln}行疑似泄漏凭证")
                break
        ids.append(cells.get("source_id", ""))
        if cells.get("checksum_sha256"):
            checksums.append(cells["checksum_sha256"])

    dup_ids = len(ids) - len(set(ids))
    if dup_ids:
        problems.append(f"source_id 重复 {dup_ids} 个")

    # duplicate_of 引用完整性（P01-003，列存在时才检查）
    if "duplicate_of" in idx:
        all_ids = {r[0] for r in data if r}
        dup_map = {}
        for ln, r in enumerate(data, 2):
            v = (dict(zip(header, r)).get("duplicate_of") or "").strip()
            if v == "UNKNOWN":
                v = ""  # 重扫默认值视为未标记
            sid = dict(zip(header, r)).get("source_id", "")
            if not v:
                continue
            if not SRC_ID_RE.match(v):
                problems.append(f"第{ln}行 duplicate_of 非法 source_id: {v!r}")
            elif v == sid:
                problems.append(f"第{ln}行 duplicate_of 指向自身")
            elif v not in all_ids:
                problems.append(f"第{ln}行 duplicate_of 指向不存在的文档: {v}")
            else:
                dup_map[sid] = v
        for sid, master in dup_map.items():
            if master in dup_map:  # 主副本自身是从 → 两级链（应直接指最终主）
                problems.append(f"{sid} 的主副本 {master} 本身是从副本")

    seen, dup_ck = set(), []
    for c in checksums:
        if c in seen and c not in dup_ck:
            dup_ck.append(c)
        seen.add(c)
    if dup_ck:
        warnings.append(f"内容完全相同的文件 {len(dup_ck)} 组（重复 checksum，待 P01 去重决策）")

    result = {
        "path": str(csv_path),
        "records": len(data),
        "fields": header,
        "problems": problems,
        "warnings": warnings,
        "duplicate_checksum_groups": dup_ck,
    }
    return result


def main(argv=None) -> int:
    csv_path = Path(argv[0] if argv else "data_manifest.csv")
    r = validate(csv_path)
    print(f"manifest: {r['path']}")
    print(f"记录数: {r['records']}  字段数: {len(r['fields'])}")
    for w in r["warnings"]:
        print(f"警告: {w}")
    if r["problems"]:
        print(f"问题 {len(r['problems'])} 项:")
        for p in r["problems"]:
            print(f"  - {p}")
        return 1
    print("验证通过: 无问题")
    return 0


if __name__ == "__main__":
    sys.exit(main())
