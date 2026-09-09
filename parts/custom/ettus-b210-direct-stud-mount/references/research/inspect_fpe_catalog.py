"""Read catalog/document files from the official FPE Debian package; never install/run it."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import urllib.request

URL = "https://assets.frontpanelexpress.com/fpd/Version-6.5.1/FrontDesign-US-6.5.1-amd64.deb"
ROOT = Path(__file__).resolve().parent
ARCHIVE = Path("C:/b210work/FPE-source-6.5.1.deb")
if not ARCHIVE.exists():
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, ARCHIVE)
blob = ARCHIVE.read_bytes()
assert blob[:8] == b"!<arch>\n"
offset = 8
parts = {}
while offset + 60 <= len(blob):
    head = blob[offset:offset+60]
    name = head[:16].decode("ascii").strip().rstrip("/")
    size = int(head[48:58].decode("ascii").strip())
    parts[name] = blob[offset+60:offset+60+size]
    offset += 60 + size + (size % 2)
data_name = next(name for name in parts if name.startswith("data.tar"))
with tarfile.open(fileobj=io.BytesIO(parts[data_name])) as package:
    members = [{"name": m.name, "size": m.size} for m in package.getmembers() if m.isfile()]
    record = {"source_url": URL, "date": "2026-09-08", "sha256": hashlib.sha256(blob).hexdigest(),
              "package_bytes": len(blob), "members": members, "installed_or_executed": False}
    (ROOT / "fpe_package_manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    selected = {
        "./opt/FrontDesign/etc/FrontDesign/Bolt.d/10-Base.ini": "FPE_6_5_1_Bolt_10-Base.ini",
        "./opt/FrontDesign/share/FrontDesign/Scripts/Office/Bolzen.fpjs": "FPE_6_5_1_Bolzen.fpjs",
    }
    for original, output_name in selected.items():
        source = package.extractfile(original)
        assert source is not None
        (ROOT / output_name).write_bytes(source.read())
    interesting = [m for m in members if any(k in m["name"].lower() for k in
                   ("bolt", "stud", "bolzen", "standoff", "catalog", "katalog", "material", "data", ".xml", ".csv", ".ini"))]
    print(json.dumps({"bytes": len(blob), "interesting": interesting}, indent=2))
