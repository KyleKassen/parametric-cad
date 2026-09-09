"""Reproduce a readable procurement BOM from retained catalog evidence."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    source = json.loads((HERE / "references/research/catalog_bom.json").read_text(encoding="utf-8"))
    lines = [
        "# Bill of materials - D1 direct stud plate",
        "",
        "For one B210 installation. Catalog details and prices checked 2026-09-08; "
        "no purchase placed.",
        "",
        "| Item | Qty | Supplier / order identifier | Complete specification and application "
        "| Pack / budget |",
        "| --- | ---: | --- | --- | --- |",
        "| P01 | 1 | Custom machine shop: plate_D1.step + drawing | "
        "150 x 148 x 3.50 +/-0.05 mm, certified 6061-T6/T651, minimum room-temperature "
        "yield 240 MPa; clear/natural chemical conversion MIL-DTL-5541 Type II Class 3; "
        "all dimensions after finish | Quote required |",
        "| P02 | 1 | Front Panel Express: final custom support panel | "
        "Reference coupon 180 x 200 x 6 mm only; final panel outline, supports and material "
        "to be confirmed. FPE 5-10 mm catalog aluminum is EN AW-5754 H22, "
        "not the adapter's 6061. Stud installation native in FPD. | Quote required |",
    ]
    for item in source["items"]:
        url = item.get("url")
        label = item["part_number"]
        supplier = item["vendor"] + ": " + (f"[{label}]({url})" if url else label)
        budget = (
            f"{item['pack_qty']}/pack; ${item['pack_price_usd']:.2f}/pack"
            if item.get("pack_price_usd") is not None
            else "FPE factory-installed; quote required"
        )
        lines.append(
            f"| {item['item_id']} | {item['qty']} | {supplier} | {item['description']} | {budget} |"
        )
    total = sum(i.get("initial_procurement_cost_usd") or 0 for i in source["items"])
    lines += [
        "",
        f"One pack of each of the three McMaster hardware items totals **${total:.2f}**, "
        "excluding shipping and tax.",
        "Each selected McMaster pack contains 100 pieces; the per-assembly consumption "
        "is four screws, four washers and four locknuts.",
        "The FPE studs, supporting panel, machined adapter and finishing "
        "are additional, unquoted costs.",
        "",
        "No washers go under the countersunk housing screws.",
        "The M3 x 6 screw length includes its head; physical protrusion and real head seating "
        "govern acceptance, not the simplified CAD head.",
        "The screw catalog lists Class 10.9 and 120000 psi tensile; neither establishes "
        "the reduced-head or installed insert capacity.",
        "Nut nylon maximum 85 C is a catalog material limit, not the allowable radio, "
        "FPE adhesive or installation ambient.",
        "FPE WGU30 denotes its native load-stud element, M3 / 12 mm / reverse side / "
        "zero depth offset; it is not a McMaster SKU or a generic stud substitution.",
        "",
        "Required existing item: one enclosed B210 matching the supplied STEP; remove its four "
        "adhesive feet, retain all original internal hardware.",
        "Tools: 2 mm hex driver for housing screws and 5.5 mm AF socket "
        "(<=10 mm OD, >=9 mm clear internal depth) for stud nuts; "
        "actual access and qualified torque procedure required.",
        "No liquid threadlocker is approved for the initial fit prototype. "
        "Conditional LOCTITE 222 / McMaster 1810A27 is discussed in the research note "
        "and intentionally excluded from the order list.",
        "See ASSEMBLY.md for head recession, protrusion, full engagement, "
        "locking and inspection requirements.",
        "",
    ]
    (HERE / "BOM.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"BOM generated; three McMaster packs ${total:.2f}")


if __name__ == "__main__":
    main()
