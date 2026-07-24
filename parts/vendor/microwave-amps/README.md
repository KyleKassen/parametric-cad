# AM59-3S-64-64 vendor references

- `AM59-3S-64-64.STEP` is the vendor packaging assembly.
- `datasheets/AM59-005D.pdf` is the user-supplied model-specific product specification dated November 2025.
- `references/AM59-3S-64-64_analysis.json` and `references/views/` are generated exact-kernel analysis and inspection views.

The PDF is authoritative for the 2.5 kg nominal mass, 3% duty limit, electrical values, connector list, environmental limits, and M4 mounting callout. The STEP is authoritative for physical keep-outs and the as-modeled connector/fan geometry.

Known source mismatch: the PDF drawing lists forward and reverse sample ports. The current STEP clearly resolves the input, output, and forward monitor, while the reverse-monitor region is not equally clear. Designs must reserve the full PDF connector envelope and verify the physical amplifier before release.
