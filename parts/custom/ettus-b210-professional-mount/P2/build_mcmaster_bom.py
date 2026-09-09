"""Regenerate the P2 purchasing Markdown and UTF-8 CSV from verified catalog JSON.

Run with Python 3 from any directory. Uses only the standard library.
Catalog facts and installed quantities are owned by references/catalog_bom.json.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "references" / "catalog_bom.json"
SCOPES = ("flat", "upright", "combined")


def dec(value):
    return Decimal(str(value))


def money(value):
    return f"${dec(value):.2f}"


def md(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def link(item):
    return f'[{item["mcmaster_part_number"]}]({item["url"]})'


def row_cost(item, scope):
    return dec(item["pack_price_usd"]) * item["initial_procurement_packs"][scope]


def installed_qty(item, scope):
    if "installed_qty_" + scope in item:
        return f'{item["installed_qty_" + scope]} patches'
    return str(item["qty_" + scope])


def verify(data):
    items = data["items"]
    assert len({i["item_id"] for i in items}) == len(items), "Duplicate item IDs"
    assert len({i["mcmaster_part_number"] for i in items}) == len(items), "Duplicate SKUs"
    for item in items:
        assert item["url"] == f'https://www.mcmaster.com/{item["mcmaster_part_number"]}/'
        assert item["evidence_status"] == "VERIFIED_PRIMARY_LIVE_PRODUCT_DETAIL"
        assert dec(item["pack_price_usd"]) / item["pack_qty"] == dec(item["cost_per_unit_exact_usd"])
        for scope in SCOPES:
            assert row_cost(item, scope) == dec(item["initial_procurement_cost_usd"][scope])
            count = item["qty_" + scope]
            if isinstance(count, int):
                assert item["initial_procurement_packs"][scope] * item["pack_qty"] >= count
        if item["item_id"].startswith("H"):
            assert item["qty_combined"] == item["qty_flat"] + item["qty_upright"]
    for scope in SCOPES:
        assert sum(row_cost(i, scope) for i in items) == dec(data["initial_procurement_total_usd"][scope])
        hardware = sum(dec(i["cost_per_unit_exact_usd"]) * i["qty_" + scope]
                       for i in items if i["item_id"].startswith("H"))
        assert hardware == dec(data["allocated_installed_hardware_usd"][scope])
    s = data["retainer_stack"]
    grip = sum(dec(s[name]) for name in ("bar_thickness_nominal", "head_washer_thickness_nominal",
                                       "spacer_length_nominal", "selected_shim_stack_nominal"))
    entry = dec(s["screw_length_nominal"]) - grip
    assert entry == dec(s["screw_entry_nominal"])
    assert dec(s["boss_height_nominal"]) - entry == dec(s["tip_recess_nominal"])
    f = data["foot_stack"]
    foot_stack = sum(dec(f[name]) for name in ("integral_bolt_seat_total_thickness_nominal",
                     "top_washer_thickness_nominal", "support_plate_thickness_nominal",
                     "bottom_washer_thickness_nominal", "nut_overall_height_nominal"))
    assert foot_stack == dec(f["head_to_nut_end_stack_nominal"])
    assert dec(f["screw_length_nominal"]) - foot_stack == dec(f["tail_beyond_nut_nominal"])


def write_markdown(data):
    items = data["items"]
    s = data["retainer_stack"]
    lines = [
        "# B210 mount P2 — McMaster purchasing BOM", "",
        f'**{money(data["initial_procurement_total_usd"]["combined"])} buys the listed starter inventory for two independently complete mounts: one flat and one upright.** '
        f'Prices were observed on {data["source_date"]}, in USD. No order has been placed.', "",
        "This catalog BOM covers purchased hardware and consumables. Machined parts, raw machining stock, finish, supporting plate, radio, cables, tools, labor, shipping and tax are excluded. Reconfirm prices and specifications at procurement. Physical fit and joint qualification remain required.", "",
        "## Installed quantities", "",
        "AR means select the actual installed amount during fit-up. For the PET film, the installed counts below are cut patches; one purchased sheet supplies both mounts. The threadlocker bottle and shim packs are shared selection inventory.", "",
        "| Item | Exact McMaster part | Specification | Flat | Upright | Both |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for item in items:
        lines.append("| " + " | ".join((item["item_id"], link(item), md(item["description"]),
                                         installed_qty(item, "flat"), installed_qty(item, "upright"),
                                         installed_qty(item, "combined"))) + " |")
    lines += ["", "H06 is fitted under the **four upright foot screw heads only**. It replaces H03 at those locations. Keep the standard H03 washer under each corresponding bottom nut. All other through-bolt joints use one H03 under the head and one under the nut. Each retainer uses one H03 under its screw head.", "",
              "## Purchase quantities for both mounts", "",
              "Purchase quantities include unused pieces caused by pack sizes. One pack of each shim is fit-selection inventory; installed shim counts remain AR.", "",
              "| Item / part | Pack size | Buy packs | Pieces / containers received | USD / pack | USD line total |",
              "| --- | ---: | ---: | --- | ---: | ---: |"]
    for item in items:
        packs = item["initial_procurement_packs"]["combined"]
        received = packs * item["pack_qty"]
        unit = item["pack_unit"] + ("s" if received != 1 else "")
        lines.append(f'| {item["item_id"]} / {link(item)} | {item["pack_qty"]} | {packs} | '
                     f'{received} {md(unit)} | {money(item["pack_price_usd"])} | {money(row_cost(item, "combined"))} |')
    lines += [f'| **Total** | | | | | **{money(data["initial_procurement_total_usd"]["combined"])}** |', "",
              f'For a single mount, separately purchased starter inventory totals {money(data["initial_procurement_total_usd"]["flat"])} flat or '
              f'{money(data["initial_procurement_total_usd"]["upright"])} upright. Do not add those two figures to estimate the combined purchase: sheet, bottle and packs are shared.', "",
              "The CSV preserves the exact pack-price / pack-quantity unit cost without rounding to cents. All currency totals here use purchased pack quantities. These figures are hardware estimates, not a complete fabrication quotation.", "",
              "## Retainer fit and shim selection", "",
              "1. Measure the actual device at the specified contact regions, all four purchased spacers, machined bosses and bars, and the bonded film with its release liner removed. Match spacer lengths before choosing shims. Follow the shim locations on the final assembly drawing.",
              f'2. The nominal stack at each station is {s["selected_shim_stack_nominal"]:.4f} mm: one S02 0.50 mm, one S01 0.10 mm and one S03 0.0508 mm shim. That is three rings at each of four stations: 12 rings per mount, or 24 rings for both. Each shim part contributes four nominal rings per mount, eight for both. This recipe establishes nominal CAD fit; actual catalog thickness ranges require measurement.',
              f'3. Select the actual stack to obtain a measured top gap of {s["final_cold_and_warm_top_gap_min"]:.2f}–{s["final_cold_and_warm_top_gap_max"]:.2f} mm at both cold and representative warm operation. The bars provide positive capture without preloading the enclosure. The actual shim count remains AR. Do not exceed four shim rings at a station without revising the design. Center the larger-bore S03 shim on a supported bearing face.',
              f'4. Nominal head-to-boss grip is 5 + 1 + 30 + {s["selected_shim_stack_nominal"]:.4f} = 36.6508 mm. With an M5 × 45 screw, nominal entry is {s["screw_entry_nominal"]:.4f} mm into a {s["boss_height_nominal"]:.2f} mm boss, leaving {s["tip_recess_nominal"]:.4f} mm nominal tip recess. Inspect for at least {s["effective_full_thread_engagement_min"]:.1f} mm effective full-thread engagement and at least {s["tip_recess_min"]:.1f} mm tip recess after actual tolerances, chamfers and incomplete threads. Nominal entry does not prove full-thread engagement.',
              "5. Verify the final screw never bottoms or protrudes toward the device, both bars seat on their spacer stacks, and measured gaps remain in range. Record each station’s spacer and shim selection for repeatable reassembly.", "",
              "## Purchased-part and assembly requirements", "",
              "- **Spacers:** McMaster 94669A146 does not identify alloy, temper, yield strength or finish. Its listed tensile strength and hardness do not establish 6061-T6 yield strength. Do not substitute it into a 6061-T6 calculation. Qualify the actual spacer joint against the engineering note and inspect for permanent shortening during preload/prototype testing.",
              "- **Film:** cut eight 16 × 20 mm patches with R1 corners per mount. Catalog film is 0.127 ± 0.0127 mm, but adhesive inclusion in that thickness is not stated. The final installed film including adhesive must measure ≤0.20 mm. No structural, friction or cooling benefit is credited.",
              "- **Foot bolts and seats:** use four H07 M5 × 30 mm foot screws through integral bolt seats of 10 mm total thickness; the main foot remains 6 mm. Nominal head-to-nut-end stack is 10 + 1.2 + 6 + 1 + 5 = 23.2 mm, leaving 6.8 mm nominal screw tail beyond the nut. Inspect full nut and nylon-insert engagement and underside clearance with the actual stack. The integral seats provide local foot stiffness without relying on the soft oversized washer to spread bending load.",
              "- **Foot top washers:** H06 catalog diameters are nominal; its technical drawing does not state diameter tolerances. Inspect OD ≥14.9 mm as a design acceptance requirement. Catalog thickness is 1.0–1.4 mm, and CAD uses 1.2 mm. Recheck foot screw protrusion with the delivered washers. Hardness B56 does not establish a high-strength washer class; qualify local washer/seat behavior on the prototype.",
              "- **Hardware strength:** screws are verified Class 12.9, nuts Class 10, and H03 washers are cataloged for Class 10.9. H06 strength grade is unspecified. These parts and the aluminum female threads constrain allowable joint preload. No full-Class-12.9 joint rating or installation torque is claimed. Use the prototype-qualified assembly procedure.",
              "- **Locking:** use nylon-insert nuts only on through-bolts. Replace after prototype removal cycles before final installation. Apply LOCTITE 243 only to the four tapped retainer joints per mount as directed by the final assembly procedure, keeping it off film and nylon inserts. Follow the [Henkel 243 technical data sheet](https://datasheets.tdx.henkel.com/LOCTITE-243-en_GL.pdf) and qualify cure on the actual joint. Adhesive breakaway test values are not tightening torque.",
              "- **Environment and interface:** black-oxide hardware is selected for stationary dry indoor service. The 25 mm flat-mount bolts and 30 mm upright-foot bolts assume the specified 6 mm support plate and finished joint stack; reselect if that interface changes. Upright web joints use 25 mm screws. This purchase list does not qualify outdoor, vehicle, airborne or overhead service.", "",
              "## Evidence and regeneration", "",
              "Each part-number link above points to its exact McMaster product page. Catalog identity, listed dimensions, pack quantity and public price were checked on the stated date; incoming physical measurements and strength tests have not been performed.", "",
              "The source is [references/catalog_bom.json](references/catalog_bom.json), with supporting hardware and spacer/film research in that folder. Regenerate this Markdown and the CSV with `python build_mcmaster_bom.py` from P2, or run the script by absolute path. The generator verifies exact unit costs, installed counts, pack-rounded totals and nominal retainer/foot-stack arithmetic before export.", ""]
    (ROOT / "McMaster_BOM.md").write_text("\n".join(lines), encoding="utf-8")


def write_csv(data):
    fields = ["item_id", "mcmaster_part_number", "description", "qty_flat", "qty_upright", "qty_combined",
              "quantity_unit", "installed_qty_flat", "installed_qty_upright", "installed_qty_combined",
              "installed_quantity_unit", "pack_qty", "pack_unit", "pack_price_usd", "cost_per_unit_exact_usd",
              "buy_packs_flat", "buy_packs_upright", "buy_packs_combined", "received_units_combined",
              "procurement_cost_flat_usd", "procurement_cost_upright_usd", "procurement_cost_combined_usd",
              "source_date", "evidence_status", "url", "notes"]
    target = ROOT / "McMaster_BOM.csv"
    with target.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for item in data["items"]:
            row = {field: item.get(field, "") for field in fields}
            for scope in SCOPES:
                row["buy_packs_" + scope] = item["initial_procurement_packs"][scope]
                row["procurement_cost_" + scope + "_usd"] = f'{row_cost(item, scope):.2f}'
            row["pack_price_usd"] = f'{dec(item["pack_price_usd"]):.2f}'
            row["received_units_combined"] = item["pack_qty"] * item["initial_procurement_packs"]["combined"]
            row["notes"] = " ".join(item["notes"])
            if item["item_id"].startswith("S"):
                row["notes"] += " Nominal recipe uses 4 of this part per mount / 8 for both; actual count remains AR."
            writer.writerow(row)
        total = {"item_id": "TOTAL", "description": "Starter purchase inventory; one flat and one upright independent mount",
                 "source_date": data["source_date"], "notes": data["price_scope"]}
        for scope in SCOPES:
            total["procurement_cost_" + scope + "_usd"] = f'{dec(data["initial_procurement_total_usd"][scope]):.2f}'
        writer.writerow(total)
    with target.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == len(data["items"]) + 1
    assert rows[-1]["procurement_cost_combined_usd"] == f'{dec(data["initial_procurement_total_usd"]["combined"]):.2f}'


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    verify(data)
    write_markdown(data)
    write_csv(data)
    print(json.dumps({"status": "PASS", "catalog_rows": len(data["items"]),
                      "outputs": ["McMaster_BOM.md", "McMaster_BOM.csv"],
                      "initial_procurement_total_usd": data["initial_procurement_total_usd"]}, indent=2))


if __name__ == "__main__":
    main()
