#!/usr/bin/env bash
# GDS writer for the RGC-CD TIA (sky130A) -- run inside IIC-OSIC-TOOLS.
#
# From the host:
#   docker exec iic-osic-tools_xvnc_uid_1000 bash -lc \
#     'cd /foss/designs/mvm-tia-comp && verify/write_gds.sh'
#
set -e
# Force sky130A: the IIC-OSIC-TOOLS container defaults PDK=ihp-sg13g2, so a
# ':=' default would NOT override it. This design is sky130A.
export PDK=sky130A
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "### Write GDS (magic -> tapeout/tia.gds)"
magic -dnull -noconsole -rcfile env/.magicrc verify/write_gds.tcl 2>&1 \
      | grep -viE "INFO\]|read from|Reading|Processing" || true

GDS="tapeout/tia.gds"

if [ -s "$GDS" ]; then
  echo
  echo "### GDS written: $GDS ($(du -h "$GDS" | cut -f1))"
else
  echo "### ERROR: $GDS was not produced" >&2
  exit 1
fi
