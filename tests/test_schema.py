import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "db"))
sys.path.insert(0, str(ROOT / "calc"))
import schema  # noqa: E402
from auger_rules import DOSING  # noqa: E402


def test_refs_point_at_real_columns():
    for b in schema.BOOKS:
        for s in b.sheets:
            for c in s.cols:
                if c.ref:
                    book, sheet, col = c.ref.split("/")
                    target = {x.name: x for x in schema.BY_NAME[book].sheets}[sheet]
                    assert col in [x.name for x in target.cols], c.ref


def test_lines_match_dosing():
    assert {code for code, *_ in schema.LINES} == set(DOSING)


def test_every_book_has_read_me_and_a_folder():
    folders = {"Product Master", "Formulation Data Base", "Daily Formulation Report",
               "Extrusion Schedule", "Converting Schedule"}
    for b in schema.BOOKS:
        assert b.folder in folders, b.name
        if b.name.endswith(".xlsx"):   # the printed formulation (.docx) has no sheets; its cover carries the sources
            assert "Read Me" in [s.name for s in b.sheets], b.name


def test_destination_by_name():
    assert schema.destination("FRM Formulation Report 2026-09-24.xlsx") == "Daily Formulation Report"
    assert schema.destination("EXT Extrusion Schedule 2026-09-24.xlsx") == "Extrusion Schedule"
    assert schema.destination("Product Master.xlsx") == "Product Master"
    assert schema.destination("Formulation Master.xlsx") == "Formulation Data Base"
    assert schema.destination("something else.xlsx") is None


def test_templates_pass_their_own_check(tmp_path):
    for p in schema.templates(tmp_path):
        assert schema.check(p) == [], p.name


def test_check_catches_duplicate_key_and_bad_value(tmp_path):
    from openpyxl import load_workbook
    p = next(x for x in schema.templates(tmp_path) if x.name == "Formulation Master.xlsx")
    wb = load_workbook(p)
    ws = wb["Lines"]
    ws.append(["SE11", 1, "VOLUME", "Hopper 1-5", "1", "", None, "Yes"])
    wb.save(p)
    problems = schema.check(p)
    assert any("duplicate key" in what for _, _, what in problems)
    assert any("'Dosing'" in what for _, _, what in problems)
