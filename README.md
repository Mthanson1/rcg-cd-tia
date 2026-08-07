# mvm-tia-comp

130 nm Regulated-Cascode + Capacitive-Degeneration TIA (sky130A).
Reconstruction + layout/PEX of the design documented in `docs/main.tex`.

> **PDK:** sky130A (baked into the IIC-OSIC-TOOLS image). The original design doc
> targeted sky130B; this project uses sky130A -- device models/caps may differ
> slightly from the pre-layout numbers in the doc.

## Repository layout
```
ip/        xschem schematic (tia.sch)      (tracked)
layout/    magic .mag layout cells         (tracked)
sim/       testbenches + run scripts       (tracked)
verify/    DRC/LVS/PEX scripts + reports   (tracked)
env/       .magicrc .xschemrc .spiceinit   (tracked)
docs/      design doc (LaTeX) + figures    (tracked)
tapeout/   signed-off final GDS            (tracked)
artifacts/ transient netlists/logs/GDS     (git-ignored)
extern/    sky130A-gmid submodule (gm/Id)  (tracked)
```

## Launching the toolchain
From the host:
```bash
export DESIGNS=$HOME/ASIC/projects        # already in ~/.bashrc
cd ~/ASIC/toolbox/IIC-OSIC-TOOLS
./start_shell.sh                          # headless CLI  (or ./start_vnc.sh for GUI)
```
Inside the container the project is at `/foss/designs/mvm-tia-comp`. Select the PDK with
`export PDK=sky130A` (image default is ihp-sg13g2), then use the `env/` configs, e.g.:
```bash
cd /foss/designs/mvm-tia-comp
xschem --rcfile env/.xschemrc
magic  -rcfile env/.magicrc
```
