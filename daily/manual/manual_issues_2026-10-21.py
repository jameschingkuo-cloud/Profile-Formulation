# Issues for the 21 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7nFrNYR.PDF (SCHEDULE 10/21, sent 12:53, run 12:58:41) and "Die Cutting Schedule 10-21.pdf".
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 20 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-21.docx" proposes 44 of 79 orders as last issued on their line; 35 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 20 Oct
 ('Medium','EXT','SE22','H6AA163-1, H6AA163-2, RP26707-2','New orders, no formula issued on their line','New since 20 Oct: SE22 H6AA163-1 SPAA0OF5, H6AA163-2 SPAA0OF3, RP26707-2 RPAA0KS73. Also SE61 H6AA063-1 RBP30EB22 is new on its line (same product last ran there as H69A300-1 with BF0000EB3)','system PDF'),
 ('Info','EXT','(several)','H69A039-1, H6AA077-5, H69A181-2, H69A288-11, H6AA043-1, RP26911-2','Gone since 20 Oct','Gone from the extrusion schedule (6): SE11 H69A039-1; SE13 H6AA077-5, H69A181-2; SE22 H69A288-11, H6AA043-1; SE43 RP26911-2','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H69A044-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 ('Medium','EXT','SE25','H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 68 rows on 11 pages','CNV PDF'),
 ('Info','CNV','SD41 & 42, SD51','H6AA163-1, H6AA163-2','New on the converting schedule since 20 Oct','SD41 & 42 Guillotine H6AA163-1 SPAA0OF5; SD51 Slitter H6AA163-2 SPAA0OF3. Gone since 20 Oct (8): H5BA121-1, H5BA122-1, H5BA123-1, H69A075-2, H68A252-2, H68A227-1, H69A038-1, H69A218-1','CNV PDF'),
]
