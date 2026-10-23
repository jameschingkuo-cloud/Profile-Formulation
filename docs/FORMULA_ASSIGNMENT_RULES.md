# Formula assignment rules (James Kuo, from 23 Oct 2026)

James, 23 Oct 2026: *"our current solution is not possible. There are too many new product code which make the one to one
match not very useful. To make it work, we need to build logic system so that you assign formulation to product base on
logic"*. He annotated the W% Master Formulation draft (Notes column: Main / Secondary / replace by / archive / remove /
rename) and gives the rules below. Each rule is quoted as he gave it, then what it means for the code, then how it tests
against the data on file. Nothing here is applied until the rule tests clean and James has seen the result.

## R1. Colour decides the grade letter
James: *"a few rules for general, if its color (not black or white) its always graphic grade order (FUA, FAA etc)"*.
- Colour other than KS (black) and WB (white) -> graphic grade -> third character of the code is `A` (FUA…, FAA…, FHA…, FRA…).
- KS and WB orders: the grade comes from the schedule (grade A = graphic -> `A`; grade P = packaging -> `0`), to be confirmed.
- **Exception: the bubble line** (SE61, co-extrusion, James's "BB line"; codes BF…). James, 23 Oct: *"bubble line are
  expection. so BF does not apply to this rule. its BF0 even when its EB"* - *"we cant make the bubble process smooth
  enough to product graphic grade at this moment"*. A BF code always has `0` in the third place: the bubble line makes
  packaging grade only, so a coloured order there is still `0`.
- Test, 23 Oct: of James's Main/Secondary rows for colours other than KS/WB, 64 carry `A` after his renames; the 24 that
  keep `0` are customer-specific (Carter, Orbis, Tzu-Chi), roll, HDPE (HU…), the BB line (BF…), PE, flame-retardant and a
  few standard ones (FU0001EAD, FU0151EB4, FU1400GD4, FU0000NC6, FU0000NSG, FU0001SSA, FU001TLW4, FU001EAW4).
  James, 23 Oct: the standard ones get `A` too (*"A. did i miss them in the notes?"*): FU0001EAD -> FUA001EAD,
  FU0151EB4 -> FUA151EB4, FU0000NC6 -> FUA000NC6, FU0000NSG -> FUA000NSG, FU0001SSA -> FUA001SSA; the exact spelling of
  FU1400GD4, FU001TLW4 and FU001EAW4 (four digits / three-letter premix colour) to come from James. Customer-specific,
  roll, HDPE (HU), BB line (BF) and PE codes keep what his notes say.
- Why (James, 23 Oct): *"because we cant feed reclaim in anyways as its too hard to control color, so no reason that to
  make them graphic"*: a coloured order never takes reclaim, so it is graphic grade by nature.

## R2. Reclaim only in black and white
Follows from R1's reason: reclaim (PP WB / Mix Reclaim, the RU… codes, "Secondary packing grade", R4 = 100% reclaim) is
used only for KS and WB orders. Test, 23 Oct: see the reclaim-by-colour count below R1 in the chat log; to be written in
once confirmed.

## R3. The schedule's Spec column is the quality grade; R4 is mostly reclaim
James, 23 Oct 2026 (answering what decides black/white): *"R1 is standard and R4 is the worst grade so R4 is mostly reclaim"*.
- Spec R1R1R1 = standard board; R4R4R4 = lowest grade -> a reclaim formulation (RU…, "R4" in James's notes). R2 / R3 sit between
  (his notes: RU0001WB4 "R2 LTL wrap", FUA011WB5 "4.6mm, Triple wall, R3").
- Test, 23 Oct (James's Main rows with a run on file): R4R4R4 -> reclaim median 97%; R2R2R2 -> 28%; R1R1R1 and R3R3R3 -> 0%.
- Observed with it, every Tech issue on file (latest per line + product): the Spec decides the code's first two letters.
  To confirm with James before use:

  | Spec (schedule) | Code starts | Meaning (James's words / notes)              |
  |-----------------|-------------|----------------------------------------------|
  | R1R1R1          | FU          | standard                                     |
  | R2R2R2          | RU / FU     | LTL wrap, some reclaim ("R2")                |
  | R3R3R3          | FU          | triple wall ("R3")                           |
  | R4R4R4          | RU          | worst grade, mostly reclaim                  |
  | OPOPOP          | FX          | extra opaque ("OP")                          |
  | S1S1S1          | FS          | ultra smooth ("S1")                          |
  | A1A1A1          | FA          | anti-static                                  |
  | U1U1U1          | FE          | extra UV ("U1"). James, 23 Oct: *"Extra UV is FE"*; FH on old pages is the same thing |
  | F1F1F1 / F4F4F4 | FR          | flame retardant                              |
  | R6R6R6, RDRDRD, RMR6R6 | BF   | the BB line (SE61 co-extrusion)              |

## R4. The three middle digits are a sequence number
James, 23 Oct 2026: *"just sequence. when we replace them with new version of the same product"* - *"version #"*.
- They carry no composition meaning. A new version of a formulation for the same product gets the next number; which
  version is current is what James marked **Main** (and **Secondary**) in the W% Master. So the assignment is a lookup,
  not a computation: prefix (R3) + grade letter (R1) + colour and thickness (from the product code) + the order's
  application (VOIDFORM, corn box, sign blank, customer, season ...) -> the Main row -> its code.

## First test of the lookup (23 Oct 2026)
112 product/line pairs the Word formulation left to the engineer between 8 and 23 Oct, through R1-R4 and James's Main
rows (prefix from the Spec, grade letter from the colour / schedule grade, colour and thickness from the product code):
- 24: Main found and its settings are known on that line -> could have been issued.
- 50: Main found, but it has never run on that line -> needs the line settings (auger calculation from the W%).
- 18: more than one Main for the key: WB 4 mm graphic (FUA151WB4 "Summer" vs FUA152WB4 "Winter": 14 orders on SE13,
  SE31, SE32), KS 3 mm packaging (FU0032KS3 vs FU0051KS3), KS 6.3 mm, WB 4 mm VOIDFORM (FU0021WB4 vs FU0151WB4 "SE43").
- 20: no W% Master row for the key: SE61 EB 3/5 mm (BF… are co-extrusion, "Not computed" - Tech's own SE61 pages have
  them, so the lookup must also take a code already issued on the line), PK 2 mm anti-static, FW 4 mm flame retardant,
  WB 3 mm opaque.

## R5. Summer and winter formulations
James, 23 Oct 2026: *"winter start in start of nov. Summar starts in the start of april"*.
- Winter formulation from 1 November to 31 March; summer formulation from 1 April to 31 October. The schedule's run date
  decides (today's formulation is for the schedule in hand).
- Where it applies: a key with a "Summer" Main and a "Winter" Main in the W% Master. On 23 Oct that is WB 4 mm graphic
  only: FUA151WB4 "Main Summer fomulation" and FUA152WB4 "Main Winter Formulation" (James's rename of FUA151WB4 2 of 2).
  Tech's own 2026 issues agree: SE13 / SE31 / SE32 ran FUA152WB4 on 23 Sep - 7 Oct and FUA151WB4 for the SE43 group - to
  be checked against the season boundary when the November pages come in.
- What the data shows (23 Oct): the season is a **composition** switch, not a change of the printed name. Tech's pages
  print FUA152WB4 on the auger lines and FUA151WB4 on SE43 in every month on file; but the composition behind them changes:
  Aug-Oct issues (2020, 2021, 2025, 2026) run about 74% virgin / 15% homopolymer F1203K / 8-9% talc (James's "Summer"),
  the 28 Oct 2022 issue for the Dec 2022 - Jan 2023 runs about 80% virgin / 8% homopolymer / 9% talc ("Winter"). So under
  James's naming the lookup prints FUA151WB4 (1 Apr - 31 Oct) or FUA152WB4 (1 Nov - 31 Mar), and each line's settings must
  be keyed by (line, season composition), not by the name Tech printed before. Tech issued the winter pages on 28 Oct
  2022, a few days before 1 Nov.

## Built: daily/assign.py (23 Oct 2026)
`daily/resolve.py` now asks the rules for every order with no earlier issue on its line and no approved master row;
`ASSIGN_RULES=0` turns them off. A proposal prints as PROPOSED BY RULE (code) on every row; a Main never run on the line
stays an Exception that names the code and its W%. Backtest (`tests/test_assign.py`; `work/backtest_rules.py -v` lists
the misses), as each morning before Tech issued, on the 145 orders the issue history could not answer:
- 109 (75%): the rule names the formulation Tech issued that day (17 with the very settings, 8 with settings Tech then
  tuned, 84 naming the code where the line had no settings yet).
- 23: a different one. Mostly James's cleanup, where Tech's page still printed a code he replaced (WB 4 mm packaging:
  his Main FU0031WB4 vs FU0041WB4 / FU0021WB4 / FUA152WB4 on SE12, SE13, SE24, SE25; WB 5 mm VOIDFORM: his Main FU0051WB5
  vs FU0011WB5 "secondary Voidform"); and the weight-blender lines, to settle with James: SE43 prints FU0151WB3 for WB
  3 mm packaging (his notes: Secondary; FU0032WB3 Main) and FU0010GS3 / FU0010BD3 / FUA000BD3 for coloured 3 mm (R1 says
  FUA151GS3 / FUA151BD3); SE42 prints FU0151KS3 for CPP30KS215 (his note: "Main SE43 only"; KS 3 mm packaging has two
  Mains, FU0032KS3 and FU0051KS3). The GT premix orders (DPP40WB1700: FU001GTW4 / FU0021GT4, his note "???") are left
  to the engineer.
- 13: no proposal, the bubble line on 23 and 28 Sep before any SE61 issue was on file (the line fallback needs one).
25 Sep as that morning (`tests/test_resolve.py`): both new orders proposed by rule with the codes Tech issued that day
(FU0021WB4, FXA020WB4), nothing left for the engineer. 23 Oct: 70 orders instead of 41 (29 by rule, all with settings),
29 Exceptions instead of 58, 25 of them naming the code and waiting only for line settings (FU0031WB4 on SE12/13/23/25/31,
FU0061WBD on SE32, FUA031KS5/6 and FUA032KS4 on SE21 ...).

## Settings carry over only for the same formulation (23 Oct 2026)
A "replace by ..." note means two things. Where the old row has the same composition as James's Main (every group within
2.5 points: FUA152WB4 on the auger lines in Sep 2026 -> his FUA151WB4 "Summer"), it is the same formulation under an older
name: the line's settings printed under the old name carry over. Where the composition differs (FU0041WB4, 30% reclaim ->
FU0031WB4; FU0011WB5 -> FU0051WB5 for VOIDFORM), it is a replacement: the Main needs its own settings on the line (the
auger calculation), and the old settings are never reused. `daily/assign.py` `same_composition` / `replace_target`; the
revision-2 workbook's "Replaced" sheet says which is which. With this, the backtest counts 99 of 145 as the same
formulation Tech issued and 33 as different - the 10 that moved are Tech printing a code James replaced.

## Revision 2 of the W% Master (23 Oct 2026)
James: *"keep this excel in your MD file and produce a revision"*; *"make a new Master W % formulation excel for me to
review and clean up"*; *"capture all the indicators like OP, R1, A1 etc"*. `calc/revise_w_master.py` ->
`W% Master Formulation (draft v2).xlsx` (published to the workspace): his Main / Secondary rows under the names he gave
(old names as "Printed as"), the indicator each prefix stands for (R1/R2/R3, R4, OP, S1, A1, U1, F1/F4, bubble line) next
to the Spec and grade the schedule printed on the formulation's latest run (amber where they disagree), "Replaced" (same
formulation or other composition), "Archived", and "Open for James" with what the notes do not settle.

## R6. The printout uses James's names, never an old code (23 Oct 2026)
James: *"Don't use old formula code in the print out"*. Every row of the Word formulation (and the Draft, the page) shows
the code under the name James gave in the W% Master: a Main's old names (renames, and same-composition rows he folded
into it) print as the Main - FUA152WB4 on an auger line in summer prints FUA151WB4, FU0001RF6 prints FUA001RF6, RU0000KS3
prints RU0001KS3; the name Tech printed stays in the Draft's Source column ("printed as ..."), the settings are Tech's as
issued, untouched. `daily/assign.py` `current_name` (an old name that is nowhere current, pointing to one Main) and, for an
order's issued rows, the Main the rules name for that order; a name still current (FUA152WB4 is the winter name and the
sign-blank Main) or pointing to two Mains (FH0001NSA) stays as printed. `ASSIGN_RULES=0` prints the codes as Tech did.

## Next: line settings from the W% (the auger calculation), first backtest (23 Oct 2026)
For a Main never run on a line: setting = W% x the line's throughput / the hopper's calibration slope (Tech's calc
library: current slopes per line / hopper / material; the recipes' g/min), each material on the hopper that carries its
role on that line (`calc/auger_rules.py`). Cross-line backtest (`work/backtest_auger3.py`): a recipe's settings on line L
predicted from the same code's composition on another line, with L's slopes and L's usual throughput for the order's GSM
(69 recipes, 310 hopper settings): median error 1.1 setting points, 63% within 2, 80% within 5, 90% within 10. The tail is
throughput (an order run slower than the line's usual rate: FUA051KSA 10 mm on SE21/22) and tiny-slope additive hoppers
(FR0021GS4 H5). So calculated settings must print as such - PROPOSED SETTINGS (calculated), with the W% and the assumed
throughput beside them, for Tech to check - never as issued settings. James to see these numbers before it goes in.

## 3 mm VOIDFORM, checked in the records (23 Oct 2026)
James: *"For the one that said void form. I think you probably put it as standard and that's why I missed it during clean
up. Check old record for 3mm void form formula"*. Every Tech issue on file: SE11 prints FU0022WB3 "(For VOIDFORM order
only)" for the 3 mm WB VOIDFORM orders (24 issues since 23 Sep; the calc library notes it "Void Form" since 2023) - James
marked it Main Voidform. SE43 prints FU0151WB3 for its 3 mm WB orders, VOIDFORM (H69A038-1, 28-30 Sep) and plain
packaging (H69A183-2/-3, H69A330-3, 6-7 Oct) alike; revision 1 labelled it "Standard" because its latest run was the
VOIDFORM order and the page row carried no "(For VOIDFORM ...)" note, so James's note became "Secondary Packing grade".
Proposed: FU0151WB3 = "Main SE43" for 3 mm WB, as FU0151KS3 ("Main SE43 only") and FU0151WB4 ("Main Voidform, SE43").
On the "Open for James" sheet of revision 2.
