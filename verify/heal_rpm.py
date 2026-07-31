# KLayout heal pass for the TIA GDS: fix rpm.1a (min rpm width) in resbank.
#
# The res_high_po_0p35 resistors are placed with staggered tops, so magic's
# generated rpm (86/20) leaves an isolated 0.75um-wide finger < 1.27um min.
# Fill the rpm envelope of the resbank cell with a single covering box: this
# only fills the interior notch (the outer boundary is unchanged, so no new
# rpm spacing / precision-resistor rules are triggered) yet makes the mask
# >=1.27um wide everywhere.
#
# Run:  klayout -b -r verify/heal_rpm.py -rd gds=tapeout/tia.gds
import pya, sys

gds = None
for a in sys.argv:
    if a.startswith("gds="):
        gds = a.split("=", 1)[1]
gds = gds or "tapeout/tia.gds"

RPM = (86, 20)
CELL = "resbank"

ly = pya.Layout()
ly.read(gds)
li = ly.layer(*RPM)
cell = ly.cell(CELL)
if cell is None:
    raise SystemExit(f"heal_rpm: cell {CELL} not found in {gds}")

# Recursive rpm region (pcell strips + resbank-level shapes), in resbank frame.
reg = pya.Region(pya.RecursiveShapeIterator(ly, cell, li))
reg.merge()
if reg.is_empty():
    raise SystemExit(f"heal_rpm: no rpm (86/20) found under {CELL}")

bb = reg.bbox()
cell.shapes(li).insert(pya.Box(bb))
ly.write(gds)
print(f"heal_rpm: filled rpm envelope in {CELL} -> "
      f"[{bb.left*ly.dbu:.3f},{bb.bottom*ly.dbu:.3f} .. "
      f"{bb.right*ly.dbu:.3f},{bb.top*ly.dbu:.3f}] um; wrote {gds}")
