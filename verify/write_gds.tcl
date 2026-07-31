# Magic: write the TIA top cell to GDS for tapeout.
# Run:  magic -dnull -noconsole -rcfile env/.magicrc verify/write_gds.tcl
# Produces: tapeout/tia.gds
drc off
crashbackups stop
# Work where the .mag cells live so subcells resolve.
cd layout
load tia -dereference
select top cell
# Flatten nothing: keep hierarchy, write the sky130 GDS layer map from the tech.
gds write ../tapeout/tia.gds
puts "GDS written -> tapeout/tia.gds"
quit -noprompt
