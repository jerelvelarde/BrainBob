"""Authoring source, not a training-data generator. Public synthetic diagnostic cases."""
import json
import random
from pathlib import Path

# Each row: independent template, existing fact, equivalent, conflicting, unrelated.
EVAL = [
    ('launch', 'Aster production launch is scheduled for 2026-11-06.', 'Aster goes live on November 6, 2026.', 'Aster production launch is now scheduled for 2026-11-13.', 'Aster internal rehearsal is scheduled for 2026-11-13.'),
    ('owner', 'Mina is the sole incident commander for incident INC-82.', 'INC-82 has exactly one incident commander: Mina.', 'Omar replaces Mina as the sole incident commander for INC-82.', 'Mina is the incident commander for incident INC-83.'),
    ('negation', 'Workspace Elm does not permit public links.', 'Public sharing links are prohibited in workspace Elm.', 'Public sharing links are now permitted in workspace Elm.', 'Workspace Birch permits public links.'),
    ('duration', 'Project Cedar retains access logs for 14 days.', 'Cedar access logs are kept for two weeks.', 'Cedar access log retention has changed to 30 days.', 'Cedar billing records are kept for 30 days.'),
    ('money', 'The approved total budget for Orion phase 1 is USD 12000.', 'Orion phase 1 has an approved total budget of twelve thousand US dollars.', 'The approved total budget for Orion phase 1 is now USD 15000.', 'Orion phase 2 has an approved total budget of USD 15000.'),
    ('timezone', 'The Kestrel review starts at 09:00 UTC on 2026-10-20.', 'The Kestrel review starts at 10:00 UTC+01:00 on 2026-10-20.', 'The Kestrel review now starts at 11:00 UTC on 2026-10-20.', 'The Kestrel retrospective starts at 11:00 UTC on 2026-10-20.'),
    ('contact', 'The current support address for account Lumen is help@lumen.example.', 'Contact Lumen account support at help@lumen.example.', 'The current support address for account Lumen is now care@lumen.example.', 'The current support address for account Nova is care@nova.example.'),
    ('units', 'Service Pike has a maximum request payload of 1024 bytes.', 'Service Pike accepts payloads of at most 1 KiB.', 'Service Pike now allows a maximum request payload of 2048 bytes.', 'Service Pike response payloads have a maximum size of 2048 bytes.'),
    ('threshold', 'A purchase above USD 5000 requires two approvers in team Juniper.', 'In Juniper, purchases exceeding USD 5000 need two approvals.', 'Juniper now requires two approvers only for purchases above USD 10000.', 'Juniper expense reports must be submitted within 10 days.'),
    ('preference', 'For written status updates, Nia prefers bullet points over paragraphs.', 'Nia prefers status reports formatted as bullets rather than paragraphs.', 'Nia now prefers paragraphs instead of bullet points for written status updates.', 'Nia prefers afternoon meetings.'),
    ('location', 'Order O-14 must be delivered to Dock 7.', 'Dock 7 is the required delivery location for order O-14.', 'Order O-14 must now be delivered to Dock 9.', 'Order O-15 must be delivered to Dock 9.'),
    ('version', 'The production parser in Grove is version 2.4.1.', 'Grove production runs parser v2.4.1.', 'Grove production now runs parser version 2.5.0.', 'Grove staging runs parser version 2.5.0.'),
    ('frequency', 'Harbor project invoices are sent every Monday.', 'Harbor sends project invoices weekly on Mondays.', 'Harbor project invoices are now sent every Friday.', 'Harbor project payroll is processed every Friday.'),
    ('count', 'The Iris plan includes exactly 8 editor seats.', 'Eight editor seats are included in the Iris plan.', 'The Iris plan now includes exactly 12 editor seats.', 'The Iris plan includes 12 viewer seats.'),
    ('set', 'Only PDF and PNG files are allowed for intake form Finch.', 'Finch intake accepts PNG or PDF files and no other formats.', 'Finch intake now accepts only PDF, PNG and JPEG files.', 'Finch export supports CSV files.'),
    ('interval', 'The current maintenance window for Quartz is 02:00 to 04:00 UTC.', 'Quartz maintenance currently runs from 2 a.m. through 4 a.m. UTC.', 'The current Quartz maintenance window is now 03:00 to 05:00 UTC.', 'Quartz customer support operates from 03:00 to 05:00 UTC.'),
    ('condition', 'For team Maple, travel booking requires manager approval before purchase.', 'Maple employees must obtain manager approval before buying travel.', 'Maple travel can now be purchased before manager approval.', 'Maple equipment purchases require finance approval.'),
    ('identifier', 'Account customer-204 belongs to the company Vale.', 'Vale is the company associated with customer account customer-204.', 'Customer account customer-204 has been reassigned from Vale to Rook.', 'Account customer-205 belongs to the company Rook.'),
    ('historical', 'In September 2026, the Zephyr support tier was Silver.', 'Zephyr had the Silver support tier during September 2026.', 'Correction: Zephyr had the Gold support tier in September 2026, not Silver.', 'In October 2026, the Zephyr support tier was Gold.'),
    ('entity', 'Alex Chen in Legal is the owner of contract C-91.', 'Contract C-91 is owned by Legal team member Alex Chen.', 'Contract C-91 is now owned by Alex Chen in Engineering, replacing Alex Chen in Legal.', 'Alex Chen in Engineering owns contract C-92.'),
]
DEV = [
    ('dev-color', 'The approved badge color for Spruce is blue.', 'Spruce badges are approved to be blue.', 'Spruce badges must now be green.', 'Spruce office walls are green.'),
    ('dev-transport', 'Shipment S-400 travels by rail.', 'Rail is the transport mode for shipment S-400.', 'Shipment S-400 will now travel by sea.', 'Shipment S-401 travels by sea.'),
    ('dev-format', 'The weekly Wren archive is encrypted.', 'Encryption is enabled for the weekly Wren archive.', 'Encryption is now disabled for the weekly Wren archive.', 'The daily Wren archive is not encrypted.'),
    ('dev-temperature', 'The current target temperature for chamber Cobalt is 5 Celsius.', 'Chamber Cobalt has a current target of 5 degrees Celsius.', 'Chamber Cobalt now has a target of 8 Celsius.', 'Chamber Copper has a target temperature of 8 Celsius.'),
]


def build(rows, split):
    cases = []
    for group, old, same, conflict, unrelated in rows:
        for verdict, new in [('same', same), ('conflict', conflict), ('unrelated', unrelated)]:
            cases.append({'template_id': group, 'existing': {'text': old, 'date': '2026-10-01'},
                          'candidate': {'text': new, 'date': '2026-10-16'},
                          'gold': verdict})
    random.Random(1729).shuffle(cases)
    for i, case in enumerate(cases, 1):
        case['id'] = f'{split}-{i:03d}'
        case['existing']['id'] = f'm-{i:03d}'
        case['candidate']['source_id'] = f's-{i:03d}'
    return cases


if __name__ == '__main__':
    root = Path(__file__).parent
    for split, rows in [('eval', EVAL), ('dev', DEV)]:
        (root / f'{split}.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in build(rows, split)))
