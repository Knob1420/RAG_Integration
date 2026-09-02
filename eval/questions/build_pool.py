#!/usr/bin/env python3
"""TASK-P00-004: 候选问题池构建.

数据来源: 2026-09-01 对 83 份资料的本地锚点提取（标题/编号节/表头/结论句/版本表,
见 docs/reports/P00-data-profile.md 与本文件 generation_method 字段）。
问题全部锚定到真实 source_id 与证据位置; 不含资料正文。

产出: eval/questions/question_pool.csv + eval/questions/question_cards/Q-XXX.yaml
用法: python eval/questions/build_pool.py   (RAG 环境)
"""

import csv
import sys
from pathlib import Path

import yaml

OUT = Path(__file__).parent
# manifest 中核实过的 source_id
S = {
    "zongti": "SRC-F0D610E0D6",      # 总体设计方案 20240305 Z0
    "shuomingshu": "SRC-117228955F",  # 计算模块技术说明书 V1.0 docx
    "sm_pdf": "SRC-0DF11E7A29",       # 技术说明书盖章版 pdf
    "dagang": "SRC-CE7695FE95",       # 验收级环境试验大纲
    "zongjie": "SRC-321374652A",      # 正样件研制与质量总结报告
    "ids_pwr": "SRC-D24F1ADE39",      # 电源模块 IDS 表
    "yaokong": "SRC-3956F61513",      # 遥控遥测汇总表 xlsx
    "banben": "SRC-B0DA913F5C",       # 软件版本控制 xlsx
    "ck831": "SRC-7878EEE3F2",        # 程控时间表 8.31
    "ck92": "SRC-797371ABE3",         # 程控时间表 9.2
    "ck828": "SRC-CD675E4634",        # 程控时间表 8.28
    "jiaofu": "SRC-50FA015FB7",       # 交付清单 xlsx
    "scan1": "SRC-D669ED4FD3",        # 验收测试记录表 pdf(扫描)
    "scan2": "SRC-F0476730C9",        # 归档目录同名扫描件
    "huiyi": "SRC-9E3D43D729",        # 20240306 初样方案讨论纪要 docx
    "huiyi_pdf": "SRC-E150838109",    # SCS-01 20240712 讨论纪要 pdf
    "test0813": "SRC-6ED2CE6761",     # 0813 测试与问题记录
    "laolian": "SRC-83765A0E9F",      # 老炼测试结果
    "fanxiu": "SRC-7A10397C1D",       # 返修后上星测试情况和处理建议
    "pwr_design": "SRC-4C11C78870",   # 电源模块方案设计报告
    "pwr_sm": "SRC-2AC203A529",       # 电源模块说明书 V1.0
    "fugai": "SRC-7ABA176185",        # 测试覆盖性分析及检查报告
    "zhengming": "SRC-E813A4B35A",    # 计算模块产品证明书 Z0102
    "lvli": "SRC-81483943EB",         # 计算模块产品履历书 doc
    "ids_cpu": "SRC-F8E406DD21",      # 计算模块 IDS 表
}

FIELDS = [
    "question_id", "question", "task_type", "business_context",
    "related_source_ids", "evidence_locations", "answerable",
    "requires_multiple_sources", "version_or_time_constraint",
    "status_constraint", "required_claims", "forbidden_claims",
    "value_score", "difficulty", "generation_method", "review_status",
]

# 公共 forbidden（每问追加）
COMMON_FB = ["不得编造资料中不存在的数值/结论", "不得将 filesystem_mtime 当作 document_version"]


def q(i, question, ttype, ctx, srcs, ev, ans, multi, vtc, sc, req, fb, vs, dif, gm):
    return {
        "question_id": f"Q-{i:03d}", "question": question, "task_type": ttype,
        "business_context": ctx, "related_source_ids": srcs, "evidence_locations": ev,
        "answerable": ans, "requires_multiple_sources": multi,
        # 无约束显式 NONE（不冒充有约束）
        "version_or_time_constraint": vtc or "NONE",
        "status_constraint": sc or "NONE",
        "required_claims": req, "forbidden_claims": fb + COMMON_FB,
        "value_score": vs, "difficulty": dif, "generation_method": gm,
        "review_status": "machine_draft",
    }


A, PA, UA = "answerable", "partially_answerable", "unanswerable"
ANCH, MANI, DUP = "profile_anchor", "manifest_derived", "duplicate_pair_derived"

POOL = [
    # ── 参数/接口/IDS（10）──
    q(1, "智加X100计算模块的处理器由哪些部分组成？", "parameter_lookup",
      "单机规格确认", [S["shuomingshu"], S["zongti"]],
      ["技术说明书 表3.5 特性和规格(处理器行)", "总体设计方案 3.3 智能计算模块总体设计"],
      A, False, "", "", ["列出全部处理器构成并引用表/节位置"], ["不得遗漏 GPU 部分"], 3, "easy", ANCH),
    q(2, "智加X100计算模块对外电连接器有哪些？各自的接口类型和功能是什么？", "interface_lookup",
      "星上集成对接", [S["shuomingshu"], S["ids_cpu"]],
      ["技术说明书 5.外部接口/表 电连接器(序号/编号/型号/类型/功能)", "计算模块IDS 接口数据单7 电连接器"],
      A, True, "", "", ["逐连接器给出类型与功能", "两份资料结论需一致或指出差异"], ["不得混淆计算模块与电源模块的连接器"], 3, "medium", ANCH),
    q(3, "电源模块IDS表包含哪些接口数据单？", "interface_lookup",
      "接口数据单完整性核对", [S["ids_pwr"]],
      ["电源模块IDS 目录标题(接口数据单1~12: 机械特性/热特性/电源/电连接器/接点分配/接地等)"],
      A, False, "", "", ["按序号列出全部接口数据单名称"], [], 2, "easy", ANCH),
    q(4, "电源模块IDS表的文件编号是什么？", "parameter_lookup",
      "文档编号体系登记", [S["ids_pwr"]],
      ["电源模块IDS 表内 文件编号字段(SCS-01-IDS-1 布局)"],
      A, False, "", "", ["给出文件编号并说明所在表格位置"], [], 1, "easy", ANCH),
    q(5, "智加X100整机对外的低速接口有哪些？通过什么器件实现？", "interface_lookup",
      "测控通信方案核对", [S["zongti"]],
      ["总体设计方案 3.3/3.5 节 低速接口描述段(RS422/CAN/GPIO 与 CPLD)"],
      A, False, "", "", ["列全低速接口种类与数量", "指明由 CPLD 实现及其职责"], [], 3, "easy", ANCH),
    q(6, "CPU遥控协议与CPU遥测协议各自的最后修订时间是多少？", "parameter_lookup",
      "协议版本核对", [S["yaokong"]],
      ["遥控遥测汇总表 sheet'CPU遥控协议'与'CPU遥测协议' 表头行(最后修订时间)"],
      A, False, "答案须以表内'最后修订时间'为准，非文件 mtime", "",
      ["给出两个 sheet 各自的修订时间", "区分遥控与遥测"], ["不得用 filesystem_mtime 回答"], 3, "medium", ANCH),
    q(7, "CPLD遥测代号TMD201/TMD202/TMD203分别对应什么含义？", "parameter_lookup",
      "遥测判读依据", [S["yaokong"]],
      ["汇总表 sheet'CPLD遥测' 行 TMD201~TMD203"],
      A, False, "", "", ["逐代号给出含义", "注明所在 sheet 与行"], [], 2, "easy", ANCH),
    q(8, "智加X100计算模块的包络尺寸是多少？", "parameter_lookup",
      "结构安装适配", [S["shuomingshu"]],
      ["技术说明书 3.4.1 包络尺寸 节"],
      A, False, "", "", ["给出尺寸数值及单位并引用节号"], [], 3, "easy", ANCH),
    q(9, "智加X100计算模块的供电要求是什么？", "parameter_lookup",
      "电源配电设计", [S["shuomingshu"], S["ids_pwr"]],
      ["技术说明书 4.4 设备供电要求", "电源模块IDS 接口数据单6 电源"],
      A, True, "", "", ["给出供电参数并引用出处", "如两处口径不一致须指出"], [], 3, "medium", ANCH),
    q(10, "计算模块安装时导热硅脂用量有什么要求？", "parameter_lookup",
      "装配工艺", [S["shuomingshu"], S["sm_pdf"]],
      ["技术说明书 2.2 注意事项(导热硅脂用量句)"],
      A, False, "", "", ["给出用量上限并引用章节"], [], 1, "easy", ANCH),

    # ── 验收测试/环境试验/结论（10）──
    q(11, "正样件验收级随机振动试验的结论是什么？", "test_result_lookup",
      "验收结论追溯", [S["zongjie"]],
      ["总结报告 环境试验相关章节'随机振动试验通过'结论句"],
      A, False, "", "结论须为原文明确表述的'通过'", ["给出结论及其判定句位置"], ["不得推断未写明的试验通过"], 3, "easy", ANCH),
    q(12, "正样件热真空试验的结论是什么？", "test_result_lookup",
      "验收结论追溯", [S["zongjie"]],
      ["总结报告 '热真空试验通过考核'结论句"],
      A, False, "", "", ["给出结论及位置"], [], 3, "easy", ANCH),
    q(13, "热摸底试验的结论是什么？", "test_result_lookup",
      "验收结论追溯", [S["zongjie"]],
      ["总结报告 '热摸底试验通过'结论句"],
      A, False, "", "", ["给出结论及位置"], [], 2, "easy", ANCH),
    q(14, "老炼测试中载荷遥控指令遍历(CPLD/CPU)的测试结论是什么？", "test_result_lookup",
      "上星前测试确认", [S["laolian"]],
      ["老炼测试结果 4.2 载荷遥控指令遍历 结论列/结论句"],
      A, False, "", "须引用'测试结论'列或结论句原文表述",
      ["区分 CPLD 与 CPU 遍历结果", "引用测试步骤表的结论列"], [], 3, "medium", ANCH),
    q(15, "老炼测试覆盖了哪几个测试日期/阶段？", "test_result_lookup",
      "测试过程完整性", [S["laolian"]],
      ["老炼测试结果 章节标题(8月27日程控/8月28日/9月1日/9月2日 各节)"],
      A, False, "答案按文档章节时序整理", "", ["列出全部测试日及当日项目"], [], 2, "medium", ANCH),
    q(16, "返修后上星测试进行了多少次上电启动？结论如何？", "test_result_lookup",
      "返修归零确认", [S["fanxiu"]],
      ["返修后上星测试报告 正样件装星启动测试段(上电次数与无异常结论)"],
      A, False, "", "", ["给出次数与结论", "注明 TMS 遥测判读依据(如文中有)"], [], 3, "easy", ANCH),
    q(17, "GPU板启动异常问题的定位结论是什么？依据了哪些交叉验证？", "test_result_lookup",
      "故障定位追溯", [S["fanxiu"]],
      ["返修报告 交叉验证段(备件主板+正样GPU板 / 正样主板+备件GPU板 两组合的结果)"],
      A, False, "", "", ["给出问题跟随对象", "列出两组交叉验证及各自结果", "说明备件上能否复现"], [], 3, "medium", ANCH),
    q(18, "验收级环境试验大纲规定的试验项目及顺序是什么？", "test_result_lookup",
      "试验大纲执行核对", [S["dagang"]],
      ["环境试验大纲 '验收试验项目和顺序' 节(试验项目/试验顺序表)"],
      A, False, "", "", ["按顺序列出试验项目"], [], 3, "medium", ANCH),
    q(19, "环境试验大纲对故障修复后再试验的时间有何规定与建议？", "parameter_lookup",
      "试验规则查询", [S["dagang"]],
      ["环境试验大纲 '再试验' 节(累计上限与建议区间句)"],
      A, False, "", "区分'规定上限'与'建议范围'两种表述",
      ["给出累计上限数值", "给出建议区间"], [], 2, "easy", ANCH),
    q(20, "《智加X100（硬件）验收测试记录表》中各测试项目的结论是什么？", "test_result_lookup",
      "验收测试记录数字化", [S["scan1"], S["scan2"]],
      ["验收测试记录表 PDF——纯扫描件(8/8页无文本层, 见 P00-data-profile)",
       "待 OCR 后补: 各测试项目行'测试结果/结论'列"],
      UA, False, "依赖 OCR 化(parse_status=PENDING)", "",
      ["回答前须声明扫描件未解析", "OCR 后按行给出结论"], ["不得在无证据时声称全部通过"], 3, "hard", ANCH),

    # ── 方案设计与会议决策（5）──
    q(21, "初样方案讨论会(20240306)对CPU核数提出了什么建议？", "meeting_action_lookup",
      "设计变更溯源", [S["huiyi"], S["zongti"]],
      ["会议纪要 建议段(2核→4核句)", "对照总体设计方案 3.3 节 CPU 选型"],
      PA, True, "建议→设计落实需两份资料比对", "建议类表述不得写成已决定",
      ["给出建议原文位置", "比对该建议是否反映在总体设计方案中，不能确认则说明证据不足"],
      ["不得把'建议'表述为'已执行'"], 3, "medium", ANCH),
    q(22, "初样方案讨论会对正样件FPGA和CPU器件等级提出了什么建议？", "meeting_action_lookup",
      "元器件等级决策", [S["huiyi"]],
      ["会议纪要 宇航级器件建议句"],
      A, False, "", "建议类表述不得写成已决定", ["给出建议内容与位置"], ["不得声称正样已实际采用宇航级(未见证据)"], 2, "easy", ANCH),
    q(23, "FPGA上注更新通道存在什么问题？会议提出了什么改进建议？", "meeting_action_lookup",
      "在轨更新方案演进", [S["huiyi"], S["zongti"]],
      ["会议纪要 上注通道段(422速率低/千兆网预留句)", "总体设计方案 3.6.1-3.6.4 在轨更新各节"],
      PA, True, "", "", ["给出问题与建议", "对照总体设计方案 3.6 节是否体现(部分可答)"], [], 2, "medium", ANCH),
    q(24, "为什么CPLD下建议挂载EEPROM？", "design_decision_lookup",
      "硬件设计意图", [S["huiyi"]],
      ["会议纪要 EEPROM建议句(存储内容)"],
      A, False, "", "", ["给出需存储的信息类别", "注明建议出处"], [], 2, "easy", ANCH),
    q(25, "载板设计中CPU与万兆网/系统盘/数据盘采用什么通道？系统盘接口如何实现？", "design_decision_lookup",
      "架构设计追溯", [S["zongti"]],
      ["总体设计方案 3.3 节 PCIe通道与mSATA实现句"],
      A, False, "", "", ["给出通道类型", "说明系统盘接口的实现方式"], [], 2, "easy", ANCH),

    # ── 跨文档追溯（7）──
    q(26, "正样件总结报告的'引用文件'章节引用了哪些文件？其中哪些能按编号对应到本项目已登记资料？", "cross_document_trace",
      "追溯图种子", [S["zongjie"], "MANIFEST"],
      ["总结报告 '引用文件' 节编号列表", "data_manifest.csv 文件名/编号匹配"],
      A, True, "", "", ["列出引用文件", "逐项标注是否可回链到 manifest source_id"],
      ["不得虚构未登记的引用对应"], 3, "medium", ANCH),
    q(27, "遥控遥测汇总表的'修改记录'sheet与各协议sheet的'最后修订时间'如何共同反映协议版本演进？", "cross_document_trace",
      "协议版本链", [S["yaokong"]],
      ["汇总表 sheet'修改记录'(序号/修改时间/修改内容/修改人)", "各协议sheet 表头'最后修订时间'行"],
      A, True, "须用表内修订时间，不用文件mtime", "",
      ["梳理修改记录条目与各协议修订时间的对应", "指出CPU与CPLD协议的最近修订"],
      ["不得将文件 mtime 当作协议版本时间"], 3, "medium", ANCH),
    q(28, "程控时间表8.31与9.2相比，程控安排发生了哪些变化？", "cross_document_trace",
      "程控演进比对", [S["ck831"], S["ck92"]],
      ["两文件 sheet'Sheet2'(序号/北京时间/星上时间/任务/指令/判据 列)"],
      A, True, "比对以表内'北京时间/星上时间'列为准", "",
      ["列出新增/删除/变更的程控条目", "说明两表共同列结构"], [], 3, "medium", ANCH),
    q(29, "交付清单中的生产编号与产品证明书、产品履历书如何对应？", "cross_document_trace",
      "产品实物追溯", [S["jiaofu"], S["zhengming"], S["lvli"]],
      ["交付清单 sheet'主星'(产品/编号/生产编号 列)", "产品证明书 Z0102 标识", "产品履历书 单机标识"],
      A, True, "", "", ["给出编号对应关系", "注明各自证据位置"], [], 3, "medium", ANCH),
    q(30, "测试覆盖性检查矩阵中，哪些测试项目未覆盖'整星集成测试'？", "cross_document_trace",
      "覆盖性缺口识别", [S["fugai"]],
      ["覆盖性报告 表(测试项目 × 单机验收/系统集成/整星集成 三列)"],
      PA, False, "", "", ["按矩阵列出空缺项", "如矩阵存在空行/合并单元格致无法判定须指出"], [], 3, "medium", ANCH),
    q(31, "技术说明书V1.0(docx)与其盖章版PDF内容是否一致？差异如何界定？", "cross_document_trace",
      "版本链与主副本判定", [S["shuomingshu"], S["sm_pdf"]],
      ["两文件结构对照(docx 章节标题 vs pdf 书签/文本)", "P00-sample-log 同名盖章版记录"],
      PA, True, "docx为V1.0名义项; 盖章版为签署版", "",
      ["给出章节级一致性结论方法", "明确两文件的主副本关系建议"],
      ["不得在未逐节比对前声称完全一致"], 2, "hard", DUP),
    q(32, "总结报告中的试验执行情况与环境试验大纲规定的项目如何对应？有无大纲规定但总结未提及的项目？", "cross_document_trace",
      "大纲↔执行闭环", [S["dagang"], S["zongjie"]],
      ["大纲 '验收试验项目和顺序' 表", "总结报告 各试验结论句/执行情况节"],
      PA, True, "", "", ["逐项目标注: 大纲有/总结有、大纲有/总结未见", "对'未见'项说明是未做还是未写（证据不足时标注）"],
      ["不得将'总结未提及'直接断言为'未执行'"], 3, "hard", ANCH),

    # ── 时间/版本/变化比较（4）──
    q(33, "UBOOT与CPU(linux)软件的版本迭代时间线是什么？", "time_or_version_compare",
      "软件版本演进", [S["banben"]],
      ["软件版本控制 sheet'Sheet1'(板卡级软件版本号/版本号/更新时间/更新内容 列)"],
      A, False, "以表内'更新时间/版本号'为准", "",
      ["分别梳理两个软件的版本序列", "区分'提测版本'与'版本号'两列"],
      ["不得混淆提测版本与正式版本号"], 3, "medium", ANCH),
    q(34, "计算模块与电源模块说明书的文档版本标注是什么？IDS表的修订版本机制如何记录？", "time_or_version_compare",
      "文档版本体系", [S["shuomingshu"], S["pwr_sm"], S["ids_pwr"]],
      ["两份说明书 文件名/文内版本字段", "IDS表 修订表(修订前版本号/修订后版本号/修订日期 列)"],
      A, True, "区分 文件名版本号 / 文内版本字段 / 修订表条目", "",
      ["给出各文档的版本标注来源", "说明IDS修订表结构与最新版本确定方法"], [], 2, "medium", ANCH),
    q(35, "程控时间表8.28/8.31/9.2四份文件按文件修改时间排序如何？该顺序与内容演进是否吻合？", "time_or_version_compare",
      "版本线索有效性检验", [S["ck828"], S["ck831"], S["ck92"], "MANIFEST"],
      ["manifest filesystem_mtime 字段(2025-08~09)", "各文件 Sheet2 程控条目时间列"],
      PA, True, "filesystem_mtime 仅作排序线索, 不等于 document_version", "",
      ["给出四份文件的 mtime 排序", "与表内程控时间演进比对并说明是否吻合", "明确 mtime 的线索局限性"],
      ["不得将 mtime 序列称为文档版本号"], 3, "medium", MANI),
    q(36, "测试覆盖性分析报告自身的文件编号与版本号是什么？", "time_or_version_compare",
      "文档编号登记", [S["fugai"]],
      ["覆盖性报告 表(文件编号 SCS-01-… / 版本号 字段)及修订表"],
      A, False, "", "", ["给出文件编号与版本号字段值"], [], 1, "easy", ANCH),

    # ── 冲突/资料不足/不可回答（5）──
    q(37, "三份《（硬件）验收测试记录表》PDF为近重复扫描件，其测试结论目前能否提取？需要什么前置条件？", "insufficient_evidence",
      "扫描件解析缺口", [S["scan1"], S["scan2"]],
      ["P00-data-profile: 8/8页 chars<50(无文本层)", "manifest 三份同名记录(同尺寸不同哈希)"],
      UA, False, "依赖 OCR(parse_status=PENDING)", "",
      ["明确回答'当前不可回答'及原因", "给出前置条件(OCR/版面还原)", "引用三份副本的 source_id"],
      ["不得猜测记录表内容"], 3, "medium", DUP),
    q(38, "0813测试中'点胶固定后复测'的复测结果记录是否完整？", "insufficient_evidence",
      "测试记录完整性", [S["test0813"]],
      ["0813测试与问题记录 2.2.3 点胶固定后复测 节"],
      PA, False, "", "若复测结论缺失须显式说明，不得补写",
      ["给出该节已有的记录内容类型", "判断结论字段是否完整(部分可答)"], ["不得代填复测结论"], 2, "medium", ANCH),
    q(39, "GPU板子卡问题原厂分析是否已有结论？项目侧的处理建议是什么？", "insufficient_evidence",
      "遗留问题跟踪", [S["fanxiu"]],
      ["返修报告 处理情况和建议 段(原厂反馈/个性问题/备件不复现句)"],
      PA, False, "以报告撰写时点为准，后续结论未见资料", "",
      ["区分'原厂结论'与'项目侧建议'", "原厂结论标注为未见/短期无法给出"],
      ["不得虚构原厂分析结论"], 3, "medium", ANCH),
    q(40, "会议建议的CPU 4核方案是否落实到了总体设计方案的器件选型？两处资料能否闭环判定？", "conflict_detection",
      "建议→设计闭环检验", [S["huiyi"], S["zongti"]],
      ["会议纪要 CPU核数建议句", "总体设计方案 器件表(序号/器件类型/具体型号/厂商/备注)"],
      PA, True, "", "",
      ["检查器件表 CPU 行是否可判定核数", "若型号无法判断核数则明确'证据不足'而非'未落实'"],
      ["不得在证据不足时断言已落实或未落实"], 3, "hard", ANCH),
]


def main() -> int:
    # "MANIFEST" 是特殊引用, 校验器单独放行
    csv_path = OUT / "question_pool.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in POOL:
            r = dict(row)
            r["related_source_ids"] = ";".join(r["related_source_ids"])
            r["evidence_locations"] = ";".join(r["evidence_locations"])
            r["required_claims"] = ";".join(r["required_claims"])
            r["forbidden_claims"] = ";".join(r["forbidden_claims"])
            w.writerow(r)

    cards = OUT / "question_cards"
    cards.mkdir(exist_ok=True)
    for stale in cards.glob("Q-*.yaml"):
        stale.unlink()
    for row in POOL:
        (cards / f"{row['question_id']}.yaml").write_text(
            yaml.safe_dump(row, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"pool: {len(POOL)} → {csv_path} + {cards}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
