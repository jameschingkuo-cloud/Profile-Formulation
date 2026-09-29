# Issues found while transcribing the 29 Sep 2026 packet (scan doc05261220260929142225.pdf, sent in chat 29 Sep)
# that the automated checks don't cover. Each was seen on today's page image.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','Formulation pages scanned separately','The 29 Sep schedule scan has EXT and CNV only (26 pages). Tech’s 13 FRM pages (SE11-SE61, dated 9/29/26) came later as a separate scan, doc05261320260929142259.pdf. Before they came, the pipeline’s FRM Draft / "FRM Formulation 2026-09-29.docx" proposed 72 of 76 orders: all 71 carried-over orders match Tech’s issue field for field; RP26810-1 differs (Tech added FU0041KS4); the 4 new orders were Exceptions and Tech wrote them new formulas','FRM scan'),
 # ---- FRM (doc05261320260929142259.pdf), new today
 ('Medium','FRM','SE21','H69A203-1','Resin not on IWPFT062','FU0012BL5 Hopper 1 prints "PP Virgin-silo 3 (DOW-C104)" (63). DOW-C104 is not on IWPFT062; the nearest is 50-1560-034 PC104 = TI4015F (Braskem, Active). Silo 3 normally holds F6502A. Which resin is it, and is it in silo 3?','FRM p4'),
 ('Medium','FRM','SE21','H69A203-1','New formula written with an obsolete resin','FU0012BL5 is new today and Hopper 3 prints F1102K (10). F1102K is obsolete, replaced by F1203K by Formosa (James Kuo, 29 Sep 2026). Read as F1203K; Tech to correct the formula','FRM p4'),
 ('Low','FRM','SE21','H69A203-1','Alternate source not on IWPFT062','FU0012BL5 Hopper 5 prints "CaCO3 -Heritage HM-10HP (BayShore BI-113)" (27). HM-10HP = CA410 (James, 29 Sep 2026); BayShore BI-113 is not on IWPFT062 as a CaCO3 source','FRM p4'),
 ('Medium','FRM','SE21','RP26810-1','Reclaim formula listed second, no note','RP26810-1 now has FUA152KS4 (no reclaim; F1203K 13) then FU0041KS4 (PP Mix Reclaim 70), no note on either. The plant rule is reclaim first, virgin as the fallback (James, 29 Sep 2026): the page order says the opposite. Which runs first?','FRM p4'),
 ('Info','FRM','SE21','H69A203-1, H67A164-2, H67A164-1','New formula codes vs the calc workbooks','Tech issued FU0012BL5, FU0001RF6 and FU0070KS6; the calc workbooks list FU0011BL5 / FUA011BL5, FU0000RF6 and RU0000KS4 for these products. Settings are Tech’s own; codes recorded as issued','FRM p4, Product Master'),
 ('Info','FRM','SE24','RP26604-1','Grouped with the handwritten run-with','RP26604-1 is on FUA152WB4 with RP26901-1 and RP26803-2, as the handwritten "Run with RPA40WB3051" on the EXT page said','FRM p7'),
 ('Info','FRM','SE11','(page)','Handwriting on the page (disregard)','A pen loop around the FU0022WB3 VOIDFORM note and RP26811-1 Vistamaxx 34. James Kuo, 29 Sep 2026: "disregard the loop. someone had a question so i circle it while explaining"','FRM p1'),
 ('Info','FRM','(auger lines)','','Hopper rules','180 hopper settings on Tech’s auger-line pages checked against the draft hopper rules (Q13): none outside them, including the four new formulas','FRM p1-10'),
 # ---- EXT, new today
 ('Medium','EXT','SE21','H69A203-1, H67A164-1, H67A164-2','New orders on SE21','H69A203-1 RPP50BL1501 (BL, 5.0 mm, 1,003 GSM), H67A164-2 RPP63RF1 (colour RF, 6.3 mm, 1,404 GSM) and H67A164-1 RPP63KS1 (KS, 6.3 mm). Each has a pen dot in the margin. "Tulsa Plastics, hold thickness between 6.2 & 6.5mm" on both H67A164 rows. Not on any earlier FRM page: formulation needed from an engineer','scan p5'),
 ('Info','EXT','SE21','H67A164-2','Colour RF (answered by the FRM)','Colour printed RF RF RF. Tech’s FRM gives the colour as RF-R26006A = IWPFT062 50-7002-601 CR400RF "Red / R26006A" (Amtopp, Active): RF is red','scan p5, FRM p4'),
 ('Info','EXT','SE24','RP26604-1','New order with handwritten run-with','RP26604-1 SPA40WB755 (Slitter, 200 plts) is new on SE24, with "Run with RPA40WB3051" handwritten under the instructions and a margin dot. Also new on the Slitter page (SD51, 0 OF 200, DUM61)','scan p9, p25'),
 ('Medium','EXT','SE23','(page)','Report page 9 missing from the scan','SE23 continues on report page 9 (its line total), which is not in the scan. Handwritten 3,939,487# on page 8 equals the sum of its 7 weights (same as on 28 Sep). Report page 11 is also not in the scan','scan p8-10'),
 ('Info','EXT','SE25 / SE61','','Printed as separate reports','SE25 (run 13:31:50) and SE61 (run 13:34:20) are separate reports, each "PAGE 1"; SE25 prints its own Final Total 259,828 PCs / 533,334 LBs = its line total. The main report (13:26:45) has no Final Total in the scan, so the missing SE23 total cannot be checked through it','scan p12, p15'),
 ('Info','EXT','SE31 / SE25','H69A290-3, H69A291-10, H68A111-4','Orders gone since 28 Sep','No longer on the schedule: H69A290-3 and H69A291-10 (SE31), H68A111-4 (SE25). H68A111-5 now prints the full roll instructions instead of "SAME AS ABOVE"','scan p10, p12'),
 # ---- EXT, still true from 28 Sep
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','scan p8'),
 ('Info','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap (hand corrections)','H68A091-1: 999 struck through, 1880 written below (loose 8s). H64A244-1: 999 -> 1044','scan p8, p12'),
 ('Low','EXT','SE21','RP26424-2','Order width above length','Order size printed 96 x 48 (cut 96 x 48 5/8), the other way round from the other rows','scan p5'),
 ('Low','EXT','SE23','H68A127-1','Old instruction date','In-str Date 19-Mar, far from the Sep-Oct dates on the other rows. Now "20 PLTS DONE"','scan p8'),
 ('Info','EXT','SE43','H68A080-1','Handwriting over the record','"-PA205" above H68A080-1 (equals the printed die). "-BB510" over H68A020-1 is gone today','scan p14'),
 ('Info','EXT','SE31','RP26826-3','Typo','"RUN WIHT RPA40WB3051" (sic)','scan p10'),
 # ---- CNV
 ('Medium','CNV','SD41/SD42','RP26618-3','Board use more than ordered','"BOARD USE FROM OTHER ORDER RP26618-3 245 OF 200" (237 on 28 Sep)','scan p23'),
 ('Low','CNV','SD41/SD42','RP26422-6, RP26506-4','Done more than ordered','152 DONE of 150 pallets; 134 DONE of 120','scan p23'),
 ('Medium','CNV','SD22','H61A218-1 / H63A199-1','Same product, different weight tolerance','Both DPP40WB1673, target 0.2988: ranges 0.2779-0.3197 vs 0.2839-0.3137','scan p20'),
 ('Low','CNV','SC31','H67A063-1, H68A142-1','Packing note vs pieces per pallet','"120pcs laid flat" and "a total of 140 pcs"; Pc./Plt. 140','scan p26'),
 ('Info','CNV','SD31','RP26731-2','Order listed twice','934 OF 999 and 0 OF 999, blank quantities; banner "RP26731-2 & RP26731-2"','scan p16-17'),
 ('Info','CNV','SD51','(all rows)','Excel overflow','Semi Start prints ####; Total Sheets ###### on RP26525-3 and RP26604-1 (RP26604-1 Semi Start is blank)','scan p25'),
 ('Info','EXT','(all)','','Line totals check','All 12 printed line totals equal their rows (SE11-SE22, SE24, SE25, SE31, SE32, SE42, SE43, SE61); SE23’s is on the missing report page 9','p1-15'),
 ('Info','Scan reader','(all)','','Glyph-reader crosscheck','Tesseract 5.4 installed 29 Sep. It read the "Prod" header as "ROD" on pages 1, 5 and 9, so the reader found no columns there; ext_scan_reader.anchors now fixes the columns from any three header words. Crosscheck: 67 of 76 orders identical; the rest settled by eye in favour of the transcription (H67A164-2 RF read as OF by the reader; SE61 page and the handwriting over H68A080-1 misread)','p1-15'),
]
