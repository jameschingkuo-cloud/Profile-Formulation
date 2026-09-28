import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "product_master"))
import prepare  # noqa: E402


def test_thickness_from_code():
    assert prepare.decode_code("RPA40WB3051")["thk"] == 4.0
    assert prepare.decode_code("RPP33WB12")["thk"] == 3.3
    assert prepare.decode_code("RPAA0WB318")["thk"] == 10.0
    assert prepare.decode_code("RBPD0EB1")["thk"] == 13.0


def test_code_letters():
    d = prepare.decode_code("RBP50EB10")
    assert (d["material"], d["grade"], d["colour"]) == ("BBB", "P", "EB")


def test_letter_o_for_zero():
    assert prepare.decode_code("DPPAOKS27") == {}
    assert prepare.suggest_code_fix("DPPAOKS27") == "DPPA0KS27"


def _rec(code, thk):
    return {"Product Code": code, "Thk (mm)": thk, "Formula Last Run": dt.date(2026, 9, 1)}


def test_in_between_thickness_is_low_not_conflict():
    res = prepare.analyse([_rec("RPP33WB1", 3), _rec("RPP40WB2", 10), _rec("RPP40WB3", 4)],
                          dt.date(2026, 9, 28))
    by_code = {f["Product Code"]: (f["Severity"], f["Category"]) for f in res["fixes"]}
    assert by_code["RPP33WB1"] == ("Low", "Thickness: confirm from spec")
    assert by_code["RPP40WB2"] == ("High", "Thickness conflict")
    assert "RPP40WB3" not in by_code


def test_multi_value_cells():
    assert prepare.numbers("4 | 4.3") == [4.0, 4.3]
    assert prepare.numbers("1,052") == [1052.0]
