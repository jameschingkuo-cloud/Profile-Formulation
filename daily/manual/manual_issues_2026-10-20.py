# Issues for the 20 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7mgEamc.PDF (SCHEDULE 10/20, sent 15:14, run 13:25:36) and "Die Cutting Schedule 10-20.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 19 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-20.docx" proposes 46 of 82 orders as last issued on their line; 36 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 19 Oct
 ('Medium','EXT','SE25','H69A040-1, H69A284-5','New orders, no formula issued on their line','New since 19 Oct: SE25 H69A040-1 CPP40WB320, H69A284-5 RPP40WB890 (the Word file lists the ones it could not match)','system PDF'),
 ('Info','EXT','(several)','H69A357-1, H69A116-2, H69A116-3','Gone since 19 Oct','Gone from the extrusion schedule (3): SE11 H69A357-1; SE25 H69A116-2, H69A116-3','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE11','H69A039-1','GSM vs weight range','GSM 631 printed with range 582-600','system PDF'),
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H69A044-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 75 rows on 11 pages','CNV PDF'),
 ('Info','CNV','SC31','H69A040-1','New on the converting schedule since 19 Oct','SC31 H69A040-1 CPP40WB320; nothing gone since 19 Oct','CNV PDF'),
]
