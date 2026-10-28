# Issues for the 28 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7uY90aK.PDF (SCHEDULE 10/28, sent 13:08, run 13:41:14) and "Die Cutting Schedule 10-28.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 27 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-28.docx" gives 86 of 91 orders a formulation (as last issued or by James\'s rules); 5 orders (SE22 H6AA231-1 to -5) are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 27 Oct
 ('Info','EXT','(several)','H6AA237-1, H6AA068-4, H6AA229-1, H6AA227-1, H6AA227-2, H6AA221-1, H6AA221-2, H6AA222-1, H6AA222-2, H6AA223-1, H6AA223-2, H6AA231-1..5, H6AA115-1, H69A061-1','New since 27 Oct','New on the extrusion schedule (18): SE11 H6AA237-1; SE13 H6AA068-4; SE21 H6AA229-1, H6AA227-1/-2, H6AA221-1/-2, H6AA222-1/-2, H6AA223-1/-2; SE22 H6AA231-1 to -5; SE25 H6AA115-1; SE31 H69A061-1','system PDF'),
 ('Info','EXT','(several)','H6AA197-1, H6AA152-6, H6AA173-1, H6AA173-2, H69A284-3, RP26120-1, H6AA060-3, H6AA063-1, H6AA200-1','Gone since 27 Oct','Gone from the extrusion schedule (9): SE11 H6AA197-1, H6AA152-6; SE21 H6AA173-1/-2; SE25 H69A284-3; SE31 RP26120-1; SE61 H6AA060-3, H6AA063-1, H6AA200-1','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions: VOIDFORM control range is 5-8% under the printed (billing) GSM, so these are as expected
 ('Info','EXT','(SE23, SE25)','H68A091-1, H68A090-1, H64A244-1','VOIDFORM GSM vs control range','Printed GSM is the billing weight; the control range in the instructions is 5-8% under it (793 -> 729-751; 1,052 -> 970-1000). As expected, none outside. SE32 H6AA097-1 (VOIDFORM, 2,691) prints no range','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 63 rows on 10 pages','CNV PDF'),
 ('Info','CNV','(several)','H69A061-1, H6AA229-1, H6AA237-1, H68A144-1','New / gone on the converting schedule since 27 Oct','New (3): H69A061-1, H6AA229-1, H6AA237-1. Gone (1): H68A144-1','CNV PDF'),
]
