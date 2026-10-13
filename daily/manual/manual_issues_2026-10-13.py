# Issues for the 13 Oct 2026 packet, built from the system's own PDFs received by the scheduled email run (daily/intake.py): the
# extrusion report BPN9PFR$_Z7fN2lno.PDF (SCHEDULE 10/13, sent 14:02, run 14:14:10) and "Die Cutting Schedule 10-13.pdf" (sent 13:55).
# Both carry their text: nothing transcribed or OCR'd, no handwriting. Carried from 12 Oct only where still true on today's PDFs.
MANUAL = [
 # (Severity, Document, Line, Order, Check, Detail, Source)
 ('Info','FRM','(all)','','No Tech FRM pages today','Only the schedules came (as PDFs). "FRM Formulation 2026-10-13.docx" proposes 57 of 84 orders as last issued on their line; 27 orders are left to the engineer (below)','packet'),
 ('Info','EXT','(all)','','Read from the system PDF','The packet\'s EXT part is the system report itself (daily/intake.py): every record, cut row and special instruction as printed; every line adds up to its printed line total','system PDF'),
 # ---- EXT, new today
 ('Medium','EXT','(several)','H6AA075-1, H6AA075-2, H69A357-1, H68A144-1, H6AA091-4, H69A376-1, H6AA028-1, H69A116-1, H69A364-1, H69A364-2, H69A259-1, H65A222-1, H69A358-1, H69A363-1, H68A143-1, H69A284-1, H69A284-2, H69A284-3, H69A058-2, H69A059-1, H69A373-1, RP26A13-1','New orders, no formula issued on their line','New since 12 Oct: SE11 H6AA075-1 DPP20PK1, H6AA075-2 DPP20PK2, H69A357-1 RPP30WB1049; SE12 H68A144-1 CPP40WB318; SE21 H6AA091-4 and H69A376-1 RPP40PK17, H6AA028-1 RPP50BL1501, H69A116-1 DPP40EA12, H69A364-1/-2 RPP40KS776, H69A259-1 RPA40KS826, H65A222-1 RPP40KS1372, H69A358-1 RPP40KS1905, H69A363-1 RPP40KS2362; SE23 H68A143-1 CPP40WB320; SE25 H69A284-1/-2/-3 RPP40WB890; SE31 H69A058-2 SPA40WB952, H69A059-1 SPA40WB953, H69A373-1 SPA30WB47; SE32 RP26A13-1 RPA40WB3143','system PDF'),
 ('Info','EXT','(several)','H69A180-1, H69A206-1, H69A338-2, H69A215-1, H69A286-1, RP26916-2, H68A226-2, H68A227-2, H68A154-1, H69A345-1, H69A267-1, H69A330-1, H69A330-2, H69A330-4, H6AA036-3','Gone since 12 Oct','Gone from the extrusion schedule (15): SE11 H69A180-1, H69A206-1; SE13 H69A338-2, H69A215-1, H69A286-1; SE21 RP26916-2; SE22 H68A226-2, H68A227-2; SE31 H68A154-1, H69A345-1; SE43 H69A267-1, H69A330-1, H69A330-2, H69A330-4, H6AA036-3','system PDF'),
 # ---- EXT, still without a formula from earlier days
 ('Medium','EXT','SE11','H6AA077-11','New order still without a formula (since 12 Oct)','H6AA077-11 RPP30KS1133 (SE11) has no formula issued','system PDF'),
 ('Medium','EXT','SE13','H69A075-1, H69A075-2','New orders still without a formula (since 7-9 Oct)','H69A075-1 DPP40WB1145 and H69A075-2 DPP40WB1155 (SE13)','system PDF'),
 ('Medium','EXT','SE22','H68A226-1, H68A227-1','New orders still without a formula (since 5-9 Oct)','H68A226-1 and H68A227-1 DPPA0WB271 (SE22, 10.0 mm)','system PDF'),
 # ---- EXT, GSM vs the weight range in the instructions
 ('Medium','EXT','SE11','H69A039-1','GSM vs weight range','GSM 631 printed with range 582-600','system PDF'),
 ('Medium','EXT','SE23','H69A166-1, H68A091-1','GSM vs weight range','GSM 793 printed; the instructions give a range of 729-751','system PDF'),
 ('Medium','EXT','SE25','H68A090-1, H64A244-1','GSM vs weight range','GSM 1,052 printed; the instructions give a range of 970-1000','system PDF'),
 # ---- CNV
 ('Info','CNV','(all)','','Read from the PDF','The converting pages are the Excel schedule\'s PDF (daily/cnv_from_pdf.py): each cell\'s full text, also where the paper cuts it off. 70 rows on 11 pages','CNV PDF'),
 ('Info','CNV','(several)','H6AA075-1, H6AA075-2, H68A144-1, H68A143-1, H69A116-1, H69A215-1, H69A373-1, H69A058-2, H69A059-1','New on the converting schedule since 12 Oct','SD31 H6AA075-1, H6AA075-2, H68A144-1; SD11/SD12 H68A143-1, H69A116-1; SD51 H69A215-1, H69A373-1, H69A058-2, H69A059-1; SC31 H68A144-1, H68A143-1','CNV PDF'),
 ('Info','CNV','SD21 / SC31','H69A074-1, H68A142-1','Gone since 12 Oct','No longer on the converting schedule: SD21 H69A074-1, SC31 H68A142-1','CNV PDF'),
]
