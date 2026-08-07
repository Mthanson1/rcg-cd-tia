# mvm-tia-comp

130 nm Regulated-Cascode + Capacitive-Degeneration TIA (sky130A).
Reconstruction + layout/PEX of the design documented in `docs/main.tex`.

> **PDK:** sky130A (baked into the IIC-OSIC-TOOLS image). The original design doc
> targeted sky130B; this project uses sky130A -- device models/caps may differ
> slightly from the pre-layout numbers in the doc.

## Just want to read it?
The full design report is committed as a PDF, so no toolchain is needed:
```bash
git clone https://github.com/Mthanson1/mvm-tia-comp.git
```
Then open `docs/main.pdf`. The rest of this README is only for re-running the
schematic, layout, simulation, or verification flows.

## Cloning for development
The gm/Id lookup data lives in a submodule (`extern/sky130A-gmid`), so clone
with submodules:
```bash
git clone --recurse-submodules https://github.com/Mthanson1/mvm-tia-comp.git
# already cloned?  ->  git submodule update --init --recursive
```
The submodule is only needed for the gm/Id sizing worksheet in `sim/`. **Every
other flow works without it** -- if the init fails, just skip it and continue.

## Prerequisites
- **[IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS)** -- a Docker
  image bundling xschem, magic, klayout, ngspice, netgen, and the sky130A PDK.
  This is the only dependency for the design/verification flows; install Docker,
  then follow that repo's README to fetch the image and launch a shell or VNC
  session with this project mounted.
- **A LaTeX distribution** with `latexmk` (TeX Live, MacTeX) -- only if you want
  to rebuild `docs/main.pdf` from source.

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
IIC-OSIC-TOOLS mounts the directory named by `$DESIGNS` at `/foss/designs`
inside the container. Point it at wherever you cloned this repo, then start a
shell (or `./start_vnc.sh` for the GUI):
```bash
export DESIGNS=/path/to/parent/of/mvm-tia-comp   # the repo's parent directory
cd /path/to/IIC-OSIC-TOOLS
./start_shell.sh                                 # headless CLI  (or ./start_vnc.sh for GUI)
```
Inside the container the project is then at `/foss/designs/mvm-tia-comp`. Select
the PDK with `export PDK=sky130A` (the image default is ihp-sg13g2), then use
the `env/` configs, e.g.:
```bash
cd /foss/designs/mvm-tia-comp
xschem --rcfile env/.xschemrc
magic  -rcfile env/.magicrc
```

## Rebuilding the design report
With a LaTeX distribution installed (`latexmk` + `pdflatex`):
```bash
cd docs
latexmk -pdf main.tex
```
