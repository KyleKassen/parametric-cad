"""Reproduce the Mean Well NSP-1600 adapter's dimensioned prototype drawing package.

Run with C:/venvs/cadquery/Scripts/python.exe make_documents.py --render
Requires final params.json, catalog BOM and CAD-derived images. Fails closed if
critical drawing dimensions change. Manufacturing DXFs are exported by model.py;
this script never invents or overwrites manufacturing geometry.
"""
from pathlib import Path
import argparse, hashlib, html, json, shutil, subprocess
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
PAGE_COUNT=6
REV='N1'
EXPECTED={}

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

def title(c,name,page,part='MEAN WELL NSP-1600 STUD MOUNT'):
    c.setFillColor(INK); c.rect(0,H-77,W,77,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold',22); c.drawString(32,H-35,name)
    c.setFont('Helvetica-Bold',10); c.drawString(33,H-59,'PRELIMINARY MECHANICAL FIT PROTOTYPE - NOT A PRODUCTION RELEASE')
    c.setStrokeColor(INK); c.setLineWidth(.6); c.line(33,49,W-33,49)
    c.setFillColor(INK); c.setFont('Helvetica',8)
    rule='1:1 check template | Verify printed calibration before use' if page==6 else 'Dimensions after finish | Do not scale drawing'
    c.drawString(33,34,f'{part} / {REV} | mm | {rule}')
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



class SVG:
    def __init__(self,w=1550,h=960):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="white"/>',
          '<style>text{font-family:Helvetica,sans-serif;fill:#142c3b;font-size:20px}.title{font-size:27px;font-weight:bold}.small{font-size:18px}.dim{fill:#006979;font-size:21px}.bold{font-weight:bold}</style>']
    def add(self,s):self.parts.append(s)
    def line(self,x1,y1,x2,y2,color='#142c3b',dash=''):
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    def txt(self,x,y,s,cls='',anchor='start'):
        self.add(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{html.escape(str(s))}</text>')
    def circle(self,x,y,r,fill='none',dash='',color='#142c3b'):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    def rect(self,x,y,w,h,r=0,fill='none',color='#142c3b'):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{color}" stroke-width="1.5"/>')
    def dimh(self,x1,x2,y0,y,label):
        for x in [x1,x2]:self.line(x,y0,x,y+7,'#006979');self.line(x-4,y-4,x+4,y+4,'#006979')
        self.line(x1,y,x2,y,'#006979');self.txt((x1+x2)/2,y-9,label,'dim','middle')
    def dimv(self,y1,y2,x0,x,label):
        for y in [y1,y2]:self.line(x0,y,x-7,y,'#006979');self.line(x-4,y-4,x+4,y+4,'#006979')
        self.line(x,y1,x,y2,'#006979');self.add(f'<text transform="translate({x-10},{(y1+y2)/2}) rotate(-90)" class="dim" text-anchor="middle">{html.escape(label)}</text>')
    def save(self,path):path.write_text('\n'.join(self.parts+['</svg>']),encoding='utf8')


def load_inputs(require_final=True):
    pp=HERE/'params.json';p=json.loads(pp.read_text(encoding='utf-8-sig'))
    expected={'plate_width':125,'plate_length':300.6,'plate_center_y':-150.3,'plate_thickness':5,'plate_thickness_tolerance':.05,
      'corner_radius':8,'edge_break':.4,'bore_deburr':.1,'housing_clearance_diameter':3.4,'countersink_diameter_reference':6.1,
      'countersink_angle_deg':90,'screw_length_overall':8,'screw_head_diameter':6,'screw_head_recess_nominal':.05,
      'screw_projection_accept_min':2.75,'screw_projection_accept_max':3.35,'manufacturer_max_penetration':4,
      'fan_relief_width':37.15,'fan_relief_length':29.6,'fan_relief_center_y':-284.3,'fan_relief_radius':.5,
      'fan_relief_depth':.5,'fan_relief_depth_tolerance':.05,'minimum_physical_fan_gap':.2,
      'stud_pitch_x':110,'stud_pitch_y':264.7,'stud_pattern_center_x':0,'stud_pattern_center_y':-148.45,
      'stud_pattern_rotation_deg':0,'stud_clearance_diameter':3.8,'stud_projection':12,'panel_reference_width':145,
      'panel_reference_length':340,'panel_reference_thickness':6,'tool_socket_envelope_diameter':10,
      'tool_socket_envelope_height':60,'tool_socket_internal_depth_min':10,'service_lift_min':20,
      'screw_diameter':3,'screw_pitch':.5,'screw_head_height_catalog':1.7,'screw_hex_drive':2,
      'stud_diameter':3,'washer_id':3.2,'washer_od':7,'washer_thickness_nominal':.55,
      'nut_across_flats':5.5,'nut_height_nominal':4,'source_terminal_plane_y':0,'source_fan_extreme_y':-300.6,
      'intake_reservation_length':100,'exhaust_reservation_length':100,'nominal_device_mass_kg_manufacturer':1.8}
    changed={k:p.get(k) for k,v in expected.items() if k not in p or abs(float(p[k])-v)>1e-7}
    for key,value in {'housing_points':[[-35,-16.1],[35,-16.1],[0,-280.8]],'fan_relief_centers_x':[-21.425,21.425],'manufacturer_bottom_torque_kgf_cm':[6,8]}.items():
        if p.get(key)!=value:changed[key]=p.get(key)
    if changed:raise ValueError(f'Review dimensioned annotations for changed CAD: {changed}')
    if p.get('units')!='mm' or not p.get('revision','').startswith('N1'):raise ValueError('N1 mm parameters required.')
    cp=HERE/'references/research/catalog_bom.json';cat=json.loads(cp.read_text(encoding='utf-8-sig'))
    selected={r['item_id']:r['part_number'] for r in cat['items']}
    for ident,pn in {'H01':'91294A128','H02':'98688A142','H03':'90576A102'}.items():
        if selected.get(ident)!=pn:raise ValueError(f'Review changed catalog {ident}')
    checks=[]
    if require_final:
        for name in ['cad_verification.json','manufacturing_verification.json']:
            f=HERE/'quality'/name;r=json.loads(f.read_text(encoding='utf-8-sig'))
            if r.get('status')!='PASS':raise ValueError(f'Final CAD check required: {name}')
            if r.get('params_sha256') and r['params_sha256']!=hashlib.sha256(pp.read_bytes()).hexdigest():raise ValueError(f'Stale verification: {name}')
            checks.append((f,r))
    return p,cat,pp,cp,checks


def stud_points(p):
    return [(x,y) for x in [-p['stud_pitch_x']/2,p['stud_pitch_x']/2]
      for y in [p['stud_pattern_center_y']-p['stud_pitch_y']/2,p['stud_pattern_center_y']+p['stud_pitch_y']/2]]


def plan_svg(path,p):
    s=SVG();s.txt(35,40,'M01 / TWO-SIDED MACHINED ADAPTER - PLAN AND HOLE COORDINATES','title')
    s.txt(35,75,'mm after finish. Plan orientation is maintained for both views; underside features are projected through. Do not scale.','small')
    k=2.;py=lambda y:170-y*k
    for index,cx in enumerate([272,644]):
        px=lambda x:cx+x*k
        s.rect(px(-62.5),py(0),125*k,300.6*k,8*k,'#f6f9fa')
        s.txt(cx,140,'CONTACT-SIDE PLAN' if index==0 else 'UNDERSIDE FEATURE PLAN','small bold','middle')
        if index==0:
            for x in p['fan_relief_centers_x']:
                s.rect(px(x-37.15/2),py(-269.5),37.15*k,29.6*k,.5*k,'#c8e1e8','#006979')
        for i,(x,y) in enumerate(p['housing_points'],1):
            s.circle(px(x),py(y),1.7*k,'white')
            if index==1:s.circle(px(x),py(y),3.05*k,'none')
            s.line(px(x)-9,py(y),px(x)+9,py(y),'#7892a1','6 2 1 2');s.line(px(x),py(y)-9,px(x),py(y)+9,'#7892a1','6 2 1 2')
            s.txt(px(x)+12,py(y)+24 if i<3 else py(y)+7,f'H{i}','small')
        for i,(x,y) in enumerate(stud_points(p),1):
            s.circle(px(x),py(y),1.9*k,'white');s.txt(px(x)-33 if x<0 else px(x)+11,py(y)-11,f'S{i}','small')
        s.line(cx,160,cx,783,'#7892a1','15 4 2 4')
        s.txt(cx,810,'FAN END / C / Y=-300.6','small','middle')
        if index==0:
            s.dimh(px(-62.5),px(62.5),170,107,'125.00 +/-0.10')
            s.dimv(170,py(-300.6),px(-62.5),76,'300.60 +/-0.10')
            s.rect(px(-62.5)+10,450,28,28,fill='white');s.txt(px(-62.5)+24,471,'B','bold','middle')
    s.txt(860,120,'COORDINATES FROM EDGE DATUMS B / C','bold')
    for xx,label in zip([870,995,1160,1320],['ID','X from B','Y from C','BORE']):s.txt(xx,158,label,'small bold')
    coords=[(f'H{i}',x+62.5,y+300.6,'DIA3.4') for i,(x,y) in enumerate(p['housing_points'],1)]+[(f'S{i}',x+62.5,y+300.6,'DIA3.8') for i,(x,y) in enumerate(stud_points(p),1)]
    for j,row in enumerate(coords):
        for xx,val in zip([870,995,1160,1320],[row[0],f'{row[1]:.3f}',f'{row[2]:.3f}',row[3]]):s.txt(xx,192+j*34,val,'small')
    notes=['H1-H3: DIA3.4 +0.10/0 THRU; 90-deg CSK FROM A.',
      'S1-S4: DIA3.8 +0.10/0 THRU.',
      'All bore axes: position DIA0.10 | A | B | C, RFS.',
      'BASIC coordinate values; position controls holes.',
      'A = lower main-panel seating plane, Z0.',
      'B = left edge X-62.5; C = fan-end edge Y-300.6.',
      '4X outer R8 +/-0.25; rim break 0.4 x45 degrees.',
      'Fan pockets are TOP SIDE ONLY: see detailed page 3.',
      'No stud-base reliefs, thermal pad or grease.',
      'Gauge actual PSU pattern BEFORE final machining.',
      'Nominal CSK pattern cannot absorb all OEM +/-0.5.']
    for i,line in enumerate(notes):s.txt(850,458+i*28,line,'small')
    s.txt(35,836,'MATERIAL: certified 6061-T6/T651, Sy>=240 MPa. Machine nominal 6 mm /1/4-in stock to 5.00 +/-0.05.','small')
    s.txt(35,870,'FINISH: clear MIL-DTL-5541 Type II Class 3 conversion. Dimensions apply after finish. A flatness 0.10.','small')
    s.txt(35,904,'Top metal seating lands parallel 0.10 to A. Deburr bore rims<=0.10; no large break on fan-pocket boundaries.','small')
    s.txt(35,941,'PRELIMINARY FIT PROTOTYPE - physical case, screw, fan and FPE-joint inspection required.','bold');s.save(path)


def detail_svg(path,p):
    s=SVG();s.txt(35,40,'M01 / FAN-FRAME RELIEF DETAIL AND REAR FASTENER SECTION','title')
    s.txt(35,70,'Detailed top plan; datums B/C are defined on page 2. Reliefs clear fan frames while supporting metal bracket lands.','small')
    k=10.;cx=470;px=lambda x:cx+x*k;py=lambda y:461-(y+300.6)*k
    s.line(px(-44),py(-300.6),px(44),py(-300.6));s.line(px(-44),py(-267),px(44),py(-267))
    for x in p['fan_relief_centers_x']:s.rect(px(x-37.15/2),py(-269.5),37.15*k,29.6*k,5,'#c8e1e8','#006979')
    s.circle(px(0),py(-280.8),1.7*k,'white');s.line(px(0),120,px(0),480,'#7892a1','15 4 2 4')
    s.dimh(px(-40),px(-2.85),py(-299.1),506,'37.15 +/-0.10 REF')
    s.dimh(px(-2.85),px(2.85),py(-269.5),108,'5.70 +/-0.10 LAND')
    s.dimv(py(-269.5),py(-299.1),px(40),909,'29.60 +/-0.10 REF')
    s.txt(965,128,'TWO TOP POCKETS / R0.50 +/-0.10','bold')
    for i,line in enumerate(['Each pocket floor 0.50 +/-0.05 below top.',
      'X boundaries from B: 22.50 /59.65;',
      '65.35 /102.50 for second pocket.',
      'Y boundaries from C: 1.50 /31.10.',
      'Each boundary location +/-0.05.',
      'Boundary values control; sizes are REF.',
      'Remaining thickness >=4.40 locally.',
      'Actual fan-frame gap >=0.20.',
      'Keep central 5.7 and outside metal lands.',
      'R0.5 requires suitable small cutter access.']):s.txt(965,167+i*29,line,'small')
    s.txt(35,557,'SECTION THROUGH H3 / NOMINAL X-Z PROFILE / UNIFORM SCALE','bold')
    k=25.;cx=470;px=lambda x:cx+x*k;pz=lambda z:752-z*k
    points=[(-15,0),(-3.05,0),(-1.7,1.35),(-1.7,4.9),(-1.8,5),(-2.85,5),(-2.85,4.5),(-15,4.5)]
    for q in [points,[(-x,z) for x,z in reversed(points)]]:
        d=' '.join(('M' if i==0 else 'L')+f'{px(x)},{pz(z)}' for i,(x,z) in enumerate(q))+' Z';s.add(f'<path d="{d}" fill="#dce8ef" stroke="#142c3b" stroke-width="2"/>')
    s.line(cx,605,cx,815,'#7892a1','12 4 2 4');s.dimh(px(-3.05),px(3.05),752,811,'DIA6.1 REF / 90-degree CSK')
    s.dimv(pz(5),pz(0),px(15),889,'5.00 +/-0.05')
    s.rect(49,737,30,30,fill='white');s.txt(64,759,'A','bold','middle');s.line(79,752,95,752)
    for i,line in enumerate(['HEAD / SEAT ACCEPTANCE',
      'Head flush to 0.10 BELOW A.',
      'Full conical seating; no head rocking.',
      'Effective seat diameter >=5.70.',
      'Straight bore ligament >=3.30.',
      'Nominal straight 3.55 after 0.10 deburr.',
      'Screen: mouth<=6.20; angle>=89 deg;',
      'throat>=3.30; page 2 bore size governs.']):s.txt(965,576+i*29,line,'bold' if i==0 else 'small')
    s.txt(35,866,'Use received M3 x8 DIN 7991 screws as the seat gauge. Nominal CAD head is an ideal 90-degree proxy.','small')
    s.txt(35,900,'Manufacturer max intrusion 4.00 from PSU face. Prototype received-stack window 2.75-3.35; nominal 3.05.','small')
    s.txt(35,934,'No inherited 2 mm female-engagement criterion. Verify that complete screw threads traverse the actual flanged boss.','small');s.save(path)


def embed_svg(c,path,x,y,w,h):
    d=svg2rlg(str(path));sc=min(w/d.width,h/d.height);d.scale(sc,sc);renderPDF.draw(d,c,x+(w-d.width*sc)/2,y+(h-d.height*sc)/2)


def template_page(c,p):
    """Actual PDF-unit geometry at1:1, rotated+90 degrees; no image scaling."""
    title(c,'1:1 fit template / print at actual size',6)
    mm=72/25.4;px=lambda x,y:(56-y)*mm;py=lambda x,y:(148.5+x)*mm
    c.setStrokeColor(INK);c.setLineWidth(.45)
    c.roundRect(56*mm,86*mm,300.6*mm,125*mm,8*mm,fill=0,stroke=1)
    c.setStrokeColor(TEAL);c.setDash(5,3)
    for xx in [-42.5,42.5]:c.line(px(xx,0),py(xx,0),px(xx,-300.6),py(xx,-300.6))
    c.setDash();c.setStrokeColor(INK)
    for typ,points,dia in [('H',p['housing_points'],p['housing_clearance_diameter']),('S',stud_points(p),p['stud_clearance_diameter'])]:
        for i,(x,y) in enumerate(points,1):
            xx,yy=px(x,y),py(x,y);c.circle(xx,yy,dia/2*mm,fill=0,stroke=1);c.line(xx-4*mm,yy,xx+4*mm,yy);c.line(xx,yy-4*mm,xx,yy+4*mm)
            text(c,xx+5*mm,yy+3*mm,f'{typ}{i}',50,9,bold=True)
    text(c,49*mm,219*mm,'TERMINAL CHASSIS PLANE / Y0',255,10,bold=True,color=TEAL)
    text(c,271*mm,219*mm,'FAN END / DATUM C',250,10,bold=True,color=TEAL)
    text(c,58*mm,79*mm,'Dashed lines: 85 mm PSU width envelope. Template is pattern evidence only; do not drill through an installed PSU.',880,9.7)
    # Orthogonal100 mm bars detect print scaling in both sheet directions.
    c.setStrokeColor(TEAL);c.setLineWidth(.9)
    for x in [65,165]:c.line(x*mm,58*mm,x*mm,62*mm)
    c.line(65*mm,60*mm,165*mm,60*mm);text(c,89*mm,64*mm,'100.00 mm',190,11,bold=True,color=TEAL)
    for y in [96,196]:c.line(373*mm,y*mm,377*mm,y*mm)
    c.line(375*mm,96*mm,375*mm,196*mm);c.saveState();c.translate(382*mm,146*mm);c.rotate(90);c.setFont('Helvetica-Bold',11);c.setFillColor(TEAL);c.drawCentredString(0,0,'100.00 mm');c.restoreState()
    text(c,33,133,'PRINT A3 AT 100% / ACTUAL SIZE; disable fit-to-page. Measure both 100 mm bars with a reliable rule before use. A4 shrink-to-fit is invalid.',1125,10.5,bold=True,color=AMBER)
    text(c,33,102,'Verify all three physical PSU axes before final drilling/countersinking. Manufacturer general tolerance +/-0.5 mm exceeds the nominal self-centering fit of these fixed cones. Revise named coordinates if the received pattern differs.',1125,10)
    c.showPage()


def catalog_rows(cat):
    rows=[];links=[]
    for r in cat['items']:
        pack,price=r.get('pack_qty'),r.get('pack_price_usd');buy=f'{pack} / ${price}' if pack is not None and price is not None else 'Quote required'
        rows.append([r['item_id'],r['part_number'],str(r.get('quantity',r.get('qty','AR'))),r['description'],buy]);links.append(r.get('url',''))
    return rows,links


def make_pdf(out,p,cat,plan,detail,checks):
    pdf=out/'MeanWell_N1_drawing_package.pdf';temp=Path('C:/b210work/nsp1600/documents');temp.mkdir(parents=True,exist_ok=True);stage=temp/pdf.name
    c=canvas.Canvas(str(stage),pagesize=(W,H));c.setTitle('Mean Well NSP-1600 stud adapter / N1 preliminary fit prototype');c.setAuthor('Parametric CAD engineering draft')
    product=HERE/'references/product';views=HERE/'references/views'
    title(c,'Mean Well NSP-1600 / direct stud adapter',1)
    picture(c,product/'assembled_hero.png',33,317,738,408)
    box(c,792,506,366,219,'ONE PART / DESIGNATED MOUNTING POINTS',
      'Three manufacturer-designated bottom M3 holes retain the PSU on a machined adapter. Four FPE M3 load studs, washers and nuts attach the adapter to the main metal panel.\nTwo shallow upper pockets prevent loading the exposed fan frames while preserving the metal bracket spine. No thermal pad or grease is selected.',10.3)
    box(c,792,317,366,173,'PRELIMINARY OPERATING BASIS',
      'Stationary indoor, horizontal bottom-down service in a box. Provisional NSP-1600-12; 24 V remains possible. Panel 145 x340 x6 mm is an interface coupon only.\nActual voltage/load, ambient, TEC cooling, wiring, final panel and vibration remain unconfirmed.',10.1)
    table(c,['Feature','Nominal dimension / source','Required acceptance'],[
      ['Adapter M01','125 x300.6 x5.00 mm; 6061-T6/T651','One machined part; measured actual PSU pattern before final boring'],
      ['PSU mounting','H1(-35,-16.1),H2(35,-16.1),H3(0,-280.8)','Manufacturer M3; maximum 4.00 mm intrusion'],
      ['Fan-frame relief','Two 37.15 x29.6 x0.50 mm pockets','Actual fan gap>=0.20; retain metal contact without bowing'],
      ['Initial loading basis','1.8 kg manufacturer PSU mass; 2.4 kg package allowance','145 N package screening and 5 N m cable couple; see engineering note']],33,294,[187,386,552],size=9.5,minh=35)
    count_text='; '.join(f"{len(q.get('checks',[]))} {('nominal CAD' if 'cad_verification' in f.name else 'manufacturing geometry')} checks" for f,q in checks)
    text(c,39,97,count_text+' passed. This does not qualify physical fit, housing/FPE strength, wiring or cooling. No fabrication, purchase or physical test occurred.',1110,9.7,bold=True,color=AMBER)
    c.showPage()
    title(c,'M01 / Dimensioned plans and hole-coordinate table',2,'MW-NSP-M01 / QTY1');embed_svg(c,plan,30,58,W-60,H-146);c.showPage()
    title(c,'M01 / Fan reliefs, section and countersink acceptance',3,'MW-NSP-M01 / QTY1');embed_svg(c,detail,30,58,W-60,H-146);c.showPage()
    title(c,'PSU screw stack, panel interface and service access',4)
    picture(c,views/'section_front_mount_front.png',35,468,529,246)
    picture(c,views/'section_fan_mount_front.png',35,201,529,240)
    text(c,41,726,'TERMINAL-END M3 / ACTUAL CAD SECTION',515,10,bold=True,color=TEAL)
    text(c,41,450,'FAN-CENTER M3 / METAL SPINE AND RELIEFS',515,10,bold=True,color=TEAL)
    text(c,601,719,'CONTROL THE RECEIVED THREE-SCREW STACK',551,13,bold=True,color=TEAL)
    y=text(c,601,690,'M3 x0.5 x8 DIN 7991 socket flat-head screw, McMaster 91294A128; 2 mm hex, catalog head DIA6 x1.7 mm. Overall length includes the head. Nominal CAD cone is a reference proxy, not a complete head specification.',548,10.3)
    y=text(c,601,y-15,'Actual projection P = length L + inward head recess r - finished plate thickness t. Nominal 8 +0.05 -5.00 =3.05 mm. Prototype acceptance 2.75-3.35; hard manufacturer maximum 4.00 mm. Gauge each installed screw and confirm complete threads traverse the actual flanged boss.',548,10.3)
    box(c,594,440,564,118,'MANUFACTURER TORQUE AND PHYSICAL LIMITS',
      'Mean Well recommends 6-8 kgf cm (0.5884-0.7845 N m) for bottom M3 mounting. Qualify received countersunk-head/finish/locking compatibility before applying a procedure. No arbitrary thread or head capacity is inferred.\nDo not impose an unsupported 2 mm female-engagement minimum.',9.7)
    table(c,['Panel interface','Nominal location / requirement'],[
      ['FPE stud pattern','110 x264.7 mm rectangular pitch. S1(-55,-280.8),S2(-55,-16.1),S3(55,-280.8),S4(55,-16.1)'],
      ['From adapter B/C','(7.5,19.8),(7.5,284.5),(117.5,19.8),(117.5,284.5)'],
      ['FPE location proposal','DIA0.30 position; supplier must confirm capability. Adapter bores DIA0.10 position.'],
      ['Contact and tail','Stud bases/adhesive flush or below panel. Nominal stud tail 2.45 beyond nut; verify full nylon and two complete threads.']],595,417,[156,407],size=9.3,minh=38)
    text(c,601,207,'Socket 5.5 AF, OD<=10, clear internal depth>=10; reserve 60 mm axial tool access and 20 mm removal lift. No stud standoff gap or pad is intended.',547,10,bold=True)
    text(c,41,185,'Orange = new M3 proxy; blue = adapter; green = source PSU; grey = panel.\nNominal front screw-tip/PCB gap = 1.45 mm; physical check required.',527,9,leading=12)
    text(c,39,147,'Main panel 145 x340 x6 mm is a reference coupon centred Y-150.3. Its lower-left reference stud coordinates are (17.5,39.5),(17.5,304.2),(127.5,39.5),(127.5,304.2) mm. Final panel design and supports require confirmation.',1110,9.8)
    text(c,39,95,'At front screws the source PCB begins 4.5 mm above the PSU face. Actual circuitry/solder/insulation may differ; the manufacturer 4 mm limit governs. Keep factory covers and use the designated FG earth connection.',1110,9.8,bold=True,color=AMBER)
    c.showPage()
    title(c,'Bill of materials, assembly and prototype validation',5)
    rows,links=catalog_rows(cat);custom=[['M01','Custom drawing','1','125 x300.6 x5.00 mm machined 6061-T6/T651; clear conversion; two upper fan reliefs','Quote required']]
    bot=table(c,['ID','Catalog number / link','Qty','Specification','Purchase reference'],custom+rows,33,723,[53,163,44,682,183],size=9,minh=32,links=['']+links)
    if bot<450:raise ValueError(f'BOM exceeds page budget: {bot}')
    text(c,39,bot-21,'Initial McMaster packs: $20.08, observed 2026-09-08. FPE panel/studs, custom fabrication, PSU and wiring require separate scope/quotes. No purchase made.',1110,9.5)
    text(c,39,437,'INSTALLATION / ROUTINE REMOVAL',540,13,bold=True,color=TEAL)
    y=408
    for line in [
      '1. Disconnect power and secure against reconnection. Measure the received hole pattern with the calibrated template; confirm case variant, screw dimensions and available threads.',
      '2. Inspect the finished plate and gauge all three screw seats/projections. Dry-fit on metal lands: no fan-frame contact, forced hole alignment, bowing or proud screw heads.',
      '3. Attach the adapter using three M3 screws under the qualified assembly procedure. Lower the PSU/adapter onto four verified FPE studs; fit specified washers and locknuts.',
      '4. Connect protected power/control wiring with independent strain relief and FG protective earth. Keep both 100 mm preliminary end corridors clear; verify actual lugs, bends and tools.',
      '5. For service, power down/disconnect, support the PSU, remove four stud nuts/washers and lift>=20 mm. Access the three underside screws on the bench; preserve original case hardware.'
    ]:y=text(c,39,y,line,541,9.5,leading=13.4)-10
    text(c,613,437,'PRACTICAL PROTOTYPE CHECKS',540,13,bold=True,color=TEAL)
    y=408
    for label,body in [
      ('FIT','Record actual axes, head seats, 2.75-3.35 intrusion, complete screw-thread traversal and>=0.20 fan gap. Reject any forced seating.'),
      ('RETENTION','Use engineering-note proof loads after confirming case, screw-head and FPE capacities. Surrogate proof acceptance: <=0.70 mm local deflection, <=0.85 mm combined and <=0.10 mm residual. Inspect slip, loosening and damage; record 10 removal cycles.'),
      ('COOLING / POWER','Run worst intended workload/input/ambient. Measure PSU exhaust, case and actual nut temperatures; preserve vents and horizontal derating. The 12 V full-load loss estimate ~185 W is not measured or a TEC capacity claim.'),
      ('ELECTRICAL / SERVICE','Verify real lugs, AC guards, cable bends, FG connection and safe access. Metal contact is not a qualified earth bond. Main panel, anchors and complete enclosure require application-specific validation.')
    ]:
        y=text(c,613,y,label,537,10,bold=True,color=TEAL)-2;y=text(c,613,y,body,537,9.5,leading=13.4)-13
    text(c,39,88,'Reference installation only. No vehicle, airborne, outdoor or overhead qualification. FPE anchor capacity/torque/temperature and countersunk-head compatibility remain open.',1111,9.5,bold=True,color=AMBER)
    c.showPage();template_page(c,p);c.save();shutil.copyfile(stage,pdf);return pdf,stage


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--render',action='store_true');ap.add_argument('--svg-only',action='store_true');ap.add_argument('--out',type=Path,default=OUT);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);p,cat,pp,cp,checks=load_inputs(not args.svg_only)
    plan=args.out/'MW_NSP_M01_plans_N1.svg';detail=args.out/'MW_NSP_M01_relief_sections_N1.svg';plan_svg(plan,p);detail_svg(detail,p)
    if args.svg_only:print(plan);print(detail);return
    pdf,stage=make_pdf(args.out,p,cat,plan,detail,checks)
    sources=[Path(__file__),pp,cp,HERE/'DESIGN.md',HERE/'ENGINEERING_NOTE.md',HERE/'references/engineering/engineering_results.json']+[f for f,r in checks]+sorted((HERE/'references/product').glob('*.png'))+[HERE/'references/views/section_front_mount_front.png',HERE/'references/views/section_fan_mount_front.png']
    manifest={'revision':REV,'status':'PENDING ROOT AND VISUAL REVIEW; PRELIMINARY FIT PROTOTYPE ONLY','pdf':pdf.name,'pages':PAGE_COUNT,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
      'sources':[{'path':str(f.relative_to(HERE)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sources],
      'template_scale':'1 mm =72/25.4 PDF points. Rotated+90degrees; two orthogonal100mm calibration bars. Print actual size.'}
    (args.out/'drawing_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    if args.render:
        qa=stage.parent/'qa';qa.mkdir(exist_ok=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(stage),str(qa/'page')],check=True)
        dest=args.out/'qa';dest.mkdir(exist_ok=True)
        for f in sorted(qa.glob('page-*.png')):shutil.copyfile(f,dest/f.name)
    print(pdf)


if __name__=='__main__':main()




