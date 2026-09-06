"""TASK-P01-FULL-PIPELINE: 类型化 ChunkRecord 生成。

两条策略（任务包默认决策 4）：
- 表格 per_row：每 TABLE_ROW 一 chunk（表头在 element.metadata，P02 可加rich）
- 正文 heading_window：H1 起窗，窗满 800 字或遇下一 H1 切块
KEY_VALUE 单独成块；FIGURE / PAGE_OMITTED 不产 chunk。
"""
from __future__ import annotations

from .models import ChunkRecord, DocumentElement, ElementType

MAX_CHARS = 800


def make_chunks(elements: list[DocumentElement],
                source_id: str) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    window: list[DocumentElement] = []
    window_chain: tuple = ()

    def flush():
        nonlocal window
        if window:
            chain = window[0].location.section_chain or window_chain
            chunks.append(ChunkRecord(
                source_id=source_id,
                element_ids=tuple(e.element_id for e in window),
                content="\n".join(e.content for e in window),
                strategy="heading_window",
                metadata={"section_chain": list(chain)}))
        window = []

    for e in elements:
        t = e.element_type
        if t is ElementType.TABLE_ROW:
            flush()
            chunks.append(ChunkRecord(
                source_id=source_id, element_ids=(e.element_id,),
                content=e.content, strategy="table_row",
                metadata={"header": e.metadata.get("header"),
                          "section_chain": list(e.location.section_chain)}))
        elif t is ElementType.KEY_VALUE:
            flush()
            chunks.append(ChunkRecord(
                source_id=source_id, element_ids=(e.element_id,),
                content=e.content, strategy="key_value",
                metadata={"section_chain": list(e.location.section_chain)}))
        elif t in (ElementType.PARAGRAPH, ElementType.HEADING):
            is_h1 = t is ElementType.HEADING and e.metadata.get("level") == 1
            if is_h1 and window:
                flush()
            if window and sum(len(x.content) for x in window) + len(e.content) > MAX_CHARS:
                flush()
            window.append(e)
            window_chain = e.location.section_chain or window_chain
        # FIGURE / PAGE_OMITTED：不产 chunk
    flush()
    return chunks
