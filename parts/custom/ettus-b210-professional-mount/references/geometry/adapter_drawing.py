"""Dimensioned SVG manufacturing drawing generated from adapter_params.json."""
from pathlib import Path
import sys,html
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from vertical_adapter import PARAMS as p,adapter_metrics
m=adapter_metrics();els=[]
def line(x1,y1,x2,y2,cls='line'):els.append(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
def text(x,y,s,size=3.2,anchor='start',rot=None,bold=False):
    tr=f' transform="rotate({rot} {x} {y})"' if rot else ''
    els.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{700 if bold else 400}"{tr}>{html.escape(str(s))}</text>')
def dimh(x1,x2,y,fromy,label):
    for x in [x1,x2]:line(x,fromy,x,y+2,'dim')
    els.append(f'<path class="dim" d="M{x1},{y} H{x2}" marker-start="url(#arrow)" marker-end="url(#arrow)"/>');text((x1+x2)/2,y-1.8,label,3,'middle')
def dimv(y1,y2,x,fromx,label):
    for y in [y1,y2]:line(fromx,y,x-2,y,'dim')
    els.append(f'<path class="dim" d="M{x},{y1} V{y2}" marker-start="url(#arrow)" marker-end="url(#arrow)"/>');text(x-2,(y1+y2)/2,label,3,'middle',-90)
def datum(x,y,name,dx=14,dy=0):
    line(x,y,x+dx,y+dy,'dim');els.append(f'<circle cx="{x}" cy="{y}" r="0.9" fill="#111"/>')
    xx=x+dx;yy=y+dy;els.append(f'<rect x="{xx-3}" y="{yy-3}" width="6" height="6" fill="white" stroke="#111" stroke-width="0.35"/>');text(xx,yy+1.2,name,3.5,'middle',bold=True)

# A3 landscape, true mm coordinates; user may print reduced but must use dimensions.
els.append('<rect x="8" y="8" width="404" height="281" fill="none" stroke="#111" stroke-width="0.5"/>')
text(15,18,'B210 M05  /  UPRIGHT ADAPTER',5,bold=True)
text(405,18,'P1  |  PROTOTYPE — PHYSICAL VALIDATION REQUIRED',3,'end',bold=True)
line(8,23,412,23)
ox=58;oy=222;t=p['web_t'];ft=p['foot_t'];r=p['inside_radius'];h=p['overall_height'];tip=p['foot_tip_x']
path=f'M{ox-t},{oy} H{ox+tip} V{oy-ft} H{ox+r} A{r},{r} 0 0 1 {ox},{oy-ft-r} V{oy-h} H{ox-t} Z'
els.append(f'<path d="{path}" class="outline"/>')
text(90,247,'SIDE / XZ',3.2,'middle',bold=True)
dimv(oy-h,oy,30,ox-t,str(int(h)))
dimh(ox-t,ox+tip,237,oy,str(int(t+tip)))
dimh(ox-t,ox,34,oy-h,'8.00 ±0.05')
line(ox+1.8,oy-10,90,199,'dim');text(91,199,'R6',3.3)
line(120,oy-4,135,202,'dim');text(134,199,'8.00 ±0.05',3.1,'middle')
datum(ox+27,oy,'A',0,6)
datum(ox,130,'B',15,0)
for z in p['web_hole_z']:
    yy=oy-z
    line(ox-t-3,yy,ox+3,yy,'center')
    for dd in [-p['clearance_hole_d']/2,p['clearance_hole_d']/2]:line(ox-t,yy+dd,ox,yy+dd,'hidden')

# Web face viewed along -X. Datum C is the left finished side plane Y=-18.
cx=182;w=p['strip_width'];cr=p['free_corner_radius'];xl=cx-w/2;xr=cx+w/2;yt=oy-h
els.append(f'<path class="outline" d="M{xl},{oy} V{yt+cr} Q{xl},{yt} {xl+cr},{yt} H{xr-cr} Q{xr},{yt} {xr},{yt+cr} V{oy} Z"/>')
for z in p['web_hole_z']:
    yy=oy-z;els.append(f'<circle class="outline" cx="{cx}" cy="{yy}" r="{p["clearance_hole_d"]/2}"/>');line(cx-5,yy,cx+5,yy,'center')
line(cx,oy-h-4,cx,oy+3,'center');line(xl,oy-ft-r,xr,oy-ft-r,'line');line(xl,oy-ft,xr,oy-ft,'line')
dimh(xl,xr,34,yt,'36');dimh(xl,cx,236,oy,'18 ±0.15')
dimv(oy-p['web_hole_z'][0],oy,215,xr,'26 ±0.15')
dimv(oy-p['web_hole_z'][1],oy,228,xr,'166 ±0.15')
datum(xl,130,'C',-13,0)
text(cx,247,'WEB FACE / YZ',3.2,'middle',bold=True)

# Foot top view, with free end corner radii shown.
fx=295;fy=83;fl=fx-t;fr=fx+tip;fb=fy+w/2;fa=fy-w/2
els.append(f'<path class="outline" d="M{fl},{fa} H{fr-cr} Q{fr},{fa} {fr},{fa+cr} V{fb-cr} Q{fr},{fb} {fr-cr},{fb} H{fl} Z"/>')
line(fx,fa,fx,fb);line(fx+r,fa,fx+r,fb)
for x in p['foot_hole_x']:
    xx=fx+x;els.append(f'<circle class="outline" cx="{xx}" cy="{fy}" r="{p["clearance_hole_d"]/2}"/>');line(xx,fy-5,xx,fy+5,'center')
line(fl-3,fy,fr+3,fy,'center')
dimh(fx,fx+p['foot_hole_x'][0],115,fb,'20 ±0.15')
dimh(fx,fx+p['foot_hole_x'][1],127,fb,'55 ±0.15')
dimv(fa,fb,373,fr,'36')
dimv(fa,fy,386,fr,'18 ±0.15')
text(330,52,'FOOT / XY',3.2,'middle',bold=True)
text(330,138,'All four holes Ø5.5 +0.1/−0 THRU',3.4,'middle',bold=True)
text(245,151,'MATERIAL / PROCESS',3.5,bold=True)
notes=[
 '6061-T6 aluminum, certified plate; quantity 2 identical.',
 'One-piece milled profile, 36 mm finished width.',
 'R6 is a machined inside root, not a formed bend.',
 'Suggested sawn stock: 75 × 180 × 38.1 mm.',
 'Profile DXF is the XZ outline; no sheet-metal flat.',
 'Rough saw/waterjet/mill; finish with Ø12 endmill.',
 'Shop to plan reach and workholding for 36 mm depth.',
 'Drill web and foot in two orthogonal setups.',
 'Four free top/foot corners R3 across the width.',
 'Deburr and break other accessible edges 0.2–0.5.',
 'Black sulfuric anodize 10–15 µm; sizes after finish.',
 'General ±0.2; holes ±0.15; web/foot 8.00 ±0.05.',
 'A: foot underside. B: web mating face. C: side face.',
 'B perpendicular to A within 0.1 over full height.',
 'Hold B flat within 0.1; hold A flat within 0.1.',
 'Web/foot thickness minimum 7.95 after finish.',
 'Hole centers Y18 from C. Do not scale.'
]
for i,s in enumerate(notes):text(245,158+5*i,s,2.75)

line(8,260,412,260);text(15,267,'ASSEMBLY: bracket stations Y = −66.947 / +73.053 (140 pitch). Install foot screws before fitting the cradle.',3.0)
line(8,273,412,273)
for x in [245,305,355]:line(x,273,x,289)
text(15,280,'B210 — MACHINED UPRIGHT SUPPORT',4,bold=True);text(15,286,'M05  •  MM  •  CAD and dimensions govern  •  Unqualified prototype',3)
text(250,280,'SCALE',2.5);text(250,286,'1:1 at A3',3.2)
text(310,280,'REV / DATE',2.5);text(310,286,'P1 / 2026-09-08',3.2)
text(360,280,'SHEET',2.5);text(360,286,'1 OF 1',3.2)
svg='''<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#333"/></marker></defs><style>text{font-family:Arial,sans-serif;fill:#111}.line{stroke:#111;stroke-width:.35}.outline{stroke:#111;stroke-width:.5;fill:none}.dim{stroke:#555;stroke-width:.2;fill:none}.center{stroke:#627581;stroke-width:.2;stroke-dasharray:4,1,1,1}.hidden{stroke:#555;stroke-width:.2;stroke-dasharray:2,1}</style>'''+''.join(els)+'</svg>'
out=HERE.parents[1]/'drawings';out.mkdir(exist_ok=True)
(out/'B210_M05_adapter_P1.svg').write_text(svg,encoding='utf-8')
print(out/'B210_M05_adapter_P1.svg')
