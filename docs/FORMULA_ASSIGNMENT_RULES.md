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
  expection. so BF does not apply to this rule. its BF0 even when its EB"*. A BF code always has `0` in the third place.
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
  | U1U1U1          | FH (FE?)    | extra UV ("U1"; James renames some FH -> FE) |
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
