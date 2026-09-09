"""Retrieve official sources without changing the supplied vendor documents."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
VENDOR = ROOT / "parts/vendor/meanwell-nsp-1600/datasheets"
SOURCES = {
    "NSP-1600-spec_OFFICIAL_2026-09-08.pdf": (
        "https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf"
    ),
    "Enclosed_Type_EN_OFFICIAL_2026-09-08.pdf": (
        "https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf"
    ),
}


def inspect(path: Path) -> dict:
    reader = PdfReader(path)
    if reader.is_encrypted:
        reader.decrypt("")
    texts = [(page.extract_text() or "").replace("\x00", " ") for page in reader.pages]
    output = "\n\n".join(f"PAGE {i + 1}\n{text}" for i, text in enumerate(texts))
    (HERE / (path.stem + "_text.txt")).write_text(output, encoding="utf-8")
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "pages": len(texts),
        "encrypted_original": reader.is_encrypted,
        "dates": sorted(set(re.findall(r"20\d\d[-/.]\d\d[-/.]\d\d", output))),
        "normalized_text_sha256": hashlib.sha256("".join(output.split()).encode()).hexdigest(),
    }


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url in SOURCES.items():
        destination = HERE / name
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            if not data.startswith(b"%PDF"):
                raise ValueError("Response was not a PDF")
            destination.write_bytes(data)
            records.append({"url": url, "status": "RETRIEVED", **inspect(destination)})
        except Exception as error:
            records.append({"url": url, "status": "RETRIEVAL_FAILED", "error": str(error)})
    for original in VENDOR.glob("*.pdf"):
        records.append({"source": "Existing vendor copy; preserved", **inspect(original)})
    (HERE / "source_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        render_sets = [
            ("NSP-1600-SPEC.pdf", (2, 3, 6, 8)),
            ("MeanWell_Enclosed_Type_Installation_Manual_EN.pdf", (1, 2, 4, 5)),
        ]
        with tempfile.TemporaryDirectory(prefix="nsp_pdf_research_") as temporary:
            work = Path(temporary)
            for name, pages in render_sets:
                source = VENDOR / name
                short = work / name
                shutil.copyfile(source, short)
                for page in pages:
                    prefix = work / f"{source.stem}_page_{page}"
                    subprocess.run(
                        [
                            pdftoppm,
                            "-png",
                            "-r",
                            "125",
                            "-f",
                            str(page),
                            "-singlefile",
                            str(short),
                            str(prefix),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    shutil.copyfile(
                        prefix.with_suffix(".png"), HERE / prefix.with_suffix(".png").name
                    )
    print(json.dumps(records))


if __name__ == "__main__":
    main()
