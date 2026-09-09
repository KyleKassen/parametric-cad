"""Carry independently verified same-session catalog records into this new BOM."""

from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "B210_catalog_source_snapshot.json"


def main() -> None:
    old = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    items = copy.deepcopy(old["items"][:4])
    selected = {"H01": 3, "H02": 4, "H03": 4, "F01": 4}
    for item in items:
        item["quantity"] = item["qty"] = selected[item["item_id"]]
        item["verification_context"] = (
            "Exact primary product page/catalog was independently read on 2026-09-08 "
            "in this same workspace session for the B210 direct-stud task. "
            "Specifications and observed prices are carried into the new Mean Well BOM; "
            "no new quote, purchase or same-page reread is claimed."
        )
    items[0].update(
        part_number="91294A128",
        mcmaster_part_number="91294A128",
        description=(
            "M3 x 0.5 x 8 mm hex-drive flat-head screw, 90 degree countersink; DIN 7991; "
            "black-oxide alloy steel; catalog Class 10.9 / 120000 psi tensile"
        ),
        length_mm=8.0,
        pack_price_usd=5.82,
        cost_per_unit_exact_usd="0.0582",
        initial_procurement_cost_usd=5.82,
        url="https://www.mcmaster.com/91294A128/",
        evidence_status="VERIFIED_PRIMARY_LIVE_PRODUCT_DETAIL_2026_09_08",
        verification_context=(
            "Exact M3 x 8 product selected from McMaster search table, then full product "
            "detail read live during this Mean Well task on 2026-09-08. "
            "Displayed delivers tomorrow; no order placed."
        ),
    )
    items[0]["notes"] = [
        "Selected for the three official NSP-1600 bottom M3 mounting holes.",
        "Manufacturer maximum external penetration is 4 mm from the PSU mounting face.",
        (
            "Overall 8 mm length minus 5.0 mm plate plus 0.05 mm nominal head recession "
            "gives 3.05 mm nominal penetration. The assumed 2.75-3.35 mm tolerance range "
            "needs actual finished seat/screw, engagement and internal-clearance checks."
        ),
        (
            "NSP-1600 recommended chassis mounting torque is 6-8 kgf cm "
            "(0.5884-0.7845 Nm). It does not independently qualify the reduced-loadability "
            "countersunk head, custom seat or FPE studs."
        ),
        (
            "No washer under the countersunk heads. Keep heads recessed within the "
            "finished plate envelope. Dry indoor finish."
        ),
    ]
    items[1]["notes"] = [
        "One below each FPE stud locknut. No washer under the three housing countersunk screws.",
        "Use received washer thickness in the assembled stack; no diameter tolerance invented.",
    ]
    items[2]["notes"] = [
        "Four FPE panel studs only. Confirm complete nylon engagement and protruding full threads.",
        "Prevailing and installation torque must remain compatible with unqualified FPE anchors.",
        (
            "Catalog 85 C nylon limit applies to the actual nut temperature, "
            "not an assembly ambient rating."
        ),
    ]
    items[3]["notes"] = [
        (
            "Selected WGU30 M3 load stud is internally consistent in the official "
            "FPD 6.5.1 catalog. M4 WGU40 is unselected because of conflicting ThreadSize data."
        ),
        (
            "Four axes X +/-55 mm, Y -16.1 and -280.8 mm in the adapter datum; "
            "panel reference is 145 x 340 x 6 mm centered Y -150.3 mm."
        ),
        (
            "Nominal 12 mm geometric projection minus 5.0 mm adapter, 0.55 mm washer "
            "and 4 mm nut leaves 2.45 mm tail. Confirm actual projection/thread runout "
            "and socket depth >=10 mm, outside diameter <=10 mm."
        ),
        (
            "FPE base/cavity values are nominal catalog geometry. Installed load, torque "
            "and temperature capacity remain unverified; qualify actual panel anchors."
        ),
    ]
    items[3]["stud_coordinates_mm"] = {
        "x": [-55.0, 55.0],
        "y": [-16.1, -280.8],
        "all_combinations": True,
    }
    result = {
        "revision": "N1 preliminary Mean Well bottom adapter",
        "source_date": "2026-09-08",
        "currency": "USD",
        "scope": "One adapter installation: three PSU bottom screws and four FPE panel studs.",
        "items": items,
        "custom_fabrication_items": [
            {
                "item_id": "M01",
                "quantity": 1,
                "description": (
                    "125 x 300.6 x 5.00 +/-0.05 mm CNC adapter, certified 6061-T6/T651 "
                    "with minimum room-temperature yield 240 MPa; clear MIL-DTL-5541 "
                    "Type II Class 3 conversion after machining; two 0.50 +/-0.05 mm "
                    "fan-frame relief pockets per final model/drawings."
                ),
                "fan_reliefs": {
                    "depth_mm": 0.5,
                    "depth_tolerance_mm": 0.05,
                    "x_intervals_mm": [[-40, -2.85], [2.85, 40]],
                    "y_interval_mm": [-299.1, -269.5],
                    "corner_radius_mm": 0.5,
                },
                "price_usd": None,
            },
            {
                "item_id": "P01",
                "quantity": 1,
                "description": (
                    "145 x 340 x 6 mm reference main-panel coupon centered Y -150.3 mm. "
                    "Final installation panel, supports and FPE installed-stud acceptance "
                    "require confirmation."
                ),
                "price_usd": None,
            },
        ],
        "selected_tim": None,
        "known_mcmaster_initial_pack_subtotal_usd": 20.08,
        "known_installed_fastener_allocated_cost_usd": "0.7450",
        "full_procurement_total_usd": None,
        "price_scope": (
            "Observed on 2026-09-08: screw exact page in this Mean Well task; washers "
            "and nuts in the same-session B210 exact-product verification. Tax, freight, "
            "custom machining/finish, FPE panel/studs, PSU, cables, lugs, guards, "
            "strain relief, fixtures and validation excluded."
        ),
        "purchased_or_ordered": False,
        "notes": [
            (
                "12 V model is a provisional electrical selection; 24 V remains possible. "
                "Load, ambient, input voltage and installed wiring are unconfirmed."
            ),
            (
                "No thermal pad or grease is selected. Preserve manufacturer forced-air "
                "cooling and qualify the enclosure heat-removal boundary."
            ),
            (
                "At the 12 V model's 1500 W output and 89 percent typical efficiency, "
                "calculated PSU loss is about 185 W. This is a planning calculation, "
                "not a measured enclosure load or guaranteed efficiency."
            ),
            (
                "Provide the designated PSU FG protective-earth connection. Adapter/stud "
                "metal contact and conversion coating do not establish protective-earth compliance."
            ),
        ],
    }
    (HERE / "catalog_bom.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Wrote selected 4-row purchased-hardware BOM; McMaster packs $20.08")


if __name__ == "__main__":
    main()
