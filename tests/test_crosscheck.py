import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scan_reader"))
import crosscheck  # noqa: E402


def test_24_sep_regression():
    """HANDOFF §7.7 second-day test: 76 of 80 orders identical; the reader's misreads show up as differences."""
    res = crosscheck.crosscheck(ROOT / "data/packets/packet_2026-09-24.json", ROOT / "data/ext_read_2026-09-24.csv")
    assert res["orders_transcribed"] == 80
    assert res["agree"] == 76
    where = {w for _, w, _ in res["problems"]}
    assert {"H69A066-2", "H69A237-2", "RP26826-1", "RP26410-1"} <= where
    # every printed line total ties to its rows, except SE25 whose total page was missing that day
    assert [p for p in res["problems"] if p[1].startswith("SE")] == [
        ("Medium", "SE25", "no printed line total found on the transcription")]
