from pathlib import Path
import json,itertools
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,FancyBboxPatch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'FPE'
p=json.loads((ROOT/'params.json').read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
colors={'bedrock':'#427a95','router':'#173f59','oz':'#267b76','b210':'#74539a','psu':'#b8732b'}
def rect(ax,x,y,w,h,color,alpha=1,lw=1.5,ls='-',z=2):
 patch=Rectangle((x,y),w,h,facecolor=color,edgecolor=color,alpha=alpha,lw=lw,linestyle=ls,zorder=z);ax.add_patch(patch);return patch
def boxline(ax,x,y,w,h,color,lw=1.5,ls='-',z=3):
 patch=Rectangle((x,y),w,h,facecolor='none',edgecolor=color,lw=lw,linestyle=ls,zorder=z);ax.add_patch(patch);return patch

fig,ax=plt.subplots(figsize=(12,12))
fig.subplots_adjust(left=.08,right=.97,top=.91,bottom=.10)
ax.add_patch(Rectangle((-36.195,-36.195),504.19,504.19,fill=False,ec='#82929b',lw=1.2,ls='--'))
ax.add_patch(FancyBboxPatch((0,0),431.8,431.8,boxstyle='round,pad=0,rounding_size=6.35',fc='#f6f8fa',ec='#384851',lw=1.8,zorder=0))
rect(ax,0,250,215.9,181.8,'#d7ebd7',.85,z=1)
ax.text(107.95,337,'RESERVED\n215.9 × 181.8 mm\nFactory hardware/tool space excluded',ha='center',va='center',fontsize=13,color='#28552b',linespacing=1.5)
for x,y in itertools.product([22.225,409.575],repeat=2):
 ax.add_patch(Circle((x,y),15,fc='white',ec='#64717a',ls='--',lw=1,zorder=5));ax.add_patch(Circle((x,y),6.35,fc='white',ec='#202c34',lw=1,zorder=6))
for h in p['mounting_holes'][4:]:ax.add_patch(Circle((h['x'],h['y']),h['diameter']/2,fc='white',ec='#202c34',lw=1,zorder=5))
# Declared cable/air allowances; transparency distinguishes them from solids.
for x,y,w,h,col in [(4.04,32,50,150,colors['bedrock']),(64,197,116,50,colors['bedrock']),(47,-31.799573,150,40,colors['router']),(47,174.430011,150,40,colors['router']),(227,-34,110,60,colors['b210']),(227,186,110,60,colors['b210']),(235.9,-2.05,92.2,40,colors['oz']),(240,176.05,84,30,colors['oz']),(359.4,-34.4,41,100,colors['psu']),(359.4,366.2,41,100,colors['psu'])]:
 rect(ax,x,y,w,h,col,.08,lw=.8,ls='--',z=1);boxline(ax,x,y,w,h,col,.8,'--',2)
# Lower devices and adapter outlines.
rect(ax,39,15,166,184,colors['bedrock'],.12,z=2);boxline(ax,39,15,166,184,colors['bedrock'],1.5,'--',4)
rect(ax,223.9,37.95,116.2,138.099,colors['oz'],.20,z=2);boxline(ax,223.9,37.95,116.2,138.099,colors['oz'],1.5,'--',4)
# Windowed carrier, upper router and raised B210 plate.
boxline(ax,32,2,180,210,colors['router'],2.4,z=6);boxline(ax,49,27,146,160,colors['router'],1.1,':',5)
rect(ax,36.1,8.200427,171.8,166.229584,colors['router'],.23,z=3)
rect(ax,207,32,150,148,colors['b210'],.21,z=3);boxline(ax,207,32,150,148,colors['b210'],2,z=6)
# PSU original side-tab outline envelope, device and terminal extent.
rect(ax,357.4,49.4,45,316.8,colors['psu'],.24,z=2)
for y in [49.4,301.4]:rect(ax,343.9,y,72,44,colors['psu'],.24,z=2)
rect(ax,359.4,27.6,41,338.6,colors['psu'],.55,z=3)
for h in p['hardware']:
 fc='#111827' if h['catalog_code']=='WGO30' else 'white'
 ax.add_patch(Circle((h['x'],h['y']),2.4,fc=fc,ec='#111827',lw=.8,zorder=8))
for x,y in itertools.product([41.1,202.9],[48.65,131.35]):ax.add_patch(Circle((x,y),2.4,fc='#e8f1f8',ec=colors['router'],lw=1,zorder=8))
ax.text(122,111,'Peplink over\nBedrock',ha='center',va='center',fontsize=15,color=colors['router'],weight='bold')
ax.text(122,74,'Carrier underside Z70\nBedrock contact retained',ha='center',va='center',fontsize=10,color=colors['router'])
ax.text(282,115,'B210 over OZ',ha='center',va='center',fontsize=13,color=colors['b210'],weight='bold')
ax.text(282,83,'Adapter underside Z50\nRemove for OZ service',ha='center',va='center',fontsize=10,color=colors['b210'])
ax.text(379.9,202,'MEAN WELL PSU',rotation=90,ha='center',va='center',fontsize=12,color='#593411',weight='bold')
ax.text(122,229,'Bedrock cable allowance',ha='center',va='center',fontsize=9,color=colors['bedrock'])
ax.text(282,217,'B210 cable allowance',ha='center',va='center',fontsize=9,color=colors['b210'])
ax.text(379.9,417,'100 mm exhaust',rotation=90,ha='center',va='center',fontsize=9,color=colors['psu'])
ax.text(122,-16,'Router cables',ha='center',va='center',fontsize=9,color=colors['router'])
ax.text(282,-17,'B210 cables',ha='center',va='center',fontsize=9,color=colors['b210'])
ax.set(xlim=(-44,478),ylim=(-44,478),xlabel='Panel X, mm — origin at lower-left',ylabel='Panel Y, mm — cabinet upright')
ax.set_aspect('equal');ax.set_xticks([0,100,200,300,400,431.8]);ax.set_yticks([0,100,200,250,300,400,431.8]);ax.grid(alpha=.13,zorder=0)
fig.suptitle('SCE20 R2 · compact stacked layout',fontsize=20,weight='bold',y=.965)
fig.text(.5,.934,'Component outlines and chosen cable/air allowances · all dimensions in millimetres',ha='center',fontsize=11,color='#52616a')
fig.text(.5,.052,'Dashed circles: Ø30 factory-tool envelopes to Z60.  Dashed colored boxes: cable/air planning space.\nBlack points: raised support anchors.  White points: direct studs/router standoffs.  Larger dashed border: inner case walls.',ha='center',fontsize=9,color='#52616a',linespacing=1.5)
for ext in ['png','svg']:fig.savefig(OUT/f'LAYOUT_R2.{ext}',dpi=180,facecolor='white')
plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(14,7.5),sharey=True)
fig.subplots_adjust(left=.065,right=.96,top=.85,bottom=.20,wspace=.20)
def dim(ax,x,lo,hi,label):
 ax.annotate('',xy=(x,hi),xytext=(x,lo),arrowprops={'arrowstyle':'<->','color':'#384851','lw':.8});ax.text(x+3,(lo+hi)/2,label,rotation=90,va='center',fontsize=9,color='#384851')
for ax in axes:
 rect(ax,-115,-6,235,6,'#bac5cc',1,z=0)
 ax.axhline(0,color='#2e3c46',lw=1)
 ax.set(xlim=(-120,130),ylim=(-8,125),xlabel='Local horizontal envelope, mm')
 ax.set_aspect('equal');ax.set_yticks([0,20,32.72,50,70,80,109.3,120]);ax.grid(axis='y',alpha=.16);ax.spines[['top','right']].set_visible(False)
axes[0].set_ylabel('Z above backpanel front, mm')
a=axes[0]
rect(a,-83,0,166,6,colors['bedrock'],.8);rect(a,-67.957,6,132.957,51,colors['bedrock'],.55)
for x in [-70,70]:
 rect(a,x-2.5,0,5,20,'#4b5563',.8,z=5);rect(a,x-3.1754,20,6.3508,50,'#4b5563',.8,z=5)
rect(a,-90,70,180,4,colors['router'],.9,z=6)
for x in [-80.9,80.9]:rect(a,x-2.5,74,5,6,'#4b5563',.8,z=5)
rect(a,-85.9,80,171.8,29.3,colors['router'],.55)
a.text(0,95,'Peplink envelope',ha='center',color='white',weight='bold',fontsize=11)
a.text(0,33,'Bedrock\nDirect thermal contact',ha='center',va='center',color='#173f59',fontsize=10)
a.text(0,64,'13 mm to carrier rim',ha='center',fontsize=9,color=colors['router'])
dim(a,-107,0,70,'70 mm carrier underside');dim(a,111,0,109.3,'109.3 mm overall')
a.set_title('Peplink over Bedrock',fontsize=14,weight='bold',pad=12)
b=axes[1]
rect(b,-58.1,0,116.2,32.72,colors['oz'],.5)
for x in [-68,68]:rect(b,x-2.5,0,5,20,'#4b5563',.8,z=5);rect(b,x-3.1754,20,6.3508,30,'#4b5563',.8,z=5)
rect(b,-75,50,150,4,colors['b210'],.9,z=6);rect(b,-61.1745,54,122.348,33.7,colors['b210'],.6,z=5)
boxline(b,-46.1,32.72,92.2,47,'#b94545',1.2,'--',7)
b.text(0,70,'B210 envelope',ha='center',color='white',weight='bold',fontsize=11,zorder=8)
b.text(0,17,'OZ closed housing',ha='center',va='center',color='#174f4d',fontsize=10)
b.text(0,41,'17.28 mm closed gap',ha='center',fontsize=9,color=colors['oz'])
dim(b,-107,0,50,'50 mm adapter underside');dim(b,109,0,87.7,'87.7 mm overall')
b.set_title('B210 over OZ',fontsize=14,weight='bold',pad=12)
fig.suptitle('SCE20 R2 · stack heights and service',fontsize=20,weight='bold',y=.96)
fig.text(.5,.90,'Envelope side views · native Ø5 stems to Z20, then 5.5 AF extension columns',ha='center',fontsize=11,color='#52616a')
fig.text(.275,.115,'Remove Peplink and carrier together for Bedrock service.\nCarrier removal preserves the lower thermal interfaces.',ha='center',fontsize=10,color=colors['router'],linespacing=1.5)
fig.text(.75,.115,'Remove B210/adapter before opening OZ.\nDashed red area shows the 47 mm outward service allowance.',ha='center',fontsize=10,color='#873a3a',linespacing=1.5)
fig.text(.5,.04,'Planning envelopes, not a sectioned manufacturing drawing.  Confirm actual cable access, fasteners, temperature and load capacity.',ha='center',fontsize=9,color='#52616a')
for ext in ['png','svg']:fig.savefig(OUT/f'SIDE_VIEW_R2.{ext}',dpi=180,facecolor='white')
plt.close(fig)
print('Created LAYOUT_R2 and SIDE_VIEW_R2 PNG/SVG drawings.')
