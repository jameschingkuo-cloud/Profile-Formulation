# Issues for the 5 Oct 2026 packet, built from the system's own PDFs sent in chat 5 Oct (daily/intake.py): the extrusion
# report BPN9PFR$_Z7XTIDbA.PDF (run 10/05/26 13:42:46) and the converting schedule "Die Cutting Schedule 10-05.pdf" (printed
# from Excel, issue date 10/5/2026). Both carry their text: nothing transcribed or OCR'd, no handwriting.
# Carried from 2 Oct only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-05.docx" proposes 68 of 81 orders as last issued on their line; 13 new orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','SE22 / SE31 / SE61','H6AA020-1, H6AA020-2, H69A031-3, H69A350-7, H69A354-1, H69A354-2','New orders, no formula issued on their line','H6AA020-1 DPPA0WB268 and H6AA020-2 DPPA0WB269 (SE22, 10.0 mm, GSM 2,006, "Send to flatbed"; converting SD21 dies F0320 / F0321). H69A031-3 SPA60WM1 (SE31, 6.0 mm WM). H69A350-7 RBP33EB64 (SE61, Bradford). H69A354-1 RBP50EB53 and H69A354-2 RBP50EB54 (SE61): the same products ran on SE61 on 30 Sep as H64A289-3 / -4 on BF0000EB5','system PDF p6, p10, p16'),
 ('Medium','EXT','SE25 / SE43 / SE61','H68A090-1, H69A330-6, H69A330-10, H69A350-1…-4','New orders still without a formula (since 2 Oct)','H68A090-1 DPP50WB308 (SE25; the same product ran as H66A116-1 on FU0011WB5 / FUA011WB5), H69A330-6 RPP30GS130 and H69A330-10 RPP30BD58 (SE43), H69A350-1…-4 RBP33EB42 / 41 / 53 / 48 (SE61). No Tech FRM or approved master decision has come for them yet','system PDF'),
 ('Info','EXT','(several)','H66A116-1, H67A164-2, H68A127-1, H69A038-1, H69A164-1, H69A199-1, H69A203-1, H69A209-1, H69A300-1, H69A330-11, RP26731-2, RP26825-1, RP26918-1','Orders gone since 2 Oct','No longer on the extrusion schedule (13). H68A127-1 and RP26731-2 are still on the converting schedule (SD31)','system PDF'),
 # ---- EXT, still true from 2 Oct
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF p7'),
 ('Info','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap','# Plt prints 999; the converting schedule shows 786 OF 1880 (H68A091-1) and 970 OF 1044 (H64A244-1)','system PDF p7, p9; CNV p5-6'),
 ('Low','EXT','SE21','RP26424-2','Order width above length','Order size printed 96 x 48, the other way round from the other rows','system PDF p5'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 63 rows on 11 pages; every fixed field of the orders also on 2 Oct is unchanged','CNV PDF'),
 ('Info','CNV','SD21 / SD31','H6AA020-1, H6AA020-2, RP26902-1','New on the converting schedule','H6AA020-1 (0 OF 22) and H6AA020-2 (0 OF 4) on SD21, 10MM flat-bed dies F0320 / F0321. RP26902-1 (43 OF 999) on SD31, corn boxes. Gone since 2 Oct: H67A120-1 (SD22), H69A062-1, H69A062-5, H69A066-4 (SD41/SD42)','CNV p1, p4'),
 ('Info','CNV','SD31 / SD21 / SD51','H68A127-1, H68A170-2, H6AA020-1, H6AA020-2, H68A154-1','Cell text wider than its cell','H68A127-1 Color "WB GT WB" (the paper shows "B GT V"); Semi-Size of H68A170-2, H6AA020-1, H6AA020-2 and H68A154-1 runs past its cell. Copied in full from the PDF','CNV p1, p4, p10'),
 ('Medium','CNV','SD41/SD42','RP26618-3','Board use more than ordered','"BOARD USE FROM OTHER ORDER RP26618-3 286 OF 200" (280 on 2 Oct)','CNV p8'),
 ('Low','CNV','SD41/SD42','RP26422-6, RP26506-4','Done more than ordered','152 DONE of 150 pallets; 134 DONE of 120','CNV p8'),
 ('Medium','CNV','SD22','H61A218-1 / H63A199-1','Same product, different weight tolerance','Both DPP40WB1673, target 0.2988: ranges 0.2779-0.3197 vs 0.2839-0.3137','CNV p5'),
 ('Low','CNV','SC31','H68A142-1','Packing note vs pieces per pallet','"120pcs laid flat" and "a total of 140 pcs"; Pc./Plt. 140','CNV p11'),
 ('Info','CNV','SD31','RP26731-2','Order listed twice','999 OF 999 and 0 OF 999, blank quantities; off the extrusion schedule today','CNV p2'),
 ('Info','CNV','SD51','(all rows)','Excel overflow','Semi Start prints ####; Total Sheets ###### on RP26525-3 and RP26604-1 (the PDF holds the same marks)','CNV p10'),
]
