# Issues for the 26 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7sKYt8d.PDF (SCHEDULE 10/26, sent 13:35, run 14:23:06) and "Die Cutting Schedule 10-26.pdf" (sent 13:33).
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 23 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-26.docx" gives 75 of 82 orders a formulation (as last issued or by James\'s rules); 7 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 23 Oct
 ('Info','EXT','(several)','H6AA199-1, H67A165-1, H6AA147-2, H6AA201-1, H68A244-1, H6AA017-1, H69A181-1, RP26A09-3, RP26A01-1, H69A289-1, H6AA034-1, H68A053-1, H69A350-4, H69A350-7, H6AA124-1, H6AA124-2, H6AA124-3','Gone since 23 Oct','No new orders since 23 Oct. Gone from the extrusion schedule (17): SE13 H6AA199-1; SE21 H67A165-1, H6AA147-2, H6AA201-1, H68A244-1, H6AA017-1; SE25 H69A181-1; SE31 RP26A09-3, RP26A01-1, H69A289-1, H6AA034-1; SE32 H68A053-1; SE61 H69A350-4, H69A350-7, H6AA124-1, H6AA124-2, H6AA124-3','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 60 rows on 8 pages','CNV PDF'),
 ('Info','CNV','(several)','H5CA088-1, H69A075-1, H6AA080-1, H6AA080-2','Gone from the converting schedule since 23 Oct','No new orders. Gone (4): H5CA088-1, H69A075-1, H6AA080-1, H6AA080-2','CNV PDF'),
]
