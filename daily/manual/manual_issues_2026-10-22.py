# Issues for the 22 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7osaRuK.PDF (SCHEDULE 10/22, sent 13:36, run 13:25:11) and "Die Cutting Schedule 10-22.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 21 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-22.docx" proposes 43 of 86 orders as last issued on their line; 43 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 21 Oct
 ('Medium','EXT','SE21','H67A165-1, H67A165-2, H6AA017-1, H6AA037-1, H6AA091-2, H6AA133-1, H6AA147-2, RP26826-6, RP26826-7, RP26A02-1, RP26A15-1','New orders, no formula issued on their line','New since 21 Oct (SE21): H67A165-1 RPP63KS1, H67A165-2 RPP63RF1, H6AA017-1 RPA50KS281, H6AA037-1 DPP40KS303, H6AA091-2 RPA60KS136, H6AA133-1 RPA60WB243, H6AA147-2 RPA60KS110, RP26826-6 RPP40FW2, RP26826-7 SPA40YF117, RP26A02-1 RPA40NS235, RP26A15-1 RPA40KS744. Also SE61 H6AA063-1 RBP30EB22 is still new on its line (same product last ran there as H69A300-1 with BF0000EB3)','system PDF'),
 ('Info','EXT','(several)','H69A220-1, H69A058-1, H6AA043-2, RP26826-1','Gone since 21 Oct','Gone from the extrusion schedule (4): SE11 H69A220-1; SE22 H69A058-1, H6AA043-2; SE61 RP26826-1','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H69A044-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 ('Medium','EXT','SE25','H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 66 rows on 11 pages','CNV PDF'),
 ('Info','CNV','(several)','H6AA037-1, H6AA135-1, H6AA136-1, H6AA137-1, H6AA157-1, H6AA158-1, RP26826-7','New on the converting schedule since 21 Oct','New orders (7): H6AA037-1, H6AA135-1, H6AA136-1, H6AA137-1, H6AA157-1, H6AA158-1, RP26826-7. Gone since 21 Oct (7): H5CA324-1, H5CA326-1, H69A215-1, H68A226-2, H68A227-2, H69A286-1, H69A335-2','CNV PDF'),
]
