"""Reproduce the SolidRun thermal adapter's dimensioned prototype drawing package.

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
REV='T1'
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

def title(c,name,page,part='BEDROCK THERMAL STUD MOUNT'):
    c.setFillColor(INK); c.rect(0,H-77,W,77,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold',22); c.drawString(32,H-35,name)
    c.setFont('Helvetica-Bold',10); c.drawString(33,H-59,'PRELIMINARY FIT AND THERMAL PROTOTYPE - NOT A PRODUCTION RELEASE')
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
    ppath=HERE/'params.json'; p=json.loads(ppath.read_text(encoding='utf-8-sig'))
    expected={'plate_width':166,'plate_length':184,'plate_thickness':5.1,'plate_thickness_tolerance':.05,
        'corner_radius':8,'edge_break':.4,'bore_deburr':.1,'housing_clearance_diameter':4.5,
        'countersink_diameter_reference':8.1,'countersink_angle_deg':90,'screw_length_overall':8,
        'screw_head_diameter':8,'screw_head_recess_nominal':.05,'screw_projection_accept_min':2.85,
        'screw_projection_accept_max':3,'full_thread_engagement_accept_min':2,'thermal_field_width':126,
        'thermal_field_length':156,'thermal_field_corner_radius':5,'thermal_pocket_depth':.05,
        'thermal_pocket_depth_tolerance':.01,'thermal_gap_accept_max':.1,'tile_contact_land_diameter':8,
        'underside_countersink_land_diameter':10,'stud_pitch_x':152,'stud_pitch_y':164,
        'stud_clearance_diameter':3.8,'stud_projection':12,'panel_reference_width':200,
        'panel_reference_length':220,'panel_reference_thickness':6,'tool_socket_envelope_diameter':10,
        'tool_socket_envelope_height':60,'tool_socket_internal_depth_min':8,'service_lift_min':20,
        'thermal_vent_width':1,'thermal_vent_start_x':62,'thermal_vent_end_x':84}
    changed={k:p.get(k) for k,v in expected.items() if k not in p or abs(float(p[k])-v)>1e-7}
    if p.get('housing_points')!=[[-60,-70],[60,-70],[0,-40],[0,30],[-50,70],[50,70]]:changed['housing_points']=p.get('housing_points')
    if p.get('thermal_vent_y_positions')!=[-20,20]:changed['thermal_vent_y_positions']=p.get('thermal_vent_y_positions')
    if p.get('units')!='mm' or not p.get('revision','').startswith('T1'):raise ValueError('T1 millimetre parameters required.')
    if changed:raise ValueError(f'Review dimensioned annotations for changed CAD: {changed}')
    catpath=HERE/'references/research/catalog_bom.json'
    cat=json.loads(catpath.read_text(encoding='utf-8-sig'))
    selected={row['item_id']:row['part_number'] for row in cat['items']}
    for ident,pn in {'H01':'91294A188','H02':'98688A142','H03':'90576A102','T01':'10405K83'}.items():
        if selected.get(ident)!=pn:raise ValueError(f'Catalog selection changed: {ident}')
    for name in ['cad_verification.json','manufacturing_verification.json']:
        check=json.loads((HERE/'exports'/name).read_text(encoding='utf8'))
        if check.get('status')!='PASS':raise ValueError(f'Final CAD check has not passed: {name}')
        expected_count=94 if name=='cad_verification.json' else 60
        if len(check['checks'])!=expected_count:raise ValueError(f'Review check-count caption for {name}')
        if 'params_sha256' in check and check['params_sha256']!=hashlib.sha256(ppath.read_bytes()).hexdigest():
            raise ValueError(f'Final verification is stale relative to parameters: {name}')
    return p,cat,ppath,catpath


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


def plate_svg(path,p):
    s=SVG();s.txt(35,40,'M01 / MACHINED THERMAL ADAPTER - CONTACT-SIDE PLAN','title')
    s.txt(35,76,'All dimensions mm after finish. Coordinates BASIC; position tolerance controls holes. Do not scale.','small')
    k=3.;cx=401;cy=445;px=lambda x:cx+x*k;py=lambda y:cy-y*k
    l,r,t,b=px(-83),px(83),py(92),py(-92)
    s.rect(l,t,166*k,184*k,8*k,'#f7f9fa')
    s.rect(px(-63),py(78),126*k,156*k,5*k,'#cde8e6','#006979')
    for y in [-20,20]:s.rect(px(62),py(y+.5),21*k,1*k,fill='#cde8e6',color='#006979')
    for i,(x,y) in enumerate(p['housing_points'],1):
        s.circle(px(x),py(y),4*k,'#f7f9fa');s.circle(px(x),py(y),2.25*k,'white')
        s.line(px(x)-15,py(y),px(x)+15,py(y),'#7892a1','8 3 1 3')
        s.line(px(x),py(y)-15,px(x),py(y)+15,'#7892a1','8 3 1 3')
        s.txt(px(x)+17,py(y)-13,f'H{i}','small')
    # Match model.stud_points(), STEP component identifiers and the exported CSV.
    studs=[(-76,-82),(-76,82),(76,-82),(76,82)]
    for i,(x,y) in enumerate(studs,1):
        s.circle(px(x),py(y),1.9*k,'white');s.txt(px(x)+(14 if x<0 else -42),py(y)+(-12 if y>0 else 25),f'S{i}','small')
    s.line(cx,t-10,cx,b+10,'#7892a1','15 4 2 4');s.line(l-8,cy,r+8,cy,'#7892a1','15 4 2 4')
    s.dimh(l,r,t,112,'166.00 +/-0.10');s.dimv(t,b,l,69,'184.00 +/-0.10')
    s.dimh(px(-63),px(63),py(-78),765,'126.00 +/-0.10 THERMAL FIELD')
    s.dimv(py(78),py(-78),r,707,'156.00 +/-0.10 FIELD')
    s.line(l,cy,l+25,cy);s.rect(l+26,cy-15,30,30,fill='white');s.txt(l+41,cy+7,'B','bold','middle')
    s.line(590,b,590,b+20);s.rect(575,b+21,30,30,fill='white');s.txt(590,b+44,'C','bold','middle')
    s.txt(792,120,'HOLE COORDINATES FROM DATUMS B / C','bold')
    for xx,label in zip([800,920,1080,1250],['ID','X from B','Y from C','BORE']):s.txt(xx,159,label,'small bold')
    for i,(x,y) in enumerate(p['housing_points']):
        for xx,value in zip([800,920,1080,1250],[f'H{i+1}',f'{x+83:.3f}',f'{y+92:.3f}','DIA4.5']):s.txt(xx,192+i*31,value,'small')
    for i,(x,y) in enumerate(studs):
        for xx,value in zip([800,920,1080,1250],[f'S{i+1}',f'{x+83:.3f}',f'{y+92:.3f}','DIA3.8']):s.txt(xx,397+i*31,value,'small')
    notes=['H1-H6: DIA4.5 +0.10/0 THRU; CSK FROM A.',
           'S1-S4: DIA3.8 +0.10/0 THRU.',
           'All bore axes: position DIA0.10 | A | B | C, RFS.',
           'A = lower hard seating plane (opposite face).',
           'B = left edge; C = lower edge, excluding breaks.',
           'Outer corners: 4X R8 +/-0.25.',
           'Thermal-field corners: 4X R5 +/-0.25 each face.',
           'Top field: depth 0.050 +/-0.010; 6X DIA8 islands.',
           'Bottom: same field; 6X DIA10 countersink lands.',
           'Field center: X83/Y92 from B/C +/-0.10; islands on H axes.',
           '2X escape grooves EACH face: width 1.0 +/-0.10,',
           'Y72/112 from C; X145 from B to +X edge, loc.+/-0.10.']
    for i,line in enumerate(notes):s.txt(790,532+i*25,line,'small')
    s.txt(35,833,'M01: QTY1. Certified 6061-T6/T651; finished thickness 5.10 +/-0.05. No formed bends.','small')
    s.txt(35,868,'Teal = recessed compound field / escape grooves. White circles and rim = hard seating features.','small')
    s.txt(35,903,'A flatness 0.03; Tile lands flatness 0.03 and parallelism 0.03 to A. No stud-base relief.','small')
    s.txt(35,941,'PRELIMINARY FIT AND THERMAL PROTOTYPE - physical thread, gap and joint qualification required.','bold')
    s.save(path)


def section_svg(path,p):
    s=SVG();s.txt(35,40,'M01 / HOUSING-FASTENER SECTION AND TWO-SIDED MACHINING','title')
    s.txt(35,77,'Section through H4, away from thermal-field boundary. Uniform nominal X/Z scale. Dimensions govern.','small')
    k=33.;ox=455;oy=381;px=lambda x:ox+x*k;pz=lambda z:oy-z*k
    left=[(-11,.05),(-5,.05),(-5,0),(-4.05,0),(-2.25,1.8),(-2.25,5.0),(-2.35,5.1),(-4,5.1),(-4,5.05),(-11,5.05)]
    right=[(-x,z) for x,z in reversed(left)]
    for points in [left,right]:
        d=' '.join(('M' if i==0 else 'L')+f'{px(x)},{pz(z)}' for i,(x,z) in enumerate(points))+' Z'
        s.add(f'<path d="{d}" fill="#dce8ef" stroke="#142c3b" stroke-width="2"/>')
    s.line(ox,155,ox,445,'#7892a1','12 4 2 4')
    s.dimh(px(-4.05),px(4.05),pz(0),445,'DIA8.1 REF / 90-degree CSK')
    s.dimv(pz(5.1),pz(0),px(11),874,'5.10 +/-0.05')
    s.line(px(-9),pz(0),87,pz(0));s.rect(48,pz(0)-15,30,30,fill='white');s.txt(63,pz(0)+7,'A','bold','middle')
    s.txt(972,173,'TWO INDEPENDENT RECESSES','bold')
    for i,line in enumerate(['Top and bottom fields:','0.050 +/-0.010 deep EACH.','Top hard islands: 6X DIA8.','Underside CSK lands: 6X DIA10.','Land diameters +/-0.10.','Bore deburr <=0.10 at top.','No proud burr or coating ridge.']):s.txt(972,211+i*32,line,'small')
    s.txt(35,516,'SIX COUNTERSINKS: ACTUAL SCREW HEAD / STACK ACCEPTANCE','bold')
    notes=['90-degree countersink from A; nominal mouth DIA8.1 REF. Gauge with received M4 x8 DIN 7991 screws.',
      'Head flush to 0.10 BELOW A; effective conical seating DIA>=7.60, full contact and no head rocking.',
      'Actual straight cylinder >=3.00 after top deburr. Nominal: CSK depth 1.80, straight 3.20 with 0.10 deburr.',
      'Screen: mouth<=8.20; included angle>=89 deg; throat>=4.40. Page 2 bore tolerance still governs.',
      'Nominal 90-degree CAD head is an idealized proxy; catalog head height does not bound the actual seat.',
      'Above Tile-contact plane: actual tip projection2.85-3.00; effective FULL thread engagement>=2.00.',
      'Deduct 0.584 geometric entry, additional incomplete female-entry phase and actual incomplete screw tip.',
      'Verify >=0.50 clearance to the actual full-diameter blind-hole limit. The drill-point tip is not usable bore depth.']
    for i,line in enumerate(notes):s.txt(35,554+i*28,line,'small')
    s.txt(35,792,'MACHINING AND FINISH / PROPOSED PROTOTYPE ACCEPTANCE','bold')
    for i,line in enumerate(['Face both sides of nominal 6 mm /1/4-in certified 6061 stock; use supported two-sided workholding.',
      'Clear conversion coating MIL-DTL-5541 Type II Class 3 by qualified vendor; all fit dimensions AFTER finish.',
      'Thermal fields Ra<=1.6 micrometres. Outer rim 0.4 x45-degree break; avoid rounding hard-contact lands.',
      'Grooves each face: Y72/112 from C; X145 from B through +X edge; depth 0.050 +/-0.010.',
      'Top hard-land effective OD>=7.90. Gauge physical threads/heads/gaps; no installation torque is qualified.']):s.txt(35,828+i*27,line,'small')
    s.save(path)


def embed_svg(c,path,x,y,w,h):
    d=svg2rlg(str(path));sc=min(w/d.width,h/d.height);d.scale(sc,sc)
    renderPDF.draw(d,c,x+(w-d.width*sc)/2,y+(h-d.height*sc)/2)


def rows_from_catalog(cat):
    rows=cat.get('items',cat.get('rows',[]));result=[];links=[]
    if not rows:raise ValueError('Catalog item rows required.')
    for r in rows:
        pn=r.get('part_number','');pack=r.get('pack_qty');price=r.get('pack_price_usd')
        purchase=f'{pack} / ${price}' if pack is not None and price is not None else r.get('purchase_note','Quote required')
        result.append([r.get('item_id',''),pn,str(r.get('quantity',r.get('qty','AR'))),r.get('description',''),purchase])
        links.append(r.get('url',''))
    return result,links


def make_pdf(out,p,cat,plan,sections):
    pdf=out/'SolidRun_T1_drawing_package.pdf';temp=Path('C:/b210work/solidrun/documents');temp.mkdir(parents=True,exist_ok=True)
    stage=temp/pdf.name;c=canvas.Canvas(str(stage),pagesize=(W,H));c.setTitle('SolidRun Bedrock thermal stud adapter / T1 preliminary prototype')
    c.setAuthor('Parametric CAD engineering draft');c.setCreator('Reproducible make_documents.py / ReportLab')
    product=HERE/'references/product';views=HERE/'references/views'
    title(c,'SolidRun Bedrock / thermal stud adapter',1)
    picture(c,product/'assembled_hero.png',32,293,745,430)
    box(c,794,500,364,225,'ONE STRUCTURAL AND THERMAL INTERFACE',
      'Six existing flat-face Tile holes retain the computer on one machined plate. Four exposed M3 panel studs carry the plate into the supporting metal panel. Shallow thermal-compound fields connect both broad faces; hard lands carry the fastener grip.\nThe opposite one-bank fins remain exposed.',10)
    box(c,794,293,364,190,'PROVISIONAL INSTALLATION BASIS',
      'Stationary indoor service inside a box. Main panel 200 x220 x6 mm is an interface coupon only. Actual TEC cooler, heat load, airflow, setpoint and panel boundaries remain unconfirmed.\nPrefer vertical panel / +Y-up fins; reserve 20 mm above/below and 10 mm at sides, plus actual plug/tool space. No complete cooling capacity or case-thread/FPE strength is qualified.',10)
    table(c,['Feature','Nominal geometry','Status / acceptance'],[
      ['M01 adapter','166 x184 x5.10; 6061-T6/T651','One CNC part; two 0.050-deep thermal fields'],
      ['Computer reference','Tile + clipped actual 60 W fin-bank geometry','Derived reference, not a native vendor configuration or 60 W rating'],
      ['Thread interface','Six measured axes; modeled M4-like 0.7 pitch','All six holes are blind; received screws and actual housing require gauges'],
      ['Thermal path','Tile -> compound -> adapter -> compound -> panel','Both actual filled fields: 0 < gap <0.10 mm; final heat rejection remains unverified']],33,270,[182,369,574],size=9.4,minh=34)
    text(c,39,88,'94 nominal CAD checks and60 manufacturing geometry checks passed. This scope does not establish physical fit, joint strength, thermal performance or a production release. No part has been fabricated or physically tested.',1110,9.6,bold=True,color=AMBER)
    c.showPage()
    title(c,'M01 / Dimensioned plate and coordinate table',2,'SR-TS-M01 / QTY1');embed_svg(c,plan,30,58,W-60,H-146);c.showPage()
    title(c,'M01 / Sections, machining and screw acceptance',3,'SR-TS-M01 / QTY1');embed_svg(c,sections,30,58,W-60,H-146);c.showPage()
    title(c,'Blind thread stack and main-panel stud interface',4)
    picture(c,views/'section_fastener.png',34,413,620,309)
    for i,(color,label) in enumerate([('#c97720','M4 screw proxy'),('#5793c4','New adapter'),('#578b73','Original Tile'),('#adb6c2','Reference panel')]):
        yy=710-i*24;c.setFillColor(colors.HexColor(color));c.rect(43,yy-5,7,7,fill=1,stroke=0);text(c,56,yy,label,142,8.4)
    text(c,39,394,'Actual CAD section: idealized external screw; physical head / tip / female-thread gauges control.',610,9,color=AMBER)
    text(c,679,720,'CONTROL THE RECEIVED SCREW STACK',475,13,bold=True,color=TEAL)
    text(c,679,690,'M4 x0.7 x8 overall-length DIN 7991 countersunk socket screw. Nominal head diameter 8 mm; catalog head height 2.3 mm; 2.5 mm hex. Length includes the head.',474,10.3)
    text(c,679,610,'Projection P = L + inward head recess r - finished plate thickness t. Nominal: 8.00 +0.05 -5.10 =2.95 mm. Entry cone 0.584 leaves 2.366 mm before additional incomplete female-entry phase, screw-tip loss and tolerances.',474,10.3)
    box(c,672,410,486,132,'ALL SIX LOCATIONS MUST PASS TOGETHER',
      'Projection 2.85-3.00; complete engagement>=2.00 after all entry/tip losses; clearance>=0.50 to verified full-diameter blind limit. Stock M4 x8 compatibility is unconfirmed. Nominal CAD full-diameter margin 3.50 -2.95 =0.55 mm is reference only.\nNever use tightening torque to discover the blind end.',10)
    table(c,['Interface','Coordinates / dimensions','Acceptance'],[
      ['Four FPE M3 stud axes','Centered X=+/-76; Y=+/-82','152 x164 pattern; proposed DIA0.30 position - supplier must accept'],
      ['Adapter stud coordinates B/C','(7,10),(159,10),(7,174),(159,174)','DIA3.8 +0.10/0; DIA0.10 position A/B/C'],
      ['Reference panel 200 x220 x6','Studs from panel left/bottom:(24,28),(176,28),(24,192),(176,192)','Reference interface only; final panel/support and FPE factory features require approval'],
      ['Stud bases and adhesive','No relief in adapter','Finish flush or below panel seating surface; inspect before assembly']],33,367,[178,425,522],size=9.5,minh=37)
    text(c,39,144,'Nominal radial location reserve: 0.40 clearance -0.05 adapter position -0.15 stud position =0.20 mm before diameter, finish and straightness effects. Do not force an assembly onto mislocated studs.',1113,10)
    text(c,39,96,'Use 5.5 AF socket, OD<=10, internal clear depth>=8; reserve 60 mm tool access and 20 mm service lift. Verify full nylon engagement and at least two complete exposed threads.',1110,10,bold=True)
    c.showPage()
    title(c,'Bill of materials and interface thermal requirements',5)
    rows,links=rows_from_catalog(cat);custom=[['M01','Custom drawing','1','166 x184 x5.10 mm CNC 6061-T6/T651 adapter; clear conversion coating','Quote required']]
    bot=table(c,['ID','Catalog number / link','Qty','Specification','Purchase reference'],custom+rows,33,724,[51,151,44,696,183],size=9,minh=31,links=['']+links)
    if bot<425:raise ValueError(f'Catalog table exceeds allotted page height: {bot}')
    text(c,39,bot-22,'Prices and pack quantities are observed procurement references; verify catalog selection at purchase. FPE studs belong to supporting-panel fabrication; computer and final panel are customer-furnished.',1110,9.4)
    picture(c,product/'plate_bottom_hero.png',34,117,533,262)
    box(c,589,115,569,272,'THERMAL INTERFACE IS A MEASURED FIT',
      'Use selected Dow 340 only in the specified shallow fields, with actual filled gaps strictly 0 < gap <0.10 mm. Keep hard lands, threads and nut seats free of excess material. Clear both escape grooves on each face; verify coverage and hard seating with a controlled witness assembly. Renew compound after separation.\nThe grease is nonstructural: no adhesion, friction, electrical isolation or ground-bond capacity is credited. No device finish removal is authorized.\nA and Tile lands each require 0.03 flatness; top lands 0.03 parallelism to A. These proposed shop limits do not establish actual Tile/panel flatness or thermal contact.',10)
    text(c,39,82,'No unverified torque or locking adhesive is specified. Case-thread and FPE anchorage qualification must establish the complete preload / locking procedure before service release.',1110,9.8,bold=True,color=AMBER)
    c.showPage()
    title(c,'Assembly, service and practical prototype validation',6)
    picture(c,product/'exploded_iso.png',33,390,551,335)
    text(c,39,378,'Blue = nominal grease-pocket volume, not a solid pad or an extra structural spacer.',541,8.7,color=TEAL)
    text(c,610,721,'ASSEMBLE ON THE BENCH, THEN INSTALL TO THE PANEL',545,12.8,bold=True,color=TEAL)
    y=691
    for step in [
      '1. Confirm the physical Tile / one-bank configuration. Gauge all six threads, blind limits, screw heads/tips and complete engagement. Measure mass, contact flatness and finished plate dimensions.',
      '2. Perform a clean witness assembly to verify hard-land contact and compound-field gaps. Apply the qualified amount of compound to the top field without filling threads. Seat the six underside M4 screws evenly using a qualified preload procedure.',
      '3. Inspect FPE stud position, straightness, anchorage and flush bases. Apply bottom compound field; lower computer/adapter over studs, then fit the specified washers and nuts without forcing the pattern.',
      '4. Mate actual cables and add independent panel strain relief. Preserve plug/latch, bend and fin-channel space. Confirm access with the specified socket and service lift before operating.'
    ]:y=text(c,610,y,step,545,9.6,leading=13.5)-10
    text(c,39,359,'PROTOTYPE CHECKS / RECORD CONDITIONS AND MEASUREMENTS',1110,13,bold=True,color=TEAL)
    table(c,['Check','Method and release evidence'],[
      ['Fit / blind-hole retention','Gauge each physical screw projection, head seat, >=2.00 complete engagement and >=0.50 blind-end gap. Inspect hard contact, no head rocking and no interference. Stop if any requirement conflicts.'],
      ['Mechanical loads','Apply engineering-note proof loads only after housing and FPE capacities are established. Inspect plate set, thread/anchor damage, joint slip and loosening; record permanent deflection and retained fastener condition.'],
      ['Thermal interfaces','Witness both filled fields and measure local gap / roughness / flatness. With actual workload, instrument Tile, adapter, main panel, enclosure air and TEC boundaries; compare steady temperatures to approved limits.'],
      ['System heat rejection','Test worst intended ambient, TEC setpoint, supply and airflow. Measure computer power/heat, fin temperatures and main-panel boundary. Check condensation risk at the coldest setpoint; no cooling capacity is assumed.'],
      ['Cables / service','Mate all actual plugs, verify bend radii and latch/tool access. Power off, disconnect cables, remove four stud nuts/washers and lift computer plus adapter; renew lower compound before refitting.']],33,336,[172,953],size=9.15,minh=36)
    text(c,39,86,'Separating the computer from its adapter is a bench operation: remove six underside screws and renew the upper compound. Vehicle, airborne, outdoor and overhead qualification remains outside this provisional basis.',1112,9.7,bold=True)
    c.showPage();c.save();shutil.copyfile(stage,pdf);return pdf,stage


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--render',action='store_true');ap.add_argument('--svg-only',action='store_true');ap.add_argument('--out',type=Path,default=OUT);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);p,cat,ppath,catpath=load_inputs()
    plan=args.out/'SR_TS_M01_dimensioned_plan_T1.svg';sec=args.out/'SR_TS_M01_sections_T1.svg';plate_svg(plan,p);section_svg(sec,p)
    if args.svg_only:print(plan);print(sec);return
    pdf,stage=make_pdf(args.out,p,cat,plan,sec)
    sources=[Path(__file__),ppath,catpath,HERE/'exports/cad_verification.json',HERE/'exports/manufacturing_verification.json']+sorted((HERE/'references/product').glob('*.png'))+[HERE/'references/views/section_fastener.png']
    manifest={'revision':REV,'pages':PAGE_COUNT,'status':'GENERATED - REQUIRES VISUAL REVIEW; PRELIMINARY FIT AND THERMAL PROTOTYPE','pdf':pdf.name,
      'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'sources':[{'path':str(s.relative_to(HERE)),'sha256':hashlib.sha256(s.read_bytes()).hexdigest()} for s in sources]}
    (args.out/'drawing_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    if args.render:
        qa=stage.parent/'qa';qa.mkdir(exist_ok=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(stage),str(qa/'page')],check=True)
        dest=args.out/'qa';dest.mkdir(exist_ok=True)
        for f in sorted(qa.glob('page-*.png')):shutil.copyfile(f,dest/f.name)
    print(pdf)


if __name__=='__main__':main()



