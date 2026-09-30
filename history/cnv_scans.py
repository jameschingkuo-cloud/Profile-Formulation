"""Converting schedules kept only as scans, read by eye (Claude, 30 Sep 2026; James Kuo: "any production schedule you can get
your hands on, go through and update your data base"). Written in the daily packet's CNV layout so daily/record.py
(cnv_rows) records them exactly as it records a day's scan. Converting sheets print no totals; every order and product
below was checked against the same day's extrusion schedule (the scan's EXT pages, history/image_days_manual.py) where the
order is on it, and a cell printed cut off by its neighbour is completed only from the same order on another sheet of the
same day (H2AA266-1 ink '3005Blue', printed in full on SD11/SD12 and SC31).

    python history/cnv_scans.py          -> work/history/cnv_scans.json (list of packet-like days)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

KEYS = ('order', 'product_code', 'extrusion_status', 'semi_pc_plt', 'semi_size', 'color', 'apl', 'mm', 'flute', 'die_no',
        'die_description', 'die_status', 'plate_status', 'ink_color', 'total_sheets', 'pack_code', 'num_plts', 'pc_per_plt',
        'req_date')


def r(*v, done='', notes='', hand=''):
    d = dict(zip(KEYS, v))
    d.update(done_note=done, row_notes=notes, handwritten=hand, unclear='')
    return d


FLEXCON = ('For next use Flexcon pallet tickets. Put 1 ticket on each of the 40" sides. Must be packed well to prevent boxes '
           'from getting dirty during shipment.')
PACK123 = ('Pack on 48x40 pallet 100pcs laid flat. Alternate direction of boxes so they lay flat. Place 3 bundles vertically on '
           'short & 2 long sides for a total of 150 pcs. Should not be over 49" tall. / *Must use specially purchased "new" heat '
           'treated pallets for this order. These pallets must be stored indoors. / Must use plastic slip and cover sheets. Use '
           'paper board corner protectors.')
CORN = ('Sustainer 8.5 Corn Box (Rev 8.5")',)
COVER = '***Cover sheets must be put on all pallets produced before being sent to Packers.'
TICKETS4 = '***Please put pallet tickets on all 4 sides, not all 4 together on 1 side. Packers will not do this for you.'
SLIT = 'Please allow sufficient cure time for these. Up to 10 days if possible. / Width -0,+1/8, Length -0,+1/8(try to keep +1/16), Hump/Warpage <1/4"'

DAYS = [{
    'packet_date': '2022-11-02',
    'source_scan': 'Downloads/doc05067520260827113931.pdf',
    'ext': [], 'frm': [],
    'cnv': [
        {'scan_page': 101, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - BOBST DIE CUTTER', 'line_no': 'SD31 BOBST',
         'line_code': 'SD31', 'issue_date': '11/2/2022', 'page_of': '1 of 2',
         'banner_notes': [{'position': 'before H2AA171-1', 'text': '**For next please make full pallets only. No partial pallets or pallets with overages.'},
                          {'position': 'before H2AA284-1', 'text': FLEXCON}],
         'rows': [
             r('H2AA028-1', 'CPP40WB361', '15 OF 15', '260', '58 3/16x24 13/16', 'WB', 'P', '4', 'P', 'B0374', 'Halbert Mill Brick Box', 'IN', 'NA', 'NA', '3,900', '48x62', '15', '260', '5-Dec', notes='Use Halbert Mill tickets'),
             r('H2AA029-1', 'DPP40WB882', '12 OF 12', '260', '53 7/8x42 3/8', 'WB', 'P', '4', 'P', 'B0411', 'Lid', 'IN', 'NA', 'NA', '3,000', '48x54', '12', '250', '30-Nov'),
             r('H2AA122-1', 'DPP40WB1242', '0 of 18', '290', '28 3/4x55 1/2', 'WB', 'P', '4', 'P', 'B0301', '8" bliss wrap Natural Stone', 'IN', 'RA722', 'Black', '5,040', '30x54', '18', '280', '22-Nov'),
             r('H2AA171-1', 'DPP40WB1433', '24 OF 22', '295', '31 5/8x40 7/8', 'WB', 'P', '4', 'P', 'B0810', '10x29.63 Partition', 'IN', 'NA', 'NA', '25,520', '42X62', '11', '2320', '11-Nov',
               notes='Watch weights. Target wt is 0.2988. Acceptable range is 0.2779 - 0.3197 / Mark with 4mm 10" 9 slot 154#. No pinched edges. Please use pallet sizes shown as agreed to by VoidForm. Need PALLET TICKETS ON ALL 4 SIDES.'),
             r('H2AA257-1', 'DPP30WB948', '0 OF 5', '385', '33X29 6/16', 'WB', 'P', '3', 'P', 'B0924', 'Flexcon RLE Hopper Bin', '?', 'NA', 'NA', '7,560', '35x62', '3', '2520', '9-Dec'),
             r('H2AA266-1', 'CPP30WB206', '0 OF 10', '395', '80x36 7/16', 'WB', 'P', '3', 'P', 'B0700', 'Commissary Solutions Blue', 'IN', 'RA747', '3005Blue', '3,950', '48X40', '10', '395', '19-Dec',
               notes='Ink printed with its first character cut off by the cell ("?005Blue"); 3005Blue as printed in full for this order on SD11/SD12 and SC31 the same day'),
             r('H2AA284-1', 'CPP40WB318', '32 OF 32', '300', '74 3/16x33 3/16', 'WB', 'P', '4', 'P', 'B0735', 'Flexcon/Nemera Small 1-2-3 Btm Box', 'IN', 'NA', 'NA', '9,600', '48x40', '32', '300', '10-Nov',
               done='Heat Treated*   15 DONE', notes=PACK123),
             r('H2AA291-2', 'DPP40WB946', '0 OF 20', '260', '28 3/4x52 1/2', 'WB', 'P', '4', 'P', 'B0520', 'Halquist Stone Bliss Wrap', 'IN', 'RA698', '187Red', '5,000', '30x54', '20', '250', '21-Nov'),
             r('H2AA291-3', 'DPP70WB39', '0 of 8', '160', '20 11/16x47 11/16', 'WB', 'P', '7', 'P', 'B0521', 'Stone box bliss end', 'IN', 'NA', 'NA', '10,048', '48x40', '4', '2512', '21-Nov'),
             r('H2BA003-1', 'DPP40WB1235', '32 OF 56', '292', '47 1/4x45 5/8', 'WB', 'P', '4', 'P', 'B759A', CORN[0], 'IN', 'NA', 'NA', '16,240', '44x44', '56', '290', '4-Nov'),
             r('H2BA004-1', 'DPP40WB1235', '0 OF 56', '292', '47 1/4x45 5/8', 'WB', 'P', '4', 'P', 'B759A', CORN[0], 'IN', 'NA', 'NA', '16,240', '44x44', '56', '290', '4-Nov'),
         ]},
        {'scan_page': 103, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - BOBST DIE CUTTER', 'line_no': 'SD31 BOBST',
         'line_code': 'SD31', 'issue_date': '11/2/2022', 'page_of': '2 of 2', 'banner_notes': [],
         'rows': [r(f'H2BA00{i}-1', 'DPP40WB1235', '0 OF 56', '292', '47 1/4x45 5/8', 'WB', 'P', '4', 'P', 'B759A', CORN[0], 'IN', 'NA', 'NA', '16,240', '44x44', '56', '290', '7-Nov') for i in (5, 6, 7)]},
        {'scan_page': 103, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - DIE CUTTER', 'line_no': 'SD11/SD12 ROTARY/ PRINTING',
         'line_code': 'SD11/SD12', 'issue_date': '11/2/2022', 'page_of': '1 of 1',
         'banner_notes': [{'position': 'top', 'text': COVER}, {'position': 'top', 'text': TICKETS4}],
         'rows': [
             r('H2AA122-1', 'DPP40WB1242', '3 of 18', '290', '28 3/4x55 1/2', 'WB', 'P', '4', 'P', 'B0301', '8" bliss wrap Natural Stone', 'IN', 'RA722', 'Black', '5,040', '30x54', '18', '280', '22-Nov'),
             r('H2AA266-1', 'CPP30WB206', '0 OF 10', '395', '80x36 7/16', 'WB', 'P', '3', 'P', 'B0700', 'Commissary Solutions Blue', 'IN', 'RA747', '3005Blue', '3,950', '48X40', '10', '395', '19-Dec'),
             r('H2AA291-1', 'DPP40WB1451', '0 OF 24', '300', '92x21', 'WB', 'P', '4', 'P', 'D0176', 'Rev. Halquist 1/2 Surround', 'IN', 'RA764', '187Red', '6,960', '48x96', '12', '580', '21-Nov'),
             r('H2AA291-2', 'DPP40WB946', '0 OF 20', '260', '28 3/4x52 1/2', 'WB', 'P', '4', 'P', 'B0520', 'Halquist Stone Bliss Wrap', 'IN', 'RA698', '187Red', '5,000', '30x54', '20', '250', '21-Nov'),
         ]},
        {'scan_page': 105, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - GUILLOTINE', 'line_no': 'SD41 & 42 GUILLOTINE',
         'line_code': 'SD41/SD42', 'issue_date': '11/2/2022', 'page_of': '1 of 1',
         'banner_notes': [
             {'position': 'top', 'text': '***Use the LEAD EDGE of the semi-finished sheets to square up. Put lead edge against back fence first so the trail edge is cut off first.'},
             {'position': 'top', 'text': TICKETS4},
             {'position': 'top', 'text': 'PUT SEMI-FINISHED PALLET TICKET BEHIND THE FINISHED GOODS TICKET. NOT ANYWHERE ELSE!'},
             {'position': 'top', 'text': "All stock sign blank orders should have Order number & Product code at the bottom of the extrusion pallet ticket. Don't mix ordes unless instructed."},
             {'position': 'before RP22907-2', 'text': 'ALSO USE RP22928-2   221 OF 222'}],
         'rows': [
             r('RP22602-5', 'SPA40WB767', '0 OF 10', '277', '49x37', 'OP', 'A', '4', 'P', 'G0001', '24x18 Sq. cut', 'NA', '', '', '11,000', '48x36', '10', '1100', '27-Nov'),
             r('RP22907-2', 'SPA43WB54', '916 OF 950', '277', '49x37', 'WB', 'A', '4.3', 'P', 'G0001', '24x18 Sq. cut', 'NA', '', '', '1,155,000', '48x36', '1050', '1100', '16-Oct',
               done='1069 DONE', notes='USE ORCHID TICKETS'),
             r('RP22A20-4', 'SPA40WB765', '68 of 68', '277', '49x37', 'WB', 'A', '4', 'P', 'G0010', '48x36 Sq cut', 'NA', '', '', '18,700', '48x36', '68', '275', '20-Nov', done='31 DONE'),
         ]},
        {'scan_page': 107, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - SLITTER', 'line_no': 'SD51 SLITTER',
         'line_code': 'SD51', 'issue_date': '11/2/2022', 'page_of': '1 of 1',
         'banner_notes': [
             {'position': 'top', 'text': COVER},
             {'position': 'top', 'text': '***Please have operators wear gloves when operating Slitter to protect dyne level & keep sheets clean.'},
             {'position': 'top', 'text': '*** For ALL Slitter orders. Please cut length on everything to maximum tolerance useless noted otherwise.'},
             {'position': 'top', 'text': TICKETS4},
             {'position': 'top', 'text': 'PUT SEMI-FINISHED PALLET TICKET BEHIND THE FINISHED GOODS TICKET. NOT ANYWHERE ELSE!'}],
         'rows': [
             r('H2AA315-1', 'SPA40WB817', '0 OF 72', '277', '51x100', 'WB', 'A', '4', 'P', 'SL297', '51X98 SQ CUT', 'NA', '', '', '19,800', '100x51 NEW', '72', '275', '17-Nov', notes=SLIT),
             r('H2AA334-1', 'SPA40WB822', '0 OF 24', '278', '98x53', 'WB', 'A', '4', 'P', 'SL301', '98x51 Sq cut', 'NA', '', '', '1650', '100x51 NEW', '24', '275', '18-Nov', notes=SLIT),
             r('RP22912-2', 'SPA40WB755', '0 OF 40', '278', '48x98', 'WB', 'A', '4', 'P', 'DUM61', '48x96 Sq cut', 'NA', '', '', '11,000', '48x96', '40', '275', '28-Nov'),
         ]},
        {'scan_page': 109, 'title': 'PP PROFILE PRODUCTION INSTRUCTIONS - FOLDER GLUER', 'line_no': 'SC31',
         'line_code': 'SC31', 'issue_date': '11/2/2022', 'page_of': '1 of 1',
         'banner_notes': [{'position': 'top', 'text': COVER}, {'position': 'top', 'text': TICKETS4},
                          {'position': 'before H29A304-1 and H2AA284-1', 'text': FLEXCON}],
         'rows': [
             r('H29A304-1', 'CPP40WB318', '32 OF 32', '300', '74 3/16x33 3/16', 'WB', 'P', '4', 'P', 'B0735', 'Flexcon/Nemera Small 1-2-3 Btm Box', 'IN', 'NA', 'NA', '9,000', '48x40', '60', '150', '28-Nov', done='Heat Treated*', notes=PACK123),
             r('H2AA028-1', 'CPP40WB361', '15 OF 15', '260', '58 3/16x24 13/16', 'WB', 'P', '4', 'P', 'B0374', 'Halbert Mill Brick Box', 'IN', 'NA', 'NA', '3,600', '48x62', '9', '400', '5-Dec', notes='Use Halbert Mill tickets'),
             r('H2AA266-1', 'CPP30WB206', '0 OF 10', '395', '80x36 7/16', 'WB', 'P', '3', 'P', 'B0700', 'Commissary Solutions Blue', 'IN', 'RA747', '3005Blue', '3,510', '48X40', '18', '195', '19-Dec'),
             r('H2AA284-1', 'CPP40WB318', '32 OF 32', '300', '74 3/16x33 3/16', 'WB', 'P', '4', 'P', 'B0735', 'Flexcon/Nemera Small 1-2-3 Btm Box', 'IN', 'NA', 'NA', '9,000', '48x40', '60', '150', '10-Nov', done='Heat Treated*', notes=PACK123),
         ]},
    ]}]


def main():
    import product_code
    import order_number
    from datetime import date
    for d in DAYS:
        on = date.fromisoformat(d['packet_date'])
        for pg in d['cnv']:
            for row in pg['rows']:
                assert not product_code.problems(row['product_code']), row
                assert not order_number.problems(row['order'], on), row
    out = config.WORK_DIR / 'history' / 'cnv_scans.json'
    out.write_text(json.dumps(DAYS, indent=1), encoding='utf-8')
    return out, sum(len(pg['rows']) for d in DAYS for pg in d['cnv'])


if __name__ == '__main__':
    print(main())
