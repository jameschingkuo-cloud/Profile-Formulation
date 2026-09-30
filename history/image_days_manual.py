"""Schedule days kept only as image scans in the Production Instruction folder, read by eye (Claude, 30 Sep 2026; James
Kuo: "if its scan, OCR them", "if it needs to be rotated, rotate them"). The scans were turned upright first
(work/history/scans/<name>.pdf). OCR alone could not confirm most rows (history/image_days.py), so every row was read
from the page image and checked two ways:

  - REF: a row whose figures (size, spec, cut, sheets, pack, pallets, stack, weight, dates, web) are the same on the scan
    as on the system's own schedule of a neighbouring day takes that day's values (the date is named); anything that
    differs on the scan is given in the row's overrides. Rows not on either neighbouring day are given in full.
  - FOOTER: every line's rows add up to the line total printed on the scan (PCs and LBs), checked by build().

Special instructions: None = as on the REF day (checked on the scan); a string = as read on the scan; ('copy', day, line,
order) = the same text as that system row (checked on the scan). REF may be (day, order): another order of the same day
whose figures the row shares (13 Nov 2023 H3BA067-4 = H3BA067-3). Handwriting goes to 'handwritten' (never read as data).
"""
SCAN_SRC = 'image scan read by eye, checked against the system schedules either side and the printed line totals'

DAYS = {
    '2020-05-08': {'file': '050820.pdf', 'lines': {
        'SE11': {'footer': (49616, 134321), 'run': '10:32:33', 'rows': [
            (1, 'HV4A339-3', 'RPP40WB1047', '2020-05-07', None, {}),
            (1, 'HV4A408-3', 'RPP40WB881', '2020-05-07', None, {}),
            (1, 'HV5A053-2', 'RPP40WB70', '2020-05-07', None, {}),
            (1, 'HV4A311-1', 'DPP40WB1134', '2020-05-07', None, {}),
            (1, 'HV4A396-1', 'DPP40WB1163', '2020-05-07', None, {}),
            (1, 'HV5A142-1', 'DPP40WB1212', '2020-05-11', None, {}),
            (1, 'RP20430-4', 'SPA43YF15', '2020-05-07', None, {}),
            (1, 'RP20428-1', 'RPP40WB156', '2020-05-07', None, {}),
            (1, 'HV5A051-1', 'RPA40WB2968', '2020-05-07', None, {}),
            (2, 'RP20217-2', 'RPA40WB1799', '2020-05-07', '', {}),
            (2, 'HV4A423-1', 'CPP40WB280', '2020-05-07', None, {}),
            (2, 'HV5A132-1', 'RPP40WB1189', '2020-05-11', 'Exact quantity only. No pcs over or short. / Part# 460060', {}),
            (2, 'HV4A425-1', 'CPP30WB206', '2020-05-07', None, {}),
            (2, 'HV4A425-2', 'CPP30WB115', '2020-05-07', None, {}),
            (2, 'HV5A041-1', 'SPA30KS24', '2020-05-07', None, {}),
        ]},
        'SE13': {'footer': (112816, 165265), 'run': '10:38:45', 'rows': [   # a reprint of SE13 alone, 10:38:45
            (3, 'RP20415-2', 'SPA40WB377', '2020-05-07',
             'Send to Guillotine. Mark lead edge & make sure of pc count. / SHEETS MUST BE FLAT. NO CURL OR LEANING PALLETS. / '
             'Use PVC slip sheets on top of each pallet. / Run with next until this is done.  Use BLUE tickets / 68 plts done', {}),
            (3, 'RP20430-5', 'SPA40WB204', '2020-05-07',
             'Send to Guillotine. Mark lead edge & make sure of pc count. / SHEETS MUST BE FLAT. NO CURL OR LEANING PALLETS. / '
             'Use PVC slip sheets on top of each pallet.     34 plts done / Run with above until this is done.  Use BLUE tickets / '
             'Use for RP20415-2', {}),
            (3, 'RP20430-2', 'SPA40WB152', '2020-05-07', None,
             {'cut_length': '37 1/4', 'total_sheets': 2016, 'plts': 8, 'weight_lbs': 2943}),
            (3, 'RP20420-1', 'SPA43WB45', '2020-05-11', None, {}),
            (3, 'RP20124-1', 'SPA43WB34', '2020-05-11', None, {}),
        ]},
        'SE21': {'footer': (30724, 137948), 'run': '10:32:33', 'rows': [
            (4, 'RP20430-1', 'RPP50KS300', '2020-05-07', '2 plts done', {}),
            (4, 'RP20507-5', 'SPA40KS56', None,
             'Send to Guillotine. Mark lead edge & make sure of pc count. / SHEETS MUST BE FLAT. NO CURL OR LEANING PALLETS. / '
             'Use PVC slip sheets on top of each pallet.',
             {'die': 'PB405', 'width': '49', 'length': '37', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'KS KS KS',
              'thk': 4.0, 'gsm': 753, 'cut_width': '49', 'cut_length': '37 1/4', 'cut_rows': 2, 'total_sheets': 1662,
              'pack': '36X48', 'plts': 6, 'pcs_stack': 277, 'stk_plt': 1, 'weight_lbs': 3224, 'instr_date': 'Stock',
              'web_width': '98'}),
            (4, 'RP20413-3', 'RPA60KS12', '2020-05-07', '', {}),
            (4, 'HV4A062-1', 'RPP63KS1', '2020-05-07', None, {}),
            (4, 'HV4A383-1', 'RPA60GE1', '2020-05-07', None, {}),
            (4, 'HV4A422-2', 'RPP60EA7', '2020-05-07', None, {}),
            (4, 'RP20422-1', 'RPA40BD26', '2020-05-07', None, {}),
            (4, 'RP20506-2', 'RPA40BL68', '2020-05-07', None, {}),
            (5, 'HV4A313-1', 'RPP50BL802', '2020-05-07', None, {}),
            (5, 'HV4A300-1', 'RPP40YF55', '2020-05-07', None, {}),
            (5, 'RP20421-3', 'SPA43YF14', '2020-05-07', None, {}),
            (5, 'RP20507-4', 'RPA40YF55', '2020-05-11', None, {}),
        ]},
        'SE22': {'footer': (42489, 465773), 'run': '10:32:33', 'rows': [
            (6, 'HV4A319-2', 'RPPA0KS260', '2020-05-07', None, {}),
            (6, 'RP20429-1', 'RPAA0KS73', '2020-05-07', None, {}),
            (6, 'HV4A432-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (6, 'HV5A004-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (6, 'HV5A002-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (6, 'HV5A003-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (6, 'HV5A005-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (6, 'HV5A006-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A007-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A009-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A070-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A071-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A072-1', 'DPPA0NS38', '2020-05-07', None, {}),
            (7, 'HV5A075-1', 'RPPA0WB241', '2020-05-07', None, {}),
            (7, 'HV5A080-1', 'RPPA0WB363', '2020-05-07', None, {}),
            (7, 'HV5A015-1', 'RPAA0WB321', '2020-05-07', None, {}),
            (8, 'HV5A015-2', 'RPAA0WB320', '2020-05-07', None, {}),
            (8, 'HV5A015-3', 'RPAA0WB322', '2020-05-07', None, {}),
            (8, 'HV3A068-1', 'RPPD0WB166', '2020-05-07', None, {}),
            (8, 'HV3A068-2', 'RPPD0WB167', '2020-05-07', None, {}),
            (8, 'HV4A104-1', 'RPPD0WB166', '2020-05-07', None, {}),
            (8, 'HV4A104-2', 'RPPD0WB167', '2020-05-07', None, {}),
            (8, 'HV4A385-1', 'RPPA0WB423', '2020-05-07', None, {}),
        ]},
        'SE23': {'footer': (21000, 130236), 'run': '10:32:33', 'rows': [    # report page 9 (scan page 9, top half)
            (9, 'RP20324-1', 'RPA40WB1151', '2020-05-11', None, {}),
            (9, 'RP20319-1', 'RPA60WB13', '2020-05-11', None, {}),
            (9, 'RP20504-2', 'RPA50WB56', '2020-05-11', None, {}),
        ]},
        'SE24': {'footer': (28780, 142343), 'run': '10:32:33', 'rows': [    # report page 10 (scan page 9, bottom half)
            (9, 'RP20429-3', 'SPA40WB365', '2020-05-07',
             'Send to Slitter. Mark lead edge & make sure of pc count. / Take to Converting. Do not double stack so QC can check. / '
             'Extrusion to hold width -0, +1/16. / KEEP RUNNING                23 plts done', {}),
            (9, 'RP20211-2', 'RPA40WB1803', '2020-05-07', None, {}),
            (9, 'HV5A047-1', 'RPA40WB1917', '2020-05-07', None, {}),
        ]},
        'SE25': {'footer': (44190, 139632), 'run': '10:32:33', 'rows': [    # report pages 11-12 (scan pages 13-14)
            (13, 'HV4A338-2', 'DPP30WB785', '2020-05-07', None, {}),
            (13, 'HV4A176-2', 'RPP30KS24', '2020-05-07', None, {}),
            (13, 'HV4A130-2', 'RPP30KS842', '2020-05-07', None, {}),
            (13, 'HV5A116-1', 'DPP30KS87', '2020-05-07', None, {}),
            (13, 'HV5A116-2', 'DPP30KS88', '2020-05-07', None, {}),
            (13, 'HV4A339-1', 'RPP30BL495', '2020-05-07', None, {}),
            (13, 'HV4A387-1', 'RPP30BL184', '2020-05-07', None, {}),
            (14, 'HV4A408-2', 'RPP30BL183', '2020-05-07', None, {}),
            (14, 'HV4A408-1', 'RPP30BL185', '2020-05-07', None, {}),
            (14, 'HV5A107-1', 'RPA30BL16', '2020-05-07', None, {}),
            (14, 'RP20506-1', 'RPA20WB28', '2020-05-07', None, {}),
            (14, 'HV4A395-1', 'RPP40WB890', '2020-05-07',
             'Rolled material. Each roll counts as 12 pcs. / Please put 1 plt ticket on the side of the 2 outside rolls. / '
             'Put 4 bands across the top & band together through the cores / No telescoping. Ends must be straight. Rolls must '
             'be tight. / No loose sloppy rolls. Watch weights.  2 plts done', {}),
            (14, 'HV4A395-2', 'RPP40WB890', '2020-05-07', None, {}),
            (14, 'HV4A395-3', 'RPP40WB890', '2020-05-07', None, {}),
        ]},
        'SE31': {'footer': (106191, 302894), 'run': '10:32:33', 'rows': [   # report pages 13-14 (scan pages 10-11)
            (10, 'HV4A330-1', 'DPP40WB1309', '2020-05-07', None, {}),
            (10, 'HV4A407-1', 'RPP40WB601', '2020-05-07', None, {}),
            (10, 'HV4A407-3', 'RPP40WB707', '2020-05-07', None, {}),
            (10, 'HV4A407-2', 'RPP40WB706', '2020-05-07', None, {}),
            (10, 'RP20420-1', 'SPA43WB45', '2020-05-11',
             'Send to Guillotine. Mark lead edge & make sure of pc count. / SHEETS MUST BE FLAT. NO CURL OR LEANING PALLETS. / '
             'Use PVC slip sheets on top of each pallet. / Use ORCHID tickets', {}),
            (10, 'HV5A025-1', 'SPA40WB312', '2020-05-11', None, {}),
            (10, 'HV5A110-9', 'RPA40WB1960', '2020-05-11', None, {'mat_spec': 'OPOPOP'}),
            (11, 'RP20504-1', 'RPA40WB1794', '2020-05-11', None, {'mat_spec': 'OPOPOP'}),
            (11, 'HV4A424-1', 'SPA40NS23', '2020-05-11', None, {}),
            (11, 'HV5A090-1', 'SPA40WB312', '2020-05-11', None, {}),
            (11, 'HV5A042-1', 'DPP40WB893', '2020-05-11', None, {}),
        ]},
        'SE32': {'footer': (12400, 91275), 'run': '10:32:33', 'rows': [     # report page 15 (scan page 12)
            (12, 'RP20211-2', 'RPA40WB1803', '2020-05-11', None, {}),
            (12, 'RP20306-1', 'RPPP0WB2', '2020-05-11', None, {}),
            (12, 'RP20228-2', 'RPPJ0WB6', '2020-05-11', None, {}),
        ]},
        'SE43': {'footer': (11000, 54120), 'run': '10:32:33', 'rows': [     # report page 16 (scan page 15, top half)
            (15, 'RP20211-2', 'RPA40WB1803', '2020-05-11', None, {}),
        ]},
        'SE61': {'footer': (2010, 5286), 'run': '10:32:33', 'rows': [       # report page 17 (scan page 15, bottom half)
            (15, 'HV4A433-2', 'RBP50KS37', '2020-05-11', None, {}),
        ]},
    }, 'final': (461216, 1769093)},  # the report's final total: every line above (SE13 as reprinted at 10:38:45) adds to it
    '2023-11-13': {'file': '111323.pdf', 'lines': {
        'SE11': {'footer': (2590, 9065), 'run': '11:57:24', 'rows': [
            (1, 'H3BA083-1', 'DPP30WB738', '2023-11-10', 'Send to Rotary Die Cutter. Mark lead & make sure of pc count / 4 done', {}),
        ]},
        'SE12': {'footer': (36710, 157046), 'run': '11:57:24', 'rows': [
            (2, 'RP23117-1', 'RPA40WB3142', '2023-11-10', None, {}),
            (2, 'H3BA033-1', 'RPP40BL1645', '2023-11-10', '1 done', {}),
            (2, 'H3BA061-1', 'RPP40WB881', '2023-11-10', None, {}),
            (2, 'H39A194-1', 'CPP40WB318', '2023-11-10', None, {}),
            (2, 'H3AA122-1', 'CPP40WB318', '2023-11-10', None, {}),
            (2, 'H3BA085-2', 'DPP40WB1543', '2023-11-16', 'Send to Flatbed. 255pcs per pallet', {}),
            (2, 'H3BA085-3', 'DPP40WB1544', '2023-11-16', 'Send to Flatbed, 255 pcs per pallet.', {}),
            (2, 'H3BA085-4', 'DPP40WB1545', '2023-11-16', 'Send to Flatbed, 255pcs per plt', {}),
        ]},
        'SE13': {'footer': (16500, 109725), 'run': '11:57:24', 'rows': [
            (3, 'RP23117-1', 'RPA40WB3142', '2023-11-10', None, {}),
        ]},
        'SE21': {'footer': (38500, 173800), 'run': '11:57:24', 'rows': [
            (4, 'RP23615-2', 'RPA40WB3143', '2023-11-10', '8 done', {}),
            (4, 'RP23601-1', 'RPA40WB3051', '2023-11-10', None, {}),
        ]},
        'SE22': {'footer': (5500, 61270), 'run': '11:57:24', 'rows': [
            (5, 'RP23217-1', 'RPAA0WB318', '2023-11-10', None, {}),
        ]},
        'SE23': {'footer': (29616, 88570), 'run': '11:57:24', 'rows': [
            (6, 'H3BA092-1', 'DPP40WB1598', None, 'Send to printing. Mark lead edge & make sure of pc count. / 15 done',
             {'die': 'PB456', 'width': '47 7/8', 'length': '43 7/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 7/8', 'cut_length': '44 1/2', 'cut_rows': 2, 'total_sheets': 15340,
              'pack': '48X54', 'plts': 52, 'pcs_stack': 295, 'stk_plt': 1, 'weight_lbs': 34515, 'instr_date': '06-Dec',
              'web_width': '95 3/4'}),
            (6, 'H3BA085-1', 'DPP40WB1207', None, 'Send to Bobst, 252 pcs per plt',
             {'die': 'PB456', 'width': '46', 'length': '45 3/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '46', 'cut_length': '46', 'cut_rows': 1, 'total_sheets': 3276,
              'pack': '44X44', 'plts': 13, 'pcs_stack': 252, 'stk_plt': 1, 'weight_lbs': 7305, 'instr_date': '03-Dec',
              'web_width': '46'}),
            (6, 'RP23601-1', 'RPA40WB3051', '2023-11-10', None, {}),
        ]},
        'SE24': {'footer': (17050, 75972), 'run': '11:57:24', 'rows': [
            (7, 'RP23601-1', 'RPA40WB3051', '2023-11-10', None, {}),
            (7, 'RP23926-18', 'RPA40WB1795', '2023-11-10', None, {}),
            (7, 'RP23609-1', 'RPP40WB1625', '2023-11-10', '', {'handwritten': 'Do not Run (after Special Instructions)'}),
        ]},
        'SE25': {'footer': (1944, 66096), 'run': '11:57:24', 'rows': [    # report page 8 (scan page 10)
            (10, 'H3BA067-3', 'RPP40WB890', '2023-11-10', ('copy', '2023-11-10', 'SE25', 'H3BA067-1'), {}),
            (10, 'H3BA067-4', 'RPP40WB890', ('2023-11-10', 'H3BA067-3'), 'ROLLS, SAME AS ABOVE', {}),
            (10, 'H3BA067-5', 'RPP40WB890', '2023-11-16', 'ROLLS, SAME AS ABOVE', {}),
        ]},
        'SE31': {'footer': (25878, 102109), 'run': '11:57:24', 'rows': [   # report page 9 (scan page 8)
            (8, 'RP23926-21', 'RPA40WB3073', '2023-11-10', '39 done', {}),
            (8, 'RP23B08-1', 'SPA40WB760', '2023-11-10', None, {}),
        ]},
        'SE32': {'footer': (11550, 48912), 'run': '11:57:24', 'rows': [    # report page 10 (scan page 9)
            (9, 'RP23601-1', 'RPA40WB3051', '2023-11-10', None, {}),
            (9, 'RP23609-1', 'RPP40WB1625', '2023-11-10', '', {'handwritten': 'Do Not Run (after Special Instructions)'}),
        ]},
        'SE43': {'footer': (66500, 140552), 'run': '11:57:24', 'rows': [
            (11, 'SH3BA01-1', 'RPP40WB1731', '2023-11-10', None, {}),
            (11, 'RP23A17-22', 'SPA43WB54', '2023-11-10', None, {}),
            (11, 'RP23601-1', 'RPA40WB3051', '2023-11-10', None, {}),
        ]},
        'SE61': {'footer': (29769, 194629), 'run': '11:57:24', 'rows': [
            (12, 'RP23915-1', 'RBP50EB10', '2023-11-10', None, {}),
            (12, 'H3BA032-3', 'RBP50EB17', '2023-11-10', None, {}),
            (12, 'H37A134-1', 'DBP33EB26', '2023-11-10', None, {'handwritten': 'BA253 written above the row'}),
            (12, 'H37A134-3', 'DBP33EB28', '2023-11-10', None, {}),
            (12, 'H37A134-7', 'DBP33EB29', '2023-11-10', None, {}),
            (12, 'H37A134-10', 'DBP33EB32', '2023-11-10', None, {}),
            (12, 'H37A134-8', 'DBP33EB30', '2023-11-10', None, {}),
            (13, 'H37A134-2', 'DBP33EB27', '2023-11-10', None, {}),
            (13, 'H37A134-6', 'DBP33EB33', '2023-11-10', None, {}),
            (13, 'H37A134-9', 'DBP33EB31', '2023-11-10', None, {}),
            (13, 'H3BA054-1', 'RBP33EB30', '2023-11-10', None, {}),
            (13, 'H3BA089-1', 'RBP33EB6', '2023-11-16', '', {}),
            (13, 'H3BA093-1', 'RBP33EB6', '2023-11-16', '', {}),
            (13, 'H3BA032-1', 'RBP30EB13', '2023-11-10', None, {}),
        ]},
    }, 'final': (282107, 1227746)},
    '2023-11-14': {'file': '111423.pdf', 'lines': {                    # no SE11 page that day
        'SE12': {'footer': (34860, 145801), 'run': '11:44:04', 'rows': [
            (1, 'RP23117-1', 'RPA40WB3142', '2023-11-13', None, {}),
            (1, 'H39A194-1', 'CPP40WB318', '2023-11-13',
             'Send to Bobst. Mark lead edge & make sure of pc count. / FLEXCON      2 done', {}),
            (1, 'H3AA122-1', 'CPP40WB318', '2023-11-13', None, {}),
            (1, 'H3BA085-2', 'DPP40WB1543', '2023-11-13', None, {}),
            (1, 'H3BA085-3', 'DPP40WB1544', '2023-11-13', None, {}),
            (1, 'H3BA085-4', 'DPP40WB1545', '2023-11-13', None, {}),
        ]},
        'SE13': {'footer': (16500, 109725), 'run': '11:44:04', 'rows': [
            (2, 'RP23117-1', 'RPA40WB3142', '2023-11-13', None, {}),
        ]},
        'SE21': {'footer': (46310, 190479), 'run': '11:44:04', 'rows': [
            (3, 'RP23615-2', 'RPA40WB3143', '2023-11-13', '24 done', {}),
            (3, 'RP23601-1', 'RPA40WB3051', '2023-11-13', None, {}),
            (3, 'H3BA116-1', 'DPP40WB1242', ('2023-11-16', 'H3BA116-1', 'SE25'),
             'Send to Bobst / MARK PALLET TAGS WITH ITEM # 10347464', {'die': 'PB405', 'pack': '30X66'}),
            (3, 'H3BA106-1', 'DPP40WB1546', ('2023-11-16', 'H3BA106-1', 'SE25'), 'Send to Die Cutter', {'die': 'PB405'}),
            (3, 'H3BA106-2', 'DPP40EA12', ('2023-11-16', 'H3BA106-2', 'SE25'), 'Send to Die Cutter', {'die': 'PB405'}),
            (3, 'H3BA108-2', 'RPA40WB3164', ('2023-11-16', 'H3BA108-2', 'SE31'), '',
             {'die': 'PB405', 'cut_rows': 1, 'web_width': '48'}),
        ]},
        'SE22': {'footer': (5500, 61270), 'run': '11:44:04', 'rows': [
            (4, 'RP23217-1', 'RPAA0WB318', '2023-11-13', None, {}),
        ]},
        'SE23': {'footer': (11000, 46750), 'run': '11:44:04', 'rows': [
            (5, 'RP23601-1', 'RPA40WB3051', '2023-11-13', None, {}),
        ]},
        'SE24': {'footer': (17050, 75972), 'run': '11:44:04', 'rows': [
            (6, 'RP23601-1', 'RPA40WB3051', '2023-11-13', None, {}),
            (6, 'RP23926-18', 'RPA40WB1795', '2023-11-13', None, {}),
            (6, 'RP23609-1', 'RPP40WB1625', '2023-11-13', '(1done)', {'handwritten': 'Do Not Run'}),
        ]},
        'SE25': {'footer': (1944, 66096), 'run': '11:44:04', 'rows': [    # report page 7 (scan page 9)
            (9, 'H3BA067-3', 'RPP40WB890', '2023-11-13', ('copy', '2023-11-13', 'SE25', 'H3BA067-3', '    16 done'), {}),
            (9, 'H3BA067-4', 'RPP40WB890', '2023-11-13', None, {}),
            (9, 'H3BA067-5', 'RPP40WB890', '2023-11-13', None, {}),
        ]},
        'SE31': {'footer': (25878, 102109), 'run': '11:44:04', 'rows': [   # report page 8 (scan page 7)
            (7, 'RP23926-21', 'RPA40WB3073', '2023-11-13', '54 done', {}),
            (7, 'RP23B08-1', 'SPA40WB760', '2023-11-13', None, {}),
        ]},
        'SE32': {'footer': (11550, 48912), 'run': '11:44:04', 'rows': [    # report page 9 (scan page 8)
            (8, 'RP23601-1', 'RPA40WB3051', '2023-11-13', None, {}),
            (8, 'RP23609-1', 'RPP40WB1625', '2023-11-13', '(1done)', {'handwritten': 'Do Not Run'}),
        ]},
        'SE43': {'footer': (66500, 140552), 'run': '11:44:04', 'rows': [   # report page 10
            (10, 'SH3BA01-1', 'RPP40WB1731', '2023-11-13', None, {}),
            (10, 'RP23A17-22', 'SPA43WB54', '2023-11-13', None, {}),
            (10, 'RP23601-1', 'RPA40WB3051', '2023-11-13', None, {}),
        ]},
        'SE61': {'footer': (29769, 194629), 'run': '11:44:04', 'rows': [   # report pages 11-12 (scan pages 12, 11)
            (12, 'RP23915-1', 'RBP50EB10', '2023-11-13', '3 done', {}),
            (12, 'H3BA032-3', 'RBP50EB17', '2023-11-13', None, {}),
            (12, 'H37A134-1', 'DBP33EB26', '2023-11-13', None, {}),
            (12, 'H37A134-3', 'DBP33EB28', '2023-11-13', None, {}),
            (12, 'H37A134-7', 'DBP33EB29', '2023-11-13', None, {}),
            (12, 'H37A134-10', 'DBP33EB32', '2023-11-13', None, {}),
            (12, 'H37A134-8', 'DBP33EB30', '2023-11-13', None, {}),
            (11, 'H37A134-2', 'DBP33EB27', '2023-11-13', None, {}),
            (11, 'H37A134-6', 'DBP33EB33', '2023-11-13', None, {}),
            (11, 'H37A134-9', 'DBP33EB31', '2023-11-13', None, {}),
            (11, 'H3BA054-1', 'RBP33EB30', '2023-11-13', None, {}),
            (11, 'H3BA089-1', 'RBP33EB6', '2023-11-13', None, {}),
            (11, 'H3BA093-1', 'RBP33EB6', '2023-11-13', None, {}),
            (11, 'H3BA032-1', 'RBP30EB13', '2023-11-13', None, {}),
        ]},
    }, 'final': (266861, 1182295)},
    '2022-11-02': {'file': 'Downloads/doc05067520260827113931.pdf', 'lines': {   # scan of 27 Aug 2026, pages 85-99 (2 report pages a sheet)
        'SE11': {'footer': (5876, 11435), 'run': '10:50:15', 'rows': [
            (85, 'H2AA266-1', 'CPP30WB206', '2022-10-28', None, {}),
            (85, 'H2AA257-1', 'DPP30WB948', '2022-10-28', None, {}),
        ]},
        'SE12': {'footer': (5500, 36575), 'run': '10:50:15', 'rows': [
            (85, 'RP22421-4', 'RPA40WB3142', '2022-10-28', None, {}),
        ]},
        'SE13': {'footer': (3300, 21946), 'run': '10:50:15', 'rows': [
            (87, 'RP22421-4', 'RPA40WB3142', '2022-10-28', None, {}),
            (87, 'H2AA332-1', 'RPA40WB3206', None, 'WHITE OPAQUE.',
             {'die': 'PA406', 'width': '60', 'length': '120', 'mat': 'PPP A', 'mat_spec': 'OPOPOP', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 651, 'cut_width': '60', 'cut_length': '120 3/4', 'cut_rows': 1, 'total_sheets': 550,
              'pack': '60X120', 'plts': 2, 'pcs_stack': 275, 'stk_plt': 1, 'weight_lbs': 3658, 'instr_date': '28-Nov',
              'web_width': '60',
              'handwritten': 'OPOPOP circled; a material list with settings written under the row (e.g. PC416 63, 1203 15, TL460 14)'}),
        ]},
        'SE21': {'footer': (96850, 256035), 'run': '10:50:15', 'rows': [
            (87, 'RP22907-2', 'SPA43WB54', '2022-10-28',
             'SEND TO GUILLOTINE. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / SHEET MUST BE FLAT. NO CURL OR LEANING PALLETS. USE PVC SLIP / '
             'SHEETS ON TOP OF EACH PALLET.    USE ORCHID TICKETS. / 232 PLTS DONE', {}),
            (87, 'RP22A25-2', 'RPA40WB3073', '2022-10-28', None, {}),
            (87, 'RP22928-1', 'RPA40WB3143', '2022-10-28', None, {}),
            (87, 'RP22A12-1', 'RPA60WB240', '2022-10-28', None, {}),
        ]},
        'SE22': {'footer': (18750, 237564), 'run': '10:50:15', 'rows': [
            (89, 'H2AA169-1', 'RPPD0WB157', '2022-10-28', 'VOID FORM, WATCH WEIGHTS, KEEP AS CLOSE AS POSSIBLE. / 16 PLTS DONE', {}),
            (89, 'H2AA283-1', 'RPPD0WB132', '2022-10-28', None, {}),
            (89, 'RP22A31-1', 'RPAA0WB318', '2022-11-10', '', {}),
            (89, 'H29A356-1', 'RPPA0NS63', '2022-11-10', None, {}),
            (89, 'H29A357-1', 'RPPA0NS63', '2022-11-10', None, {}),
            (89, 'H29A357-2', 'RPPA0NS64', '2022-11-10', None, {}),
        ]},
        'SE23': {'footer': (92760, 235615), 'run': '10:50:15', 'rows': [
            (91, 'H2BA003-1', 'DPP40WB1235', None, 'SEND TO BOBST. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / CORN BOX / 32 PLTS DONE',
             {'die': 'PB456', 'width': '47 1/4', 'length': '45 5/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 1/4', 'cut_length': '46 1/4', 'cut_rows': 2, 'total_sheets': 16352,
              'pack': '44X44', 'plts': 56, 'pcs_stack': 292, 'stk_plt': 1, 'weight_lbs': 37773, 'instr_date': '12-Nov',
              'web_width': '94 1/2'}),
            (91, 'H2BA004-1', 'DPP40WB1235', None, 'SEND TO BOBST. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / CORN BOX',
             {'die': 'PB456', 'width': '47 1/4', 'length': '45 5/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 1/4', 'cut_length': '46 1/4', 'cut_rows': 2, 'total_sheets': 16352,
              'pack': '44X44', 'plts': 56, 'pcs_stack': 292, 'stk_plt': 1, 'weight_lbs': 37773, 'instr_date': '12-Nov',
              'web_width': '94 1/2'}),
            (91, 'H2BA005-1', 'DPP40WB1235', None, 'SEND TO BOBST. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / CORN BOX',
             {'die': 'PB456', 'width': '47 1/4', 'length': '45 5/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 1/4', 'cut_length': '46 1/4', 'cut_rows': 2, 'total_sheets': 16352,
              'pack': '44X44', 'plts': 56, 'pcs_stack': 292, 'stk_plt': 1, 'weight_lbs': 37773, 'instr_date': '12-Nov',
              'web_width': '94 1/2'}),
            (91, 'H2BA006-1', 'DPP40WB1235', None, 'SEND TO BOBST. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / CORN BOX',
             {'die': 'PB456', 'width': '47 1/4', 'length': '45 5/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 1/4', 'cut_length': '46 1/4', 'cut_rows': 2, 'total_sheets': 16352,
              'pack': '44X44', 'plts': 56, 'pcs_stack': 292, 'stk_plt': 1, 'weight_lbs': 37773, 'instr_date': '12-Nov',
              'web_width': '94 1/2'}),
            (91, 'H2BA007-1', 'DPP40WB1235', None, 'SEND TO BOBST. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / CORN BOX',
             {'die': 'PB456', 'width': '47 1/4', 'length': '45 5/8', 'mat': 'PPP P', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 753, 'cut_width': '47 1/4', 'cut_length': '46 1/4', 'cut_rows': 2, 'total_sheets': 16352,
              'pack': '44X44', 'plts': 56, 'pcs_stack': 292, 'stk_plt': 1, 'weight_lbs': 37773, 'instr_date': '12-Nov',
              'web_width': '94 1/2'}),
            (91, 'RP22630-1', 'RPA40WB3051', '2022-10-28', 'KEEP RUNNING      USE YELLOW TICKETS', {}),
        ]},
        'SE24': {'footer': (58370, 210397), 'run': '10:50:15', 'rows': [
            (93, 'H2AA206-1', 'RPA40WB3410', '2022-10-28', 'RUN WITH NEXT UNTIL THIS IS DONE.        53 PLTS DONE', {}),
            (93, 'RP22630-1', 'RPA40WB3051', '2022-10-28', None, {}),
            (93, 'RP22912-2', 'SPA40WB755', '2022-10-28', None, {}),
        ]},
        'SE25': {'footer': (19178, 36336), 'run': '10:50:15', 'rows': [    # report page 8 (scan page 97)
            (97, 'H2AA122-1', 'DPP40WB1242', '2022-10-28', 'SEND TO PRINTING. MARK LEAD EDGE & MAKE SURE OF PC COUNT. / 3 PLTS DONE',
             {'handwritten': 'check mark by the row'}),
            (97, 'H2AA291-1', 'DPP40WB1451', '2022-10-28', None, {}),
            (97, 'H2AA291-2', 'DPP40WB946', '2022-10-28', None, {}),
            (97, 'H2AA291-3', 'DPP70WB39', '2022-10-28', None, {}),
            (97, 'RP22201-1', 'RPP40WB1625', '2022-10-28', None, {}),
        ]},
        'SE31': {'footer': (46986, 214998), 'run': '10:50:15', 'rows': [   # report page 9 (scan page 95)
            (95, 'RP22A14-2', 'RPA40WB3133', '2022-10-28', '3 PLTS DONE / WHITE OPAQUE', {'mat_spec': 'OPOPOP'}),
            (95, 'RP22602-5', 'SPA40WB767', '2022-10-28', None, {'mat_spec': 'OPOPOP'}),
            (95, 'H2AA315-1', 'SPA40WB817', '2022-10-28', None, {}),
            (95, 'H2AA334-1', 'SPA40WB822', None,
             'SEND TO SLITTER, MARK LEAD EDGE & MAKE SURE OF PC COUNT. / TAKE TO CONVERTING. DO NOT DOUBLE STACK SO QC CAN CHECK. / '
             'EXTRUSION TO HOLD WITH 0-0, +1/16.',
             {'die': 'PC405', 'width': '98', 'length': '53', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB',
              'thk': 4.0, 'gsm': 700, 'cut_width': '98', 'cut_length': '53 3/4', 'cut_rows': 1, 'total_sheets': 6672,
              'pack': '51X100', 'plts': 24, 'pcs_stack': 278, 'stk_plt': 1, 'weight_lbs': 34428, 'instr_date': '23-Nov',
              'web_width': '98'}),
        ]},
        'SE43': {'footer': (20900, 85657), 'run': '10:50:15', 'rows': [    # report page 11 (scan page 99)
            (99, 'RP22630-1', 'RPA40WB3051', '2022-10-28', 'KEEP RUNNING      USE YELLOW TICKETS', {}),
            (99, 'RP22A28-1', 'RPA30WB37', '2022-11-10', None, {'handwritten': 'PB204 written above the row'}),
            (99, 'H2AA008-1', 'RPP30BL264', '2022-11-10', None, {}),
        ]},
        'SE61': {'footer': (3580, 62143), 'run': '10:50:15', 'rows': [     # report page 12 (scan page 99)
            (99, 'RP22518-1', 'RBPA0KS14', '2022-10-28', '2 PLTS DONE',
             {'total_sheets': 550, 'plts': 5, 'weight_lbs': 9482, 'handwritten': '#2 and PC357 written by the row'}),
            (99, 'H29A351-1', 'RBPA0EB12', '2022-10-28', None, {}),
            (99, 'H2AA296-1', 'RBPA0EB10', '2022-10-28', None, {}),
            (99, 'H2AA031-1', 'RBP33EB6', '2022-10-28', None, {'handwritten': 'BA253 written above the row'}),
        ]},
    }, 'final': (383050, 1455451),
       # report page 10 (SE32) is not in the scan: the final total is 11,000 PCs / 46,750 LBs more than the lines read, the
       # same as RP22630-1 alone on SE32 on 28 Oct and 10 Nov 2022 - not recorded (a page not read is never guessed)
       'unread': (11000, 46750, 'report page 10 (SE32) not in the scan')},
    '2014-04-24': {'file': 'Downloads/doc05084320260828161814.pdf', 'lines': {   # scan of 28 Aug 2026, page 240: report page 16 only
        'SE25': {'footer': (84098, 122756), 'run': '11:34:45', 'rows': [
            (240, 'RP14408-1', 'SPA43WB42', None, 'Send to Guillotine. Mark lead edge & make sure of pc count. / Use pallet tickets from schedule book.  Use ORANGE tickets / Run with next 2 orders   KEEP RUNNING / Run this and the 19x49 on one side of the bad spot and / the 25x37 on the other side of it.', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 4.3, 'gsm': 752, 'width': '49', 'length': '37', 'cut_width': '49', 'cut_length': '37 1/4', 'cut_rows': 1, 'total_sheets': 27700, 'pack': '36X48', 'plts': 100, 'pcs_stack': 277, 'stk_plt': 1, 'weight_lbs': 53738, 'instr_date': 'Stock', 'web_width': '49'}),
            (240, 'RP14408-2', 'SPA43WB43', None, 'Send to Guillotine. Mark lead edge & make sure of pc count. / Use pallet tickets from schedule book.  Use ORANGE tickets / Run with above and next. Run this on operators side.', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 4.3, 'gsm': 753, 'width': '25', 'length': '37', 'cut_width': '25', 'cut_length': '37 1/4', 'cut_rows': 1, 'total_sheets': 27700, 'pack': '36X48', 'plts': 50, 'pcs_stack': 277, 'stk_plt': 2, 'weight_lbs': 27423, 'instr_date': 'Stock', 'web_width': '25'}),
            (240, 'RP14411-2', 'SPA43WB49', None, 'Send to Guillotine. Mark lead edge & make sure of pc count. / Use pallet tickets from schedule book. Run with order above / Use PINK tickets.', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 4.3, 'gsm': 753, 'width': '19', 'length': '49', 'cut_width': '19', 'cut_length': '49 3/8', 'cut_rows': 1, 'total_sheets': 27700, 'pack': '36X48', 'plts': 50, 'pcs_stack': 277, 'stk_plt': 2, 'weight_lbs': 27700, 'instr_date': 'Stock', 'web_width': '19'}),
            (240, 'HP4A156-1', 'RPP40BL416', None, 'Rolled material. Each roll counts as 12 pcs. / Please put 1 plt ticket on the side of the 2 outside rolls. / Put 3 bands across top & band together through the cores. / No telescoping. Ends must be straight. Rolls must be tight. / No loose sloppy rolls. Watch lengths.', {'die': 'PB506', 'mat': 'PPP P', 'mat_spec': 'R2R2R2', 'colour': 'BL BL BL', 'thk': 4.0, 'gsm': 783, 'width': '87', 'length': '300', 'cut_width': '87', 'cut_length': '303', 'cut_rows': 1, 'total_sheets': 324, 'pack': '84X102', 'plts': 9, 'pcs_stack': 12, 'stk_plt': 3, 'weight_lbs': 9396, 'instr_date': '09-May', 'web_width': '87'}),
            (240, 'HP4A207-1', 'RPP40WB1056', None, 'Rolls, Same as above. Use YELLOW tickets.', {'die': 'PB506', 'mat': 'PPP P', 'mat_spec': 'R2R2R2', 'colour': 'WB WB WB', 'thk': 4.0, 'gsm': 753, 'width': '90', 'length': '300', 'cut_width': '90', 'cut_length': '303', 'cut_rows': 1, 'total_sheets': 72, 'pack': '84X102', 'plts': 2, 'pcs_stack': 12, 'stk_plt': 3, 'weight_lbs': 2079, 'instr_date': '07-May', 'web_width': '90'}),
            (240, 'HP4A186-3', 'RPA50WB207', None, '', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 5.0, 'gsm': 1003, 'width': '21', 'length': '72', 'cut_width': '21', 'cut_length': '72 3/4', 'cut_rows': 2, 'total_sheets': 200, 'pack': '48X74', 'plts': 1, 'pcs_stack': 100, 'stk_plt': 2, 'weight_lbs': 430, 'instr_date': '07-May', 'web_width': '42'}),
            (240, 'HP4A186-1', 'RPA50WB205', None, '', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 5.0, 'gsm': 1003, 'width': '30', 'length': '144', 'cut_width': '30', 'cut_length': '144 3/4', 'cut_rows': 3, 'total_sheets': 201, 'pack': '31X145', 'plts': 1, 'pcs_stack': 200, 'stk_plt': 1, 'weight_lbs': 1236, 'instr_date': '07-May', 'web_width': '90'}),
            (240, 'HP4A186-2', 'RPA50WB206', None, '', {'die': 'PB506', 'mat': 'PPP A', 'mat_spec': 'R1R1R1', 'colour': 'WB WB WB', 'thk': 5.0, 'gsm': 1003, 'width': '30', 'length': '88', 'cut_width': '30', 'cut_length': '88 3/4', 'cut_rows': 3, 'total_sheets': 201, 'pack': '31X88', 'plts': 1, 'pcs_stack': 200, 'stk_plt': 1, 'weight_lbs': 754, 'instr_date': '07-May', 'web_width': '90'}),
        ]},
    }, 'partial': 'report page 16 (SE25) only; the other pages of that day are not in the scan'},
}


def build(hist_csv=None, out_csv=None):
    """-> rows in the ext_history.csv format (+ 'source'); raises when a line or a day does not add up to its printed total."""
    import csv
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    import config
    import product_code
    sys.path.insert(0, str(root / 'history'))
    import prod_instr as H
    hist_csv = hist_csv or config.WORK_DIR / 'history' / 'ext_history.csv'
    out_csv = out_csv or config.WORK_DIR / 'history' / 'ext_history_scans.csv'
    ref = {}                                             # an order can run on two lines the same day (RP20420-1)
    for r in csv.DictReader(open(hist_csv, encoding='utf-8')):
        ref[(r['date'], r['line'], r['order'])] = r
    out, notes = [], []
    for day, d in DAYS.items():
        y, m, dd = day.split('-')
        run_date = f'{int(m)}/{dd}/{y[2:]}'
        tot = [0, 0]
        for line, L in d['lines'].items():
            s_pcs = s_lbs = 0
            for page, order, prod, rday, special, over in L['rows']:
                over = dict(over)
                hand = over.pop('handwritten', '')
                if isinstance(special, tuple):                  # ('copy', day, line, order[, text added on the scan])
                    special = ref[(special[1], special[2], special[3])]['special'] + (special[4] if len(special) > 4 else '')
                if rday:
                    rt = rday if isinstance(rday, tuple) else (rday,)
                    rd_, ro_, rl_ = rt[0], (rt[1] if len(rt) > 1 else order), (rt[2] if len(rt) > 2 else line)
                    b = ref.get((rd_, rl_, ro_))                 # REF (day, order, line): the same order on another line
                    if not b or b['prod_code'] != prod:
                        raise SystemExit(f'{day} {line} {order}: no {prod} on the system schedule of {rday}')
                    r = {k: b[k] for k in H.FIELDS}
                    for k, v in over.items():
                        if str(r.get(k)) != str(v):
                            notes.append(f'{day} {order}: {k} {r.get(k)} on {rd_} ({ro_}), {v} on the scan')
                else:
                    r = {k: '' for k in H.FIELDS}
                r.update({k: v for k, v in over.items()})
                if product_code.problems(prod):
                    raise SystemExit(f'{day} {order}: {prod} breaks the product-code rule')
                r.update(date=day, file=d['file'], run_date=run_date, run_time=L['run'], page=page, line=line, t='Y',
                         order=order, order_base=order.split('-')[0], suffix=order.split('-')[1], prod_code=prod,
                         special=(r['special'] if special is None else special), source=SCAN_SRC, handwritten=hand)
                s_pcs += int(r['total_sheets'])
                s_lbs += int(r['weight_lbs'])
                out.append(r)
                ref[(day, line, order)] = r              # a later scanned day may take this day as its reference
            if (s_pcs, s_lbs) != L['footer']:
                raise SystemExit(f'{day} {line}: rows add up to {s_pcs} PCs {s_lbs} LBs; the scan prints {L["footer"]}')
            tot[0] += s_pcs
            tot[1] += s_lbs
        if d.get('partial'):
            notes.append(f"{day}: {d['partial']}")
        if d.get('unread'):                             # a report page missing from the scan: the final total says how much
            tot = [tot[0] + d['unread'][0], tot[1] + d['unread'][1]]
            notes.append(f"{day}: {d['unread'][2]}; the final total accounts for {d['unread'][0]:,} PCs / {d['unread'][1]:,} LBs not recorded")
        if d.get('final') and tuple(tot) != d['final']:
            raise SystemExit(f'{day}: lines add up to {tot}; the report\'s final total is {d["final"]}')
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, H.FIELDS + ['source', 'handwritten'])
        w.writeheader()
        w.writerows(out)
    return len(out), notes, out_csv


if __name__ == '__main__':
    n, notes, path = build()
    print(n, 'rows ->', path)
    for x in notes:
        print('  ', x)
