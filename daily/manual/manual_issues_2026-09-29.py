# Issues found while transcribing the 29 Sep 2026 packet (scan doc05261220260929142225.pdf, sent in chat 29 Sep)
# that the automated checks don't cover. Each was seen on today's page image.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No formulation pages in the scan','The 29 Sep scan has EXT (15 pages) and CNV (11 pages) only. The formulation for today is the pipeline’s FRM Draft / "FRM Formulation 2026-09-29.docx" (James, 29 Sep 2026: "whenever i or any other engineer scan you the production schedule. you will product a word formulation document")','scan p1-26'),
 # ---- EXT, new today
 ('Medium','EXT','SE21','H69A203-1, H67A164-1, H67A164-2','New orders on SE21','H69A203-1 RPP50BL1501 (BL, 5.0 mm, 1,003 GSM), H67A164-2 RPP63RF1 (colour RF, 6.3 mm, 1,404 GSM) and H67A164-1 RPP63KS1 (KS, 6.3 mm). Each has a pen dot in the margin. "Tulsa Plastics, hold thickness between 6.2 & 6.5mm" on both H67A164 rows. Not on any earlier FRM page: formulation needed from an engineer','scan p5'),
 ('Medium','EXT','SE21','H67A164-2','Colour RF not seen before','Colour printed RF RF RF (read at zoom: R + F). RF has not appeared in earlier packets; what colour is it?','scan p5'),
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
 ('Info','EXT','(all)','','Glyph-reader crosscheck not run','Tesseract is not installed on this PC, so scan_reader/ext_scan_reader.py could not run. Independent check used instead: every printed line total equals the transcribed rows','p1-15'),
]
