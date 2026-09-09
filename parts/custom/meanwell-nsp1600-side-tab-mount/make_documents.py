"""Reproduce the Mean Well NSP-1600 side-tab adapter's dimensioned prototype drawing package.

Run with C:/venvs/cadquery/Scripts/python.exe make_documents.py --render
Requires final params.json, catalog BOM and CAD-derived images. Fails closed if
critical drawing dimensions change. Manufacturing DXFs are exported by model.py;
this script never invents or overwrites manufacturing geometry.
"""
from pathlib import Path
import argparse, hashlib, html, json, math, shutil, subprocess
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
REV='N2'
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


def load_inputs(final=True):
    pp=HERE/'params.json';p=json.loads(pp.read_text(encoding='utf-8-sig'))
    expected={'plate_width':72,'plate_length':316.8,'plate_center_y':-142.2,'plate_thickness':6,'plate_thickness_tolerance':.05,
      'spine_width':45,'tab_length':44,'plate_fan_end_y':-300.6,'plate_terminal_end_y':16.2,'corner_radius':4,'edge_break':.4,
      'bore_deburr':.1,'housing_clearance_diameter':4.5,'countersink_diameter_reference':8.1,'countersink_angle_deg':90,
      'screw_diameter':4,'screw_pitch':.7,'screw_length_overall':10,'screw_head_diameter':8,'screw_head_height_catalog':2.3,
      'screw_head_recess_nominal':.05,'screw_hex_drive':2.5,'screw_projection_accept_min':3.75,'screw_projection_accept_max':4.35,
      'manufacturer_max_penetration':5,'stud_pitch_x':57,'stud_pitch_y':252,'stud_pattern_center_x':0,'stud_pattern_center_y':-131.8,
      'stud_pattern_rotation_deg':0,'stud_clearance_diameter':3.8,'stud_diameter':3,'stud_projection':12,'washer_id':3.2,'washer_od':7,
      'washer_thickness_nominal':.55,'nut_across_flats':5.5,'nut_height_nominal':4,'panel_reference_width':92,
      'panel_reference_length':340,'panel_reference_thickness':6,'tool_socket_envelope_diameter':10,'tool_socket_envelope_height':60,
      'tool_socket_internal_depth_min':10,'service_lift_min':20,'case_width_side':41,'case_height_side':85,
      'device_side_rotate_y_deg':90,'intake_reservation_length':100,'exhaust_reservation_length':100,
      'nominal_device_mass_kg_manufacturer':1.8,'front_thread_zone_depth':2.1}
    changed={k:p.get(k) for k,v in expected.items() if k not in p or abs(float(p[k])-v)>1e-7}
    for key,value in {'housing_points':[[2.3,-5.8],[2.3,-257.8]],'tab_stations_y':[-257.8,-5.8],
        'manufacturer_side_torque_kgf_cm':[7,10],'device_side_translate':[-20.5,0,42.5],
        'rear_thread_not_modeled':True,'device_face_source':'+X'}.items():
        if p.get(key)!=value:changed[key]=p.get(key)
    if changed:raise ValueError(f'Review fixed drawing annotations after changed CAD: {changed}')
    if p.get('units')!='mm' or not p.get('revision','').startswith('N2'):raise ValueError('N2 millimetre parameters required')
    cp=HERE/'references/research/catalog_bom.json';cat=json.loads(cp.read_text(encoding='utf-8-sig'))
    selected={r['item_id']:r['part_number'] for r in cat['items']}
    for ident,pn in {'H01':'91294A190','H02':'98688A142','H03':'90576A102'}.items():
        if selected.get(ident)!=pn:raise ValueError(f'Review changed catalog {ident}')
    checks=[]
    if final:
        for name in ['cad_verification.json','manufacturing_verification.json']:
            f=HERE/'quality'/name;r=json.loads(f.read_text(encoding='utf8'))
            if r.get('status')!='PASS':raise ValueError(f'Final verification required: {name}')
            if r.get('params_sha256') and r['params_sha256']!=hashlib.sha256(pp.read_bytes()).hexdigest():raise ValueError(f'Stale check: {name}')
            checks.append((f,r))
        engineering=json.loads((HERE/'references/engineering/engineering_results.json').read_text(encoding='utf8'))
        required={'plate_thickness_mm':6,'tab_length_mm':44,'device_force_N':125,'package_force_N':140,
          'head_seat_effective_OD_min_mm':7.6,'straight_ligament_accept_min_mm':3.9,
          'local_proof_elastic_limit_mm':.3,'combined_proof_elastic_limit_mm':.4,'residual_limit_mm':.1}
        if any(abs(engineering['inputs'][k]-v)>1e-7 for k,v in required.items()):raise ValueError('Review changed engineering annotations')
        if round(engineering['plate']['minimum_frame_yield_factor'],2)!=3.33 or round(engineering['contacts']['seat_pressure_factor3_yield_ratio'],2)!=1.84:raise ValueError('Review changed frame/contact ratios')
        if engineering['plate']['contact_status']!='HOLD':raise ValueError('Review changed contact release status')
    return p,cat,pp,cp,checks


def stud_points(p):
    return [(x,y) for x in [-p['stud_pitch_x']/2,p['stud_pitch_x']/2]
      for y in [p['stud_pattern_center_y']-p['stud_pitch_y']/2,p['stud_pattern_center_y']+p['stud_pitch_y']/2]]


def outline_vertices(p):
    a,w=p['spine_width']/2,p['plate_width']/2;h=p['tab_length']/2;rear,front=p['tab_stations_y'];lo,hi=p['plate_fan_end_y'],p['plate_terminal_end_y']
    return [(-a,lo),(a,lo),(a,rear-h),(w,rear-h),(w,rear+h),(a,rear+h),(a,front-h),(w,front-h),(w,hi),(-w,hi),(-w,front-h),(-a,front-h),(-a,rear+h),(-w,rear+h),(-w,rear-h),(-a,rear-h)]


def outline_commands(p):
    """Tangent quarter circles represented by standard cubic Beziers (<0.002 mm error).

    Authoring geometry only; exact machining contours are exported by model.py.
    """
    vv=outline_vertices(p);r=p['corner_radius'];k=4*(math.sqrt(2)-1)/3;arcs=[]
    for i,(x,y) in enumerate(vv):
        prev,nxt=vv[i-1],vv[(i+1)%len(vv)];l=math.dist(prev,(x,y));rr=math.dist(nxt,(x,y));u=((x-prev[0])/l,(y-prev[1])/l);v=((nxt[0]-x)/rr,(nxt[1]-y)/rr)
        inn=(x-r*u[0],y-r*u[1]);out=(x+r*v[0],y+r*v[1]);c1=(inn[0]+k*r*u[0],inn[1]+k*r*u[1]);c2=(out[0]-k*r*v[0],out[1]-k*r*v[1]);arcs.append((inn,c1,c2,out))
    commands=[('M',arcs[0][0])]
    for i,(inn,c1,c2,out) in enumerate(arcs):
        if i:commands.append(('L',inn))
        commands.append(('C',c1+c2+out))
    return commands+[('Z',())]


def svg_outline(s,p,px,py,fill='#f1f5f7'):
    d=[]
    for op,points in outline_commands(p):
        d.append(op+' '.join(f'{px(points[i]):.4f},{py(points[i+1]):.4f}' for i in range(0,len(points),2)))
    s.add(f'<path d="{" ".join(d)}" fill="{fill}" stroke="#142c3b" stroke-width="1.6"/>')


def plan_svg(path,p):
    s=SVG();s.txt(35,43,'M01 / NARROW SIDE ADAPTER WITH FOUR LOCAL EARS','title');s.txt(35,78,'Dimensions in mm after finish. Same plan orientation in both views; underside features are projected through.','small')
    k=1.8;py=lambda y:180+(16.2-y)*k
    for center,caption,csk in [(280,'CONTACT-SIDE PLAN',False),(620,'UNDERSIDE FEATURE PLAN',True)]:
        px=lambda x:center+x*k
        s.txt(center,102,caption,'bold','middle');svg_outline(s,p,px,py)
        for typ,pts,dia in [('H',p['housing_points'],4.5),('S',stud_points(p),3.8)]:
            for i,(x,y) in enumerate(pts,1):
                s.circle(px(x),py(y),dia/2*k)
                if csk and typ=='H':s.circle(px(x),py(y),8.1/2*k)
                s.txt(px(x)+(9 if typ=='H' else 0),py(y)+(25 if typ=='H' else -14),f'{typ}{i}','small','start' if typ=='H' else 'middle')
        s.line(px(2.3),164,px(2.3),770,'#7892a1','12 4 2 4')
        s.txt(center,782,'FAN END / C / Y=-300.6','small','middle')
    s.dimh(280-36*k,280+36*k,180,145,'72.00 +/-0.10 MAX')
    s.dimv(py(16.2),py(-300.6),280-22.5*k,142,'316.80 +/-0.10')
    s.dimh(280-22.5*k,280+22.5*k,465,495,'45.00 +/-0.10 SPINE')
    s.rect(206,394,29,30,fill='white');s.txt(220,416,'B','bold','middle');s.line(235,409,239.5,409)
    s.txt(790,132,'BASIC COORDINATES FROM B / C','bold')
    for x,lab in [(800,'ID'),(930,'X from B'),(1104,'Y from C'),(1315,'BORE')]:s.txt(x,175,lab,'bold')
    rows=[('H1',24.8,294.8,'DIA4.5'),('H2',24.8,42.8,'DIA4.5'),('S1',-6,42.8,'DIA3.8'),('S2',-6,294.8,'DIA3.8'),('S3',51,42.8,'DIA3.8'),('S4',51,294.8,'DIA3.8')]
    for i,row in enumerate(rows):
        for x,value in zip([800,930,1104,1315],row):s.txt(x,218+i*37,f'{value:.3f}' if isinstance(value,(int,float)) else value)
    notes=['H1-H2: DIA4.5 +0.10/0 THRU; 90-degree CSK FROM A.',
      'S1-S4: DIA3.8 +0.10/0 THRU.',
      'All bore axes: position DIA0.10 | A | B | C, RFS.',
      'A = underside seating plane, Z0.',
      'B = SPINE left tangent plane, X=-22.5.',
      'C = fan-end tangent plane, Y=-300.6.',
      'Negative stud X coordinates are intentional.',
      'B is not the outer tab edge at X=-36.',
      '16 profile corners: R4 +/-0.25, convex AND concave.',
      'External upper/lower rims: 0.4 x45-degree break.',
      'No fan pockets, stud-base reliefs, pads or grease.']
    for i,line in enumerate(notes):s.txt(780,480+i*28,line,'small')
    for i,line in enumerate(['MATERIAL: certified 6061-T6/T651, yield >=240 MPa. Face 1/4-in or thicker stock to 6.00 +/-0.05.',
      'FINISH: clear MIL-DTL-5541 Type II Class 3 conversion; all fit dimensions apply after finish.',
      'A flatness 0.10; upper contact plane parallel 0.10 to A. Bore-rim deburr <=0.10.',
      'PRELIMINARY: verify both actual M4 threads and hole positions before final boring; never force alignment.']):s.txt(35,829+i*33,line,'bold' if i==3 else 'small')
    s.save(path)


def detail_svg(path,p):
    s=SVG();s.txt(35,43,'M01 / LOCAL EAR GEOMETRY AND M4 HEAD SEAT','title');s.txt(35,78,'Front station shown. All coordinates are in the page 2 frame; fillet tangent dimensions follow the basic profile.','small')
    k=6;px=lambda x:315+x*k;py=lambda y:260+(-y-5.8)*k
    s.add('<defs><clipPath id="tab"><rect x="70" y="90" width="495" height="355"/></clipPath></defs><g clip-path="url(#tab)">');svg_outline(s,p,px,py);s.add('</g>')
    for ident,x,dia in [('S2',-28.5,3.8),('H1',2.3,8.1),('S4',28.5,3.8)]:
        s.circle(px(x),py(-5.8),dia/2*k);s.txt(px(x),py(-5.8)-35,ident,'bold','middle')
    s.dimh(px(-28.5),px(28.5),py(-5.8),479,'57.00 BASIC STUD PITCH')
    s.dimv(py(16.2),py(-27.8),px(36),606,'44.00 +/-0.10 TAB')
    for i,line in enumerate(['TAB / PROFILE CONTROL',
      '72 max width: outer tabs X=-36 /+36.',
      '45 spine: edges X=-22.5 /+22.5.',
      'Local projection beyond spine: 13.50 REF per side.',
      'Front tab Y=-27.8..+16.2; centre Y=-5.8.',
      'Rear tab Y=-279.8..-235.8; centre Y=-257.8.',
      'Both M4 rows and both tab centres: 252.00 BASIC.',
      '16 R4 contour corners; use matching STEP/DXF.',
      'Two-sided CNC; flat, supported workholding.',
      'Preserve the case contact surface at each station.']):s.txt(750,126+i*31,line,'bold' if i==0 else 'small')
    s.txt(35,514,'M4 SEAT / PARTIAL NOMINAL SECTION THROUGH HOLE AXIS','bold')
    k=22;px=lambda x:320+x*k;pz=lambda z:741-z*k
    points=[(-12,0),(-4.05,0),(-2.25,1.8),(-2.25,5.9),(-2.35,6),(-12,6)]
    for q in [points,[(-x,z) for x,z in reversed(points)]]:
        d=' '.join(('M' if i==0 else 'L')+f'{px(x)},{pz(z)}' for i,(x,z) in enumerate(q))+' Z';s.add(f'<path d="{d}" fill="#dce8ef" stroke="#142c3b" stroke-width="2"/>')
    s.line(320,583,320,785,'#7892a1','12 4 2 4');s.dimh(px(-4.05),px(4.05),741,802,'DIA8.1 REF / 90-degree CSK')
    s.dimv(pz(6),pz(0),px(12),660,'6.00 +/-0.05');s.rect(31,726,29,30,fill='white');s.txt(45,748,'A','bold','middle')
    notes=['RECEIVED HEAD / MACHINED SEAT',
      'Head flush to 0.10 BELOW A; no rocking.',
      'Effective conical seat diameter >=7.60.',
      'Actual straight bore ligament >=3.90.',
      'Nominal straight 4.10 after 0.10 top deburr.',
      'Screen mouth <=8.20; included angle >=89 deg.',
      'Screen throat 4.4..4.6; page 2 bore size governs.',
      'No washer under the M4 countersunk head.']
    for i,line in enumerate(notes):s.txt(750,543+i*31,line,'bold' if i==0 else 'small')
    for i,line in enumerate(['Gauge actual M4 x10 DIN 7991 screws: catalog head DIA8 x2.3, 2.5 mm hex. CAD head is an ideal reference proxy.',
      'Nominal intrusion 10 +0.05 -6.00 =4.05. Received-stack acceptance 3.75-4.35; manufacturer hard maximum 5.00.',
      'Rear M4 thread is NOT in the source STEP. Physical rear-thread and head/seat qualification are mandatory.']):s.txt(35,861+i*33,line,'bold' if i==2 else 'small')
    s.save(path)


def embed_svg(c,path,x,y,w,h):
    d=svg2rlg(str(path));sc=min(w/d.width,h/d.height);d.scale(sc,sc);renderPDF.draw(d,c,x+(w-d.width*sc)/2,y+(h-d.height*sc)/2)


def template_page(c,p):
    title(c,'1:1 side-interface fit template / print actual size',6)
    mm=72/25.4;px=lambda x,y:(65-y)*mm;py=lambda x,y:(148.5+x)*mm
    path=c.beginPath()
    for op,v in outline_commands(p):
        q=[component for i in range(0,len(v),2) for component in (px(v[i],v[i+1]),py(v[i],v[i+1]))]
        if op=='M':path.moveTo(*q)
        elif op=='L':path.lineTo(*q)
        elif op=='C':path.curveTo(*q)
        else:path.close()
    c.setStrokeColor(INK);c.setLineWidth(.45);c.drawPath(path,stroke=1,fill=0)
    c.setStrokeColor(TEAL);c.setDash(5,3)
    for x in [-20.5,20.5]:c.line(px(x,0),py(x,0),px(x,-300.6),py(x,-300.6))
    c.setDash();c.setStrokeColor(INK)
    for typ,points,dia in [('H',p['housing_points'],4.5),('S',stud_points(p),3.8)]:
        for i,(x,y) in enumerate(points,1):
            xx,yy=px(x,y),py(x,y);c.circle(xx,yy,dia/2*mm,fill=0,stroke=1);c.line(xx-4*mm,yy,xx+4*mm,yy);c.line(xx,yy-4*mm,xx,yy+4*mm);text(c,xx+5*mm,yy+3*mm,f'{typ}{i}',40,9,bold=True)
    text(c,48*mm,198*mm,'TERMINAL END / FRONT EARS',330,10,bold=True,color=TEAL);text(c,290*mm,198*mm,'FAN END / DATUM C',290,10,bold=True,color=TEAL)
    text(c,52*mm,101*mm,'Dashed lines: 41 mm side-case width. Outline is the local-ear adapter, not the reference main panel.',930,9.7)
    for x in [65,165]:c.line(x*mm,80*mm,x*mm,84*mm)
    c.line(65*mm,82*mm,165*mm,82*mm);text(c,89*mm,86*mm,'100.00 mm',190,11,bold=True,color=TEAL)
    for y in [99,199]:c.line(386*mm,y*mm,390*mm,y*mm)
    c.line(388*mm,99*mm,388*mm,199*mm);c.saveState();c.translate(394*mm,149*mm);c.rotate(90);c.setFont('Helvetica-Bold',11);c.setFillColor(TEAL);c.drawCentredString(0,0,'100.00 mm');c.restoreState()
    text(c,33,159,'PRINT A3 AT 100% / ACTUAL SIZE; disable fit-to-page. Measure BOTH 100 mm calibration bars before use. A4 shrink-to-fit is invalid.',1125,10.5,bold=True,color=AMBER)
    text(c,33,122,'Check the two received M4 stations before final drilling/countersinking. The fixed conical seats cannot absorb the full OEM +/-0.5 mm general tolerance. Check the actual rear thread separately; the STEP shows an open DIA5 hole.',1125,10)
    text(c,33,79,'Template axes follow the coordinate table: H1 is terminal-end, H2 fan-end; S1 rear-left, S2 front-left, S3 rear-right, S4 front-right. Do not drill through an installed PSU.',1125,9.5)
    c.showPage()


def catalog_rows(cat):
    rows=[];links=[]
    for r in cat['items']:
        pack,price=r.get('pack_qty'),r.get('pack_price_usd');buy=f'{pack} / ${price}' if pack is not None and price is not None else 'Quote required'
        rows.append([r['item_id'],r['part_number'],str(r.get('quantity',r.get('qty','AR'))),r['description'],buy]);links.append(r.get('url',''))
    return rows,links


def make_pdf(out,p,cat,plan,detail,checks):
    pdf=out/'MeanWell_N2_drawing_package.pdf';temp=Path('C:/b210work/nsp1600_side/documents');temp.mkdir(parents=True,exist_ok=True);stage=temp/pdf.name
    c=canvas.Canvas(str(stage),pagesize=(W,H));c.setTitle('Mean Well NSP-1600 narrow-side local-ear adapter / N2 preliminary prototype');c.setAuthor('Parametric CAD engineering draft')
    product=HERE/'references/product';views=HERE/'references/views'
    title(c,'Mean Well NSP-1600 / narrow side and local ears',1)
    picture(c,product/'assembled_hero.png',33,317,738,408)
    box(c,792,506,366,219,'COMPACT FOOTPRINT / SINGLE MACHINED PART',
      'The PSU seats on its original +X narrow side. Two designated M4 side stations attach it to a 45 mm spine with four local ears. Four M3 FPE studs connect the adapter to the main panel.\nMaximum width is 72 mm at the ears, versus 125 mm for N1. Height above the panel grows from 46 to 91 mm.',10.3)
    box(c,792,317,366,173,'PHYSICAL RELEASE HOLDS',
      'Confirm the unmodeled rear M4 thread. Conical-seat contact is on HOLD: the 3x pressure sensitivity gives yield ratio 1.84.\nThe published power/ambient curve is horizontal. Side-orientation output derating and cooling require manufacturer guidance or thermal qualification.',10.1)
    table(c,['Feature','Final N2 geometry / basis','Required acceptance'],[
      ['Adapter M01','316.8 long; 45 spine; 72 maximum width; 6.00 thick','CNC 6061-T6/T651; all sixteen contour corners R4'],
      ['PSU side mounting','H1(2.3,-5.8), H2(2.3,-257.8); 252 mm pitch','M4 x10; actual penetration 3.75-4.35, hard max 5.00'],
      ['Panel attachment','Four M3 FPE load studs; 57 x252 mm pattern','Actual anchor capacity, seat flushness and full nut engagement'],
      ['Load-path screening','1.8 kg PSU; 125 N device /140 N package and 5 N m couple','Frame screen factor 3.33; joint/contact qualification pending']],33,294,[187,386,552],size=9.5,minh=35)
    count='; '.join(f"{len(q.get('checks',[]))} {('nominal CAD' if 'cad_verification' in f.name else 'manufacturing geometry')} checks" for f,q in checks)
    text(c,39,97,count+' passed. These are digital checks, not proof of housing threads, conical contact, FPE strength or cooling. No fabrication or physical test occurred.',1110,9.7,bold=True,color=AMBER);c.showPage()
    title(c,'M01 / Dimensioned plans and edge-datum coordinates',2,'MW-NSP-M01 / QTY1');embed_svg(c,plan,30,58,W-60,H-146);c.showPage()
    title(c,'M01 / Local tab profile and M4 countersink section',3,'MW-NSP-M01 / QTY1');embed_svg(c,detail,30,58,W-60,H-146);c.showPage()
    title(c,'Actual side interface, screw stack and FPE placement',4)
    picture(c,views/'section_front_side_mount_front.png',35,458,529,252);picture(c,views/'section_rear_side_mount_front.png',35,198,529,239)
    text(c,41,726,'FRONT M4 / SOURCE EXTRUSION',515,10,bold=True,color=TEAL);text(c,41,445,'REAR M4 / SOURCE THREAD ABSENT',515,10,bold=True,color=TEAL)
    text(c,601,719,'RECEIVED SCREW AND SEAT CONTROL',551,13,bold=True,color=TEAL)
    y=text(c,601,690,'Two McMaster 91294A190 M4 x0.7 x10 DIN 7991 flat-head screws, 2.5 mm hex. Overall length includes the head. Catalog head DIA8 x2.3; the CAD cone is only an ideal reference proxy.',548,10.3)
    text(c,601,y-15,'P = length + inward head recess - finished plate thickness. Nominal 10 +0.05 -6.00 =4.05 mm. Gauge actual P=3.75-4.35; never exceed the manufacturer 5.00 mm intrusion limit. Confirm actual threads and complete seating without rocking.',548,10.3)
    box(c,594,440,564,118,'MANUFACTURER LIMITS / UNMODELED REAR FEATURE',
      'Side mounting recommendation: 7-10 kgf cm (0.6865-0.9807 N m). Qualify the actual countersunk seat, finish and locking procedure before use.\nRear source geometry is an open DIA5 hole, not a modeled M4 thread. Do not add a nut/insert or modify the PSU by default.',9.7)
    table(c,['FPE interface','Nominal location / requirement'],[
      ['Stud pattern','57 x252 mm rectangular pitch; S1(-28.5,-257.8), S2(-28.5,-5.8), S3(28.5,-257.8), S4(28.5,-5.8)'],
      ['From adapter B/C','(-6,42.8),(-6,294.8),(51,42.8),(51,294.8); negative X intentional'],
      ['Location proposal','Adapter position DIA0.10; FPE stud position DIA0.30, supplier confirmation required.'],
      ['12 mm stud stack','6 mm plate +0.55 washer +4 mm nut gives 1.45 nominal tail. Actual full nylon +>=1.00 complete thread beyond nut.']],595,417,[156,407],size=9.3,minh=38)
    text(c,601,194,'5.5 AF socket, OD<=10, internal clear depth>=10; reserve 60 mm axial tool access and 20 mm service lift. Keep studs/bases flush at the panel seating face.',547,9.7,bold=True)
    text(c,41,182,'Orange=new M4 proxy; blue=adapter; green=source PSU; grey=reference panel. Source thread form and hardware capacity are not represented.',527,9,leading=12)
    text(c,39,137,'Reference panel only: 92 x340 x6, centred Y=-142.2. Its lower-left stud coordinates are (17.5,54.4),(17.5,306.4),(74.5,54.4),(74.5,306.4). Final panel/support design remains unconfirmed.',1110,9.8)
    text(c,39,85,'Front DIA4 probe reaches source output-blade material 7.50 mm inward. Rear source is empty through the width. Neither observation overrides the 5 mm manufacturer limit or qualifies electrical clearance.',1110,9.5,bold=True,color=AMBER);c.showPage()
    title(c,'Bill of materials, assembly and prototype release checks',5)
    rows,links=catalog_rows(cat);custom=[['M01','Custom drawing','1','316.8 long x45 spine /72 at ears x6.00 mm; machined 6061-T6/T651; clear conversion','Quote required']]
    bot=table(c,['ID','Catalog number / link','Qty','Specification','Purchase reference'],custom+rows,33,723,[53,163,44,682,183],size=9,minh=32,links=['']+links)
    if bot<450:raise ValueError(f'BOM exceeds page budget: {bot}')
    text(c,39,bot-21,'Initial McMaster packs: $20.64, observed 2026-09-08. Custom adapter and FPE panel/studs require quotes. No purchase made.',1110,9.5)
    text(c,39,437,'INSTALLATION / ROUTINE REMOVAL',540,13,bold=True,color=TEAL);y=408
    for line in ['1. Disconnect power and secure against reconnection. Identify the original +X side; gauge both actual M4 features, especially the unmodeled rear thread, before final machining.',
      '2. Verify plate flatness, actual screw head seats and 3.75-4.35 mm penetration. Dry-fit on casing metal: no proud factory hardware, forced alignment, bowing or cover loading.',
      '3. Attach using the two M4 screws under a qualified procedure. Lower the complete PSU/adapter over four verified FPE studs; fit washers and locknuts with full nylon engagement and >=1 mm complete thread tail.',
      '4. Connect guarded power/control wiring with independent strain relief and FG earth. Preserve intake/exhaust and actual lug/tool/bend space. Side-orientation derating is a release hold.',
      '5. Power down/disconnect for removal. Support the PSU, remove four stud nuts/washers and lift>=20 mm. The M4 underside screws are accessible on the bench. Keep original covers and hardware intact.']:
        y=text(c,39,y,line,541,9.5,leading=13.4)-10
    text(c,613,437,'MECHANICAL AND THERMAL QUALIFICATION',540,13,bold=True,color=TEAL);y=408
    for label,body in [('FIT','Record actual two-hole axes, thread type/depth, screw projections, conical seats, casing contact, panel flatness and tool access. Use the 1:1 template only after checking both calibration bars.'),
      ('LOAD PATH','Frame-only yield factor 3.33; 3x seat-pressure sensitivity 1.84. Qualify joints and the paired screw/toe fixture before proof. Fixture limits: <=0.30 mm local, <=0.40 mm combined and <=0.10 mm residual. Use the engineering load path, not an isolated 1250 N bolt load.'),
      ('SIDE-ORIENTATION COOLING','Confirm permitted output current or test the intended input/load/ambient with manufacturer guidance. Measure exhaust, case and actual nylon nut temperatures. Published horizontal derating cannot be transferred to this orientation.'),
      ('SERVICE / ELECTRICAL','Check fan paths, actual cable strain relief and FG protective earth; adapter contact is not a qualified earth bond. Complete the prototype plan and removal cycles before any application release.')]:
        y=text(c,613,y,label,537,10,bold=True,color=TEAL)-2;y=text(c,613,y,body,537,9.5,leading=13.4)-13
    text(c,39,88,'PRELIMINARY ONLY: stationary indoor basis. Rear thread, case/head/toe/preload, FPE anchorage and side-orientation thermal capacity remain unqualified.',1111,9.5,bold=True,color=AMBER);c.showPage()
    template_page(c,p);c.save();shutil.copyfile(stage,pdf);return pdf,stage


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--render',action='store_true');ap.add_argument('--svg-only',action='store_true');ap.add_argument('--out',type=Path,default=OUT);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);p,cat,pp,cp,checks=load_inputs(not args.svg_only)
    plan=args.out/'MW_NSP_M01_plans_N2.svg';detail=args.out/'MW_NSP_M01_tabs_section_N2.svg';plan_svg(plan,p);detail_svg(detail,p)
    if args.svg_only:print(plan);print(detail);return
    pdf,stage=make_pdf(args.out,p,cat,plan,detail,checks)
    sources=[Path(__file__),pp,cp,HERE/'DESIGN.md',HERE/'ENGINEERING_NOTE.md',HERE/'references/engineering/engineering_results.json']+[f for f,r in checks]+sorted((HERE/'references/product').glob('*.png'))+[HERE/'references/views/section_front_side_mount_front.png',HERE/'references/views/section_rear_side_mount_front.png']
    manifest={'revision':REV,'status':'PENDING ROOT AND VISUAL REVIEW; PRELIMINARY SIDE-MOUNT PROTOTYPE ONLY','pdf':pdf.name,'pages':PAGE_COUNT,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
      'sources':[{'path':str(f.relative_to(HERE)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sources],
      'template_scale':'1 mm=72/25.4 PDF points. Rotated+90 degrees; two100 mm bars. Print actual size. R4 quarter-circle Bezier approximation error<0.002 mm; machining contours come from model.py.'}
    (args.out/'drawing_source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    if args.render:
        qa=stage.parent/'qa';qa.mkdir(exist_ok=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(stage),str(qa/'page')],check=True);dest=args.out/'qa';dest.mkdir(exist_ok=True)
        for f in sorted(qa.glob('page-*.png')):shutil.copyfile(f,dest/f.name)
    print(pdf)


if __name__=='__main__':main()


