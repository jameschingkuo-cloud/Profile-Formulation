"""The product code, as a hard rule (James Kuo, 30 Sep 2026). Used by the scan readers, the daily checks and the Product
Master build, so a misread code can never be taken as a product.

    RPA 40 WB 3051
    |   |  |  +- product number: digits only ("after that is just number for the product. No english characters")
    |   |  +---- colour: two letters from the plant's colour list ("the color code is WB. WR dont exist")
    |   +------- thickness: digit 1-9 or letter A-Z, then a digit ("10 means 1mm and 90 means 9mm. A0 is 10mm and B0 is
    |            11mm"; 63 = 6.3 mm, 33 = 3.3 mm). "AQ" can never be a thickness ("so AQ is incorrect from the start")
    +----------- family: three letters (RPA, RPP, DPP, RBP, SPA, CPP, DBP, SPP, DPA, APA, DCP)

"these need to be hard rule. If anything odd is spotted, recheck the OCR again": a reader that gets a code breaking
these rules reads the cell again (other settings); a code that still breaks them is never taken, it is shown for a person.
"""
import re

CODE_RX = re.compile(r'^([A-Z]{3})([1-9A-Z])([0-9])([A-Z]{2})([0-9]{1,5})$')

# Families and colours in use (Product Master, 30 Sep 2026). A code outside these lists is not impossible (a new family or
# colour), but it is "odd": re-read, then shown for a person to confirm. Never auto-accepted.
FAMILIES = {'RPA', 'RPP', 'DPP', 'RBP', 'SPA', 'CPP', 'DBP', 'SPP', 'DPA', 'APA', 'DCP'}
COLOURS = {'WB', 'KS', 'BL', 'EB', 'NS', 'EA', 'YF', 'GS', 'JG', 'BD', 'OG', 'WM', 'SS', 'RF', 'OF', 'NC', 'PK', 'TS', 'LY',
           'IS', 'GE', 'GH', 'FW', 'BR', 'LG', 'EC', 'OH', 'GF', 'KF', 'GA', 'LT', 'TF', 'BF', 'GT'}

# OCR look-alikes, used only to repair a position whose kind is fixed by the rule (a digit position read as a letter...)
TO_DIGIT = {'O': '0', 'D': '0', 'Q': '0', 'U': '0', 'I': '1', 'L': '1', 'T': '1', 'J': '1', 'Z': '2', 'S': '5', 'G': '6',
            'B': '8', 'A': '4', 'E': '6', '/': '7'}
TO_LETTER = {'0': 'O', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '8': 'B', '7': 'T'}
LOOKALIKE_LETTERS = {'B': 'RE8', 'R': 'B', 'W': 'NM', 'N': 'WM', 'M': 'NW', 'O': 'DQ0', 'D': 'O0', 'S': '5', 'E': 'FB',
                     'F': 'E', 'I': '1LT', 'G': '6C', 'C': 'G'}


def thickness_mm(code):
    """RPA40WB3051 -> 4.0; RPAA0WB318 -> 10.0; RPP63RF1 -> 6.3. None if the code breaks the rule."""
    m = CODE_RX.match(code or '')
    if not m:
        return None
    t1, t2 = m.group(2), int(m.group(3))
    return (int(t1) if t1.isdigit() else 10 + ord(t1) - ord('A')) + t2 / 10


def problems(code, known_families=FAMILIES, known_colours=COLOURS):
    """[] when the code keeps every rule; else what is wrong, in words."""
    code = code or ''
    m = CODE_RX.match(code)
    if not m:
        out = []
        if not re.match(r'^[A-Z]{3}', code): out.append('family is not three letters')
        if len(code) < 5 or not re.match(r'^[1-9A-Z][0-9]$', code[3:5]): out.append(f'thickness "{code[3:5]}" is not a digit 1-9 or letter then a digit')
        if len(code) < 7 or not re.match(r'^[A-Z]{2}$', code[5:7]): out.append(f'colour "{code[5:7]}" is not two letters')
        if not re.match(r'^[0-9]{1,5}$', code[7:]): out.append(f'product number "{code[7:]}" is not digits only')
        return out or ['does not fit family + thickness + colour + number']
    out = []
    if m.group(1) not in known_families: out.append(f'family {m.group(1)} not in use')
    if m.group(4) not in known_colours: out.append(f'colour {m.group(4)} not in the colour list')
    return out


def repair(token, known_colours=COLOURS):
    """Positional repair of an OCR reading: letters where letters belong, digits where digits belong, a colour from the
    list. Returns (code, changed) or (None, False) when no reading keeps the rules. Several candidates -> None."""
    t = re.sub(r'[^A-Z0-9/]', '', (token or '').upper())
    if len(t) < 8:
        return None, False
    fam = ''.join(TO_LETTER.get(c, c) for c in t[:3])
    th1 = t[3]
    th2 = TO_DIGIT.get(t[4], t[4])
    num = ''.join(TO_DIGIT.get(c, c) for c in t[7:])
    col_raw = ''.join(TO_LETTER.get(c, c) for c in t[5:7])
    cands = {col_raw} if col_raw in known_colours else {
        a + b for a in {col_raw[0], *LOOKALIKE_LETTERS.get(col_raw[0], '')} for b in {col_raw[1], *LOOKALIKE_LETTERS.get(col_raw[1], '')}
        if a + b in known_colours}
    if len(cands) != 1:
        return None, False
    code = fam + th1 + th2 + cands.pop() + num
    if not CODE_RX.match(code):
        return None, False
    return code, code != t
