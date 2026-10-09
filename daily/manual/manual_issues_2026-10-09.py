# Issues for the 9 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7bvHGKN.PDF (SCHEDULE 10/09, sent 14:17, run 13:13:23) and "Die Cutting Schedule 10-9.pdf". Both carry
# their text: nothing transcribed or OCR'd, no handwriting. Carried from 8 Oct only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-09.docx" proposes 62 of 91 orders as last issued on their line; 29 orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','SE13 / SE22','H69A075-1, H69A075-2, H68A227-1, H68A227-2','New orders, no formula issued on their line','H69A075-1 DPP40WB1145 and H69A075-2 DPP40WB1155 (SE13). H68A227-1 DPPA0WB271 and H68A227-2 DPPA0WB270 (SE22, 10.0 mm; the same products as H68A226-1 / -2 below)','system PDF'),
 ('Info','EXT','SE11 / SE12 / SE43 / SE61','H69A039-1, H69A218-1, H69A183-2, H69A183-3, H69A354-2','New or gone since 8 Oct','H69A039-1 DPP30WB1023 (SE11) is new and has a formula as last issued. Gone from the extrusion schedule (4): H69A218-1 SPP40WB261 (SE12), H69A183-2 RPP30WB883 and H69A183-3 RPP30WB874 (SE43), H69A354-2 RBP50EB54 (SE61)','system PDF'),
 # ---- EXT, still without a formula from earlier days
 ('Medium','EXT','SE11 / SE12 / SE13 / SE31 / SE43','H69A330-8, H69A330-5, H69A008-1, H6AA013-1, H69A344-1, H69A345-4, H69A338-1, H69A338-2, H69A215-1, H69A286-1, H69A345-1, H6AA036-3','New orders still without a formula (since 7-8 Oct)','H69A330-8 RPP30WB1064 and H69A330-5 RPP30WB1100 (SE11). H69A008-1 CPP40WB565 (SE12). H6AA013-1 RPA40WB3821, H69A344-1 RPA40WB3684, H69A345-4 RPA40WB3812, H69A338-1 RPA40WB3502, H69A338-2 RPA40WB3819, H69A215-1 SPA40WB957 and H69A286-1 SPA40WB913 (SE13). H69A345-1 RPA40WB3164 (SE31). H6AA036-3 RPA30BD19 (SE43)','system PDF'),
 ('Medium','EXT','SE22 / SE61','H6AA020-1, H6AA020-2, H68A226-1, H68A226-2, H69A350-7','New orders still without a formula (since 5 Oct)','H6AA020-1 DPPA0WB268 and H6AA020-2 DPPA0WB269 (SE22, 10.0 mm, "Send to flatbed"). H68A226-1 DPPA0WB271 and H68A226-2 DPPA0WB270 (SE22). H69A350-7 RBP33EB64 (SE61)','system PDF'),
 ('Medium','EXT','SE25 / SE43 / SE61','H68A090-1, H69A330-6, H69A330-10, H69A350-1…-4','New orders still without a formula (since 2 Oct)','H68A090-1 DPP50WB308 (SE25), H69A330-6 RPP30GS130 and H69A330-10 RPP30BD58 (SE43), H69A350-1…-4 RBP33EB42 / 41 / 53 / 48 (SE61). No Tech FRM or approved master decision has come for them yet','system PDF'),
 ('Medium','EXT','SE43','RP26811-1','Order was issued on another line before','RPA20WB28 was issued on SE11 before, not on SE43: left to the engineer','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE11','H68A088-1, H63A200-1, H69A039-1','GSM vs weight range','GSM 514 printed with range 473-488 (H68A088-1); GSM 631 printed with range 582-600 (H63A200-1 and H69A039-1)','system PDF'),
 ('Medium','EXT','SE23','H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 ('Info','EXT','SE23 / SE25','H68A091-1, H64A244-1','999 pallets is a cap','# Plt prints 999; the converting schedule shows the real quantity','system PDF; CNV'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 62 rows on 11 pages','CNV PDF'),
 ('Info','CNV','SD31','H69A067-1','Gone since 8 Oct','No longer on the converting schedule (1 order)','CNV PDF'),
 ('Info','CNV','SD11/SD12 / SD21 / SD31','H69A075-1, H69A075-2, H68A227-1, H68A227-2','New since 8 Oct','New on the converting schedule (4 orders), also new on the extrusion schedule','CNV PDF'),
]
