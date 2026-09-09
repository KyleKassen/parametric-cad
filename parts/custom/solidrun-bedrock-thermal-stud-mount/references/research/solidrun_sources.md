# SolidRun configuration and thermal evidence

Checked 2026-09-08. Source statements below are separate from local CAD measurements, user estimates and design assumptions. No supplier contact, purchase or physical validation was performed.

## Official configuration evidence

[SolidRun's Bedrock V3000 Basic product page](https://www.solid-run.com/industrial-computers/bedrock-v3000-basic/) describes Tile as a conduction-cooled option with flat walls and blind threaded attachment to a cold plate. It says internal heat distribution permits cooling from either side. Published nominal dimensions are Tile 29×160×130 mm, 30W 45×160×130 mm and 60W 73×160×130 mm. The same page lists a CPU up to 45 W and an available ambient range up to −40…85°C, with commercial-range configurations also offered. These are configuration descriptions; they do not specify an allowable cold-plate temperature or prove the heat rejection of this custom assembly.

The **60W** label identifies the manufacturer's enclosure variant in those sources. No inspected source established that one detached fin bank dissipates 60 W, that the hybrid's fin bank and flat side divide heat equally, or that CPU power equals complete-system heat generation. The processor, RAM, drives, NICs, radios and power conversion all contribute to heat. Establish installed configuration, BIOS power limits, workload, measured electrical input power and ambient; determine heat split through the fin and panel paths experimentally or with a supported thermal model.

## Mounting guidance and absent thread limits

The [official Bedrock mounting guidance](https://solidrun.atlassian.net/wiki/spaces/developer/pages/456851457), dated 2024-11-21 in the search-indexed copy, calls for vertical fins, 20 mm free above/below and 10 mm to each side for convection. It advises supplemental active cooling when orientation changes. It repeats the Tile cold-plate concept. Its explicit thread depths concern **two rear M3 holes, 3 mm deep**, and **two bottom M4 holes, 6 mm deep**. Those values do not apply to Tile's six side holes.

The page names a Tile mounting DXF, but the current anonymous page/API returned 404 during attempted attachment retrieval. Its indexed content remained readable. **No authoritative six-side-hole M4 pitch, usable thread depth, allowed external penetration, assembly torque, clamp preload or TIM specification was recovered.** The user's M4/~4 mm description is tentative physical information. Inspect all six holes and the actual attached heatsink before selecting final screw protrusion. Do not use screw tightening to find the bottom.

No inspected official source specifies the Tile enclosure alloy or a permitted mounting-face temperature. Do not assign adapter 6061 properties to the device. Thermal-expansion mismatch, cold/hot flatness and changes in fastener preload need physical evaluation using the actual hardware and operating temperatures.

The local vendor README contains stronger claims about a 3.5 mm penetration limit, both sides being simultaneously usable and a derived hybrid being a real configuration. These are legacy modeling interpretations, not manufacturer authorization. Use the fresh geometry audit for nominal bore surfaces and obstacles; label a Tile-plus-one-fin-bank representation **derived reference geometry**, unless the actual user's hardware or supplier confirms that configuration. Preserve the actual supplied STEP.

## Operational records relevant to validation

[SolidRun's V3000 BIOS guide](https://solidrun.atlassian.net/wiki/spaces/developer/pages/464027649) lists configurable CPU power limits and thermal settings. Record the shipped settings during evaluation; do not silently change power limits to make a prototype pass. The [Bedrock SOM integration manual](https://solidrun.atlassian.net/wiki/spaces/developer/pages/709459973/Bedrock%2BSOM%2BV3000%2BR7000%2BR8000%2B-%2BHardware%2BUser%2BManual) concerns board/cartridge integration. Its internal thermal-coupling instructions cannot be treated as external Tile-wall assembly instructions.

The preliminary installation needs a demonstrated external heat sink: the custom adapter and FPE panel spread/conduct heat, while the eventual panel exterior or another cooling surface must reject it. A finite aluminum panel in a sealed box is not an unlimited cold plate. Confirm panel supports, exterior airflow/area, other box heat loads, temperature limits and fin clearance before assigning a thermal rating. The user reports a TEC-cooled enclosure; its model and thermal coupling remain unverified. No 60 W system capability, IP/environmental rating or vibration qualification is established here.
