"""Auger (hopper) preference rules: DRAFT for James to confirm (25 Sep 2026).
Per line, which material role each hopper may carry. Derived from the 2025-26 calc blocks,
the plant's 'Extruder Blender - Hopper Auger Ratios' master table (lines 1-3 run #1 colour ->
#4 virgin; lines 4-10 run #1 virgin -> #4 colour) and James's Line 6 rule (25 Sep 2026):
'Auger 1 2 and 3 are larger so 1 and 3 are usually the main PP (6502A / 1203K / reclaim),
2 feeds talc, 4 colour (W26038A), 5 CaCO3.'
Read the function, not the number: hopper numbers do not carry between lines."""

# ---- DOSING TYPE PER LINE (James Kuo, 26 Sep 2026) -- DO NOT CHANGE WITHOUT JAMES'S SAY-SO ----
# "line 7, 12, 13, and 16 use more modern weight based dosing. The rest of the lines use old Auger dosing.
#  ... the motor rotation speed is no RPM or some measurement. It is simply speed setting 0 to 100."
# WEIGHT: Set = weight % per extruder (adds to 100; one feeder may be 'Auto' = the balance). No slope.
# AUGER : Set = motor speed 0-100 with no RPM feedback. Weight % only through slope x setting.
#         The hopper rules (RULES) and checks A1-A7 apply to AUGER lines only.
# Same table as packet_extract/load.py DOSING: change both together.
DOSING = {'SE24': 'WEIGHT', 'SE42': 'WEIGHT', 'SE43': 'WEIGHT', 'SE61': 'WEIGHT',
          'SE11': 'AUGER', 'SE12': 'AUGER', 'SE13': 'AUGER', 'SE21': 'AUGER', 'SE22': 'AUGER',
          'SE23': 'AUGER', 'SE25': 'AUGER', 'SE31': 'AUGER', 'SE32': 'AUGER'}
import re

def role(material_key, raw=''):
    k = (material_key or '').upper(); r = (raw or '').upper()
    if k == 'VIRGIN PP': return 'VIRGIN'
    if k in ('1203K', '1102K'): return 'HOMO'
    if 'RECLAIM' in k or k.startswith('RCP'): return 'RECLAIM'
    if k == 'TALC': return 'TALC'
    if k == 'CACO3': return 'CACO3'
    if k == 'VISTAMAXX': return 'MODIFIER'
    if k.startswith('HDPE'): return 'HDPE'
    if re.match(r'^(UV|AS|FR|FA)[- ]', k) or 'REASKEM' in k or 'AS-401' in k: return 'ADDITIVE'
    if k in ('WB COLOR', 'KS COLOR') or re.search(r'COLOR|NPC|MB\b|PRE-?MIX|^(EA|EC|OF|BL|BD|RF|YF|LY|KF|OG|WB)[- ]|^[A-Z]{1,2}-?[A-Z]?\d{5}[A-Z]', k): return 'COLOUR'
    return 'OTHER'

# (line) -> {hopper: (hardware, main role, allowed roles)}
V, H, R, T, C, K, M, A, P = 'VIRGIN', 'HOMO', 'RECLAIM', 'TALC', 'CACO3', 'COLOUR', 'MODIFIER', 'ADDITIVE', 'HDPE'
L1_2 = {'H1': ('1:36 15x25', K, {K, A}),
        'H2': ('1:36 39x39', T, {T}),
        'H3': ('1:36 69x69', H, {H, R, A}),
        'H4': ('1:36 69x69', V, {V}),
        'H5': ('1:36 39x39', C, {C, M})}
# Lines 4-6: H1 and H3 are the two large PP augers. H1 (1:14, fastest) takes the biggest PP stream,
# H3 the second: copolymer, homo or reclaim in either (James, 25 Sep 2026). What must follow the
# material is the calibration slope (check A2), not the hopper.
L4_6 = {'H1': ('1:14 69x69', V, {V, R, H}),
        'H2': ('1:36 69x69', T, {T}),
        'H3': ('1:36 69x69', H, {H, R, V}),
        'H4': ('1:70-1:100 45-49', K, {K, A}),
        'H5': ('1:36 39x43', C, {C, M, A})}
RULES = {
 'SE11': L1_2, 'SE12': L1_2,
 'SE13': {'H1': ('1:36 15x25', A, {A, C}),
          'H2': ('1:36 39x39', T, {T}),
          'H3': ('1:36 69x69', H, {H, R}),
          'H4': ('1:14 69x69', V, {V, R}),
          'H5': ('1:36 39x39', K, {K, A, M})},
 'SE21': L4_6, 'SE22': dict(L4_6, H5=('1:36 69x69', C, {C, M, A})), 'SE23': L4_6,
 'SE31': {'H1': ('1:14 69x69', V, {V}),
          'H2': ('1:36 69x69', H, {H, R}),
          'H3': ('1:36 69x69', T, {T}),
          'H4': ('1:70 49x49', K, {K, A}),
          'H5': ('1:36 39x43', C, {C, M, K})},
 'SE25': {'H1': ('1:14 69x69', V, {V, R}),
          'H2': ('1:36 69x69', H, {H, R, V}),
          'H3': ('1:36 69x69', C, {C}),
          'H4': ('1:70 49x49', K, {K, A}),
          'H5': ('1:36 39x43', T, {T})},
}
RULES['SE32'] = RULES['SE31']


# ---- A7: slope must fit the hardware (auger lines) ----
# The auger turns at (setting/100) x motor speed / gear ratio, so g per auger turn is proportional to
# slope x gear ratio. For one screw size and one kind of pellet that number is a property of the hardware,
# the same on every line. In the 2025-26 calcs it is: PP pellets on 69x69 = 2,969 (1:36) / 3,068 (1:14);
# reclaim 3,140 / 3,245; talc 69x69 5,354; CaCO3 69x69 6,380, 39x43 1,106, 39x39 1,003; talc 39x39 842,
# 39x43 928; colour 49x49 1,226; colour 15x25 202.  A slope more than ~8% off its hardware norm is either a
# slope copied from another hopper/material or a gear ratio that is not what the header says.
def gear(g):
    try: return float(str(g).split(':')[1])
    except Exception: return None

def rev_index(slope, gear_ratio):
    q = gear(gear_ratio)
    return slope * q if (slope and q) else None

def setting_resolution(slope, setting):
    """Relative change in that feeder's dose from one step of the 0-100 dial (integer settings)."""
    return 1.0 / setting if setting else None
