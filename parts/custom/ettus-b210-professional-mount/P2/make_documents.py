"""Regenerate P2 dimensioned shop PDF and actual-CAD manufacturing DXFs. Catalog BOM is loaded from references/catalog_bom.json."""

from pathlib import Path

import argparse, csv, io, json, re

import cadquery as cq

import ezdxf

from reportlab.pdfgen import canvas

from reportlab.lib import colors

from reportlab.lib.pagesizes import A3, landscape

from reportlab.graphics import renderPDF

from svglib.svglib import svg2rlg

import model as m

HERE=Path(__file__).resolve().parent

W,H=landscape(A3)

INK=colors.HexColor('#182937')

BLUE=colors.HexColor('#00667B')

def lines(c, x, y, text, width=80, size=10, leading=15):
    import textwrap
    c.setFillColor(INK); c.setFont('Helvetica',size)
    for para in text.split('\n'):
        for line in textwrap.wrap(para,width=width,break_long_words=False) or ['']:
            c.drawString(x,y,line); y-=leading
    return y

def svg_view(c,shape,x,y,w,h,projection=(0,0,1)):
    svg=cq.exporters.getSVG(shape,opts=dict(width=w,height=h,marginLeft=55,marginTop=45,
                 projectionDir=projection,showAxes=False,showHidden=True,strokeWidth=.5))
    drawing=svg2rlg(io.BytesIO(svg.encode()))
    # svglib interprets SVG px as 0.75pt; the CAD annotation transform uses pt.
    drawing.scale(w/drawing.width,h/drawing.height)
    renderPDF.draw(drawing,c,x,y)
    match=re.search(r'scale\(([-\d.e]+),\s*([-\d.e]+)\)\s*translate\(([-\d.e]+),\s*([-\d.e]+)\)',svg)
    s,_,tx,ty=map(float,match.groups())
    return lambda xx,yy:(x+s*(xx+tx),y+h+s*(yy+ty))

def dim(c,pt,a,b,offset,label,vertical=False):
    c.setStrokeColor(BLUE);c.setFillColor(BLUE);c.setLineWidth(.6)
    ax,ay=pt(*a);bx,by=pt(*b)
    if vertical:
        xx=min(ax,bx)+offset
        c.line(ax,ay,xx,ay);c.line(bx,by,xx,by);c.line(xx,ay,xx,by)
        for yy in [ay,by]: c.line(xx-3,yy-3,xx+3,yy+3)
        c.saveState();c.translate(xx-6,(ay+by)/2);c.rotate(90);c.setFont('Helvetica',10);c.drawCentredString(0,0,label);c.restoreState()
    else:
        yy=min(ay,by)+offset
        c.line(ax,ay,ax,yy);c.line(bx,by,bx,yy);c.line(ax,yy,bx,yy)
        for xx in [ax,bx]: c.line(xx-3,yy-3,xx+3,yy+3)
        c.setFont('Helvetica',10);c.drawCentredString((ax+bx)/2,yy+5,label)

def table(c, headers, rows, x,y,widths,rowh=28,size=9):
    c.setFillColor(BLUE);c.rect(x,y-rowh,sum(widths),rowh,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('Helvetica-Bold',size)
    xx=x
    for h,w in zip(headers,widths):c.drawString(xx+6,y-rowh+10,h);xx+=w
    y-=rowh
    for ri,row in enumerate(rows):
        c.setFillColor(colors.HexColor('#EDF2F4') if ri%2==0 else colors.white)
        c.rect(x,y-rowh,sum(widths),rowh,fill=1,stroke=0)
        c.setFillColor(INK);c.setFont('Helvetica',size);xx=x
        for txt,w in zip(row,widths):c.drawString(xx+6,y-rowh+10,str(txt));xx+=w
        y-=rowh
    return y

def title(c,title,page,part='B210 / P2'):
    c.setFillColor(INK);c.rect(0,H-70,W,70,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('Helvetica-Bold',21);c.drawString(35,H-40,title)
    c.setFont('Helvetica',8);c.drawRightString(W-35,H-58,'PRELIMINARY - PROTOTYPE MANUFACTURE / NOT QUALIFIED')
    c.setStrokeColor(INK);c.line(35,52,W-35,52);c.setFillColor(INK);c.setFont('Helvetica',8)
    c.drawString(35,35,f'{part} | mm | Dimensions apply AFTER finish | Do not scale drawing')
    c.drawRightString(W-35,35,f'2026-09-08 / {page} of 6')

def check_drawing_configuration(p):
    """Prevent a future geometry edit from silently retaining P2 dimensions."""
    required={'base_width':160,'base_length':180,'base_thickness':8,'pocket_floor_z':4,
      'support_land_height':1.5,'end_stop_top':7.8,'support_y_pitch':76,
      'thread_boss_top':9.2,'thread_boss_od':12,'retainer_bolt_x':68,
      'bar_thickness':5,'spacer_length':30,'spacer_od':10,'spacer_id':5.3,
      'film_thickness':.2,'device_pan_z':5.7,'retainer_bolt_length':45}
    changed={k:p.get(k) for k,v in required.items() if p.get(k) is None or abs(p[k]-v)>1e-7}
    if changed:raise ValueError(f'Update and review P2 drawing annotations for changed geometry: {changed}')
    import vertical_adapter as va
    req_adapter={'web_t':6,'foot_t':6,'strip_width':36,'overall_height':176,
      'foot_tip_x':65,'inside_radius':6,'rib_width':3,'rear_return_depth':8,
      'foot_rib_height':8,'pocket_corner_radius':3,'foot_bolt_boss_od':20,'foot_bolt_boss_top':10}
    changed={k:va.PARAMS.get(k) for k,v in req_adapter.items() if va.PARAMS.get(k)!=v}
    if changed:raise ValueError(f'Update and review adapter drawing annotations: {changed}')


def export_dxf(p,out):
    """Actual CAD cross sections, not generic outlines or sheet-metal flats."""
    check_drawing_configuration(p)
    from ezdxf.addons import Importer
    import vertical_adapter as va
    out.mkdir(parents=True,exist_ok=True)
    def section(shape,z,path):
        cq.exporters.exportDXF(cq.Workplane('XY').newObject([shape]).section(z),str(path))
    def layered(stations,name):
        doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM
        for layer,shape,z in stations:
            doc.layers.new(layer);temp=out/f'_{layer}.dxf';section(shape,z,temp)
            src=ezdxf.readfile(temp);before=set(e.dxf.handle for e in doc.modelspace())
            imp=Importer(src,doc);imp.import_modelspace();imp.finalize()
            for e in doc.modelspace():
                if e.dxf.handle not in before:e.dxf.layer=layer
            temp.unlink()
        doc.layers.new('REFERENCE_TEXT');ent=doc.modelspace().add_text('P2 mm - SELECT ONE SECTION LAYER; SEE STEP/PDF. NOT A SHEET-METAL FLAT.',dxfattribs={'height':3,'layer':'REFERENCE_TEXT'});ent.dxf.insert=(-80,190,0)
        doc.saveas(out/name)
    base=m.create_base(p)
    layered([(f'XY_Z_{z:.2f}',base,z) for z in [2.0,4.1,5.45,7.7,8.2]],'B210_M01_machining_sections_P2.dxf')
    section(m.create_bar(p),2.5,out/'B210_M02_profile_P2.dxf')
    section(m.film(p),.1,out/'B210_M04_film_profile_P2.dxf')
    adapter=va.build_adapter()
    layered([(f'XZ_AT_Y_{y:.2f}',adapter.translate((0,-y,0)).rotate((0,0,0),(1,0,0),-90),0) for y in [0,16.5]],'B210_M05_machining_sections_P2.dxf')
    for name,xs in [('flat',[-70,70]),('upright',[20,55])]:
        doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM;doc.layers.new('DRILL_D5p5');doc.layers.new('REFERENCE_TEXT')
        for x in xs:
            for y in [p['center_y']-70,p['center_y']+70]:doc.modelspace().add_circle((x,y),2.75,dxfattribs={'layer':'DRILL_D5p5'})
        ent=doc.modelspace().add_text('MM - 4X DIA5.5 THRU; ASSUMED RIGID PLATE, SEE P2 SHOP PACK',dxfattribs={'height':3,'layer':'REFERENCE_TEXT'});ent.dxf.insert=(min(xs),p['center_y']+85,0)
        doc.saveas(out/f'B210_{name}_plate_drill_template_P2.dxf')
    audit=[]
    for path in sorted(out.glob('*P2.dxf')):
        d=ezdxf.readfile(path);a=d.audit();audit.append({'file':path.name,'units':d.units,'entities':len(d.modelspace()),'errors':len(a.errors)})
    (out/'drawing_dxf_audit_P2.json').write_text(json.dumps(audit,indent=2))
    if any(v['units']!=4 or v['errors'] or not v['entities'] for v in audit):raise ValueError('DXF audit failure')

def make_pdf(p,out):
    import vertical_adapter as va
    check_drawing_configuration(p)
    if p.get('revision')!='P2':raise ValueError('P2 parameters required')
    catpath=HERE/'references'/'catalog_bom.json';cat=json.loads(catpath.read_text(encoding='utf-8-sig'))
    pdf=out/'B210_mount_shop_pack_P2.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H))
    c.setTitle('B210 flat and upright mounting system - P2 prototype shop pack')
    c.setAuthor('Parametric CAD engineering draft');c.setCreator('CadQuery and ReportLab; editable make_documents.py')
    base=m.create_base(p);bar=m.create_bar(p);adapter=va.build_adapter();cy=p['center_y']
    title(c,'B210 mounting system | P2 flat and upright',1)
    for name,x in [('flat',35),('upright',W/2+5)]:
        path=out/'views'/f'{name}_iso.png'
        if not path.exists():raise FileNotFoundError(f'Final actual CAD view required: {path}')
        c.drawImage(str(path),x,325,width=530,height=415,preserveAspectRatio=True,anchor='c',mask='auto')
    table(c,['Option','Structural footprint','Height above plate','Plate fixing centers'],[
        ['Flat','160 x180','50.851 nominal incl. screw heads','140 x140; 4 xDIA5.5'],
        ['Upright','79 x180','176 nominal','35 x140; 4 xDIA5.5']],35,302,[125,240,300,455],rowh=31)
    lines(c,40,197,'P2: 8 mm broad base with integral thread bosses; 5 mm retainer bars; 6 mm upright web/foot with integral ribs and 10 mm thick foot bolt seats.\nBoth orientations use the same cradle. Upright supports are identical and bolt to the cradle. Custom structural parts are unwelded 6061-T6/T651.\nReserve front RF 60 mm and rear USB/DC/reference 70 mm beyond the model, subject to actual connector and cable dimensions.\nReserve 50 mm normal-to-cradle withdrawal flat /60 mm upright, plus tools and plate underside access. Do not size a box from the part envelope alone.\nPreliminary installation: rigid flat 6 mm metal plate in stationary indoor service. Box size, cable route, temperature and support stiffness remain to be confirmed.',width=173,size=10,leading=18)
    c.showPage()
    title(c,'M01 | Machined cradle base and integral bosses',2,'B210-M01 / P2 / QTY 1')
    pt=svg_view(c,base,42,116,585,590)
    dim(c,pt,(-80,cy-90),(80,cy-90),-28,'160 +/-0.20')
    dim(c,pt,(-80,cy-90),(-80,cy+90),-25,'180 +/-0.20',True)
    dim(c,pt,(-70,cy+70),(70,cy+70),32,'140 hole pitch')
    dim(c,pt,(70,cy-70),(70,cy+70),37,'140 hole pitch',True)
    dim(c,pt,(-68,cy-38),(68,cy-38),20,'136 tap pitch')
    lines(c,650,724,'DATUM A: underside Z0. B: X centerplane. C: Y=3.053 centerplane.\nCertified 6061-T6/T651; general linear +/-0.20, angles +/-0.5deg.\nBroad plate 8.00 +/-0.10; MIN 7.90. A flatness 0.10.\nOuter plan R16; accessible outer edges 0.5 x45deg.\nBlack sulfuric anodize 10-15um; final fit dimensions govern.',width=81,size=9.5,leading=15)
    table(c,['Feature','Coordinates / size','Requirement'],[
        ['4 plate bores','X +/-70; Y=C +/-70','DIA5.5 +.10/0 THRU'],
        ['4 thread bosses','X +/-68; Y=C +/-38','DIA12; top Z9.20 +/-.05'],
        ['4 retainer taps','Concentric with bosses','M5 x0.8-6H THRU'],
        ['4 foot reliefs','X +/-46.7995; Y +/-60.0075','DIA16 +.20/0 THRU'],
        ['Lower pocket','X +/-61.50; Y -75.430 /81.155','Floor Z4.00 +/-.10'],
        ['Upper end relief','Y -77.930 /83.306','Floor Z7.80 +/-.05'],
        ['4 hard lands','X +/-50; Y=C +/-38','16 x20 R1; Z5.50 +/-.05'],
        ['Center window','X +/-40; Y=C +/-50','80 x100 R5 THRU']],640,629,[116,215,182],rowh=30,size=8)
    lines(c,650,345,'Hole centers +/-0.10 coordinate from B/C; no chain tolerances.\nPocket width +0.10/0; end positions +/-0.05. Land coplanarity0.05.\nMachine pockets, lands and bosses from one blank. No bonded support blocks.\nDIA6 cutter corner reliefs: exact contours in STEP and Z-layer DXF.\nDrill 4.2 then tap M5 THRU. Assembly complete thread engagement>=7.5 mm;\nscrew-tip recess>=0.5 mm above underside. Actual screw and shim sizes govern.\nMask threads and spacer seats during anodize; seats clean and flat.\nCritical inner end-stop edges: deburr<=0.10; no general chamfer here.\nStock must allow 9.20 mm bosses plus facing allowance; mill broad plate to8.\nAn 8 mm finished blank cannot produce the integral bosses.',width=80,size=9,leading=14)
    sec=base.intersect(cq.Workplane('XY').box(180,.15,30).translate((0,cy+38,10)).val())
    svg_view(c,sec.rotate((0,0,0),(1,0,0),-90),648,83,505,105)
    lines(c,653,183,'SECTION Y=C+38: integral floor, hard lands and raised thread seats',width=100,size=8)
    c.showPage()
    title(c,'M02 / M03 / M04 | Retainer, spacer and film',3)
    pt=svg_view(c,bar,45,480,600,226)
    dim(c,pt,(-80,-10),(80,-10),-25,'160 +/-0.20')
    dim(c,pt,(-68,0),(68,0),40,'136 +/-0.10; 2X DIA5.5 +0.10/0 THRU')
    lines(c,679,718,'M02 RETAINER BAR - QTY 2\nCertified 6061-T6/T651;160 x20 x5.\nThickness 5.00 +/-0.10; MIN 4.90 after finish.\nWidth 20.00 +/-0.10; plan corners R3.\nHoles X +/-68,Y0; coordinate tolerance +/-0.10.\nEdges0.5 x45deg; hole rims deburred.\nUnderside flatness 0.05; black anodize as M01.\nPET patch centers X +/-50,Y0.',width=67,size=10,leading=16)
    svg_view(c,m.create_spacer(p),42,257,265,180,projection=(0,-1,0))
    lines(c,324,452,'M03 CATALOG SPACER - QTY 4\nMcMaster 94669A146, aluminum.\nOD10 +/-0.13; ID5.300 +/-0.13.\nLength 30.00 +/-0.13; catalog tolerances apply.\nAlloy, temper and yield not stated in catalog.\nMeasure and match actual spacer lengths.\nAnnular metal shims sit under spacers.\nNominal reference shim total0.6508:\n0.50 +0.10 +0.0508; measure actual stack.',width=55,size=10,leading=16)
    lines(c,679,452,'M04 ANTI-MAR FILM - QTY 8\nMcMaster 8689K65 PET sheet, acrylic adhesive.\nCut 8 patches 16 x20 with R1 corners per mount.\nFour on hard lands; four below retainer bars.\nInstalled bonded TOTAL thickness <=0.20 mm.\nCatalog 0.005 +/-.0005 in =0.127 +/-.0127 mm;\nadhesive inclusion not explicit. Measure total.\nAdhesive on mount; PET face contacts case.\nCatalog limit 150F /65.6C; qualify actual\nbox temperature, adhesion and wear.',width=66,size=10,leading=16)
    table(c,['Assembled Z station','Reference dimension','Acceptance'],[
        ['Pan underside','5.70 with0.20 mm lower film','Actual case rests on four hard lands'],
        ['Device top','39.40 nominal','Measure actual enclosure'],
        ['Bar underside','9.20 +30 +0.6508 =39.8508','Select measured spacer/shim stack'],
        ['Top film underside','39.6508 reference','Four gaps 0.20-0.30, cold and warm']],42,265,[245,365,510],rowh=28,size=9)
    lines(c,45,109,'Metal seats carry screw preload; no clamping preload on the radio. CAD gap 0.2508 mm is a reference, not a delivered fit guarantee.\nFilm has no credited retention, strength, friction, cooling or grounding function. No thick foam substitution; reset gaps after any change.',width=174,size=9,leading=15)
    c.showPage()
    title(c,'M05 | Ribbed upright support',4,'B210-M05 / P2 / QTY 2 IDENTICAL')
    pt=svg_view(c,adapter.rotate((0,0,0),(1,0,0),-90),38,140,492,565)
    dim(c,pt,(-14,0),(65,0),-25,'79 +/-0.20 overall X')
    dim(c,pt,(-14,0),(-14,176),-24,'176 +/-0.20',True)
    dim(c,pt,(0,26),(0,166),34,'140 hole pitch',True)
    svg_view(c,adapter,545,505,253,210,projection=(1,0,0))
    footpt=svg_view(c,adapter,820,505,306,210,projection=(0,0,1))
    dim(c,footpt,(65,-18),(65,18),20,'36 +/-0.10',True)
    lines(c,565,492,'WEB VIEW: holes Y0',width=50,size=8)
    lines(c,839,492,'FOOT VIEW: holes X20/55, Y0',width=50,size=8)
    table(c,['Feature','Position','Dimension / tolerance'],[
        ['Main web','X=-6 to0','6.00 +/-.10; MIN 5.90'],
        ['Foot floor','Z=0 to6','6.00 +/-.10; MIN 5.90'],
        ['2 integral foot bosses','X20 /55; Y0; DIA20','Top Z10.00 +/-.10; MIN 9.90'],
        ['Overall width','Y=-18 to18','36.00 +/-.10'],
        ['Rear returns','X=-14 to-6; Z0 to176','2X3.00 wide x8.00 deep'],
        ['Foot ribs','X=-14 to65; Z6 to14','2X3.00 wide x8.00 high'],
        ['Rib Y zones','Y=-18 to-15 /15 to18','Rib3 +/-.10; MIN 2.90'],
        ['Channel openings','30 mouth;24 flat floor','Inside blendsR3; front rootR6'],
        ['2 web holes','Y0; Z26 /166','DIA5.5 +.10/0 alongX'],
        ['2 foot holes','Y0; X20 /55','DIA5.5 +.10/0 THRU10 alongZ']],546,474,[123,223,227],rowh=24,size=8)
    lines(c,552,202,'A=foot undersideZ0; B=cradle mating faceX0; C=width centerplaneY0.\nA flatness 0.10; A/B perpendicularity 0.10 over160. Hole coordinates +/-.15.\nGeneral +/-.20, angles +/-.5deg. Return depth/rib height8 +/-.10; MIN 7.90.\nMachine one-piece certified 6061-T6/T651 from 82 x180 x38.1 oversize stock.\nOrthogonal pocket setups; nominal wall gap5, floor gap2 before boss blend.\nBoss-floor blend R0.2-0.5 adds material (nominal CAD sharp); floor gap about 1.5 nominal.\nSmall-tool finish required; shop verifies cutter diameter, reach and toolpath.\nBlack anodize 10-15um; mask seats. Deburr0.2-0.5; preserve full root and ribs.\nPair atY=-66.947/+73.053; 140 spacing. Not a freestanding stand.',width=104,size=9,leading=14)
    lines(c,43,110,'R6 front root center(X6,Z12), tangent(X6,Z6)/(X0,Z12). STEP defines rib-blend transitions.\nMachined part: layered DXF sections complement STEP; no sheet-metal flat pattern or bend allowance.',width=103,size=8,leading=13)
    c.showPage()
    title(c,'Hardware | Exact McMaster procurement schedule',5)
    rows=[]
    short={'H01':'M5x45 cap screw; Class 12.9 black oxide','H02':'M5x25 cap screw; Class 12.9 black oxide',
      'H03':'ISO7089 steel washer; OD10, ID5.3, t0.9-1.1','H04':'M5 locknut; Class 10 zinc steel, DIN985',
      'H05':'Al spacer; L30, OD10, ID5.3, each +/-.13','H06':'Foot TOP washer; OD15, ID5.3, t1.0-1.4',
      'H07':'Foot screw M5x30; Class 12.9 black oxide',
      'C01':'PET adhesive sheet 27x20in;8 patches/version','C02':'LOCTITE 243 removable threadlocker,0.34fl oz',
      'S01':'DIN988 spring-steel shim,5ID x10OD x.10','S02':'DIN988 spring-steel shim,5ID x10OD x.50',
      'S03':'18-8 shim,6.35ID x9.525OD x.0508'}
    for item in cat['items']:
        key=item['item_id'];pn=item['mcmaster_part_number'];price=item.get('pack_price_usd');qty=item.get('pack_qty')
        price=f'${price:.2f} / {qty}' if isinstance(price,(int,float)) else 'See catalog BOM'
        rows.append([key,pn,short.get(key,item['description'][:60]),item.get('qty_flat','AR'),item.get('qty_upright','AR'),price])
    y=table(c,['ID','McMaster PN','Specification / role','Flat','Upright','USD / pack qty'],rows,35,730,[47,108,452,89,89,335],rowh=27,size=8.5)
    for idx,item in enumerate(cat['items']):
        top=730-27*(idx+1)
        c.linkURL(item['url'],(82,top-27,190,top),relative=0,thickness=0)
    lines(c,42,y-25,'Four H06 large washers go on TOP of upright feet only; ordinary H03 washers remain below supporting plate. Accept H06 OD>=14.9 mm on receipt; catalog OD tolerance is not stated. H06 is zinc steel, DIN9021; no strength grade stated.\nUse 4 mm hex drive and 8 mm nut wrench. Screws are Class 12.9, washers catalogued for Class 10.9, nuts Class 10: do not apply maximum screw-class preload to these lower-rated joints or aluminum members. Dry indoor service; establish assembly tightening procedure.\nReference retainer entry:45 -(5 bar +1 washer +30 spacer +.6508 shim)=8.3492 mm;9.2 boss gives0.8508 mm nominal tip recess. Actual COMPLETE engaged threads>=7.5 mm and tip recess>=0.5 mm must both be inspected; nominal entry is not effective engagement.\nFoot M5x30 stack:10 mm integral boss +1.2 top washer +6 plate +1 lower washer +5 nut =23.2 mm; nominal tail 6.8 mm. Head top Z16.2; tip Z-18.8 (foot bolt).\nThrough bolts assume6 mm rigid plate and underside access. Inspect>=2 complete threads beyond locknut. Select different lengths for actual plate/washer stacks. No screw enters the radio.\nUse the fewest metal shims; no more than 4 per location without redesign. Measure all stacks. Fine shim 98126A161 is an inch-size substitute; center it under the spacer. Keep spring-steel shims dry.\nPrices observed2026-09-08 before tax/shipping, not quotes. Installed counts are per complete version. One film sheet and one threadlocker bottle can serve both. See catalog_bom.json/CSV for all full descriptions, tolerances, pack rounding and source URLs.',width=175,size=9.5,leading=15)
    lines(c,43,101,'Catalog part numbers in the table link directly to their McMaster product pages. Full catalog evidence accompanies this PDF. No purchase or physical hardware inspection performed.',width=175,size=9,leading=14)
    c.showPage()
    title(c,'Installation, removal and prototype release gates',6)
    lines(c,39,728,'ASSEMBLY / INSTALLATION\n1. Inspect material certificates, dimensions, finish, deburring and actual hardware. Check ribs, bosses and bearing seats. Keep precision seats and threads clean.\n2. Fit 4 PET patches on hard lands and 4 below bars. Measure installed bonded thickness without release liner; maximum 0.20 mm. Record actual thickness.\n3. Flat: mount cradle at X +/-70,Y=C +/-70 using M5x25, washers both sides and new locknuts. Assumed plate 6 mm, accessible from below.\n4. Upright: attach supports to plate first at foot X20/55,Y=-66.947/+73.053. Use M5x30 through the 10 mm thick integral bolt seats, large OD15 washers on top, ordinary OD10 washers and locknuts below. Then attach cradle to webs at Z26/166 with M5x25, ordinary washers and locknuts.\n5. Place disconnected radio in cradle. Feet enter 16 mm reliefs; metal pan bears on four film-covered hard lands. Actual labels and device screw heads must clear relieved ends and stops; installed label clearance >=0.20 mm.\n6. Fit matched spacers, measured shim stacks, two bars and four M5x45 screws with washers. Close metal seats, never clamp the case. Inspect all four top gaps 0.20-0.30 mm, complete threads>=7.5 mm and screw-tip recess>=0.5 mm simultaneously.\n7. Apply threadlocker 243 only to retainer/base threads, following supplier preparation/cure procedure. Connect actual plugs, check cable bend radius and anchor cables to supporting plate. Log final stacks/gaps and witness marks.\nREMOVAL\nPower down, disconnect cables, remove 4 retainer screws, bars and spacer/shims. Withdraw normal to cradle plane; reserve 50 mm flat /60 mm upright. Keep each shim stack identified by position. Disassemble enclosure off-mount. Replace worn films/locknuts, reset gaps and restore locking on service.',width=111,size=10.5,leading=16)
    lines(c,781,728,'DIGITAL DELIVERABLES\nActual supplied STEP imported, measured and preserved.\n196 source solids, including duplicate front overlays, documented.\nEditable CAD source, actual STEP exports and machining DXFs accompany this pack.\nVerification reports state the checked revision, digital checks, calculations and assumptions.\nNo fabrication, FEA, physical load, thermal or vibration test has occurred.\n\nBEFORE SERVICE\nConfirm actual mounting plate and box.\nWeigh device and complete mount.\nMeasure case, label and device-fastener clearances.\nSet/record all four cold and warm gaps.\nVerify no unintended case clamp load.\nPerform staged retention, handling and cable-force tests per prototype plan.\nTest worst expected operating temperature in actual box.\nInspect permanent set, cracks, loose screws, film wear and case damage after loading.\nApprove supporting structure and its fixing edge distances.\n\nNeither PET nor anodized contact establishes protective or RF ground. Provide a separate verified bond if required.\n\nStationary indoor preliminary scope. No vehicle, airborne, outdoor or overhead qualification claimed.',width=55,size=10,leading=15)
    c.showPage();c.save()
    (out/'drawing_source_manifest_P2.json').write_text(json.dumps({'revision':p['revision'],'params':p,'adapter_params':va.PARAMS,'catalog_source':str(catpath),'pdf':pdf.name},indent=2))
    return pdf

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('C:/b210work/professional_mount_P2'));args=ap.parse_args()
    p=m.load_params()
    if p.get('revision')!='P2':raise SystemExit('Waiting for settled P2 parameters; no drawings generated.')
    export_dxf(p,args.out);print(make_pdf(p,args.out))
