#!/usr/bin/env python3
"""TASK-P01-003: 主副本判定与标记（2026-09-06 用户裁定三项规则）.

1. 副本：内容全等（content_sha256 相等 或 5字符指纹 J=1.0，含微差副本）→ 组内标主从。
   主副本优先级：归档编号件 > 正题目录/根目录 > 盖章目录 > 外发目录。
2. 跨格式等价：盖章目录的 PDF 导出 ↔ 同基名 docx → docx 为主（结构富）。
3. 版本族（J 0.5~0.99）：不标记，全部保留进索引（P01-004 标 doc_family/effective_version）。

输出：manifest 增列 duplicate_of（空=主/独立，非空=主副本 source_id）
     + docs/reports/P01-duplicate-marking.md（83 份处置表）。
用法：RAG env 下 python scripts/mark_duplicates.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "data_manifest.csv"
ELEMENTS = Path("/home/zjlab/Documents/build_LLMs/NLP_course_hf/RAG/Data/derived/p01/elements.jsonl")
RUNS = Path("/home/zjlab/Documents/build_LLMs/NLP_course_hf/RAG/Data/derived/p01/runs.jsonl")
REPORT = REPO / "docs/reports/P01-duplicate-marking.md"


def stem(fn: str) -> str:
    """归一化文档基名：去扩展（含 .docx.pdf 双扩展）/日期/版本号/编号前缀/括注。"""
    s = fn.lower()
    s = re.sub(r"\.docx\.pdf$", "", s)
    s = re.sub(r"\.(pdf|docx|xlsx|doc)$", "", s)
    s = re.sub(r"20\d{6}|\d{8}|\d{4}\.\d{1,2}\.\d{1,2}|\d{1,2}\.\d{1,2}(?=\.)", "", s)
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"v\d+(\.\d+)?", "", s)
    s = re.sub(r"[_\-— ()（）\d]+", "", s)
    return s

DUP_J = 0.995   # 副本线：J≥此值内容全等（实测微差副本 0.9995；最近版本对 0.911）
EXPORT_C = 0.7  # 盖章导出线：pdf(盖章目录)↔同基名 docx 的包含度。实测真导出对 ≈0.79
               # （PDF 提取空格/块合并噪声压低），故须叠加 盖章目录+跨格式+同基名 三信号


def shingles(t: str) -> set[str]:
    t = re.sub(r"\s+", "", t)  # 空白归一：提取噪声不打断指纹
    return {t[i:i + 5] for i in range(0, max(len(t) - 4, 1), 3)}


def load_content() -> dict[str, str]:
    text: dict[str, str] = {}
    for line in open(ELEMENTS, encoding="utf-8"):
        e = json.loads(line)
        if e["element_type"] != "page_omitted":
            text[e["source_id"]] = text.get(e["source_id"], "") + e["content"]
    return text


def load_content_sha() -> dict[str, str]:
    latest: dict[str, str] = {}
    for line in open(RUNS, encoding="utf-8"):
        r = json.loads(line)
        latest[r["source_id"]] = r.get("stats", {}).get("content_sha256", "")
    return latest


def find_families(kept: list[str], S: dict[str, set]) -> list[list[str]]:
    """版本族检测（P01-004 复用）：J≥0.5 并查集聚族，返回 ≥2 成员的族列表。"""
    fam_parent = {s: s for s in kept}

    def ffind(x):
        while fam_parent[x] != x:
            fam_parent[x] = fam_parent[fam_parent[x]]
            x = fam_parent[x]
        return x

    for a, b in combinations(kept, 2):
        if a not in S or b not in S or not S[a] or not S[b]:
            continue
        inter = len(S[a] & S[b])
        if inter / len(S[a] | S[b]) >= 0.5:
            fam_parent[ffind(a)] = ffind(b)
    fams: dict[str, list[str]] = {}
    for s in kept:
        fams.setdefault(ffind(s), []).append(s)
    return [v for v in fams.values() if len(v) > 1]


def master_key(row: dict) -> tuple:
    p = row["relative_path"]
    return ("外发" in p, "盖章" in p, "3d打印 归档" not in p, row["filesystem_mtime"])


def main() -> int:
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    text = load_content()
    S = {sid: shingles(t) for sid, t in text.items()}
    csha = load_content_sha()
    by_sid = {r["source_id"]: r for r in rows}

    # ---- 1. 内容全等组（sha 相等 或 指纹 J=1.0），并查集合并 ----
    parent = {r["source_id"]: r["source_id"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_sha: dict[str, list[str]] = {}
    for r in rows:
        h = csha.get(r["source_id"])
        if h:
            by_sha.setdefault(h, []).append(r["source_id"])
    for sids in by_sha.values():
        for s in sids[1:]:
            union(sids[0], s)
    sids = [r["source_id"] for r in rows if r["source_id"] in S]
    for a, b in combinations(sids, 2):
        if find(a) == find(b):
            continue
        if S[a] and S[b]:
            j = len(S[a] & S[b]) / len(S[a] | S[b])
            if j >= DUP_J:  # 全等或微差（实测 3 字符差 → 0.9995）
                union(a, b)

    groups: dict[str, list[str]] = {}
    for sid in parent:
        groups.setdefault(find(sid), []).append(sid)
    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

    dup_of: dict[str, str] = {}
    dup_kind: dict[str, str] = {}
    for members in dup_groups.values():
        members.sort(key=lambda s: master_key(by_sid[s]))
        master, slaves = members[0], members[1:]
        for s in slaves:
            dup_of[s] = master
            dup_kind[s] = "副本(内容全等)"

    # ---- 2. 跨格式等价：盖章 pdf 导出 ↔ 同基名 docx ----
    docx_by_stem: dict[str, list[str]] = {}
    for r in rows:
        if r["file_extension"] == ".docx" and r["source_id"] not in dup_of:
            docx_by_stem.setdefault(stem(r["file_name"]), []).append(r["source_id"])
    for r in rows:
        if r["file_extension"] != ".pdf" or "盖章" not in r["relative_path"]:
            continue
        sid = r["source_id"]
        if sid in dup_of:
            continue
        cands = docx_by_stem.get(stem(r["file_name"]), [])
        cands = [c for c in cands
                 if S.get(sid) and S.get(c)
                 and len(S[sid] & S[c]) / min(len(S[sid]), len(S[c])) >= EXPORT_C]
        if cands:
            cands.sort(key=lambda s: master_key(by_sid[s]))
            dup_of[sid] = cands[0]
            dup_kind[sid] = "副本(盖章PDF导出)"

    # ---- 3. 版本族（报告记录，不标记）----
    kept = [r["source_id"] for r in rows if r["source_id"] not in dup_of]
    fams = find_families(kept, S)
    fam_of = {}
    for i, members in enumerate(sorted(fams, key=lambda m: by_sid[m[0]]["relative_path"]), 1):
        for s in members:
            fam_of[s] = f"F{i}"

    # ---- 写 manifest（增列 duplicate_of）----
    fields = list(rows[0].keys())
    if "duplicate_of" not in fields:
        fields.append("duplicate_of")
    for r in rows:
        r["duplicate_of"] = dup_of.get(r["source_id"], "")
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # ---- 报告：83 份全处置表 ----
    lines = [
        "# P01-003 主副本判定处置表（2026-09-06 用户裁定）",
        "",
        "规则：① 内容全等→组内标主从（归档>正题/根>盖章>外发）；"
        "② 盖章 PDF 导出↔docx 取 docx 为主；③ 版本族全保留，P01-004 标记。",
        "",
        f"总量 83：主/独立 {len(kept)}，从副本 {len(dup_of)}，版本族 {len(fams)} 族。",
        "",
        "| source_id | 处置 | 路径 |",
        "|---|---|---|",
    ]
    order = {"副本(内容全等)": 1, "副本(盖章PDF导出)": 2}
    for r in sorted(rows, key=lambda r: (order.get(dup_kind.get(r["source_id"], ""), 0),
                                         r["relative_path"])):
        sid = r["source_id"]
        if sid in dup_of:
            disp = f"从→{dup_of[sid]}（{dup_kind[sid]}）"
        elif sid in fam_of:
            disp = f"主/独立 · 版本族 {fam_of[sid]}（P01-004 待标）"
        else:
            disp = "主/独立"
        lines.append(f"| {sid} | {disp} | {r['relative_path']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    n_slave = len(dup_of)
    print(f"从副本标记 {n_slave} 份（内容全等 "
          f"{sum(1 for v in dup_kind.values() if '全等' in v)} / 盖章导出 "
          f"{sum(1 for v in dup_kind.values() if '盖章' in v)}）")
    print(f"版本族 {len(fams)} 族（仅报告记录）：")
    for members in fams.values():
        print("  " + " | ".join(by_sid[s]["file_name"][:30] for s in members))
    print(f"报告: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
