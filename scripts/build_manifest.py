#!/usr/bin/env python3
"""TASK-P00-002: 航天资料元数据清单生成器.

递归扫描资料目录，为 PDF/DOC/DOCX/XLSX 生成含稳定 source_id 的 data_manifest.csv。
不解析正文，不输出正文日志，不调用外部模型 API，不复制原始资料。

用法: python scripts/build_manifest.py <资料目录> [--output data_manifest.csv]
"""

import argparse
import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

SUPPORTED_EXTS = {".pdf", ".doc", ".docx", ".xlsx"}

# Office 打开文档时的锁临时文件（~$xxx.docx），非真实资料
def is_junk(name: str) -> bool:
    return name.startswith("~$")

# 字段名对齐 TASK-P00-003A 契约；人工确认前填 UNKNOWN（filesystem_mtime 刻意不叫 document_version）
FIELDS = [
    "source_id",
    "file_name",
    "relative_path",
    "file_extension",
    "file_size",
    "checksum_sha256",
    "filesystem_mtime",
    "document_type",
    "title",
    "document_internal_id",
    "document_version",
    "effective_version",
    "document_status",
    "subsystem",
    "security_level",
    "external_model_allowed",
    "parse_status",
    "notes",
]

# 人工确认前为 UNKNOWN 的字段（重扫时保留已确认值）
UNKNOWN_OK_FIELDS = {
    "document_type", "title", "document_internal_id", "document_version",
    "effective_version", "document_status", "subsystem",
    "security_level", "external_model_allowed",
}


def make_source_id(relative_path: str) -> str:
    """source_id 由相对路径决定，确定性生成，重复运行不变。"""
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:10]
    return f"SRC-{digest.upper()}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def scan(root: Path) -> list:
    records = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED_EXTS or is_junk(p.name):
            continue
        st = p.stat()
        rel = p.relative_to(root).as_posix()
        records.append({
            "source_id": make_source_id(rel),
            "file_name": p.name,
            "relative_path": rel,
            "file_extension": p.suffix.lower(),
            "file_size": st.st_size,
            "checksum_sha256": sha256_file(p),
            "filesystem_mtime": datetime.fromtimestamp(
                st.st_mtime).isoformat(timespec="seconds"),
            "document_type": "UNKNOWN",
            "title": "UNKNOWN",
            "document_internal_id": "UNKNOWN",
            "document_version": "UNKNOWN",
            "effective_version": "UNKNOWN",
            "document_status": "UNKNOWN",
            "subsystem": "UNKNOWN",
            "security_level": "UNKNOWN",
            "external_model_allowed": "UNKNOWN",
            "parse_status": "NOT_STARTED",
            "notes": "",
        })
    return records


def load_existing(output: Path) -> dict:
    if not output.exists():
        return {}
    with output.open(newline="", encoding="utf-8") as f:
        return {row["relative_path"]: row for row in csv.DictReader(f)}


def build_manifest(root: Path, output: Path) -> dict:
    """扫描 root，对比旧清单（若有），写入 output，返回变更报告。"""
    old = load_existing(output)
    new = {r["relative_path"]: r for r in scan(root)}

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        rel for rel in set(new) & set(old)
        if new[rel]["checksum_sha256"] != old[rel]["checksum_sha256"]
    )

    # 保留已有 source_id：同路径沿用旧 id（含内容变化时，保持资料血缘）
    # 保留已人工确认的元数据（旧值非 UNKNOWN/非空时，重扫不覆盖回 UNKNOWN）
    for rel in set(new) & set(old):
        new[rel]["source_id"] = old[rel]["source_id"]
        for col in UNKNOWN_OK_FIELDS:
            if old[rel].get(col, "UNKNOWN") != "UNKNOWN" and new[rel][col] == "UNKNOWN":
                new[rel][col] = old[rel][col]

    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(new.values())

    return {
        "total": len(new),
        "added": len(added), "added_paths": added,
        "removed": len(removed), "removed_paths": removed,
        "changed": len(changed), "changed_paths": changed,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("materials_dir", type=Path, help="资料目录（仓库外，仅记录相对路径）")
    ap.add_argument("--output", type=Path, default=Path("data_manifest.csv"))
    args = ap.parse_args(argv)
    if not args.materials_dir.is_dir():
        ap.error(f"资料目录不存在: {args.materials_dir}")
    r = build_manifest(args.materials_dir, args.output)
    print(f"清单条数: {r['total']}")
    print(f"新增: {r['added']}  删除: {r['removed']}  变化: {r['changed']}")
    for rel in r["added_paths"]:
        print(f"  + {rel}")
    for rel in r["removed_paths"]:
        print(f"  - {rel}")
    for rel in r["changed_paths"]:
        print(f"  ~ {rel}")
    print(f"已写入: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
