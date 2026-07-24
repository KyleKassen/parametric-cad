# Industrial design language

Distilled from Kyle's reference set (2026-07-24): five product shots of
TRIYOSYS-class pan-tilt positioners. Applies to every custom part in this
repo whose exterior anyone will see. Engineering geometry (seal planes,
thermal paths, clearances) is never compromised for styling; the styling
vocabulary is chosen so it *adds* stiffness, drainage, or airflow function
wherever possible.

## The vocabulary

1. **No raw edges.** Every visible plan corner carries a generous radius
   (R8-R16 on enclosure-scale parts); every visible rim or flange edge gets
   a chamfer or step. A knife-edged extruded box is never a finished part.
2. **Sculpted walls, not slabs.** Large flat faces carry a recessed panel
   (1.5-2 mm) with a rounded-corner boundary, leaving a proud perimeter
   frame. Inside the recess: chevron/X stiffening ribs, triangulated webs,
   or a clean field. Minimum structural wall thickness is preserved under
   every recess.
3. **Fastener rhythm.** Visible screws are counterbored socket heads at a
   regular pitch, inset consistently from edges, symmetric about
   centerlines. Fasteners are part of the composition — never scattered.
4. **Radiused base flange.** Floor-standing or mast-mounted assemblies end
   in a square/rectangular flange with large corner radii and a chamfered
   or stepped edge. Corner holes only when the mating pattern is actually
   released.
5. **Functional texture.** Louver scallops at air paths, ribbing where
   stiffness is wanted, drip edges over apertures. Texture must earn its
   place: it cools, sheds water, or stiffens.
6. **Machined identity details.** One emblem per product face maximum:
   embossed logo or concentric-ring/crosshair motif, shallow (<=1 mm),
   centered on a panel. Circular hubs get concentric step rings and bolt
   circles.
7. **Blend transitions.** Where prismatic meets cylindrical (pedestals,
   pods), use large shoulder radii or a deliberate step — never an abrupt
   butt joint.
8. **Uniform finish.** Matte black or dark gray across the assembly;
   connectors and gaskets are the only contrast elements.

## CadQuery execution rules

- Bake plan radii into the base solids (`box(...).edges("|Z").fillet(r)`
  on simple prisms) *before* boolean operations; avoid late fillets on
  complex unions — that is the main kernel-failure risk.
- Recessed panels: cut a rounded-corner prism 1.5-2 mm deep, then union
  ribs back inside, intersected with the pocket volume.
- Chamfers: apply on lone simple solids (e.g. a crown plate's top edges)
  before unioning onto the parent.
- Counterbores: plain cylinder cuts (head Ø + through Ø), always on flat
  lands, never on slopes.
- Keep a `build_stages()` generator current so styling failures bisect.

## Render presentation rules

- `render_scene(..., axes=False)` for anything shown to a human; axis
  triads are for verification views only.
- Dark matte palette: body (0.16-0.20 gray), accents slightly lighter;
  translucency only in engineering/fit views, not product shots.
- Hero view: three-quarter iso from slightly above; supporting views as
  needed. White or light-neutral background.
