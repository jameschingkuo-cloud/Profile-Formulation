"""The order number, as a hard rule. Read from the system's own schedules (Technical Engineering Team/Production
Instruction, 1,162 days, 2020-04-01 to 2026-09-24; history/prod_instr.py, history/analyze.py), 30 Sep 2026:

    H 6 9 A 039 - 1        H orders:  H + year digit + month + A + 3 digits
    SH 6 9 A 04 - 1        SH orders: SH + year digit + month + A + 2 digits
    RP 26 8 21 - 1         RP orders: RP + 2-digit year + month + 2 digits
    month = 1-9, A (Oct), B (Nov), C (Dec); suffix = 1-2 digits (max 43 seen)

Every order printed since August 2022 keeps this (the letter A after an H/SH month: 39,307 of 39,307; 2020-21 H orders used
a year letter, V = 2020, W = 2021; the last left the schedule on 27 Jul 2022). An order is never dated after the schedule it is on (0 of
62,662 rows). H and SH orders are always under 2 years old on a schedule (26,779 rows); RP stock orders can be old
(RP20624-1 was still scheduled on 9 Sep 2026, 75 months on), so they have no age limit.

James Kuo, 30 Sep 2026 (the product-code rules): "these need to be hard rule. If anything odd is spotted, recheck the OCR
again". The first rule (H + 2 digits + letter + 3 digits) had the month and the A the wrong way round: it refused every
October-December H order (H5CA..., H6AA...) and a reader could turn the month A into a 4.
"""
import re
from datetime import date

MONTHS = '123456789ABC'
MONTH = {c: i for i, c in enumerate(MONTHS, 1)}
ORDER_RX = re.compile(r'^(H\d[1-9A-C]A\d{3}|SH\d[1-9A-C]A\d\d|RP\d\d[1-9A-C]\d\d)-(\d{1,2})$')
BASE_RX = re.compile(r'^(H\d[1-9A-C]A\d{3}|SH\d[1-9A-C]A\d\d|RP\d\d[1-9A-C]\d\d)$')


def opened(order, on=None):
    """(year, month) the order was opened, from its number; None if the number breaks the rule. A one-digit year is
    the latest year ending in that digit that is not after `on` (the schedule date; default today)."""
    base = (order or '').split('-')[0]
    if not BASE_RX.match(base):
        return None
    on = on or date.today()
    if base.startswith('RP'):
        return 2000 + int(base[2:4]), MONTH[base[4]]
    k = 1 if base[0] == 'H' else 2
    y = on.year - (on.year - int(base[k])) % 10
    return y, MONTH[base[k + 1]]


def problems(order, on=None):
    """[] when the order number keeps the rule (and, given the schedule date `on`, is not dated after it)."""
    order = order or ''
    if not ORDER_RX.match(order):
        return ['order number does not fit H + year + month + A + 3 digits, SH + year + month + A + 2 digits, or '
                'RP + 2-digit year + month + 2 digits, then -suffix (month 1-9, A, B, C)']
    if on:
        y, m = opened(order, on)
        if (y, m) > (on.year, on.month):
            return [f'order dated {y}-{m:02d}, after the schedule date {on.isoformat()}']
        if order[0] in 'HS' and (on.year - y) * 12 + on.month - m >= 24:     # H/SH: under 2 years in every schedule
            return [f'order dated {y}-{m:02d}: an H/SH order two years or more before the schedule ({on.isoformat()})']
    return []
