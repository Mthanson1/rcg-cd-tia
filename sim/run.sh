#!/usr/bin/env bash
# Run all RGC-CD TIA testbenches with ngspice.
#
# Inside the IIC-OSIC-TOOLS container:
#     cd /foss/designs/mvm-tia-comp/sim && ./run.sh
#
# From the host (headless, one-shot):
#     export DESIGNS=$HOME/ASIC/projects
#     docker run --rm -e PDK=sky130A -v "$DESIGNS":/foss/designs \
#         hpretl/iic-osic-tools:latest -s bash -lc \
#         'cd /foss/designs/mvm-tia-comp/sim && ./run.sh'
set -e
: "${PDK:=sky130A}"; export PDK
mkdir -p ../artifacts
for tb in tb_op tb_dc tb_ac tb_ac_realistic tb_ac_load tb_ac_tune tb_noise tb_range; do
    echo "############################## $tb ##############################"
    ngspice -b "$tb.spice"
done
