"""TASK-P00-003A 测试: manifest 验证器的各失败/成功路径."""

from pathlib import Path

from scripts.validate_manifest import validate

FIELDS = [
    "source_id", "file_name", "relative_path", "file_extension", "file_size",
    "checksum_sha256", "filesystem_mtime", "document_type", "title",
    "document_internal_id", "document_version", "effective_version",
    "document_status", "subsystem", "security_level",
    "external_model_allowed", "parse_status", "doc_family", "notes",
]


def write_csv(path, rows):
    lines = [",".join(FIELDS)]
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def good_row(**over):
    r = ["SRC-X", "a.pdf", "dir/a.pdf", ".pdf", "10", "ab" * 32,
         "2024-03-07T09:18:42"] + ["UNKNOWN"] * 9 + ["NOT_STARTED", "", ""]
    for k, v in over.items():
        r[FIELDS.index(k)] = v
    return r


def test_valid_manifest_passes(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(), good_row(source_id="SRC-Y", relative_path="dir/b.docx",
                                       file_name="b.docx", file_extension=".docx")])
    r = validate(f)
    assert r["problems"] == [] and r["records"] == 2


def test_empty_or_duplicate_source_id_fails(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(source_id=""), good_row(), good_row()])
    r = validate(f)
    assert any("source_id 为空" in p for p in r["problems"])
    assert any("source_id 重复" in p for p in r["problems"])


def test_unsupported_extension_fails(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(file_extension=".txt")])
    assert any("扩展名不受支持" in p for p in validate(f)["problems"])


def test_absolute_path_fails(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(relative_path="/home/u/x/a.pdf")])
    assert any("绝对路径" in p for p in validate(f)["problems"])


def test_bad_mtime_and_parse_status_fail(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(filesystem_mtime="2024/03/07", parse_status="TODO")])
    ps = validate(f)["problems"]
    assert any("mtime 格式" in p for p in ps)
    assert any("parse_status 非法枚举" in p for p in ps)


def test_confirmed_enum_fields_pass_and_bad_values_fail(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(security_level="内部可用", external_model_allowed="YES")])
    assert validate(f)["problems"] == []
    write_csv(f, [good_row(security_level="随便")])
    assert any("security_level 非法取值" in p for p in validate(f)["problems"])
    write_csv(f, [good_row(external_model_allowed="maybe")])
    assert any("external_model_allowed 非法取值" in p for p in validate(f)["problems"])


def test_forged_unknown_field_fails(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(title="伪造标题")])
    assert any("title 未确认却填了值" in p for p in validate(f)["problems"])


def test_ragged_row_and_dup_header_fail(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(), ["source_id"] + ["x"] * 5])  # 列数不一致
    ps = validate(f)["problems"]
    assert any("列数不一致" in p for p in ps)


def test_secret_leak_fails(tmp_path):
    f = tmp_path / "m.csv"
    write_csv(f, [good_row(notes="key sk-abcdef0123456789abcdef")])
    assert any("疑似泄漏凭证" in p for p in validate(f)["problems"])


def test_duplicate_checksum_warns_not_fails(tmp_path):
    f = tmp_path / "m.csv"
    same = "cd" * 32
    write_csv(f, [good_row(checksum_sha256=same),
                  good_row(source_id="SRC-Y", relative_path="dir/b.pdf",
                           file_name="b.pdf", checksum_sha256=same)])
    r = validate(f)
    assert r["problems"] == []
    assert any("重复 checksum" in w for w in r["warnings"])


def test_duplicate_of_reference_checks(tmp_path):
    f = tmp_path / "m.csv"
    header = FIELDS + ["duplicate_of"]

    def row(sid, name, dup=""):
        return ([sid, name, name, ".pdf", "10", "ab" * 32,
                 "2024-03-07T09:18:42"] + ["UNKNOWN"] * 9
                + ["NOT_STARTED", "", "", dup])

    rows = [row("SRC-AAAAAAAA01", "a.pdf"),
            row("SRC-AAAAAAAA02", "b.pdf", "SRC-AAAAAAAA01")]  # 合法从副本
    lines = [",".join(header)] + [",".join(r) for r in rows]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    r = validate(f)
    assert not any("duplicate_of" in p for p in r["problems"])

    bad = [row("SRC-AAAAAAAA03", "c.pdf", "SRC-AAAAAAAA03"),   # 自指
           row("SRC-AAAAAAAA04", "d.pdf", "SRC-DEADBEEF01"),   # 不存在
           row("SRC-AAAAAAAA05", "e.pdf", "bad")]              # 格式非法
    lines = [",".join(header)] + [",".join(r) for r in rows[:1] + bad]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ps = validate(f)["problems"]
    assert any("指向自身" in p for p in ps)
    assert any("不存在" in p for p in ps)
    assert any("非法 source_id" in p for p in ps)
