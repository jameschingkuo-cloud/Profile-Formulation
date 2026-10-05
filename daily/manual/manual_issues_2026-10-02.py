# Issues for the 2 Oct 2026 packet, built from the system's own PDFs sent in chat 2 Oct: the extrusion report
# BPN9PFR$_Z7Ubmp3i.PDF (run 10/02/26 13:14:34) and the converting schedule "Die Cutting Schedule 10-02.pdf" (printed from
# Excel, issue date 10/2/2026). Both carry their text: nothing was transcribed or OCR'd, so there is no handwriting today.
# Carried from 30 Sep only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-02.docx" proposes 81 of 88 orders as last issued on their line; 7 new orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/packet_from_pdf.py): every record, cut row and special instruction as printed; every line adds up to its printed line total and the Final Total is 6,325,199 PCs / 21,541,117 LBs','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','SE25 / SE43 / SE61','H68A090-1, H69A330-6, H69A330-10, H69A350-1…-4','New orders, no formula issued on their line','H68A090-1 DPP50WB308 (SE25; the same product ran here as H66A116-1 on FU0011WB5 / FUA011WB5, issued 30 Sep). H69A330-6 RPP30GS130 and H69A330-10 RPP30BD58 (SE43): never on a schedule since 2020; no GS order on SE43 since 2025, RPP30BD50 is the nearest. H69A350-1…-4 RBP33EB42 / 41 / 53 / 48 (SE61, BBB R6R6R6 EB KS EB 3.3 mm, Bradford, both sides 42 dynes): each product ran on SE61 before (Jan-Aug 2026) but no Tech FRM page for them is on file','system PDF p11, p15-18'),
 ('Info','EXT','SE31','H69A066-5','Order back on SE31','H69A066-5 is on SE31 today (not on 30 Sep); formula as last issued for it','system PDF p12'),
 ('Info','EXT','(several)','H69A237-1, RP26810-1, RP26925-1, RP26311-1, H68A111-5, H69A097-1, RP26826-3','Orders gone since 30 Sep','No longer on the extrusion schedule: H69A237-1 (SE13), RP26810-1 and RP26925-1 (SE21), RP26311-1 (SE22), H68A111-5 and H69A097-1 (SE25), RP26826-3 (SE31)','system PDF'),
 ('Info','EXT','SE11 / SE22 / SE25 / SE61','H69A180-1, H69A180-2, H68A053-1, H64A244-1, H68A020-1','In-str dates moved later','H69A180-1 / -2 02-Oct -> 15-Oct; H68A053-1 10-Sep -> 15-Oct; H64A244-1 15-Sep -> 20-Oct; H68A020-1 01-Oct -> 15-Oct','system PDF'),
 # ---- EXT, still true from 30 Sep
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF p8'),
 ('Info','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap','# Plt prints 999; the converting schedule shows 786 OF 1880 (H68A091-1) and 823 OF 1044 (H64A244-1)','system PDF p8, p11; CNV p5-6'),
 ('Low','EXT','SE21','RP26424-2','Order width above length','Order size printed 96 x 48, the other way round from the other rows','system PDF p5'),
 ('Low','EXT','SE23','H68A127-1','Old instruction date','In-str Date 19-Mar, far from the Sep-Oct dates on the other rows. Now "31 PLTS DONE"','system PDF p8'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off at the cell edge. 64 rows on 11 pages ("Page: n of 11" on every page today, SD11/SD12 and SD21 included)','CNV PDF'),
 ('Info','CNV','SD31 / SD21 / SD51','H68A127-1, H68A170-2, H68A154-1','Cell text wider than its cell','H68A127-1 Color is "WB GT WB" (the paper shows "B GT V"); H68A170-2 Semi-Size "51 4/16 X 73 12/16"; H68A154-1 Semi-Size runs into the next cell. Copied in full from the PDF','CNV p1, p4, p10'),
 ('Info','CNV','SD31 / SD22','H69A051-1, H69A052-1, RP26410-1, H68A090-1','New on the converting schedule','H69A051-1, H69A052-1 (0 OF 56) and RP26410-1 (262 OF 999) on SD31 (corn boxes); H68A090-1 (0 OF 386) on SD22. Gone since 30 Sep: H68A160-1 (SD31), H69A066-6 (SD41/SD42)','CNV p2, p7'),
 ('Medium','CNV','SD41/SD42','RP26618-3','Board use more than ordered','"BOARD USE FROM OTHER ORDER RP26618-3 280 OF 200" (256 on 30 Sep)','CNV p8'),
 ('Low','CNV','SD41/SD42','RP26422-6, RP26506-4','Done more than ordered','152 DONE of 150 pallets; 134 DONE of 120','CNV p8'),
 ('Medium','CNV','SD22','H61A218-1 / H63A199-1','Same product, different weight tolerance','Both DPP40WB1673, target 0.2988: ranges 0.2779-0.3197 vs 0.2839-0.3137','CNV p5'),
 ('Low','CNV','SC31','H68A142-1','Packing note vs pieces per pallet','"120pcs laid flat" and "a total of 140 pcs"; Pc./Plt. 140','CNV p11'),
 ('Info','CNV','SD31','RP26731-2','Order listed twice','934 OF 999 and 0 OF 999, blank quantities; the corn-box note names "RP26731-2 & RP26731-2 & RP26410"','CNV p1-2'),
 ('Info','CNV','SD51','(all rows)','Excel overflow','Semi Start prints ####; Total Sheets ###### on RP26525-3 and RP26604-1 (the PDF holds the same marks)','CNV p10'),
]
