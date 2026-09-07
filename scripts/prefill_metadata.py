#!/usr/bin/env python3
"""TASK-P01-004: manifest 业务元数据预填（规则预填，覆盖不了留 UNKNOWN 待人工）.

字段与规则（全部来自路径/文件名的确定性信号，不猜）：
- document_type：文件名关键词（纪要/IDS/试验大纲/说明书/清单…）
- subsystem：文件名关键词（电源/结构/软件/计算模块…）
- doc_family：版本族共享族名（复用 003 的 find_families，族名=成员共同基名）
- effective_version：文件名日期（20250120 → 20250120）或 程控式短日期（8.31）
- document_version：文件名 V 号（V1.0）

产出：manifest 更新 + docs/reports/P01-metadata-prefill.md（预填/UNKNOWN 清单）。
用法：RAG env 下 python scripts/prefill_metadata.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from mark_duplicates import ELEMENTS, find_families, shingles, stem  # noqa: E402

MANIFEST = REPO / "data_manifest.csv"
REPORT = REPO / "docs/reports/P01-metadata-prefill.md"

# (关键词, 值)，按序首个命中生效——具体词在前，泛化词在后
TYPE_RULES = [
    ("验收测试记录表", "验收测试记录表"),
    ("验收测试细则", "验收测试细则"),
    ("测试细则", "测试细则"),
    ("测试记录", "测试记录"),
    ("IDS", "IDS表"),
    ("试验大纲", "环境试验大纲"),
    ("试验报告", "环境试验报告"),
    ("总结报告", "研制总结报告"),
    ("方案设计", "方案设计报告"),
    ("设计方案", "总体设计方案"),
    ("影响域", "分析报告"),
    ("说明书", "说明书"),
    ("证明书", "产品证明书"),
    ("履历书", "产品履历书"),
    ("交付清单", "交付清单"),
    ("版本控制", "版本控制"),
    ("遥测", "遥测遥控汇总"),
    ("遥控", "遥测遥控汇总"),
    ("程控", "程控时间表"),
    ("联调", "联调记录"),
    ("纪要", "会议纪要"),
]
SUBSYSTEM_RULES = [
    ("电源", "电源模块"),
    ("结构", "结构"),
    ("软件", "软件"),
    ("计算模块", "计算模块"),
    ("X100", "计算模块"),
    ("载荷", "载荷"),
]


def rule(rules, text):
    for kw, val in rules:
        if kw in text:
            return val
    return "UNKNOWN"


def versions(fn: str) -> tuple[str, str]:
    """(document_version, effective_version)：V 号与日期（先剥扩展名再匹配）。"""
    base = re.sub(r"\.(pdf|docx|xlsx|doc)$", "", fn, flags=re.I)
    dv = ev = "UNKNOWN"
    m = re.search(r"[Vv](\d+(?:\.\d+)?)", base)
    if m:
        dv = "V" + m.group(1)
    m = re.search(r"(20\d{6}|\d{8})", base)
    if m:
        ev = m.group(1)
    else:
        m = re.search(r"[^\d.](\d{1,2}\.\d{1,2})$", base)  # 程控 8.31 式（结尾）
        if m:
            ev = m.group(1)
    return dv, ev


def main() -> int:
    import json
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    text = {}
    for line in open(ELEMENTS, encoding="utf-8"):
        e = json.loads(line)
        if e["element_type"] != "page_omitted":
            text[e["source_id"]] = text.get(e["source_id"], "") + e["content"]
    S = {sid: shingles(t) for sid, t in text.items()}

    kept = [r["source_id"] for r in rows if not r.get("duplicate_of")]
    fams = find_families(kept, S)
    fam_name = {}
    for members in fams:
        by_sid = {r["source_id"]: r for r in rows}
        name = stem(by_sid[members[0]]["file_name"]).strip(".")
        for s in members:
            fam_name[s] = name

    if "doc_family" not in rows[0]:
        for r in rows:
            r["doc_family"] = ""
    for r in rows:
        fn, sid = r["file_name"], r["source_id"]
        hit = fn + "/" + r["relative_path"]
        r["document_type"] = rule(TYPE_RULES, hit)
        r["subsystem"] = rule(SUBSYSTEM_RULES, hit)
        r["document_version"], r["effective_version"] = versions(fn)
        if sid in fam_name:
            r["doc_family"] = fam_name[sid]

    fields = list(rows[0].keys())
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    tc = Counter(r["document_type"] for r in rows)
    sc = Counter(r["subsystem"] for r in rows)
    fam_members = sum(1 for r in rows if r["doc_family"])
    lines = [
        "# P01-004 元数据预填结果（2026-09-07）",
        "",
        "规则全部来自路径/文件名确定性信号；UNKNOWN 为规则未覆盖，待人工定。",
        "",
        f"- document_type：预填 {sum(v for k, v in tc.items() if k != 'UNKNOWN')}"
        f" / UNKNOWN {tc.get('UNKNOWN', 0)}",
        f"- subsystem：预填 {sum(v for k, v in sc.items() if k != 'UNKNOWN')}"
        f" / UNKNOWN {sc.get('UNKNOWN', 0)}",
        f"- doc_family：{len(fams)} 族 {fam_members} 份；"
        f"effective_version/date 预填 "
        f"{sum(1 for r in rows if r['effective_version'] != 'UNKNOWN')}；"
        f"document_version(V号) {sum(1 for r in rows if r['document_version'] != 'UNKNOWN')}",
        "",
        "## 逐份清单",
        "",
        "| source_id | document_type | subsystem | doc_family | eff_ver | ver | 路径 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['source_id']} | {r['document_type']} | "
                     f"{r['subsystem']} | {r['doc_family'] or '—'} | "
                     f"{r['effective_version']} | {r['document_version']} | "
                     f"{r['relative_path']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("document_type:", dict(tc.most_common()))
    print("subsystem:", dict(sc.most_common()))
    print("版本族:", {stem(next(r['file_name'] for r in rows if r['source_id'] == m[0])): len(m)
                    for m in fams})
    print(f"报告: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
