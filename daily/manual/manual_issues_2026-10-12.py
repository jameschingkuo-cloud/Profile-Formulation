# Issues for the 12 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7ejslMp.PDF (SCHEDULE 10/12, sent 12:55, run 13:24:42) and "Die Cutting Schedule 10-12.pdf". Both carry
# their text: nothing transcribed or OCR'd, no handwriting. Carried from 9 Oct only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-12.docx" proposes 67 of 77 orders as last issued on their line; 10 orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','SE11','H6AA077-11','New order, no formula issued on its line','H6AA077-11 RPP30KS1133 (SE11) is new since 9 Oct and has no formula issued','system PDF'),
 ('Info','EXT','(several)','H68A088-1, H63A200-1, H69A330-8, H69A330-5, H69A008-1, H6AA013-1, H69A344-1, H69A345-4, H69A338-1, RP25523-2, H6AA020-1, H6AA020-2, H69A330-3, H69A330-7, H69A267-2','Gone since 9 Oct','Gone from the extrusion schedule (15): SE11 H68A088-1, H63A200-1, H69A330-8, H69A330-5; SE12 H69A008-1; SE13 H6AA013-1, H69A344-1, H69A345-4, H69A338-1; SE21 RP25523-2; SE22 H6AA020-1, H6AA020-2; SE43 H69A330-3, H69A330-7, H69A267-2','system PDF'),
 # ---- EXT, still without a formula from earlier days
 ('Medium','EXT','SE13 / SE31','H69A215-1, H69A286-1, H69A075-1, H69A075-2, H69A345-1','New orders still without a formula (since 7-9 Oct)','H69A215-1 SPA40WB957, H69A286-1 SPA40WB913, H69A075-1 DPP40WB1145 and H69A075-2 DPP40WB1155 (SE13). H69A345-1 RPA40WB3164 (SE31)','system PDF'),
 ('Medium','EXT','SE22','H68A226-1, H68A226-2, H68A227-1, H68A227-2','New orders still without a formula (since 5-9 Oct)','H68A226-1 and H68A227-1 DPPA0WB271; H68A226-2 and H68A227-2 DPPA0WB270 (SE22, 10.0 mm)','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE11','H69A039-1','GSM vs weight range','GSM 631 printed with range 582-600','system PDF'),
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 61 rows on 11 pages','CNV PDF'),
 ('Info','CNV','SD41/SD42','H68A223-1','Gone since 9 Oct','No longer on the converting schedule (1 order); no new orders','CNV PDF'),
]
