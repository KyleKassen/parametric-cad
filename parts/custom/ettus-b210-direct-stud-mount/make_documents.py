"""Reproduce the direct-stud mount's dimensioned prototype drawing package.

Run with C:/venvs/cadquery/Scripts/python.exe make_documents.py --render
Requires final params.json, catalog BOM and CAD-derived images. Fails closed if
critical drawing dimensions change. Manufacturing DXFs are exported by model.py;
this script never invents or overwrites manufacturing geometry.
"""
from pathlib import Path
import argparse, hashlib, html, io, json, math, shutil, subprocess, textwrap
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.graphics import renderPDF
from reportlab.pdfbase.pdfmetrics import stringWidth
from svglib.svglib import svg2rlg

HERE=Path(__file__).resolve().parent
OUT=HERE/'drawings'
W,H=landscape(A3)
INK=colors.HexColor('#142c3b')
TEAL=colors.HexColor('#006979')
PALE=colors.HexColor('#eaf1f4')
AMBER=colors.HexColor('#9b5816')
PAGE_COUNT=5
REV='D1'
EXPECTED={'plate_width':150.0,'plate_length':148.0,'plate_thickness':3.5,
          'corner_radius':8.0,'edge_chamfer':.4,'housing_hole_diameter':3.4,
          'housing_x_pitch':93.599,'housing_y_pitch':120.015,
          'stud_hole_diameter':3.8,'stud_x_pitch':136.0,'stud_y_pitch':120.015,
          'countersink_diameter':6.1,'countersink_angle':90.0}

def wrap(s,width,size,font='Helvetica'):
    s=str(s).replace('\u2013','-').replace('\u2014','-').replace('\u2011','-')
    lines=[]
    for para in s.split('\n'):
        words=para.split(); line=''
        for word in words:
            candidate=(line+' '+word).strip()
            if line and stringWidth(candidate,font,size)>width:
                lines.append(line); line=word
            else: line=candidate
        lines.append(line)
    return lines

def text(c,x,y,s,width,size=10,leading=None,bold=False,color=INK):
    leading=leading or size*1.4; font='Helvetica-Bold' if bold else 'Helvetica'
    c.setFillColor(color); c.setFont(font,size)
    for line in wrap(s,width,size,font): c.drawString(x,y,line); y-=leading
    return y

def box(c,x,y,w,h,label,body,size=10):
    c.setFillColor(PALE); c.roundRect(x,y,w,h,6,fill=1,stroke=0)
    text(c,x+13,y+h-23,label,w-26,11,bold=True,color=TEAL)
    return text(c,x+13,y+h-46,body,w-26,size,leading=size*1.45)

def title(c,name,page,part='B210 DIRECT-STUD MOUNT'):
    c.setFillColor(INK); c.rect(0,H-77,W,77,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold',22); c.drawString(32,H-35,name)
    c.setFont('Helvetica-Bold',10); c.drawString(33,H-59,'PRELIMINARY FIT PROTOTYPE - NOT A QUALIFIED INSTALLATION')
    c.setStrokeColor(INK); c.setLineWidth(.6); c.line(33,49,W-33,49)
    c.setFillColor(INK); c.setFont('Helvetica',8)
    c.drawString(33,34,f'{part} / {REV} | mm | Dimensions after finish | Do not scale drawing')
    c.drawRightString(W-33,34,f'2026-09-08 | {page} / {PAGE_COUNT}')

def picture(c,path,x,y,w,h):
    if not path.exists(): raise FileNotFoundError(f'Final CAD-derived image required: {path}')
    iw,ih=ImageReader(str(path)).getSize(); scale=min(w/iw,h/ih)
    c.drawImage(str(path),x+(w-iw*scale)/2,y+(h-ih*scale)/2,iw*scale,ih*scale,mask='auto')

def table(c,headers,rows,x,y,widths,size=9,minh=29,links=None):
    heights=[max(minh,14+max(len(wrap(s,w-14,size)) for s,w in zip(row,widths))*size*1.32) for row in rows]
    c.setFillColor(TEAL); c.rect(x,y-29,sum(widths),29,fill=1,stroke=0)
    xx=x
    for s,w in zip(headers,widths): text(c,xx+7,y-19,s,w-14,size,bold=True,color=colors.white); xx+=w
    y-=29
    for i,(row,rh) in enumerate(zip(rows,heights)):
        c.setFillColor(PALE if i%2==0 else colors.white); c.rect(x,y-rh,sum(widths),rh,fill=1,stroke=0)
        xx=x
        for j,(s,w) in enumerate(zip(row,widths)):
            text(c,xx+7,y-15,s,w-14,size,leading=size*1.32)
            if links and j==1 and links[i]: c.linkURL(links[i],(xx,y-rh,xx+w,y),relative=0,thickness=0)
            xx+=w
        y-=rh
    return y

def load_inputs():
    ppath=HERE/'params.json'
    if not ppath.exists(): raise FileNotFoundError('Final params.json required before drawing generation.')
    p=json.loads(ppath.read_text(encoding='utf-8-sig'))
    if p.get('units')!='mm' or not p.get('revision','').startswith('D1'):
        raise ValueError('D1 millimetre parameters required.')
    # Adapt only this mapping if the CAD schema changes; values remain guarded.
    aliases={
        'plate_width':['plate_width','width'], 'plate_length':['plate_length','length'],
        'plate_thickness':['plate_thickness','thickness'], 'corner_radius':['corner_radius','plate_corner_radius'],
        'edge_chamfer':['edge_break','edge_chamfer','plate_edge_chamfer'],
        'housing_hole_diameter':['housing_clearance_diameter','housing_hole_diameter','housing_hole_dia','device_hole_diameter'],
        'housing_x_pitch':['housing_x_pitch','housing_pitch_x','device_hole_pitch_x'],
        'housing_y_pitch':['housing_y_pitch','housing_pitch_y','device_hole_pitch_y'],
        'stud_hole_diameter':['stud_clearance_diameter','stud_hole_diameter','stud_hole_dia'],
        'stud_x_pitch':['stud_x_pitch','stud_pitch_x'], 'stud_y_pitch':['stud_y_pitch','stud_pitch_y'],
        'countersink_diameter':['countersink_diameter_reference','countersink_diameter','countersink_mouth_diameter','countersink_dia'],
        'countersink_angle':['countersink_angle_deg','countersink_angle']}
    resolved={}
    for key,names in aliases.items():
        found=[p[n] for n in names if n in p]
        if not found: raise ValueError(f'Map final CAD parameter to drawing guard: {key}')
        resolved[key]=float(found[0])
    changed={k:resolved[k] for k,v in EXPECTED.items() if abs(resolved[k]-v)>1e-6}
    additional={'plate_thickness_tolerance':.05,'bore_deburr':.1,'screw_length_overall':6.,'screw_head_diameter':6.,
                'screw_head_recess_nominal':.05,'stud_projection':12.,'stud_pattern_rotation_deg':0.,
                'stud_pattern_center_x':0.,'stud_pattern_center_y':0.}
    changed.update({k:p.get(k) for k,v in additional.items() if p.get(k) is None or abs(float(p[k])-v)>1e-6})
    if changed: raise ValueError(f'Drawing annotations require review for changed CAD: {changed}')
    catpath=HERE/'references/research/catalog_bom.json'
    if not catpath.exists(): raise FileNotFoundError('Final catalog_bom.json required.')
    catalog=json.loads(catpath.read_text(encoding='utf-8-sig'))
    catalog_items=catalog.get('items',[])
    selected={r.get('item_id'):r.get('part_number') for r in catalog_items}
    for item,pn in {'H01':'91294A126','H02':'98688A142','H03':'90576A102'}.items():
        if selected.get(item)!=pn: raise ValueError(f'Review hardware annotations for changed {item}: {selected.get(item)}')
    return p,catalog,ppath,catpath

def plate_svg(path):
    """Dimensioned nominal part views; dimensions and actual screw gauge govern."""
    e=html.escape
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1550" height="960" viewBox="0 0 1550 960">',
         '<rect width="1550" height="960" fill="white"/>',
         '<style>text{font-family:Helvetica,sans-serif;fill:#142c3b;font-size:19px}.title{font-size:26px;font-weight:bold}.small{font-size:17px}.dim{fill:#006979;font-size:20px}.bold{font-weight:bold}</style>']
    def line(x1,y1,x2,y2,color='#142c3b',dash=''):
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def txt(x,y,s,cls='',anchor='start'):
        svg.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{e(s)}</text>')
    def dimh(x1,x2,y0,y,label):
        for x in [x1,x2]: line(x,y0,x,y+6,'#006979'); line(x-4,y-4,x+4,y+4,'#006979')
        line(x1,y,x2,y,'#006979'); txt((x1+x2)/2,y-8,label,'dim','middle')
    def dimv(y1,y2,x0,x,label):
        for y in [y1,y2]: line(x0,y,x-6,y,'#006979'); line(x-4,y-4,x+4,y+4,'#006979')
        line(x,y1,x,y2,'#006979')
        svg.append(f'<text transform="translate({x-9},{(y1+y2)/2}) rotate(-90)" class="dim" text-anchor="middle">{e(label)}</text>')
    scale=3.1; cx=390; cy=421; px=lambda x:cx+x*scale; py=lambda y:cy-y*scale
    left,right,top,bottom=px(-75),px(75),py(74),py(-74)
    txt(38,39,'M01 / ADAPTER PLATE - DIMENSIONED PART VIEWS','title')
    txt(38,73,'Plan: housing-contact side; hidden countersink mouths shown dashed. Datum A is opposite face.','small')
    svg.append(f'<rect x="{left}" y="{top}" width="{150*scale}" height="{148*scale}" rx="{8*scale}" fill="#f7f9fa" stroke="#142c3b" stroke-width="2.2"/>')
    for x in [-46.7995,46.7995]:
        for y in [-60.0075,60.0075]:
            for dia,dash in [(3.4,''),(6.1,'4 3')]: svg.append(f'<circle cx="{px(x)}" cy="{py(y)}" r="{dia/2*scale}" fill="none" stroke="#142c3b" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    for x in [-68,68]:
        for y in [-60.0075,60.0075]: svg.append(f'<circle cx="{px(x)}" cy="{py(y)}" r="{1.9*scale}" fill="none" stroke="#142c3b" stroke-width="1.5"/>')
    for y in [-60.0075,60.0075]: line(px(-72),py(y),px(72),py(y),'#7892a1','13 4 2 4')
    line(cx,top-7,cx,bottom+7,'#7892a1','13 4 2 4')
    dimh(left,right,top,113,'150.00 +/-0.10')
    dimh(px(-68),px(68),py(60.0075),150,'136.000 REF stud pitch')
    dimh(px(-46.7995),px(46.7995),py(-60.0075),705,'93.599 REF housing pitch')
    dimv(top,bottom,left,68,'148.00 +/-0.10')
    dimv(py(60.0075),py(-60.0075),left,112,'120.015 REF both patterns')
    txt(cx,bottom+91,'Use coordinate table; no chain tolerance.','small','middle')
    # Datum markers, referenced to the remaining straight edge after chamfer.
    line(left,cy,left+29,cy); svg.append(f'<rect x="{left+30}" y="{cy-16}" width="30" height="30" fill="white" stroke="#142c3b"/>'); txt(left+45,cy+6,'B','bold','middle')
    dc=580; line(dc,bottom,dc,bottom+22); svg.append(f'<rect x="{dc-15}" y="{bottom+23}" width="30" height="30" fill="white" stroke="#142c3b"/>'); txt(dc,bottom+45,'C','bold','middle')
    line(right-9,top+6,641,178); txt(647,173,'4X R8 +/-0.25','small')
    txt(795,112,'HOLE COORDINATES FROM EDGE DATUMS B / C','bold')
    for y,row in [(148,['Pattern','X from B','Y from C']),
                  (177,['Housing','28.2005 /121.7995','13.9925 /134.0075']),
                  (206,['Studs','7.0000 /143.0000','13.9925 /134.0075'])]:
        for x,s in zip([795,915,1145],row): txt(x,y,s,'small')
    for i,s in enumerate(['4X each pattern; all four X/Y combinations.',
                          'Housing bores: DIA3.4 +0.10/0 THRU.',
                          'Stud bores: DIA3.8 +0.10/0 THRU.',
                          'Each bore position: DIA0.10 | A | B | C (RFS).',
                          'Coordinate values BASIC; position controls each bore.']): txt(795,235+i*29,s,'small')
    # Nominal enlarged section at a housing mounting hole.
    sx=1060; sy=550; zscale=24; zx=lambda x:sx+x*zscale; zy=lambda z:sy-z*zscale
    txt(795,393,'SECTION AT HOUSING HOLE / NOT TO SCALE','bold')
    d=' '.join([f'M{zx(-8)},{zy(0)}',f'L{zx(-3.05)},{zy(0)}',f'L{zx(-1.7)},{zy(1.35)}',f'L{zx(-1.7)},{zy(3.4)}',f'L{zx(-1.8)},{zy(3.5)}',f'L{zx(-8)},{zy(3.5)}','Z',
                f'M{zx(8)},{zy(0)}',f'L{zx(3.05)},{zy(0)}',f'L{zx(1.7)},{zy(1.35)}',f'L{zx(1.7)},{zy(3.4)}',f'L{zx(1.8)},{zy(3.5)}',f'L{zx(8)},{zy(3.5)}','Z'])
    svg.append(f'<path d="{d}" fill="#eaf1f4" stroke="#142c3b" stroke-width="2"/>')
    line(sx,435,sx,601,'#7892a1','13 4 2 4')
    dimv(zy(3.5),zy(0),zx(8),1290,'3.50 +/-0.05')
    dimh(zx(-3.05),zx(3.05),zy(0),594,'DIA6.1 REF mouth / 90 deg')
    line(zx(-8),zy(0),804,zy(0)); svg.append(f'<rect x="774" y="{zy(0)-15}" width="30" height="30" fill="white" stroke="#142c3b"/>'); txt(789,zy(0)+7,'A','bold','middle')
    txt(795,644,'4X 90-degree countersink FROM UNDERSIDE A.','bold')
    txt(795,675,'Gauge with actual M3 x6 DIN 7991 screw; 6 mm head.','small')
    txt(795,704,'Head must be flush to 0.10 below datum A.','small')
    txt(795,733,'Actual straight cylindrical ligament >=1.80.','small')
    txt(795,762,'Nominal REF: CSK depth 1.35; straight 2.05 with 0.10 top deburr.','small')
    txt(795,791,'Effective conical seat DIA >=5.70; full seating, no head rocking.','small')
    txt(795,820,'Screen: mouth <=6.20; angle >=89 deg; throat >=3.30.','small')
    txt(38,840,'MATERIAL: certified 6061-T6/T651. Machine from 4 mm stock; face both sides to finished thickness.','small')
    txt(38,870,'FINISH: clear MIL-DTL-5541 Type II Class 3 conversion coating by qualified vendor. No electrical-bond qualification.','small')
    txt(38,900,'A flatness 0.10. Rim 0.4 x45 deg; angles +/-0.5 deg. Bore rims deburr <=0.10 except CSK seats. No local reliefs.','small')
    txt(38,934,'PRELIMINARY FIT PROTOTYPE - mm, after finish. Dimensions and physical screw gauge govern. Do not scale.','bold')
    svg.append('</svg>'); path.write_text('\n'.join(svg),encoding='utf8')

def embed_svg(c,path,x,y,w,h):
    drawing=svg2rlg(str(path)); s=min(w/drawing.width,h/drawing.height)
    drawing.scale(s,s); renderPDF.draw(drawing,c,x+(w-drawing.width*s)/2,y+(h-drawing.height*s)/2)

def rows_from_catalog(cat):
    rows=cat if isinstance(cat,list) else cat.get('items',cat.get('rows',cat.get('bom',[])))
    if not rows: raise ValueError('Map final catalog rows to drawing BOM.')
    result=[]; links=[]
    for r in rows:
        ident=r.get('item',r.get('id',r.get('item_id','')))
        pn=r.get('part_number',r.get('mcmaster_part_number',r.get('catalog_part_number','')))
        desc=r.get('description',r.get('specification',''))
        qty=r.get('quantity',r.get('qty',r.get('qty_per_mount','AR')))
        if isinstance(qty,dict): qty=str(qty)
        pack=r.get('pack_qty',r.get('pack_quantity',''))
        price=r.get('observed_usd_pack_price',r.get('pack_price_usd',r.get('price_usd','')))
        purchase=(str(pack)+' / $'+str(price)) if pack not in ['',None] and price not in ['',None] else str(r.get('purchase_note','Quote required'))
        url=r.get('url',r.get('source_url',''))
        result.append([ident,pn,str(qty),desc,purchase]); links.append(url)
    return result,links

def make_pdf(out,p,cat,svg):
    pdf=out/'B210_direct_stud_mount_shop_pack_D1.pdf'
    # A short staging path avoids Win32 library long-path limits.
    temp=Path('C:/b210work/direct_stud_documents'); temp.mkdir(parents=True,exist_ok=True)
    stage=temp/pdf.name; c=canvas.Canvas(str(stage),pagesize=(W,H))
    c.setTitle('B210 direct-stud adapter - preliminary fit prototype / D1')
    c.setAuthor('Parametric CAD engineering draft'); c.setCreator('Reproducible make_documents.py / ReportLab')
    product=HERE/'references/product'; views=HERE/'references/views'

    title(c,'B210 direct-stud mounting adapter',1)
    picture(c,product/'assembled_hero.png',32,285,745,449)
    box(c,800,504,358,223,'A SIMPLE, DIRECT LOAD PATH',
        'Radio -> four existing underside standoffs -> four M3 countersunk screws -> one machined adapter -> four M3 panel studs / nuts -> supporting metal panel.\nNo cradle, upper straps or modifications to the radio. Remove the four adhesive feet to expose the existing interfaces.',10)
    box(c,800,285,358,202,'INSTALLATION BASIS',
        'Stationary indoor, plate-facing-up service inside a box. Supporting surface is a rigid flat metal panel. The 180 x200 x6 mm panel shown is a reference coupon, not a complete Front Panel Express panel order.\nFinal box dimensions, loads, cooling and cable routing require installation-specific confirmation.',10)
    table(c,['Item','Nominal interface','Requirement'],[
        ['Adapter','150 x148 x3.50 mm; 6061-T6/T651','One custom machined part; no local face reliefs'],
        ['Radio interface','93.599 x120.015 mm; four existing axes','M3 reported by user; usable depth and full engagement still unverified'],
        ['Panel interface','136.000 x120.015 mm; four M3 studs','Stud bases / adhesive must finish flush or below the panel seating face']],32,264,[190,365,570],size=9.5,minh=39)
    text(c,36,91,'Model views are CAD-derived. The actual radio, selected screws, FPE stud installation and complete assembly have not been fabricated or physically tested.',1100,10,bold=True,color=AMBER)
    c.showPage()

    title(c,'M01 / Dimensioned machined adapter plate',2,'B210-DS-M01 / QTY 1')
    embed_svg(c,svg,31,60,W-62,H-150)
    c.showPage()

    title(c,'Panel stud interface and critical screw stack',3)
    picture(c,views/'section_fastener.png',34,403,615,323)
    for i,(color,label) in enumerate([('#c97720','New external M3 proxy'),('#5793c4','Adapter plate'),('#578b73','Original pan / insert / internal screw'),('#adb6c2','Reference main panel')]):
        yy=716-i*28; c.setFillColor(colors.HexColor(color)); c.rect(41,yy-5,7,7,fill=1,stroke=0)
        text(c,54,yy,label,143,8,leading=10)
    text(c,39,388,'CAD screw is an idealized 90-degree proxy. Catalog head height is not a maximum; physical head/seat inspection governs.',601,9,color=AMBER)
    text(c,39,370,'Nominal CAD tip gap: 3.5738 -2.55 =1.0238 mm. This gap is not physically verified.',601,9.3,bold=True,color=AMBER)
    text(c,660,719,'HOUSING SCREW: CONTROL ACTUAL PROJECTION',496,13,bold=True,color=TEAL)
    text(c,660,691,'4 x McMaster 91294A126: M3 x0.5 x6 DIN 7991 flat-head socket screw, black-oxide alloy steel; nominal 6 mm head, 1.7 mm head height, 2 mm hex. Length includes the head.',493,10.5)
    text(c,660,606,'Install from adapter underside A. Projection P = overall screw length L + inward head recess r - plate thickness t. Nominal: 6.00 +0.05 -3.50 =2.55 mm. Actual screw length, seat and finished plate thickness govern.',493,10.5)
    box(c,654,387,504,140,'FIT ACCEPTANCE - ALL FOUR LOCATIONS',
        'Actual tip projection above the housing-contact face: 2.40-2.90 mm. Gap to the existing internal PCB screw: >=0.50 mm. Effective full thread engagement: >=2.00 mm after deducting entry and tip incomplete threads.\nReject any stack that cannot satisfy all three conditions.',10)
    table(c,['Panel feature','Coordinates / dimensions','Acceptance'],[
        ['4 M3 stud axes','X +/-68; Y +/-60.0075, relative adapter center','136.000 x120.015 rectangle'],
        ['FPE stud locations','DIA0.30 position relative panel interface datums','Supplier must confirm achievable installation tolerance'],
        ['Adapter stud bores','DIA3.8 +0.10/0; DIA0.10 position A/B/C','Nominal radial clearance0.40; keep studs straight'],
        ['Panel seating surface','6 mm panel is reference only','Stud bases / adhesive flush or below; four end-face contacts verified']],34,344,[190,361,574],size=9.5,minh=35)
    text(c,39,135,'Positional screening: 0.40 nominal radial clearance -0.05 adapter radial position -0.15 stud radial position =0.20 mm residual before diameter, finish and straightness effects. Coordinate agreement is required; do not force studs into the adapter.',1115,10)
    text(c,39,87,'STEP screw-tip separation is 3.5738 mm from the pan, not permitted penetration. User-reported roughly 4 mm depth is an estimate. Physically gauge each interface.',1115,10,bold=True,color=AMBER)
    c.showPage()

    title(c,'Bill of materials / one complete mount',4)
    rows,links=rows_from_catalog(cat)
    custom=[['M01','Custom drawing','1','150 x148 x3.50 mm machined 6061-T6/T651 adapter; clear conversion coating','Quote required']]
    table_bottom=table(c,['ID','Catalog number / link','Qty','Complete specification','Purchase reference'],custom+rows,33,724,[53,157,46,686,183],size=9,minh=34,links=['']+links)
    if table_bottom<180: raise ValueError(f'Catalog table exceeds page budget: bottom={table_bottom:.1f}')
    text(c,39,table_bottom-23,'Catalog links point to the cited source records. Prices, pack quantities and availability are procurement observations, not a fabrication quote. Verify the selected item at purchase.',1100,9.5)
    text(c,39,table_bottom-62,'FPE studs belong to the supporting-panel fabrication scope. The interface drawing specifies their position and installation acceptance; it is not a released full-panel order. The radio and supporting panel are customer-furnished.',1100,9.5)
    text(c,40,430,'UNDERSIDE / ACTUAL CAD',520,10,bold=True,color=TEAL)
    picture(c,product/'plate_bottom_hero.png',38,184,525,235)
    box(c,594,184,564,244,'PANEL NUT ACCESS AND REMOVAL',
        'Use a 5.5 mm AF socket with outside diameter <=10 mm and internal clear depth >=9 mm. Nominal stud height above nut bottom is 7.95 mm. Reserve >=40 mm axial tool access and >=20 mm unobstructed lift for service.\nStud tail is nominally3.9-4.0 mm beyond the nut; verify full nylon engagement and at least two complete exposed threads. Qualify locknut prevailing torque against FPE stud anchorage.',9.5)
    box(c,33,79,1125,98,'HARDWARE AND FINISH LIMITS',
        'Use the qualified screw seating geometry and measured stack; no longer housing screws. Catalog strength class does not establish countersunk-head proof capacity. No locking consumable or installation torque is qualified here. Clear conversion coating does not establish an electrical bond.',9.5)
    c.showPage()

    title(c,'Assembly, removal and prototype verification',5)
    picture(c,product/'exploded_iso.png',33,365,560,363)
    text(c,621,722,'ASSEMBLY SEQUENCE',532,13,bold=True,color=TEAL)
    y=693
    steps=[
        '1. With power removed, expose and identify all four underside threads. Remove feet and adhesive without damaging the case; retain the feet. Confirm thread, depth, end-face coplanarity and cleanliness.',
        '2. Gauge each selected screw in the finished adapter. Verify head recess, 2.40-2.90 projection and at least 2.00 effective full engagement with at least 0.50 internal screw-tip clearance.',
        '3. Attach the adapter to the radio using four M3 x6 screws from underside A. Seat evenly. Stop for resistance before contact; do not use torque to detect the internal screw tip.',
        '4. Verify the installed panel studs are straight and their bases/adhesive flush or below the seating surface. Lower the radio/adapter assembly over the studs; install specified washers and nuts.',
        '5. Connect cables with the required mating, bend and tool space. Provide independent cable strain relief to the panel. Confirm ventilation and cover access before powering the radio.'
    ]
    for s in steps: y=text(c,621,y,s,530,9.7,leading=13.8)-12
    text(c,39,335,'PROTOTYPE VALIDATION / RECORD RESULTS BEFORE RELEASE',1110,13,bold=True,color=TEAL)
    table(c,['Check','Method and acceptance'],[
        ['Fit and screw stack','Measure all eight axes and all four screw projections; confirm end-face contact, internal tip clearance and effective engagement. Record actual screw, plate and device dimensions.'],
        ['Retention and support','Use the separate engineering note\'s numerical proof loads after confirming case/insert and FPE stud capacity. Inspect pan deformation, slip, loosening, permanent set and stud/base damage.'],
        ['Cable / service access','Mate actual plugs, satisfy cable minimum bend radii, fit tools and remove the assembly without connector loading. Disconnect cables before lifting the radio/adapter from studs.'],
        ['Thermal operation','Run the intended SDR workload at the highest intended box ambient; compare temperatures with an appropriate baseline. Verify no functional faults, excessive temperature or blocked ventilation.'],
        ['Installation qualification','Confirm box/panel stiffness, final loads, orientation, shock/vibration and environment. No vehicle, airborne, outdoor or overhead qualification is claimed.']],33,311,[185,940],size=9.3,minh=37)
    text(c,39,87,'Removal: power off and disconnect cables; remove panel-stud nuts and washers; lift the radio and adapter together. Access the underside screws only after removal.',1112,9.6,bold=True)
    c.showPage(); c.save(); shutil.copyfile(stage,pdf)
    return pdf,stage

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--render',action='store_true'); ap.add_argument('--svg-only',action='store_true'); ap.add_argument('--out',type=Path,default=OUT); args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    svg=args.out/'B210_DS_M01_dimensioned_D1.svg'
    if args.svg_only:
        plate_svg(svg); print(svg); return
    p,cat,ppath,catpath=load_inputs(); plate_svg(svg)
    pdf,stage=make_pdf(args.out,p,cat,svg)
    sources=[Path(__file__),ppath,catpath]+sorted((HERE/'references/product').glob('*.png'))+[HERE/'references/views/section_fastener.png']
    manifest={'revision':REV,'pages':PAGE_COUNT,'status':'ROOT REVIEW APPROVED FOR PRELIMINARY FIT PROTOTYPE; NOT A PRODUCTION RELEASE','pdf':pdf.name,
              'sources':[{ 'path':str(s.relative_to(HERE)),'sha256':hashlib.sha256(s.read_bytes()).hexdigest()} for s in sources]}
    (args.out/'drawing_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    if args.render:
        qa=stage.parent/'qa'; qa.mkdir(exist_ok=True)
        subprocess.run(['pdftoppm','-scale-to','1600','-png',str(stage),str(qa/'page')],check=True)
        qout=args.out/'qa'; qout.mkdir(exist_ok=True)
        for image in sorted(qa.glob('page-*.png')): shutil.copyfile(image,qout/image.name)
    print(pdf)

if __name__=='__main__': main()
