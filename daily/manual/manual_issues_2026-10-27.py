# Issues for the 27 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7tvl19r.PDF (SCHEDULE 10/27, sent 12:47, run 12:56:25) and "Die Cutting Schedule 10-27.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 26 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-27.docx" gives 81 of 82 orders a formulation (as last issued or by James\'s rules); 1 order (RP26A15-1) is left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 26 Oct
 ('Info','EXT','(several)','H6AA152-6, H69A343-1, H69A335-1, H6AA217-6, H6AA148-1, H6AA208-1, H6AA205-1, H69A059-1','New since 26 Oct','New on the extrusion schedule (8): SE11 H6AA152-6; SE12 H69A343-1; SE13 H69A335-1, H6AA217-6; SE22 H6AA148-1; SE23 H6AA208-1; SE24 H6AA205-1; SE31 H69A059-1','system PDF'),
 ('Info','EXT','(several)','RP26811-1, H6AA037-1, H69A040-1, H6AA033-1, H6AA123-1, H6AA124-4, H6AA124-5, H6AA060-2','Gone since 26 Oct','Gone from the extrusion schedule (8): SE11 RP26811-1; SE21 H6AA037-1; SE25 H69A040-1; SE31 H6AA033-1, H6AA123-1; SE61 H6AA124-4, H6AA124-5, H6AA060-2','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions: VOIDFORM control range is 5-8% under the printed (billing) GSM, so these are as expected
 ('Info','EXT','(SE23, SE25)','H68A091-1, H68A090-1, H64A244-1','VOIDFORM GSM vs control range','Printed GSM is the billing weight; the control range in the instructions is 5-8% under it (793 -> 729-751; 1,052 -> 970-1000). As expected, none outside','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 61 rows on 9 pages','CNV PDF'),
 ('Info','CNV','(several)','H69A059-1, H69A343-1, H6AA152-6, H69A008-1, H69A044-1','New / gone on the converting schedule since 26 Oct','New (3): H69A059-1, H69A343-1, H6AA152-6. Gone (2): H69A008-1, H69A044-1','CNV PDF'),
]
