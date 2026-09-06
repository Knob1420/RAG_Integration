"""parse_xlsx 合成样例测试：多行表头/合并单元格/key_value 区/守恒。"""
from pathlib import Path

import openpyxl

from rag_integration.models import RouteId
from rag_integration.parse_xlsx import parse_xlsx

SID = "SRC-0123456789"


def build(tmp_path: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "清单"
    # 元信息区（两列键值）
    ws.append(["任务代号", "X100"])
    ws.append([])
    # 表区：两行表头（首行组名含空缺）+ 数据行 + 合并单元格
    ws.append(["", "输出", "输出", "输入"])
    ws.append(["序号", "信号", "地", "电压"])
    ws.append(["1", "CLK", None, "3.3"])   # C 列纵向合并
    ws.append(["2", None, None, "5.0"])    # B、C 延续合并
    ws.merge_cells("A6:A7")
    ws.merge_cells("C5:C7")                 # 注意 openpyxl append 从 A1 起，行号按实际
    p = tmp_path / "s.xlsx"
    wb.save(p)
    return p


def test_parse_xlsx(tmp_path):
    els, stats = parse_xlsx(build(tmp_path), SID, RouteId.R8, "complex: merged=2")
    kv = [e for e in els if e.element_type.value == "key_value"]
    rows = [e for e in els if e.element_type.value == "table_row"]
    assert len(kv) == 1 and kv[0].content == "任务代号: X100"
    assert kv[0].location.sheet_name == "清单"
    assert all(r.metadata["header"][0] == "序号" for r in rows)
    assert rows[0].metadata["header"][1] == "输出/信号"  # 多行表头展平
    assert stats["input_cells"] == stats["output_cells"]  # 守恒（合并展开计入）


def test_merged_title_row_and_trailing_pad(tmp_path):
    """合并标题行 + 尾部空白列：表头不被污染（真实 Sheet2 场景）。"""
    import openpyxl as ox
    wb = ox.Workbook()
    ws = wb.active
    ws.title = "S"
    note = "说明：T0 时刻相关的长文本"
    ws.append([note])                      # 合并标题行（A1:F1）
    ws.append(["序号", "北京时间", "判据"])
    ws.append(["1", "08:00", "正常"])
    ws.append(["2", "09:00", "正常"])
    ws.append(["备注尾巴"])                 # 无关区域，制造列宽不对称
    ws.merge_cells("A1:F1")
    p = tmp_path / "t.xlsx"
    wb.save(p)
    els, stats = parse_xlsx(p, SID, RouteId.R8, "r")
    kvs = [e for e in els if e.element_type.value == "key_value"]
    rows = [e for e in els if e.element_type.value == "table_row"]
    assert any(k.content == note and k.metadata.get("merged_title") for k in kvs)
    main = [r for r in rows if r.location.row_no >= 2]
    assert main[0].metadata["header"] == ["序号", "北京时间", "判据"]
    assert stats["input_cells"] == stats["output_cells"]
