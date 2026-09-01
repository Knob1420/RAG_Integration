"""TASK-P00-002 测试：空目录、重复运行、新增、修改、删除、不支持扩展名。"""

import csv

from scripts.build_manifest import build_manifest, make_source_id


def make_file(root, rel, data=b"%PDF-fake"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def read_rows(csv_path):
    with csv_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_empty_dir(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    r = build_manifest(mats, out)
    assert r["total"] == 0 and r["added"] == 0
    assert read_rows(out) == []


def test_repeat_run_stable_source_id(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "sub/a.pdf")
    build_manifest(mats, out)
    first_ids = [r["source_id"] for r in read_rows(out)]
    r2 = build_manifest(mats, out)
    assert r2["added"] == 0 and r2["changed"] == 0 and r2["removed"] == 0
    assert [r["source_id"] for r in read_rows(out)] == first_ids
    assert first_ids == [make_source_id("sub/a.pdf")]


def test_added_file_reported(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "a.pdf")
    build_manifest(mats, out)
    make_file(mats, "b.docx")
    r = build_manifest(mats, out)
    assert r["total"] == 2 and r["added"] == 1
    assert r["added_paths"] == ["b.docx"]


def test_removed_file_reported(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "a.pdf")
    make_file(mats, "b.pdf")
    build_manifest(mats, out)
    (mats / "b.pdf").unlink()
    r = build_manifest(mats, out)
    assert r["total"] == 1 and r["removed"] == 1
    assert r["removed_paths"] == ["b.pdf"]


def test_modified_file_detected_same_source_id(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "a.pdf", data=b"v1")
    build_manifest(mats, out)
    old = read_rows(out)[0]
    make_file(mats, "a.pdf", data=b"v2-content-changed")
    r = build_manifest(mats, out)
    assert r["changed"] == 1 and r["changed_paths"] == ["a.pdf"]
    new = read_rows(out)[0]
    assert new["sha256"] != old["sha256"]
    assert new["source_id"] == old["source_id"]  # 内容变化不换 id，保留血缘


def test_unsupported_extension_ignored(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "notes.txt")
    make_file(mats, "real.pdf")
    make_file(mats, "photo.jpg")
    r = build_manifest(mats, out)
    assert r["total"] == 1
    assert read_rows(out)[0]["file_name"] == "real.pdf"


def test_office_lock_file_excluded(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "real.docx")
    make_file(mats, "~$real.docx")  # Office 锁临时文件
    r = build_manifest(mats, out)
    assert r["total"] == 1
    assert read_rows(out)[0]["file_name"] == "real.docx"


def test_unknown_fields_and_mtime_field_name(tmp_path):
    mats, out = tmp_path / "mats", tmp_path / "data_manifest.csv"
    mats.mkdir()
    make_file(mats, "a.pdf")
    build_manifest(mats, out)
    row = read_rows(out)[0]
    assert row["document_version"] == "UNKNOWN"
    assert row["safety_level"] == "UNKNOWN"
    assert "filesystem_mtime" in row  # mtime 不冒充 document_version
