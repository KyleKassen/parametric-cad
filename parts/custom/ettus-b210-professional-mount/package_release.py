"""Collect checked outputs and create a portable package with SHA256 manifest."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
import ezdxf
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent

def package(staging):
    target=HERE/'exports';target.mkdir(exist_ok=True)
    for fname in ['verification_report.json','hardware_verification.json']:
        assert json.loads((staging/fname).read_text())['status']=='PASS',fname
    sections=json.loads((staging/'section_verification.json').read_text())
    assert all(x['status']=='PASS' for x in sections),sections
    for src in staging.iterdir():
        if src.name.startswith('pdf_qa'):continue
        if src.is_dir():shutil.copytree(src,target/src.name,dirs_exist_ok=True)
        elif src.is_file():shutil.copy2(src,target/src.name)
    reader=PdfReader(target/'B210_mount_shop_pack_P1.pdf')
    assert len(reader.pages)==6
    all_text='\n'.join(page.extract_text() or '' for page in reader.pages)
    for required in ['M01','M02','M03','M04','M05','PRELIMINARY','0.20-0.40','M5']:
        assert required in all_text,required
    dxf_report=[]
    for file in target.glob('*.dxf'):
        doc=ezdxf.readfile(file)
        assert doc.units==ezdxf.units.MM,file
        assert len(doc.modelspace())>0,file
        errors=doc.audit().errors
        assert not errors,(file,errors)
        dxf_report.append({'file':file.name,'units':'mm','entities':len(doc.modelspace()),'audit_errors':0})
    (target/'manufacturing_file_verification.json').write_text(json.dumps({'pdf_pages':6,'pdf_text_checks':'PASS','dxf':dxf_report},indent=2))
    archive=HERE/'B210_Mount_P1_Deliverables.zip'
    files=[f for f in HERE.rglob('*') if f.is_file() and f!=archive and '__pycache__' not in f.parts
           and f.name!='file_manifest.json' and f.suffix not in ('.pyc',)]
    manifest={'revision':'P1','status':'Prototype design only; physical validation outstanding',
              'files':{str(f.relative_to(HERE)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files}}
    manifest_path=HERE/'file_manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2))
    files.append(manifest_path)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in files:z.write(f,'B210_Mount_P1/'+f.relative_to(HERE).as_posix())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'geometry_checks':34,'hardware_checks':18,'sections':sections,'manufacturing':dxf_report},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--staging',type=Path,required=True);package(ap.parse_args().staging)
