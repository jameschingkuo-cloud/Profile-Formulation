# Issues for the 23 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7pU3dCY.PDF (SCHEDULE 10/23, sent 13:03, run 13:22:42) and "Die Cutting Schedule 10-23.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 22 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-23.docx" proposes 41 of 99 orders as last issued on their line; 58 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 21 Oct
 ('Medium','EXT','(several)','H6AA197-1, H6AA199-1, H6AA201-1, H68A244-1, H6AA173-1, H6AA173-2, RP26A22-1, RP26A22-2, RP26A22-3, RP26A08-1, H68A053-1, H6AA097-1, H6AA042-1, H6AA042-2, H6AA042-3, H69A341-1, H6AA155-1, H6AA155-2, H69A342-1, H6AA200-1, H6AA204-1','New orders on their line','New since 22 Oct (21): SE11 H6AA197-1 RPP30WB1019; SE13 H6AA199-1 SPA40WB958; SE21 H6AA201-1 RPA60KS136, H68A244-1 DPP50KS185, H6AA173-1 RPP50KS2219, H6AA173-2 RPP40KS1905, RP26A22-1 RPA40EA18, RP26A22-2 RPA40GS109, RP26A22-3 RPA40OF37; SE31 RP26A08-1 RPA40WB3051; SE32 H68A053-1 RPPD0WB176 (moved from SE22), H6AA097-1 RPPD0WB176, H6AA042-1 RPPD0WB166, H6AA042-2 RPPD0WB167, H6AA042-3 RPPD0WB165, H69A341-1 RPPD0WB177, H6AA155-1 RPPD0WB165, H6AA155-2 RPPD0WB166, H69A342-1 RPPD0WB177; SE61 H6AA200-1 and H6AA204-1 RBP30EB22 (same product last ran there as H69A300-1 with BF0000EB3)','system PDF'),
 ('Info','EXT','(several)','H69A221-1, H6AA133-1, H67A165-2, H6AA091-2, H6AA080-1, H68A053-1, H69A044-1, H69A350-3','Gone since 22 Oct','Gone from the extrusion schedule (8): SE11 H69A221-1; SE21 H6AA133-1, H67A165-2, H6AA091-2; SE22 H6AA080-1, H68A053-1 (now on SE32); SE25 H69A044-1; SE61 H69A350-3','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 ('Medium','EXT','SE25','H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 65 rows on 11 pages','CNV PDF'),
 ('Info','CNV','(several)','H6AA199-1, H6AA202-1, H6AA203-1','New on the converting schedule since 22 Oct','New orders (3): H6AA199-1, H6AA202-1, H6AA203-1. Gone since 22 Oct (3): H5BA082-1, H5BA083-1, H68A107-1','CNV PDF'),
]
