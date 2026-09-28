import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import publish  # noqa: E402


@pytest.fixture
def roots(tmp_path, monkeypatch):
    db, ws, out = tmp_path / "db", tmp_path / "workspace", tmp_path / "out"
    for d in (db, ws, out):
        d.mkdir()
    monkeypatch.setattr(config, "PUBLISH_DIR", db)
    monkeypatch.setattr(config, "DOCS_DIR", ws)
    monkeypatch.setattr(config, "OUTPUT_DIR", out)
    monkeypatch.setattr(config, "READS", tmp_path / "reads.json")
    monkeypatch.setattr(publish, "MANIFEST", tmp_path / "manifest.json")
    return db, ws, out


def test_database_files_go_to_their_folder_and_the_rest_to_the_workspace(roots):
    db, ws, _ = roots
    assert publish.destination("Product Master.xlsx") == db / "Product Master" / "Product Master.xlsx"
    assert publish.destination("FRM Formulation Report 2026-09-25.xlsx") == \
        db / "Daily Formulation Report" / "FRM Formulation Report 2026-09-25.xlsx"
    assert publish.destination("Converting Production Record.xlsx") == \
        db / "Converting Schedule" / "Converting Production Record.xlsx"
    assert publish.destination("HANDOFF - Production Formulation Automation.md") == \
        ws / "HANDOFF - Production Formulation Automation.md"
    assert publish.rel(ws / "notes.md") == "workspace/notes.md"


def test_publish_then_refuse_an_edited_file(roots):
    db, ws, out = roots
    (out / "notes.md").write_text("v1", encoding="utf-8")
    publish.main(["notes.md"])
    assert (ws / "notes.md").read_text(encoding="utf-8") == "v1"
    (ws / "notes.md").write_text("edited by someone", encoding="utf-8")   # an engineer edits the published copy
    (out / "notes.md").write_text("v2", encoding="utf-8")
    with pytest.raises(SystemExit, match="refused"):
        publish.main(["notes.md"])
    assert (ws / "notes.md").read_text(encoding="utf-8") == "edited by someone"
