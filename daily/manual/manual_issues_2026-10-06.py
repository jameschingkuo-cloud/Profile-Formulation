# Issues for the 6 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7Y53NYt.PDF (SCHEDULE 10/06, sent 13:02) and "Die Cutting Schedule 10-06.pdf" (sent 13:24). Both carry
# their text: nothing transcribed or OCR'd, no handwriting. Carried from 5 Oct only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-06.docx" proposes 65 of 81 orders as last issued on their line; 16 orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','SE21 / SE43','H66A005-1, H69A183-1, H69A183-2, H69A183-3','New orders, no formula issued on their line','H66A005-1 DPP50WB307 (SE21, GSM 1,052, "VOIDFORM"). H69A183-1 RPP30WB176, H69A183-2 RPP30WB883 and H69A183-3 RPP30WB874 (SE43)','system PDF'),
 ('Info','EXT','SE21 / SE31','H67A164-1, H69A066-2, H69A066-5, H69A031-3','Orders gone since 5 Oct','No longer on the extrusion schedule (4). H69A031-3 was one of the new orders without a formula','system PDF'),
 # ---- EXT, still without a formula from 2 Oct / 5 Oct
 ('Medium','EXT','SE22 / SE61','H6AA020-1, H6AA020-2, H69A350-7, H69A354-1, H69A354-2','New orders still without a formula (since 5 Oct)','H6AA020-1 DPPA0WB268 and H6AA020-2 DPPA0WB269 (SE22, 10.0 mm, "Send to flatbed"). H69A350-7 RBP33EB64, H69A354-1 RBP50EB53 and H69A354-2 RBP50EB54 (SE61)','system PDF'),
 ('Medium','EXT','SE25 / SE43 / SE61','H68A090-1, H69A330-6, H69A330-10, H69A350-1…-4','New orders still without a formula (since 2 Oct)','H68A090-1 DPP50WB308 (SE25), H69A330-6 RPP30GS130 and H69A330-10 RPP30BD58 (SE43), H69A350-1…-4 RBP33EB42 / 41 / 53 / 48 (SE61). No Tech FRM or approved master decision has come for them yet','system PDF'),
 # ---- EXT, still true from 5 Oct
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Info','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap','# Plt prints 999; the converting schedule shows the real quantity','system PDF; CNV'),
 ('Low','EXT','SE21','RP26424-2','Order width above length','Order size printed 96 x 48, the other way round from the other rows','system PDF'),
 ('Low','EXT','SE41','H64A178-1','Special instruction gone','5 Oct printed "Bradford, treat both sides minimum 42 dynes. Thickness range 3.3-3.8mm."; today the instruction is blank','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 62 rows on 11 pages','CNV PDF'),
 ('Info','CNV','SD41/SD42','H69A062-6','Gone since 5 Oct','No longer on the converting schedule','CNV PDF'),
]
