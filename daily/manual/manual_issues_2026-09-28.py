# Issues found while transcribing the 28 Sep 2026 packet (scan doc05253620260928134035.pdf, uploaded in chat 28 Sep)
# that the automated checks don't cover. Each was seen on today's page image.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('High','FRM','(all)','','No formulation pages in the packet','The 28 Sep packet has EXT and CNV only (25 pages); Tech’s FRM pages are not in it. FRM Draft 2026-09-28 proposes one from the last issued FRM, for Tech to check and sign','scan'),
 ('High','EXT','SE21','RP26825-1, RP26918-1, RP26925-1','New colour codes','New orders print colours NS (RPA40NS235), OF (RPA40OF37) and BD (RPA40BD59), all PPP A R1R1R1 4.0. OF and BD are not on the EXT colour list (R7). Checked at zoom: OF is letter O + F. What do OF and BD stand for? (HANDOFF Q2)','scan p5'),
 ('High','Scan reader','SE21','RP26925-1','Glyph reader silent misread (fixed)','The glyph reader read BD as BL with no flag: its colour list had no BD, so the word snapped to the nearest listed colour. Caught by the crosscheck. The reader now also reads each colour letter by letter and flags any difference (scan_reader/ext_scan_reader.py colour_word); the 25 Sep scan reads the same as before','scan p5'),
 ('Medium','EXT','SE23','(page)','Report page 8 missing from the scan','SE23 continues on report page 8 (its line total). Handwritten 3,939,487# on page 7 equals the sum of its weights, and the Final Total equals all rows, so no order is missing','scan p7-8'),
 ('Medium','EXT','SE23 / SE43','H68A127-1, H68A080-1','Order moved to another line','H68A127-1 was on SE25 on 25 Sep, now SE23; H68A080-1 was on SE42, now SE43. A formula is per line, so neither carries over (FRM Draft Exceptions)','scan p7, p13'),
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','scan p7'),
 ('Medium','EXT','SE23','H68A091-1','999 pallets is a cap','# Plt 999 struck through by hand, 1880 written below (loose 8s; 554,601 / 295 = 1,880). Also on SE25 H64A244-1: 999 -> 1044','scan p7, p11'),
 ('Low','EXT','SE24','RP26803-2','Speck on Thk','Thk looks like "4:0": a speck of dust above the decimal point, read as 4.0 (checked by eye)','scan p8'),
 ('Low','EXT','SE21','RP26424-2','Order width above length','Order size printed 96 x 48 (cut 96 x 48 5/8), the other way round from the other rows','scan p5'),
 ('Low','EXT','SE23','H68A127-1','Old instruction date','In-str Date 19-Mar, far from the Sep-Oct dates on the other rows','scan p7'),
 ('Info','EXT','SE43 / SE61','H68A080-1, H68A020-1','Handwriting over the record','"-PA205" above H68A080-1 and "-BB510" above H68A020-1 (both equal the printed die); the glyph reader could not read these rows (flagged)','scan p13, p14'),
 ('Info','EXT','(several)','','Margin dots','Pen dots beside new orders: RP26928-1 (SE22), H68A127-1 (SE23), H69A066-2, H69A290-3, H69A291-10, RP26826-3 (SE31), RP26925-1, RP26918-1, RP26825-1 (SE21), H68A080-1, H69A038-1, RP26911-2 (SE43), five BA253 orders on SE61 - they seem to mark new or moved orders','scan p5-14'),
 ('Info','EXT','SE31','RP26826-3','Typo','"RUN WIHT RPA40WB3051" (sic)','scan p9'),
 ('Info','EXT','SE11','H63A200-1','Instruction changed','Now "VOIDFORM, WEIGHT CHECK EVERY 30 MINS (RANGE 582-600 GSM) / 343 PLTS DONE"','scan p1'),
 ('Medium','CNV','SD41/SD42','RP26618-3','Board use more than ordered','"BOARD USE FROM OTHER ORDER RP26618-3 237 OF 200" (208 OF 200 on 25 Sep)','scan p22'),
 ('Low','CNV','SD41/SD42','RP26422-6, RP26506-4','Done more than ordered','152 DONE of 150 pallets; 134 DONE of 120','scan p22'),
 ('Medium','CNV','SD22','H61A218-1 / H63A199-1','Same product, different weight tolerance','Both DPP40WB1673, target 0.2988: ranges 0.2779-0.3197 vs 0.2839-0.3137','scan p19'),
 ('Low','CNV','SC31','H67A063-1, H68A142-1','Packing note vs pieces per pallet','"120pcs laid flat" and "a total of 140 pcs"; Pc./Plt. 140','scan p25'),
 ('Info','CNV','SD31','RP26731-2','Order listed twice','934 OF 999 and 0 OF 999, blank quantities; banner "RP26731-2 & RP26731-2"','scan p16'),
 ('Info','CNV','SD51','(all rows)','Excel overflow','Semi Start prints ####; RP26525-3 Total Sheets ######','scan p24'),
 ('Info','EXT','(all)','','Line totals check','All 12 printed line totals equal their rows; SE23’s is on the missing page 8. The Final Total (6,277,751 PCs / 22,103,174 LBs) equals all 75 orders exactly','p1-14'),
]
