#!/usr/bin/env python3
"""Generate the RGC-CD TIA result figures for docs/ from the ngspice artifacts.

Reads the wrdata files in ../artifacts and writes PNGs into
../docs/Figures.  Run inside the IIC-OSIC-TOOLS container (numpy + matplotlib):

    export DESIGNS=$HOME/ASIC/projects
    docker run --rm -v "$DESIGNS":/foss/designs hpretl/iic-osic-tools:latest \
        -s bash -lc 'cd /foss/designs/mvm-tia-comp/sim && python3 plot_figures.py'

Regenerate the data first with ./run.sh if the design has changed.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "..", "artifacts")
FIG = os.path.join(HERE, "..", "docs", "Figures")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
})


def load(name):
    return np.loadtxt(os.path.join(ART, name))


def save(fig, name):
    path = os.path.join(FIG, name)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print("wrote", os.path.relpath(path, HERE))


# --== linearity ==--
# range_sweep.dat: Iin, vout, Iin, vin, Iin, vd1, Iin, vs3, Iin, gain
d = load("range_sweep.dat")
iin = d[:, 0] * 1e6          # uA
vout = d[:, 1]               # V
gain = d[:, 9]               # small-signal dVout/dIin  [V/A = ohm]

fig, ax1 = plt.subplots(figsize=(7, 4.2))
ax1.plot(iin, vout, color="C0", lw=1.8, label=r"$V_{out}$")
ax1.set_xlabel(r"Input current $I_{in}$  [$\mu$A]")
ax1.set_ylabel(r"$V_{out}$  [V]", color="C0")
ax1.tick_params(axis="y", labelcolor="C0")

# small-signal transimpedance vs operating point (linearity of the gain)
ax2 = ax1.twinx()
ax2.grid(False)
ax2.plot(iin, np.abs(gain), color="C3", lw=1.4, alpha=0.9,
         label=r"$|dV_{out}/dI_{in}|$")
ax2.set_ylabel(r"Small-signal $|Z_T|$  [$\Omega$]", color="C3")
ax2.tick_params(axis="y", labelcolor="C3")
ax2.set_ylim(0, 2000)

# +/-10% linear window on the transimpedance
z0 = np.abs(gain[np.argmin(np.abs(iin - 0.0))])
lin = np.abs(np.abs(gain) - z0) <= 0.10 * z0
if lin.any():
    lo, hi = iin[lin].min(), iin[lin].max()
    ax1.axvspan(lo, hi, color="C2", alpha=0.10)
    ax1.text(0.5 * (lo + hi), ax1.get_ylim()[1],
             f"$\\pm$10% linear\n{lo:.0f} to {hi:.0f} $\\mu$A",
             ha="center", va="top", fontsize=9, color="C2")

ax1.axvline(0, color="0.5", lw=0.8, ls=":")
ax1.set_title("Input linearity: DC transfer and small-signal transimpedance")
lines = ax1.get_lines()[:1] + ax2.get_lines()[:1]
ax1.legend(lines, [l.get_label() for l in lines], loc="upper right", fontsize=9)
save(fig, "tia_linearity.png")


# --== freq response WITH realistic loading + CD-stage effect ==--
# Realistic loading (C_T=500fF input, C_L=1pF ADC load) so the design sees a
# physical dominant pole.  Two traces isolate the capacitive degenerator:
#   ac_response_loaded.dat -- with C1  (CD zero cancels the load pole -> flat)
#   ac_response_nocap.dat  -- C1 removed (no zero -> rolls off at the load pole)
def f3db(f, mag):
    # last frequency still within 3 dB of DC -- matches the ngspice `meas ...
    # fall=1` / sizing_worksheet.py convention.
    b = np.where(mag >= mag[0] - 3.0)[0]
    return f[b[-1]] if b.size else None

lp_path = os.path.join(ART, "ac_response_loaded.dat")
nc_path = os.path.join(ART, "ac_response_nocap.dat")
if os.path.exists(lp_path):
    al = np.loadtxt(lp_path)
    fL, magL = al[:, 0], al[:, 1]
    f3dbL = f3db(fL, magL)

    fig, ax1 = plt.subplots(figsize=(7, 4.2))
    ax1.semilogx(fL, magL, color="C0", lw=2.0,
                 label="With cap. degeneration ($C_1$)")
    ax1.set_xlabel("Frequency [Hz]")
    ax1.set_ylabel(r"$|Z_T|$  [dB$\Omega$]")

    if os.path.exists(nc_path):
        an = np.loadtxt(nc_path)
        fN, magN = an[:, 0], an[:, 1]
        f3dbN = f3db(fN, magN)
        ax1.semilogx(fN, magN, color="C1", lw=1.6, ls="--",
                     label="Without $C_1$ (resistive degen only)")
        if f3dbN is not None:
            ax1.axvline(f3dbN, color="C1", lw=0.8, ls=":")
            ax1.annotate(f"{f3dbN/1e6:.0f} MHz",
                         xy=(f3dbN, magN[0] - 3), xytext=(f3dbN / 12, magL[0] - 17),
                         fontsize=9, color="C1",
                         arrowprops=dict(arrowstyle="->", color="C1"))

    # real-device overlay: same TB but with sky130 poly-R + MIM-C (tia_core_dev)
    dv_path = os.path.join(ART, "ac_response_loaded_dev.dat")
    f3dbD = None
    if os.path.exists(dv_path):
        ad = np.loadtxt(dv_path)
        fD, magD = ad[:, 0], ad[:, 1]
        f3dbD = f3db(fD, magD)
        ax1.semilogx(fD, magD, color="C4", lw=1.7, ls=":",
                     label="Real sky130 devices (with $C_1$)")
        if f3dbD is not None:
            ax1.axvline(f3dbD, color="C4", lw=0.8, ls=":")

    # post-layout overlay: magic parasitic-extracted netlist (tia_pex.spice)
    px_path = os.path.join(ART, "ac_response_loaded_pex.dat")
    f3dbP = None
    if os.path.exists(px_path):
        ap = np.loadtxt(px_path)
        fP, magP = ap[:, 0], ap[:, 1]
        f3dbP = f3db(fP, magP)
        ax1.semilogx(fP, magP, color="C3", lw=1.7, ls="-.",
                     label="Post-layout (parasitic-extracted)")
        if f3dbP is not None:
            ax1.axvline(f3dbP, color="C3", lw=0.8, ls=":")

    if f3dbL is not None:
        ax1.axhline(magL[0] - 3, color="0.6", lw=0.8, ls=":")
        ax1.axvline(f3dbL, color="C0", lw=0.8, ls=":")
        bwtxt = f"ideal {f3dbL/1e6:.0f} MHz"
        if f3dbD is not None:
            bwtxt += f"\nreal  {f3dbD/1e6:.0f} MHz"
        if f3dbP is not None:
            bwtxt += f"\nPEX   {f3dbP/1e6:.0f} MHz"
        ax1.annotate(bwtxt,
                     xy=(f3dbL, magL[0] - 3), xytext=(f3dbL * 1.6, magL[0] + 2),
                     fontsize=9, color="0.2", va="top",
                     arrowprops=dict(arrowstyle="->", color="0.4"))
        # bandwidth-extension callout
        if os.path.exists(nc_path) and f3dbN:
            ax1.annotate(f"CD stage extends BW\n{f3dbN/1e6:.0f} MHz $\\to$ {f3dbL/1e6:.0f} MHz "
                         f"(${f3dbL/f3dbN:.0f}\\times$)",
                         xy=(0.03, 0.30), xycoords="axes fraction",
                         fontsize=9, color="0.25")

    ax1.set_ylim(magL[0] - 25, magL[0] + 5)
    ax1.set_title(r"Effect of capacitive degeneration ($C_T=500\,$fF, $C_L=1\,$pF)")
    ax1.legend(loc="lower left", fontsize=9)
    save(fig, "tia_freq_response_loaded.png")


# --== phase margin ==--
# loopgain.dat:     f, |L|dB, f, ph(L)[deg]   (ideal passives)
# loopgain_dev.dat: same, with real sky130 R/C devices (overlay)
def crossover(fl, lm, lp):
    """0 dB crossover freq, phase there, and PM, via log-f interpolation."""
    cr = np.where(lm <= 0.0)[0]
    if not cr.size:
        return None, None, None
    i = cr[0]
    f0 = np.interp(0.0, [lm[i], lm[i - 1]], [fl[i], fl[i - 1]])
    ph0 = np.interp(0.0, [lm[i], lm[i - 1]], [lp[i], lp[i - 1]])
    return f0, ph0, 180 + ph0

lg = load("loopgain.dat")
fl, lm, lp = lg[:, 0], lg[:, 1], lg[:, 3]
f0, ph0, pm = crossover(fl, lm, lp)

fig, (axm, axp) = plt.subplots(2, 1, figsize=(7, 5.2), sharex=True)
axm.semilogx(fl, lm, color="C0", lw=1.8, label="ideal passives")
axm.axhline(0, color="0.5", lw=0.8, ls=":")
axm.set_ylabel(r"Loop gain $|L|$  [dB]")
axm.set_title("RGC regulation loop -- gain and phase margin")

axp.semilogx(fl, lp, color="C1", lw=1.8)
axp.axhline(-180, color="0.5", lw=0.8, ls=":")
axp.set_ylabel(r"$\angle L$  [deg]")
axp.set_xlabel("Frequency [Hz]")

# real-device overlay (tia_core_dev)
dev_path = os.path.join(ART, "loopgain_dev.dat")
f0d = pmd = None
if os.path.exists(dev_path):
    lgd = np.loadtxt(dev_path)
    fld, lmd, lpd = lgd[:, 0], lgd[:, 1], lgd[:, 3]
    f0d, ph0d, pmd = crossover(fld, lmd, lpd)
    axm.semilogx(fld, lmd, color="C4", lw=1.5, ls="--", label="real sky130 devices")
    axp.semilogx(fld, lpd, color="C4", lw=1.5, ls="--")

if f0 is not None:
    for ax in (axm, axp):
        ax.axvline(f0, color="C3", lw=0.9, ls="--")
    axm.plot(f0, 0, "o", color="C3", ms=5)
    axp.plot(f0, ph0, "o", color="C3", ms=5)
    txt = f"PM = {pm:.0f}$^\\circ$ @ {f0/1e9:.2f} GHz  (ideal)"
    if pmd is not None:
        txt += f"\nPM = {pmd:.0f}$^\\circ$ @ {f0d/1e9:.2f} GHz  (real)"
    axp.annotate(txt, xy=(f0, ph0), xytext=(0.04, 0.20),
                 textcoords="axes fraction", fontsize=9,
                 arrowprops=dict(arrowstyle="->", color="C3"))
axm.legend(loc="lower left", fontsize=8)
save(fig, "tia_phase_margin.png")


# --== noise spectrum ==--
# noise_spectrum.dat: f, inoise[A/rtHz], f, onoise[V/rtHz]  (27 C)
# ngspice stores the *linear* spectral density (rms per rtHz), not squared.
ns = load("noise_spectrum.dat")
fn = ns[:, 0]
in_dens = ns[:, 1] * 1e12   # pA/sqrt(Hz)

fig, ax = plt.subplots(figsize=(7, 4.2))
ax.loglog(fn, in_dens, color="C0", lw=1.8)
ax.set_xlabel("Frequency [Hz]")
ax.set_ylabel(r"Input-referred noise  [pA/$\sqrt{\mathrm{Hz}}$]")
ax.set_title(r"Input-referred current-noise spectral density (27$^\circ$C)")
# annotate the thermal (white) floor -- median over the flat mid-band decade
mid = (fn > 1e5) & (fn < 3e6)
floor = np.median(in_dens[mid])
ax.axhline(floor, color="C3", lw=0.9, ls="--")
ax.text(fn[0] * 2, floor * 1.05,
        f"thermal floor $\\approx$ {floor:.1f} pA/$\\sqrt{{Hz}}$",
        color="C3", fontsize=9, va="bottom")
save(fig, "tia_noise_spectrum.png")


# --== s-plane pole/zero map ==--
# First-order singularities of the LOADED transimpedance Z_T(s), taken from the
# gm/Id sizing worksheet (sim/sizing_worksheet.py, SPICE-verified design):
#   CD zero      f_z   =  1/(2pi R5 C1)
#   output pole  f_out =  1/(2pi R3 C_L)     <- set by the ADC load C_L
#   CD pole      f_p   =  (1+gm3 R5)/(2pi R5 C1)
#   transimp.    f_D1  =  1/(2pi R1 C_D1)
#   input pole   f_in  =  1/(2pi Zin C_T)    <- set by the input load C_T
#   aux pole     f_aux =  1/(2pi R2 C_D2)
# All singularities are real (LHP), so the s-plane collapses onto the negative
# real axis; we plot sigma/2pi = -f on a *symlog* axis (a pure log axis can't
# show negative sigma but symlog is log-compressed in magnitude while staying 
# signed).  Placing the CD zero on the output (load) pole cancels it and hands
# the dominant-pole role to the ~GHz cluster.
from matplotlib.lines import Line2D

poles = [                       # (label, freq [Hz], category)
    (r"$f_\mathrm{out}$", 40e6,  "load"),
    (r"$f_p$",            827e6, "cd"),
    (r"$f_{D1}$",         2.13e9, "intrinsic"),
    (r"$f_\mathrm{in}$",  2.42e9, "load"),
    (r"$f_\mathrm{aux}$", 5.56e9, "intrinsic"),
]
zeros = [(r"$f_z$", 40e6, "cd")]
col = {"load": "C3", "cd": "C0", "intrinsic": "0.5"}

fig, ax = plt.subplots(figsize=(7.6, 3.4))
ax.axhline(0, color="0.35", lw=1.0)                      # the real (sigma) axis
# Poles/zeros sit on the negative real axis at sigma/2pi = -f.
# per-label (dx, dy) offsets in points; f_D1/f_in are close in frequency so
# they are staggered vertically and nudged apart horizontally to stay legible.
# (on the negated axis f_D1 is to the RIGHT of f_in, so the nudges swap sign.)
lbl_off = {r"$f_\mathrm{out}$": (0, 26), r"$f_p$": (0, 14),
           r"$f_{D1}$": (14, 26), r"$f_\mathrm{in}$": (-12, 14),
           r"$f_\mathrm{aux}$": (0, 14)}
for name, f, cat in poles:
    ax.plot(-f, 0, marker="x", ms=11, mew=2.4, color=col[cat], zorder=3)
    ax.annotate(name, (-f, 0), xytext=lbl_off[name], textcoords="offset points",
                ha="center", fontsize=9.5, color=col[cat])
for name, f, cat in zeros:
    ax.plot(-f, 0, marker="o", ms=15, mfc="none", mew=2.4, color=col[cat], zorder=4)
    ax.annotate(name, (-f, 0), xytext=(0, -22), textcoords="offset points",
                ha="center", fontsize=9.5, color=col[cat])

# symlog: log-compressed in magnitude but signed, so the negative real axis is
# representable (a plain "log" scale cannot show sigma < 0).
ax.set_xscale("symlog", linthresh=1e7)
ax.set_xlim(-9e9, -1.2e7)
ax.set_ylim(-1.1, 1.1)
ax.set_yticks([])
ax.grid(True, axis="x", alpha=0.3)
ax.set_xlabel(r"Real axis  $\sigma/2\pi$ [Hz]"
              r"  (all poles/zeros real, left-half plane; symlog)")

# cancellation callout at CD zero (f_z sits on f_out)
ax.annotate("CD zero cancels\nthe load pole", xy=(-40e6, 0.12), xytext=(-1.6e8, 0.72),
            ha="center", fontsize=9, color="C0",
            arrowprops=dict(arrowstyle="->", color="C0"))
# dominant-pole shift + achieved bandwidth (moves LEFT, deeper into the LHP)
ax.annotate("", xy=(-631e6, 0.42), xytext=(-40e6, 0.42),
            arrowprops=dict(arrowstyle="->", color="0.25", lw=1.4))
ax.text(-1.7e8, 0.55, "dominant pole moves out", fontsize=8.5,
        color="0.25", ha="center")
ax.axvline(-631e6, color="C2", lw=1.4, ls="--", zorder=2)
ax.annotate(r"sim $f_{-3\mathrm{dB}}=631$ MHz", xy=(-631e6, -0.7),
            ha="center", fontsize=9, color="C2")

leg = [Line2D([0], [0], marker="x", color="C3", lw=0, mew=2, label="load-induced pole"),
       Line2D([0], [0], marker="x", color="0.5", lw=0, mew=2, label="intrinsic pole"),
       Line2D([0], [0], marker="o", color="C0", lw=0, mfc="none", mew=2, label="CD zero")]
ax.legend(handles=leg, loc="lower left", fontsize=8, framealpha=0.9)
ax.set_title("First-order s-plane map: CD zero cancels the load pole to extend bandwidth")
save(fig, "tia_splane.png")

print("done")
