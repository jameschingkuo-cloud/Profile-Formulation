# Issues for the 19 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7l3fFV2.PDF (SCHEDULE 10/19, sent 13:41, run 14:16:34) and "Die Cutting Schedule 10-19.pdf" (sent 13:42).
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Compared with 16 Oct, the last day published.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-19.docx" proposes 46 of 83 orders as last issued on their line; 37 orders are left to the engineer','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new / gone since 16 Oct
 ('Medium','EXT','(several)','H6AA077-5, H69A181-2, H69A288-11, H6AA043-1, H6AA043-2, H69A058-1, H6AA080-1, H6AA080-2, H69A116-2, H69A116-3, H69A044-1, H69A181-1, H6AA060-1, H6AA060-2, H6AA060-3, H6AA063-1','New orders, no formula issued on their line','New since 16 Oct: SE13 H6AA077-5 RPP40WB1572, H69A181-2 DPP40WB1242; SE22 H69A288-11 RPAA0OF17, H6AA043-1 RPPA0WB457, H6AA043-2 RPPA0WB423, H69A058-1 RPAA0WB387, H6AA080-1 DPPA0WB277, H6AA080-2 DPPA0WB278; SE25 H69A116-2 DPP40WB1546, H69A116-3 DPP40WB1195, H69A044-1 DPP40WB1673, H69A181-1 DPP70WB36; SE61 H6AA060-1 RBP33EB42, H6AA060-2 RBP33EB8, H6AA060-3 RBP33EB60, H6AA063-1 RBP30EB22 (the Word file lists the ones it could not match)','system PDF'),
 ('Info','EXT','(several)','H6AA075-2, H6AA075-3, H6AA036-3, H69A364-2, H69A335-1, H69A335-2, H69A377-1, H69A378-1, H69A358-1, H69A363-1, H69A330-9, H69A373-1, H69A350-1, H69A350-2','Gone since 16 Oct','Gone from the extrusion schedule (14): SE11 H6AA075-2, H6AA075-3, H6AA036-3, H69A364-2; SE13 H69A335-1, H69A335-2, H69A377-1, H69A378-1; SE21 H69A358-1, H69A363-1; SE25 H69A330-9; SE31 H69A373-1; SE61 H69A350-1, H69A350-2','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE11','H69A039-1','GSM vs weight range','GSM 631 printed with range 582-600','system PDF'),
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H69A044-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 73 rows on 11 pages','CNV PDF'),
 ('Info','CNV','(several)','H69A181-2, H69A181-1, H69A116-2, H69A116-3, H6AA080-1, H6AA080-2, H69A044-1','New on the converting schedule since 16 Oct','SD11/SD12 H69A181-2, H69A116-2, H69A116-3; SD31 H69A181-1; SD21 H6AA080-1, H6AA080-2; SD22 H69A044-1','CNV PDF'),
 ('Info','CNV','(several)','H68A245-1, H69A052-1, H5CA064-1, H5CA323-1, H68A226-1, H69A373-1, H69A059-1','Gone since 16 Oct','No longer on the converting schedule: SD31 H68A245-1, H69A052-1, H5CA064-1, H5CA323-1; SD21 H68A226-1; SD51 H69A373-1, H69A059-1','CNV PDF'),
]
