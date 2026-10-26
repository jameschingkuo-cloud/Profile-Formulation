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
- Changed 24 Oct 2026. James, on H69A040-1 (CPP40WB320, SE25) printed "FU0031WB4 ENGINEER TO SET": *"What is the issue
  with line 10. You should have primary formulation for package grade white 4 mm"*. SE25 runs the packaging grade as
  FU0021WB4 (36% reclaim; his "replace by Main, packaging grade" into FU0031WB4, 20%). An old name James folded into a
  Main with another composition is that line's own recipe of the Main: its rows issued on the line are the Main's
  settings there, after the Main's own names (same composition) and with the reclaim presence matching. Only from Tech's
  issued pages, never an old name's calc-sheet recipe (SE13's FU062WB4 dates from 2019), and only from a group noted for
  the order's own qualifier or a plain one (SE25's FU0021WB4 roll groups stay with the rolls). Backtest on every Tech
  issue on file: 27 members gain settings, 19 equal to what Tech issued that day; the others are SE43 pages Tech changed
  on 7 Oct and the GT premix order H68A127-1. `assign.member_settings`; test `test_line_own_recipe_of_a_folded_formulation`.

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

## R7. The slitter takes the sign-blank formula
James, 23 Oct 2026: *"The slitter should use the same formula like SPA signs blank"*.
- A sign blank is an SPA (or SPP) product, or any order whose instructions send it to the slitter ("SEND TO SLITTER");
  it takes the Main James marked for sign blanks (WB 4 mm: FUA152WB4 "Main SPA"). A colour or thickness with no
  sign-blank Main takes its plain Main, as Tech prints (SPA40WM8 on SE31: FUA151WM4).
- Records, 2020-2026: every "SEND TO SLITTER" order on file is an SPA or SPP product (SE31 1,122, SE24 554, SE21 124 ...);
  on Tech's 2026 pages they print under "(For sign blank orders only)" / "SIGN BLANK" with FUA152WB4 (SE12, SE13, SE31,
  SE32, SE24), FUA151WM4 for the WM ones and FXA020WB4 for an OP one. `daily/assign.py` `wanted`.
- R6, checked on RP26717-1 (James, 23 Oct: *"RP26717-1 Sign blank why is that order sign blank. It's an RPA. Check
  logic system"*): the rules do not call it a sign blank (RPA, "RUN WITH NEXT"); the "(For sign blank orders only)"
  note and the FUA152WB4 settings are Tech's own 6-7 Oct SE13 page, where Tech grouped this order with the SPA sign
  blanks (as last issued). The naming had then wrongly renamed it to the summer FUA151WB4 by the printed code alone.
  26 Oct 2026, James on the same order: *"order RP26717-1 is just standard graphic 40. why is it using sign blank
  formula?"* / *"formulation is wrong too. it should use 48 tlc not 60"*. The order's own qualifiers decide, never the
  note of the group Tech put it in: it prints FUA151WB4 (`assign.names_for_issued`), and its own last issue lends its
  settings only when that group's notes ask for nothing the order lacks (`assign.member_settings`); otherwise a plain
  group on the line (SE13 23 Oct: talc 48, F1203K 25, virgin 48, WB 15). "RUN WITH NEXT" (run on the
  next order's formulation) is not read by the rules yet - noted for James.

## Settings sources, in order (23 Oct 2026)
James, on H68A244-1 (DPP50KS185, SE21, "Formula FU0041KS5 decided by rule; no settings on SE21"): *"you sure we don't have
this one? This is just black. Double check"*. Tech's SE21 calc sheet has had FU0041KS5 since May 2026; the lookup had only
read the FRM pages on file. A proposal's settings now come from, in order: (1) the formulation as Tech last issued it on
the line (an FRM page on file, under James's name or an old name of the same composition); (2) Tech's current calc
recipe for it on the line (`Formulation Calc Library.xlsx`, "Current Recipes", settings as Tech wrote them, materials
worded as the line's latest page prints that role on that hopper) - marked "settings from the calc sheet" on the row;
(3) none: an Exception that names the code. On 23 Oct this moves 21 of the 29 such orders into the formulation.

## The rules are the process (23 Oct 2026)
James: *"I think I know the problem. Moving forward, including today we use logic base formulation process. Remove old
logic and apply new."* From 23 Oct `daily/resolve.py` decides every order in this order: an engineer's approved decision
in the Formulation Master; then the rules (the Main for the product's fixed parts and qualifiers), with the settings from
this order's own last issue when that is the same formulation, else the line's latest issue of it, else Tech's calc
sheet; an order whose last issue was a formulation James replaced gets the Main and goes to the engineer if the line has
no settings for it. Only where the rules cannot decide (no Main, several Mains, no prefix rule) is the order printed as
last issued, marked RULES UNDECIDED. `ASSIGN_RULES=0` keeps the pre-23-Oct draft (each order as last issued) for the
backtests.
- James, 23 Oct 2026: *"No history process. If logic don't work, ask engineering for help"*. An order the rules cannot
  decide is an Exception for the engineer (its last issue, if any, is quoted as a note, never printed as the formulation).

## R8. Rolls and LTL wrap (23 Oct 2026)
James, on H69A284-3 (RPP40WB890 on SE25, spec R2R2R2, "ROLLS SAME AS ABOVE"): *"we don't have roll formulation??"*. The
rules had no roll qualifier and treated his "Main roll" rows as restricted, so the order fell to the packaging Main.
- A roll order says ROLLS / "Rolled material" in its instructions (1,967 of the 2,314 R2R2R2 orders on file); the rest
  say LTL / WRAP (the LTL wrap material). Spec R2R2R2 is their grade; the prefix stays FU for rolls.
- Rolls take James's "Main roll" for the colour and thickness (WB 4 mm: FU0021WB4, which Tech prints "(For roll material
  only) Check weight" with its run-out partner FU0001WB4 on SE25, 23-30 Sep 2026); LTL wrap takes RU0001WB4 "Main, R2
  LTL wrap" (Tech issued it for RP26923-1 on 25 Sep). The run-out row Tech prints with a Main now travels with it.
  `daily/assign.py` `wanted` / `derive`.

## R9. A Primary and its Secondary are both printed (23 Oct 2026)
26 Oct 2026, on RP26512-1 (Tech's SE21 page printed the same formulation twice, FU0041WB4 and FU0031WB4, as "run first"
/ "next"): *"i dont think we go with triple formulation now, just one primary and one secondary"*. Each member prints one
row: the one under James's own name, else Tech's first (`assign.one_row`).
James: *"When a formulation has primary and secondary, it means that both of them will need to be displayed, and let the
production team will then decide whether we have enough of particular material to run it or not. For example, if we
don't running out of reclaim, then the reclaim primary will be removed and replaced with virgin resin secondary."*
- An order's formulation is James's Primary (his Main) and, where he marked one for the same colour, thickness, prefix,
  grade and qualifiers, its Secondary. A qualified order without a Secondary of its own whose Primary runs reclaim takes
  the plain one (rolls: FU0014WB4). In every pair the rules give, the Primary has reclaim and the Secondary none (16
  pairs in the W% Master v2). `daily/assign.py` `secondary_for`, `formulation`.
- Each member gets its own rows on the line: the order's own last issue, then the line's issued groups (the one Tech
  noted for the order's qualifier first), then Tech's calc sheet. A row belongs to a member when its code is one of the
  member's printed names and it feeds reclaim exactly when the member's W% has reclaim (1 point or more), so the Primary
  and Secondary of one code (FUA060WBA, 44.5% and 0% reclaim) each get their own row. This is also why SE31's calc
  "FU0041WB4" and SE21's calc "FUA032KS4", recipes without reclaim, are no longer printed as the reclaim Mains.
  `assign.member_settings`.
- Printed Primary first (its rows in run order, reclaim first), then the Secondary, labelled "If reclaim runs out". A
  member with no settings on the line prints in its place, under its code, as one row "ENGINEER TO SET: settings for X
  on <line> · <role>", is listed on the FRM Draft's "Settings To Set" sheet (with James's W% and the order's last issue)
  and raises a High issue - also when no member has settings there yet: the formulation is decided, only the settings
  wait for the engineer. An Exception is now only an order the rules cannot decide ("Rules cannot decide: ...").
  `daily/resolve.py` `rule_rows`, `daily/render_frm.py`, the interface page.
- 23 Oct: 99 orders, 98 with a formulation by rule (26 with a Primary and a Secondary); 24 of them have a member whose
  settings an engineer sets (29 members); 1 Exception (RP26826-6, RPP40FW2: no flame-retardant FW 4 mm Main).
- Backtests see only the pages issued before their day: `HISTORY_BEFORE` now also limits the line's issued groups and
  feeder layouts. 25 Sep H68A153-1: FXA020WB4 with its settings to set, as SE31 first ran FXA020WB4 that day.

## R10. VOIDFORM never runs reclaim (23 Oct 2026)
James: *"Also, void form should not use any reclaim. Double check."* - *"There are some old void form formula that have
reclaim. I don't want them. The reclaim calcium is not stable. There are batches that have more calcium sometimes, there
are batches that have less calcium sometimes. Because void form, like I said, need to watch the weight. It makes it very
difficult to control the weight when we're running with reclaim."*
- A VOIDFORM order never gets a Primary or Secondary with reclaim in James's W%, nor a row that feeds reclaim from any
  source (its own last issue included). `assign.choose`, `secondary_for`, `formulation`.
- W% Master v2: James's "secondary Voidform" FU0011WB5 (35% reclaim) is archived; FU0011WB5 (52%), FU0041WBA (34%) and
  FU0061WBD (58%) stay as packaging Mains, marked "R10: never on a VOIDFORM order" (each last ran on one).
- Tech issued reclaim formulations on VOIDFORM orders: FU0011WB5 on SE25 (H64A244-1, H66A116-1, H68A090-1) and FU0061WBD
  on SE22 (H68A053-1); they are no longer printed. 23 Oct: the 6 VOIDFORM orders get FU0022WB3 (SE11), FU0021WB4
  (SE23), FU0051WB5 (SE25, 2 orders) and FU0001WBD (SE32, 2 orders); FU0051WB5 has never run on SE25 nor FU0001WBD on
  SE32, so those 4 print the code with "ENGINEER TO SET" until an engineer sets them.
- Tests: `tests/test_assign.py` `test_void_form_never_reclaim`, `test_primary_and_secondary_both_shown`,
  `test_primary_first_even_without_settings`.
- The interface page's "Generate the formulation from the schedule" (Daily run tab) no longer proposes from the issue
  history: it shows the rules' answer for the day the page was built for; any other day is decided by the daily run.

## R11. R4 black runs about 98% black reclaim and 2% black colour (24 Oct 2026)
James, on H6AA173-1 (RPP50KS2219, SE21, PPP P R4R4R4; RU0000KS5 never run there): *"remember the [auger] setting is
applied universally, right? So you can look at other [auger] setting with similar products such as black productions and
then put them together. And besides, if it's a R4 black production, it should run about 98% black reclaim and 2% black
color dye or master batch anyways. So take a look at that and see if you can complete this order for the KS5."*
- An R4 Primary (RU prefix, with reclaim) takes only R4 rows: reclaim with none of the virgin base (virgin PP,
  homopolymer, talc) fed - colour masterbatch and CaCO3 at most beside it (`assign.r4_recipe`). Before this, H6AA173-2
  (RPP40KS1905, R4 black 4 mm, SE21) printed a packaging recipe Tech had issued under FU0041KS4 (virgin 32, mix reclaim
  70, talc, CaCO3), an old name James folded into RU0000KS4; it now prints Tech's RU0000KS4 of 23-25 Sep (Mix Reclaim on
  hopper 3 at 99, KS colour on hopper 4 at 10).
- An R4 black Main with no R4 recipe on the line gets CALCULATED settings (`assign.r4_black_settings`): Tech's latest
  issued R4 black recipe on the line gives the hoppers; the reclaim hopper stays as Tech runs it and the colour hopper is
  set for 98/2 with the line's calibration slopes (calc library, "Auger Calibration"). If no R4 black was ever issued on
  the line: the line's R4 black recipe in Tech's calc sheet for the hoppers and slopes, and the line's black recipes of
  the same thickness for the throughput. Auger lines only.
- H6AA173-1, RU0000KS5 on SE21: Mix Reclaim hopper 3 at 99 (87.2 g/min per unit = 8,635 g/min), KS colour hopper 4 at
  11 (16.1 g/min per unit = 177 g/min): 98.0% / 2.0%. Marked "CALCULATED SETTINGS, check before running" on the Word
  file and the page; the Draft says how. (Tech's calc sheet has another R4 layout, reclaim on hopper 1 at 65: on that
  layout 5 mm at SE21's black 5 mm rate would be hopper 1 69, hopper 4 20; the issued pages are newer and win.)
- Test: `tests/test_assign.py` `test_r4_black`.

## R12. Special products run their special formula only: one Main, no Secondary (24 Oct 2026)
James, on H69A284-3 (RPP40WB890, SE25, ROLLS), printed FU0021WB4 + Secondary FU0014WB4: *"This order is a roll order,
so it should use a roll formula. Roll formula should only have one primary formula. There shouldn't be a secondary
formula. It should just be one main formula. Double check, please."* - *"Roll like void form ... They're all order that
have a special formula use running it because of their unique physical properties. So whenever we encounter specialized
product, we should use a [special] formula. So double check the roll formula."*
- A roll or VOIDFORM order gets its special Main only: no Secondary, and not the run-out row Tech prints beside it
  (SE25's "(For roll material only)" FU0001WB4). `assign.SPECIAL_ONLY`, `secondary_for`, `propose`.
- Checked: SE25's roll recipe (FU0021WB4 "(For roll material only) Check weight": virgin 40, WB reclaim 60, CaCO3 20,
  WB colour 15, talc 28) is, with SE25's calibration slopes, virgin 47.3 / reclaim 28.2 / CaCO3 19.1 / talc 3.9 /
  colour 1.4 % - exactly James's Main roll FU0021WB4 in the W% Master.
- Open: James also named "square cut" with roll and VOIDFORM; which orders that is (no schedule note says it) is to ask.
  Corn box keeps its Secondary (James's "Secondary Corn box" FU0041WB4).

## U1 natural 10 mm is FEA001NSA (26 Oct 2026)
James, shown FEA001NSA (UV-N26257A 1.4%, AS-N40095A 1.8%; SE21 Feb 2023) and FHA001NSA (UV-N26177A 4.8%, AS-N40095A
1.8%; SE22, Nov 2025 - Jan 2026), both printed FH0001NSA by Tech, for DPPA0NS75/76 (spec U1U1U1, 9 orders in 12 months,
all "Send to Rotary"): *"U1 is for FEA"*.
- Where James's FE-named Main competes with one kept under the old letter FH for the same key, the FE one is the Main
  (`assign.choose`).
- A row counts as a formula's settings only when it feeds every additive (UV, anti-static, flame retardant) the
  formula's W% lists, by number (`assign.feeds_additives`): SE22's FH0001NSA recipe (N26177A) is FHA001NSA's, so
  FEA001NSA has no SE22 settings yet; SE21 has its recipe (H1 virgin 67, H2 talc 8, H3 UV-N26257A 3, H4 AS-N40095A 17).
- Test `test_u1_natural_10mm_is_fea`. Last week's simulation unchanged; 12 months: two-Main keys 11 -> 9 products.

## Black 3 mm packaging is FU0051KS3 (26 Oct 2026)
James, shown the two plain Mains for KS 3 mm packaging (FU0032KS3 "Main, Packaging grade", 30.5% reclaim, 2016; FU0051KS3
"Main KS Packing", 40% reclaim, Jun 2020), on the FU0032KS3 2016 row: *"obsolete this one"*.
- Notes James gives after his 23 Oct file go in `assign.LATER_NOTES` (code, note in the file, note now); `rules()` and
  calc/revise_w_master.py apply them on read, and the 23 Oct file stays as received. The row is on "Archived" in W% v2.
- Black 3 mm packaging (R1R1R1, 20 orders in 12 months, 18 on SE11) now runs FU0051KS3: SE11 from its calc-sheet recipe
  (Jun 2020: H1 KS 26, H2 talc 17, H3 reclaim 35, H4 virgin 44, H5 CaCO3 13), SE21 its own (Oct 2022); SE42 and SE22
  have none ("ENGINEER TO SET"). SE43 keeps its own FU0151KS3. FU0032KS3 Vistech stays a customer Main, never proposed.
- FU0051KS3 has no Secondary in the W% Master (no virgin black 3 mm packaging row besides SE43's FU0151KS3), so R9 prints
  the Primary only.
- Test `test_ks_3mm_packaging_is_fu0051ks3`. Two-Main keys left in W% v2: KS 6 mm (FU0041KS6 / FU0062KS6).
