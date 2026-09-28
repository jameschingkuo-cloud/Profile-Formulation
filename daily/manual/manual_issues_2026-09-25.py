# Issues found while transcribing the 25 Sep 2026 packet (scan doc05252320260928124922.pdf, scanned 28 Sep)
# that the automated checks don't cover. Each was seen on today's page image; items carried over from
# 24 Sep were kept only where today's page still shows them.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 # ---- new today
 ('Info','EXT','SE31','H68A153-1','Material spec OPOPOP (R2 exception)','Printed "PPP A OPOPOP" (letter O + letter P, checked at zoom against the 0 in "4.0"). Not letter+digit. New order; special instructions say "WHITE OPAQUE". James Kuo, 28 Sep 2026: accepted; OP added to the R2 exception list (RD, RM, OP), flagged every time like RD/RM','scan p11'),
 ('High','FRM','SE31','H68A153-1','New formula code FXA020WB4 with a different WB colour','FXA020WB4: V4 is "WB-W40020M" (every other WB formula uses WB-W26038A) and V5 prints "NPC NPC PE-W22151" (NPC twice). Tech to confirm the colour masterbatch','FRM p36'),
 ('Medium','FRM','SE25','RP26923-1','Formula changed since 24 Sep','24 Sep: FU0021WB4 (virgin 40, WB reclaim 60, WB colour 16, talc 16). 25 Sep: RU0001WB4 (PP WB Reclaim 99 only). The order moved from the H69A097-1 group to its own reclaim-only row. Needs a Change Log entry once the Formulation Master exists','FRM p38'),
 ('Medium','EXT vs FRM','SE21','H69A139-1','Order on the formulation page but not on the schedule','H69A139-1 (FU0041KS4) is still on the Line 4 FRM page; it is no longer on the EXT schedule (it was on 24 Sep)','FRM p32, EXT p5-6'),
 ('Medium','EXT','SE61','H64A178-1','Thickness range vs Thk','Special instructions: "Thickness range 3.3-3.8mm", while Thk is 5.0 and the product code RBP50EB52 says 5 mm','scan p17'),
 ('Medium','FRM','SE21','RP26512-1','Two formulas with no note','FU0041WB4 and FU0031WB4 are both listed with no note saying which to use (FU0031WB4 settings are exactly 2x FU0041WB4: 80/10/60/32/36 vs 40/5/30/16/18); FU0011WB4 is the reclaim run-out backup','FRM p32'),
 ('Medium','FRM','SE22','RP26311-1','Same code, two recipes, no note','FUA060WBA printed twice: 20/5/90/7/4 and 30/5/75/7/4, with nothing to tell them apart','FRM p33'),
 ('Low','FRM','SE23','(page)','One code, three recipes','FU0021WB4 is used for the VOIDFORM group, the corn box formula (45/10/60/20) and its reclaim run-out backup (99/14/32/28). The corn box rows name the virgin resin only as "PP Virgin"','FRM p34'),
 ('Low','FRM','SE21','(page)','Material text missing its bracket','"KS-MDI PE-500 (or PolyOne LD-250 or NPC PE90000F" (no closing bracket); two groups print "(F-6502A)"','FRM p32'),
 ('Low','EXT','SE11','H63A200-1','Pallets done vs order size','A third printed instruction line "343 PLTS DONE" on an order of 6 pallets (2,160 sheets). Yesterday this line was handwritten "MAKE UP FOR SCRAP PALLETS."','scan p1'),
 ('Low','EXT','SE22','H68A053-1','Instruction date before run date','In-str Date 10-Sep on a report run 9/25/26','scan p7'),
 ('Info','EXT','SE42','H68A080-1 / RP26410-1','Handwriting in the margin','"PC405" written (with a stroke) in the left margin between the two orders. H68A080-1 prints die PA205, RP26410-1 prints PC405. Recorded as a note only','scan p15'),
 ('Info','EXT','SE31 / SE61','H68A153-1, RP26512-1, H69A039-1, H68A020-1','Glyph reader misreads, all flagged','The independent glyph reader misread 4 fields (spec D2D0DD, product code DPP40WB1238 and die PE405, GSM 68, order H68A620) and flagged every one; each was checked on the page and the transcription is right','scan p1, p6, p11, p17'),
 ('Info','CNV','SD22','(sheet)','Title vs line','SD22 BAYSEK pages are titled "BOBST DIE CUTTER"','scan p22-23'),
 ('Info','CNV','SD31','H5CA066-1 / H5CA090-1','Which row a DONE note belongs to','"43 DONE" sits on the line between the two rows; assigned to H5CA066-1 (status 0 OF 56). Also on p19 the description/status/quantity values print half a line below their order line','scan p19'),
 ('Info','CNV','SD51','RP26525-3','Excel overflow','Total Sheets prints "######" (250 x 275 = 68,750 expected); every Semi Start cell prints ####','scan p26-27'),
 ('Info','CNV','SD41/SD42','RP25A08-6','Blank required date','No Req. Date printed','scan p24'),
 # ---- carried over from 24 Sep, still on today's pages
 ('Medium','CNV','SD41/SD42','RP26618-3','Board use more than ordered','"BOARD USE FROM OTHER ORDER" line now prints 208 OF 200 (202 OF 200 on 24 Sep)','scan p24'),
 ('Medium','CNV','SD22','H61A218-1 / H63A199-1','Same product, different weight tolerance','Both DPP40WB1673, target wt 0.2988: H61A218-1 range 0.2779-0.3197, H63A199-1 range 0.2839-0.3137','scan p22'),
 ('Low','CNV','SC31 / SD11/SD12','H68A142-1','Packing note vs pieces per pallet','Note says 120 pcs laid flat / a total of 140 pcs; Pc./Plt. is 300','scan p20'),
 ('Info','CNV','SD31','H68A127-1','Colour cell cut off','Only "B GT W" visible in the Color cell (EXT says WB GT WB)','scan p18'),
 ('Info','CNV','SD31','RP26731-2','Order listed twice','RP26731-2 on two rows ("934 OF 999" and "0 OF 999") with blank quantities; banner reads "RP26731-2 & RP26731-2"','scan p19'),
 ('Medium','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap','# Plt prints 999; handwritten 1880 (H68A091-1) and 1044 (H64A244-1). Any order over 999 pallets is understated on the printout','scan p8, p13'),
 ('Low','EXT','SE61','H64A289-2','Pack code vs order size','Pack code 84X96 for an 85 x 94 order','scan p17'),
 ('Info','EXT','SE24','RP26901-1','Completed order still scheduled','"COMPELTELY DONE" (sic) in the special instructions; still on the SE24 schedule','scan p10'),
 ('Info','EXT','SE24','RP25710-1','DO NOT RUN order still scheduled','Special instructions "DO NOT RUN"; the order is counted in the SE24 total and has a formula (RU0000WB4)','scan p10, FRM p35'),
 ('Medium','FRM','SE42','RP26410-1','Resin grade printed Q1203K','"Q1203K" in V3; every other page uses F1203K (third day running)','FRM p39'),
 ('Medium','FRM','SE25','H69A097-1','Backup formula has the same code','Main and "in case PP WB Reclaim is run out" rows are both FU0021WB4 with different recipes; for H68A111 the backup has its own code (FU0001WB4)','FRM p38'),
 ('Low','FRM','(all)','','Same resin written several ways','"(6502A)", "(F6502A)", "(F-6502A)", bare "F6502A"; silo 3 / silo 4 / plain "PP Virgin". A master table needs one name per material','FRM p29-41'),
 ('Info','FRM','SE24 / SE25','','Different CaCO3 grade','HM-10HP on Line 7 and in FU0011WB5 (Line 10); HM-10MAX elsewhere','FRM p35, p38'),
 ('Low','FRM','SE25','H68A127-1','Premix note wording','Note says "WB : EA = 9 : 1" but the material is "WB GT Premix" (GT - D26002M)','FRM p38'),
 ('Info','FRM','SE25','H66A116-1, H64A244-1','Typo in note','"(Foe VOIDFORM orders only)"','FRM p38'),
 ('Medium','EXT vs CNV','','H63A200-1 and others','EXT pallet count: remaining or full order?','EXT # Plt is sometimes the remaining pallets and sometimes the full order; the "NNN PLTS DONE" notes on EXT lag the CNV status','scan p1, p13, p22'),
 # ---- day summary
 ('Info','EXT','(all)','','Line totals check','All 13 printed line totals equal their rows, and the Final Total (6,131,179 PCs / 20,771,336 LBs) equals all 71 orders exactly. First packet with no missing page','p1-17'),
 ('Info','EXT vs FRM','(all)','','Every scheduled order has a formula','71 of 71 EXT orders are on the same line’s formulation page. One FRM order (H69A139-1) is not on EXT (above)','p1-17 vs p29-41'),
 ('Info','EXT','(all)','','Orders since 24 Sep','New: H67A120-1 (SE23), H68A153-1 (SE31). Gone: H69A062-4, H69A066-1/-2/-3/-5, H69A090-2, H69A139-1, H69A237-2/-3, H69A238-1, H69A242-3','p1-17'),
]
