"""Regenerate manufacturing DXFs, dimensioned shop PDF and CSV bill of materials."""
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
INK=colors.HexColor('#182937'); BLUE=colors.HexColor('#00667B')


def bom_rows():
    return [
      ['M01','Cradle base',1,1,'6061-T6/T651; machined; B210_M01_base_P1.step'],
      ['M02','Top retainer bar',2,2,'6061-T6/T651; 160 x 20 x 8; two DIA5.5 THRU at X +/-70'],
      ['M03','Precision spacer',4,4,'6061-T6; OD12 +/-0.10; ID5.5 +0.10/0; L30 +/-0.05; square ends'],
      ['M04','Anti-mar film patch',8,8,'Polyester PET, 0.20 +/-0.03 total adhesive-backed thickness; 16 x 20 R1; supplier-rated >=60 C'],
      ['M05','Upright angle support',0,2,'6061-T6; 73 x 36 x 176 envelope; 8 mm webs; R6 root; adapter_machined.step'],
      ['H01','Retainer screw',4,4,'ISO4762 M5 x 0.8 x 50; A2-70; standard socket cap head; 4 mm hex'],
      ['H02','Flat plate / upright web screw',4,4,'ISO4762 M5 x 0.8 x 30; A2-70; 4 mm hex'],
      ['H03','Upright foot screw',0,4,'ISO4762 M5 x 0.8 x 25; A2-70; 4 mm hex'],
      ['H04','Flat washer',12,20,'ISO7089 M5; 5.3 ID x 10 OD x 1 thick; A2 stainless; compatible hardness'],
      ['H05','Prevailing torque locknut',4,8,'ISO10511 M5 x 0.8; A2-70 compatible; nylon insert; nominal 5 mm high; replace on service'],
      ['H06','Retainer thread locking',1,1,'LOCTITE243 removable medium-strength; follow Henkel TDS for actual anodized Al/stainless joint'],
      ['H07','Fit adjustment shims', 'AR','AR','Precision stainless ID5.5; OD<=12 at spacer or <=10 under head; 0.05/0.10/0.50 increments'],
      ['I01','Supporting plate (assumed)',1,1,'Rigid 6 mm metal plate with underside access; installation item; integrator approves material/stiffness'],
      ['I02','Cable restraint hardware','AR','AR','Support-plate cable clamps selected for actual cables; strain-relieve without loading radio connectors']]


def export_dxf(p,out):
    out.mkdir(parents=True,exist_ok=True)
    # Actual CAD cross sections; explicit Z station on each named layer.
    doc=ezdxf.new('R2010'); doc.units=ezdxf.units.MM
    base=m.create_base(p)
    for z in [3,6.1,7.55,9.7,10.1]:
        layer=f'SECTION_Z_{z:.2f}_mm'
        doc.layers.new(layer)
        sec=cq.Workplane('XY').newObject([base]).section(z)
        temp=out/f'_section_{z}.dxf'
        cq.exporters.exportDXF(sec,str(temp))
        src=ezdxf.readfile(temp)
        from ezdxf.addons import Importer
        imp=Importer(src,doc); before=set(e.dxf.handle for e in doc.modelspace())
        imp.import_modelspace(); imp.finalize()
        for ent in doc.modelspace():
            if ent.dxf.handle not in before: ent.dxf.layer=layer
        temp.unlink()
    doc.saveas(out/'B210_M01_machining_sections_P1.dxf')
    cq.exporters.exportDXF(cq.Workplane('XY').newObject([m.create_bar(p)]).section(4),str(out/'B210_M02_profile_P1.dxf'))
    cq.exporters.exportDXF(cq.Workplane('XY').newObject([m.film(p)]).section(.1),str(out/'B210_M04_film_profile_P1.dxf'))
    for name,xs in [('flat',[-70,70]),('upright',[20,55])]:
        doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM
        doc.layers.new('DRILL_D5p5');doc.layers.new('REFERENCE_TEXT')
        space=doc.modelspace()
        for x in xs:
            for y in [p['center_y']-70,p['center_y']+70]:
                space.add_circle((x,y),2.75,dxfattribs={'layer':'DRILL_D5p5'})
        note=space.add_text('MM - 4X DIA5.5; ASSUMED RIGID SUPPORT, SEE SHOP PACK',dxfattribs={'height':3,'layer':'REFERENCE_TEXT'})
        note.dxf.insert=(min(xs),p['center_y']+85,0)
        doc.saveas(out/f'B210_{name}_plate_drill_template_P1.dxf')


def title(c,title,page,part='B210 / P1'):
    c.setFillColor(INK); c.rect(0,H-70,W,70,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold',22); c.drawString(35,H-42,title)
    c.setFont('Helvetica',9); c.drawRightString(W-35,H-40,'PRELIMINARY - PROTOTYPE / NOT QUALIFIED')
    c.setStrokeColor(INK); c.line(35,52,W-35,52)
    c.setFillColor(INK); c.setFont('Helvetica',9)
    c.drawString(35,35,f'{part} | Units mm | Dimensions apply AFTER finish | Do not scale drawing')
    c.drawRightString(W-35,35,f'2026-09-08  /  {page}')


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


def make_pdf(p,out):
    pdf=out/'B210_mount_shop_pack_P1.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H))
    c.setTitle('B210 flat and upright mounting system - P1 prototype shop pack')
    # Assembly overview uses actual CAD renders, never invented visual geometry.
    title(c,'B210 mounting system | flat and upright',1)
    for name,x in [('flat',35),('upright',W/2+5)]:
        image=out/'views'/f'{name}_iso.png'
        if image.exists(): c.drawImage(str(image),x,305,width=530,height=435,preserveAspectRatio=True,anchor='c',mask='auto')
    table(c,['Option','Structural footprint','Above plate','Plate fixing centers'],
          [['Flat','160 x 180','56 nominal incl screw heads','140 x 140; 4 x DIA5.5'],
           ['Upright','73 x 180','176 nominal','35 x 140; 4 x DIA5.5']],35,290,[130,245,235,510],rowh=30)
    lines(c,40,185,'Hardware envelope upright: 79 x 180 above plate; allow 12 mm below assumed plate for nuts and screw ends.\nReserve front RF: 60 mm beyond modeled end face; rear USB/DC/reference: 70 mm. Actual plug and cable bend data still required.\nReserve 50 mm above top bars for flat extraction, and 60 mm in front of the upright cradle for removal. Tool space adds to the package.\nIndoor stationary preliminary basis. Use in a box only after the actual internal temperature, support stiffness and access are established.',width=155,size=10,leading=17)
    c.showPage()
    # Base drawing: exact projected B-rep, dimensional overlay in the same world frame.
    title(c,'M01 | Machined cradle base',2,'B210-M01 / P1 / QTY 1')
    pt=svg_view(c,m.create_base(p),45,122,595,580)
    cy=p['center_y']
    dim(c,pt,(-80,cy-90),(80,cy-90),-30,'160 +/-0.20')
    dim(c,pt,(-80,cy-90),(-80,cy+90),-24,'180 +/-0.20',True)
    dim(c,pt,(-70,cy+70),(70,cy+70),35,'140 BASIC')
    dim(c,pt,(70,cy-70),(70,cy+70),38,'140 BASIC',True)
    dim(c,pt,(-40,cy-50),(40,cy-50),18,'80 window')
    lines(c,677,719,'DATUM A: underside Z=0.\nDATUM B: X centerplane.\nDATUM C: Y=3.053 centerplane.\nMaterial: certified 6061-T6/T651.\nStock: 12 mm finished plate; choose oversize blank.\nOverall Z=12.00 +/-0.10; A flatness 0.10.\nOuter plan R16; outer edges 0.5 x45 deg.\nBlack anodize 10-15 um nominal.\nFinal pocket/contact dimensions govern.',width=62,size=10)
    rows=[['4 plate bores','X +/-70; Y=C +/-70','DIA5.5 +0.10/0 THRU'],
          ['4 retainer taps','X +/-70; Y=C +/-35','M5 x0.8-6H THRU'],
          ['4 foot clearances','X +/-46.7995; Y +/-60.0075','DIA16 +0.20/0 THRU'],
          ['Lower pocket','X +/-61.50; Y -75.430 /81.155','Floor Z6.00 +/-0.05'],
          ['Upper end relief','Y -77.930 /83.306','Floor Z9.80 +/-0.05'],
          ['4 support lands','X +/-50; Y=C +/-35','16 x20 R1; top Z7.50 +/-0.05'],
          ['Center window','X +/-40; Y=C +/-50','80 x100 R5 THRU']]
    table(c,['Feature','Position / size','Detail'],rows,654,540,[122,211,173],rowh=34,size=8)
    lines(c,665,252,'Hole center coordinates +/-0.10 from B/C; no accumulated chain tolerances.\nPocket width +0.10/0; end positions +/-0.05. Land coplanarity 0.05.\nCorner reliefs: 6 mm cutter; exact contours in STEP / layered DXF.\nMachine pockets with islands retained; no separate bonded support blocks.\nM5: drill4.2 then tap; >=8 mm complete engaged threads when assembled.\nCritical inner end-stop edges: deburr <=0.10. Do not apply general0.5 chamfer.\nMask thread and spacer seats for finish. Other unspecified linear +/-0.20; angles +/-0.5deg.\nPerform all pad/stop fit checks on the actual enclosure before loading.',width=74,size=9,leading=14)
    c.showPage()
    title(c,'M02 / M03 / M04 | Retainer components',3)
    pt=svg_view(c,m.create_bar(p),50,440,600,260)
    dim(c,pt,(-80,-10),(80,-10),-24,'160 +/-0.20')
    dim(c,pt,(-70,0),(70,0),46,'140 +/-0.10; 2 x DIA5.5 +0.10/0 THRU')
    lines(c,704,695,'M02 RETAINER - QTY2\n6061-T6/T651, finished 8.00 +/-0.05 thick.\n20.00 +/-0.10 wide; plan corners R3.\nHole centers X +/-70, Y=0.\nTop/bottom edges0.5 x45 deg; deburr hole rims.\nBlack anodize as M01; bearing face flatness0.05.\nSource part origin: centerXY, undersideZ0.',width=60,size=11)
    pt=svg_view(c,m.create_spacer(p),55,95,270,270,projection=(0,-1,0))
    lines(c,370,392,'M03 SPACER - QTY4\n6061-T6; OD12.00 +/-0.10; ID5.50 +0.10/0.\nLength30.00 +/-0.05; end parallelism0.03.\nCut from tube or drill bar; face both ends.\nDeburr0.2; bearing faces clean and flat.\nLeave clear conversion finish or bare dry indoor service.\nMatch spacer pairs within0.03 per bar.',width=59,size=11)
    lines(c,704,392,'M04 FILM - QTY8\n16 x20 R1; total thickness0.20 +/-0.03.\nAdhesive-backed PET anti-mar film; >=60 C supplier rating.\nFour lower land patches; four bar patches at X +/-50.\nFilm is not credited for retention or cooling.\nConfirm adhesive compatibility with the case finish.\nNo thick foam substitution without recalculation.',width=60,size=11)
    lines(c,372,224,'ASSEMBLED FIT\nPan nominal Z7.70; top Z41.40. Bar underside Z42.00.\nFilm underside on bar Z41.80: nominal gap0.40.\nMeasure each of four top gaps: accept0.20-0.40 cold/hot.\nSelect spacer lengths / annular shims to achieve gap;\nno clamping preload is applied to the enclosure.\nSupport thickness, coating and device variation require\nactual gap setting; nominal CAD alone cannot guarantee fit.',width=67,size=10)
    c.showPage()
    title(c,'M05 | Upright angle support',4,'B210-M05 / P1 / QTY 2')
    import vertical_adapter as va
    pt=svg_view(c,va.build_adapter().rotate((0,0,0),(1,0,0),-90),70,120,555,605)
    dim(c,pt,(-8,0),(65,0),-25,'73 +/-0.20')
    dim(c,pt,(-8,0),(-8,176),-25,'176 +/-0.20',True)
    dim(c,pt,(0,26),(0,166),38,'140 +/-0.10 hole pitch',True)
    lines(c,675,706,'One-piece 6061-T6; QTY2 identical.\nProfile in XZ; width36.00 +/-0.10 alongY.\nDatum A: foot undersideZ0.\nDatum B: cradle mating faceX0.\nDatum C: width centerplaneY0.\nOverall X=-8 to65 (73); Z=0 to176.\nWeb/foot8.00 +/-0.05; MIN7.95 after finish.\nInside root R6; free corners R3.\nBreak accessible edges0.2-0.5; retain full root.\nA/B perpendicularity0.10 over160.\nA flatness0.10; general linear +/-0.20.',width=64,size=11)
    table(c,['Feature','Coordinates','Detail'],[
       ['2 web holes','Y=0; Z=26 /166','DIA5.5 +0.10/0; alongX'],
       ['2 foot holes','Y=0; X=20 /55','DIA5.5 +0.10/0; alongZ'],
       ['Hole position','From A/B/C','+/-0.10 coordinate'],
       ['Installed pair','Y=-66.947 /73.053','140 center spacing']],655,487,[132,178,196],rowh=33,size=9)
    lines(c,668,314,'Profile is CNC machined, not bent sheet. No flat-pattern bend compensation.\nSaw/waterjet rough profile from oversize38.1mm plate, finishwidth36.\nFinish side profile/root with appropriate12mm cutter reach and workholding.\nDrill in two orthogonal setups using A/B/C; clamp on sacrificial stock / fixture.\nBlack anodize10-15um; mask mating seats; final dimensions govern.\nBlank approximately75 x180 x38.1; optimize nesting if making multiple mounts.\nDXF is the finished side profile; hole axes and depth are defined here and STEP.\nInstall foot bolts before cradle; inner foot bolts become obscured in service.',width=73,size=10,leading=16)
    c.showPage()
    title(c,'Hardware and assembly requirements',5)
    rows=bom_rows()
    with (out/'B210_BOM_P1.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['Item','Description','Flat qty','Upright qty','Complete specification']);w.writerows(rows)
    # Two text lines per full specification, avoiding truncated BOM cells.
    y=720
    for item,desc,qf,qu,spec in rows:
        c.setFont('Helvetica-Bold',10);c.setFillColor(BLUE)
        c.drawString(40,y,f'{item}  {desc}');c.drawString(360,y,f'Flat {qf} / Upright {qu}')
        y=lines(c,510,y,spec,width=104,size=9,leading=12)-17
    lines(c,42,150,'Retainer stack:50 screw - (8 bar +1 washer +30 spacer) =11 nominal engagement; tip1 mm above base underside.\nInspect actual screws: >=8 mm completed threads engaged, >=0.5 mm tip recess. No fastener enters the radio.\nPlate hardware assumes6mm support and underside access. Change length for actual support; at least2 full threads beyond locknut.\nNo torque value is released. Establish metal-seat tightening/locking procedure using actual finish, friction and verified thread capacity.\nDo not use enclosure gap closure as the screw-tightening stop. Allow retainer threadlocker to cure per supplier TDS before use.',width=165,size=9,leading=16)
    c.showPage()
    title(c,'Installation, service and prototype release gates',6)
    lines(c,40,712,'ASSEMBLY / INSTALLATION\n1. Inspect machined dimensions, deburring, finishes and screw-tip recess. Clean all seats. Fit four films to the integral lands and four to retainer undersides.\n2. Flat: bolt the cradle to the assumed plate at X +/-70,Y=C +/-70 using M5x30, washers both sides and new locknuts.\n3. Upright: install both supports to the plate first at X20/55,Y=-66.947/+73.053 using M5x25. Then attach the cradle to the support webs at Z26/166 using M5x30.\n4. Lower the disconnected radio into the cradle. Feet enter the16mm reliefs; the metal pan rests on the four film-covered hard lands. Check labels and seams do not bear on stops.\n5. Add spacers, bars and retainer M5x50 screws with washers. Set four top gaps to0.20-0.40mm by selecting spacer/shim stack. Close metal seats, never clamp the radio.\n6. Check source-specific end labels remain >=0.20mm clear of the low end stops. Connect actual plugs, verify bend radii and tool access, then anchor cables to the supporting plate.\n7. Inspect witness marks and locking provisions. Use threadlocker only on retainer/base threads; follow supplier cleaning, cure and service instructions.\nREMOVAL\nPower down and disconnect cables. Remove four retainer screws, two bars and four spacers. Lift radio normal to the cradle plane; reserve50mm flat /60mm upright withdrawal. Full enclosure disassembly is performed off the mount. Replace damaged films and prevailing-torque nuts, reset gaps and restore locking on reassembly.',width=98,size=11,leading=17)
    lines(c,728,712,'CHECKS AND LIMITS\nOriginal supplied STEP imported, measured and preserved.\nSource model:196 valid solids; documented duplicate front overlays.\nCAD solids, export scale/completeness, fit, removal, tool corridors and positive-stop poses are checked by verify.py.\nAnalytical metal sizing is in references/engineering; geometry results are in verification_report.json.\nNo FEA, vibration qualification or physical prototype test has occurred.\n\nBEFORE SERVICE\nWeigh actual unit;1.0kg is an allowance.\nMeasure actual enclosure and label clearances.\nVerify case contact capacity with staged fixture loads.\nTest retention with full cables and film-loss surrogate.\nThermal run both layouts in actual box.\nApprove plate stiffness, bolts and support load path.\nConfirm environment and vibration requirements.\n\nSee prototype_validation_plan.md for numerical loads, displacement limits, acceptance gates and logging.\n\nElectrical bonding is unspecified. Neither anodized contact nor films establish a protective/RF ground. Implement any required bond separately.\n\nNo airborne, vehicle, outdoor or overhead suitability is claimed.',width=60,size=10,leading=16)
    c.showPage();c.save()
    return pdf


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'exports');args=ap.parse_args()
    p=m.load_params();export_dxf(p,args.out); print(make_pdf(p,args.out))

