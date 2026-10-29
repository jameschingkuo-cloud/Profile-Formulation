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


def test_docx_content_ignores_sharepoint_metadata(tmp_path):
    """James Kuo, 29 Oct 2026: a .docx compares by what it says (body, headers, footers). SharePoint's library properties
    added on upload (customXml, docProps) are not an edit; a change to the text is."""
    import zipfile
    import config

    def make(p, body, extra=None):
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('word/document.xml', body)
            z.writestr('word/footer1.xml', '<f>step 1</f>')
            z.writestr('docProps/core.xml', '<core/>')
            for n, v in (extra or {}).items():
                z.writestr(n, v)
    a, b, c = tmp_path / 'a.docx', tmp_path / 'b.docx', tmp_path / 'c.docx'
    make(a, '<w:body>FU0031WB4 90</w:body>')
    make(b, '<w:body>FU0031WB4 90</w:body>', {'customXml/item1.xml': '<sp/>', 'docProps/custom.xml': '<c/>'})
    make(c, '<w:body>FU0031WB4 85</w:body>')
    assert config.content_hash(a) == config.content_hash(b) != config.content_hash(c)
