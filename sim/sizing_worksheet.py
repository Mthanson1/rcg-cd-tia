#!/usr/bin/env python3
# ============================================================
# RGC-CD TIA sizing worksheet  (gm/Id method, sky130A)
#
# Top-down flow: Choose, per device, a bias current and a gm/Id.
# The bias-plan (resistor/current budget) fixes every node voltage. 
# The worksheet then looks up the current density Jd(gm/Id, Vsb, Vds)
# from the sky130-gmid grid and returns W = Id/Jd, gm, ro, gm.ro, fT,
# plus the first-order small-signal hand-calcs (Zin, transimpedance,
# the full first-order pole/zero set -- input, aux-loop, transimpedance,
# degeneration zero/pole, output -- plus power) so a candidate sizing
# can be validated at a glance against SPICE.
#
# Run (numpy needed -> use the toolchain container):
#   export DESIGNS=$HOME/ASIC/projects
#   docker run --rm -v "$DESIGNS":/foss/designs hpretl/iic-osic-tools:latest \
#     -s bash -lc 'python3 /foss/designs/mvm-tia-comp/sim/sizing_worksheet.py'
#
# SPICE verify (--spice): runs the DESIGN through ngspice (op/ac/dc on
# tia_core.spice) and prints predicted vs actual (currents, bias nodes, DC
# gain, power, bandwidth/peaking, saturation, usable input range).  Needs
# ngspice + $PDK_ROOT, so run in the container:
#   docker run --rm -e PDK=sky130A -e PDK_ROOT=/foss/pdks \
#     -v "$DESIGNS":/foss/designs hpretl/iic-osic-tools:latest -s bash -lc \
#     'cd /foss/designs/mvm-tia-comp/sim && python3 sizing_worksheet.py --spice'
#
# NOTE (first-order): the hand-calcs use gm*R (ignore ro in Zin/gain
# unless noted), assume the bias loop self-consistently reaches the
# chosen currents, and read Jd at the nearest grid VSB/VDS. Treat the
# output as a starting point that SPICE then refines (~few % on W).
# Internal-node poles (V_D1, V_D2) use a gate-cap-dominated estimate
# (C ~ Cgg of the loaded gate, back-calculated from fT); the grid has
# no Cgd/Cdb, so drain/overlap and Miller caps are NOT included -- these
# poles are optimistic. Override C_D1/C_D2 in DESIGN for a tighter bound.
# ============================================================
import os
import re
import sys
import shutil
import tempfile
import subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KT = 1.380649e-23 * 300.0

# The gm/Id grid loader + (Vsb, Vds, gm/Id) interpolation lives in the
# sky130A-gmid repo, vendored here as the `extern/sky130A-gmid` git
# submodule and imported as the `gmid` package.  Run `git submodule update
# --init` after cloning.  The sys.path insert keeps this runnable in the
# ephemeral container; once the submodule is `pip install -e`'d (or on
# PYTHONPATH), the insert can be dropped.
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "extern", "sky130A-gmid")))
from gmid import GmidGrid


# ============================================================
#  Design input:  currents + gm/Id per device, + passives
#  (defaults = SPICE-verified MAX-BW / MIN-CURRENT RGC-CD for a 1 pF ADC load
#   and a single-sided (unidirectional) input: 59.4 dBohm DC / 0.33 mW,
#   f-3dB ~631 MHz, AC peaking ~0 dB, V_out~1.67 V (parked high for a
#   down-swinging sourcing input), usable input range -85..+65 uA.
#   Recipe: starve the front-end (I1,I2 set no BW -- only Zin margin); large
#   R5 (22.5k) + low I3 -> big gm3.R5 = (gm/Id).V_S3 -> big f_p at low current;
#   f_z = f_out cancels the output pole (R5*C1 = R3*C_L = 4 ns).  Id below are
#   the sizing TARGETS (they set W); SPICE OP settles at ~68/80/33 uA.  Verify
#   with --spice.  Mirrors sim/tia_core.spice.  NOTE: the ~+17 dB tb_ac peak is
#   an *unloaded* artifact -- the real 1 pF load damps it to ~0 dB.)
# ============================================================
DESIGN = dict(
    VDD=1.8,
    # RGC input stage (M1 cascode, M2 aux CS) and CD output stage (M3)
    #   device:  Id [A],   gm/Id [1/V]   (target Id -> sets W; SPICE OP differs)
    M1=dict(Id=60e-6, gmid=18.0),
    M2=dict(Id=55e-6, gmid=18.0),
    M3=dict(Id=40e-6, gmid=22.0),
    # passives (ohms / farads)
    R1=6.5e3, R2=6e3, R3=4e3, R4=9e3, R5=22.5e3, C1=178e-15,
    # environment
    C_T=500e-15,     # total input node cap (photodiode + pad + Cgs1)
    C_L=1e-12,       # output load cap (typical high-speed ADC sampling input)
    C_D1=None,       # RGC output / M3-gate node cap  (auto = Cgg3 if None)
    C_D2=None,       # aux output / M1-gate node cap  (auto = Cgg1 if None)
)


def size_device(grid, name, Id, gmid, Vsb, Vds):
    lu = grid.lookup(gmid, Vsb, Vds)
    Jd = lu["jd"]                     # uA/um
    W = Id / (Jd * 1e-6)              # um  (Id in A, Jd in A/um = Jd*1e-6)
    gm = gmid * Id
    ro = lu["gmro"] / gm
    Cgg = gm / (2 * np.pi * lu["ft"])          # total gate cap, back-out from fT
    return dict(name=name, Id=Id, gmid=gmid, Vsb=Vsb, Vds=Vds,
                Vov=2.0 / gmid, Jd=Jd, W=W, gm=gm, ro=ro,
                gmro=lu["gmro"], ft=lu["ft"], Cgg=Cgg)


def run(d=DESIGN):
    grid = GmidGrid()
    VDD = d["VDD"]
    I1, I2, I3 = d["M1"]["Id"], d["M2"]["Id"], d["M3"]["Id"]
    R1, R2, R3, R4, R5 = d["R1"], d["R2"], d["R3"], d["R4"], d["R5"]

    # --== bias plan: node voltages fall out of the current budget ==--
    V_D1 = VDD - I1 * R1          # RGC output / M3 gate
    V_vin = I1 * R4              # input node = M1 source
    V_D2 = VDD - I2 * R2          # M1 gate (aux amp output)
    V_out = VDD - I3 * R3
    V_S3 = I3 * R5

    # --== per-device Vds / Vsb (bulk at gnd) ==--
    dev = [
        size_device(grid, "M1", I1, d["M1"]["gmid"], Vsb=V_vin, Vds=V_D1 - V_vin),
        size_device(grid, "M2", I2, d["M2"]["gmid"], Vsb=0.0,   Vds=V_D2),
        size_device(grid, "M3", I3, d["M3"]["gmid"], Vsb=V_S3,  Vds=V_out - V_S3),
    ]
    m1, m2, m3 = dev

    # --== first-order small-signal hand-calcs ==--
    A_aux = m2["gm"] * R2                       # regulating aux gain
    Zin = 1.0 / (m1["gm"] * (1 + A_aux))        # RGC input R (|| R4)
    Zin = Zin * R4 / (Zin + R4)
    f_in = 1.0 / (2 * np.pi * Zin * d["C_T"])
    ZT_rgc = R1                                 # node D1 transimpedance
    Av3_dc = m3["gm"] * R3 / (1 + m3["gm"] * R5)
    Av3_hf = m3["gm"] * R3
    f_z = 1.0 / (2 * np.pi * R5 * d["C1"])
    f_p = (1 + m3["gm"] * R5) / (2 * np.pi * R5 * d["C1"])
    ZT_dc = ZT_rgc * Av3_dc
    ZT_hf = ZT_rgc * Av3_hf
    f_out = 1.0 / (2 * np.pi * R3 * d["C_L"])
    # internal-node poles (gate-cap-dominated estimate; grid gives Cgg only)
    C_D1 = d["C_D1"] or m3["Cgg"]               # RGC output / M3 gate node
    C_D2 = d["C_D2"] or m1["Cgg"]               # aux output / M1 gate node
    f_D1 = 1.0 / (2 * np.pi * R1 * C_D1)        # transimpedance-node pole
    f_aux = 1.0 / (2 * np.pi * R2 * C_D2)       # aux-loop (regulation) pole
    Ptot = VDD * (I1 + I2 + I3)
    in_R4 = np.sqrt(4 * KT / R4)                # input-node thermal current noise

    # ================= report =================
    def dbohm(z):
        return 20 * np.log10(abs(z))
    print("=" * 68)
    print(" RGC-CD TIA sizing worksheet  (sky130A, nfet L=0.15, gm/Id method)")
    print("=" * 68)
    print(f" VDD={VDD} V   nodes:  V_in={V_vin:.3f}  V_D1={V_D1:.3f} "
          f" V_D2={V_D2:.3f}  V_out={V_out:.3f}  V_S3={V_S3:.3f}")
    print("-" * 68)
    hdr = ("dev", "Id_uA", "gm/Id", "Vsb", "Vds", "Vov", "sat?",
           "Jd", "W_um", "gm_mS", "gm.ro", "fT_GHz")
    print(" {:<3} {:>6} {:>5} {:>5} {:>5} {:>5} {:>4} {:>5} {:>6} {:>6} {:>6} {:>7}"
          .format(*hdr))
    for m in dev:
        sat = "ok" if m["Vds"] > m["Vov"] + 0.05 else "LOW"
        print(" {:<3} {:>6.1f} {:>5.1f} {:>5.3f} {:>5.3f} {:>5.3f} {:>4} "
              "{:>5.2f} {:>6.1f} {:>6.2f} {:>6.1f} {:>7.1f}".format(
                  m["name"], m["Id"] * 1e6, m["gmid"], m["Vsb"], m["Vds"],
                  m["Vov"], sat, m["Jd"], m["W"], m["gm"] * 1e3,
                  m["gmro"], m["ft"] / 1e9))
    print("-" * 68)
    print(" RGC input:")
    print(f"   A_aux = gm2.R2               = {A_aux:6.1f} V/V")
    print(f"   Zin   = 1/(gm1(1+A_aux))||R4 = {Zin:6.1f} ohm")
    print(" Transimpedance:")
    print(f"   Z_T,DC  = R1.Av3_dc = {ZT_dc:7.0f} ohm ({dbohm(ZT_dc):5.1f} dBohm)")
    print(f"   Z_T,HF  = R1.Av3_hf = {ZT_hf:7.0f} ohm ({dbohm(ZT_hf):5.1f} dBohm)")
    sings = [
        ("f_in",  "P", f_in,  "input node V_in",  "1/(2pi.Zin.C_T)"),
        ("f_aux", "P", f_aux, "aux loop V_D2",    "1/(2pi.R2.C_D2)"),
        ("f_D1",  "P", f_D1,  "transimp. V_D1",   "1/(2pi.R1.C_D1)"),
        ("f_z",   "Z", f_z,   "CD degen.",        "1/(2pi.R5.C1)"),
        ("f_p",   "P", f_p,   "CD degen.",        "(1+gm3.R5)/(2pi.R5.C1)"),
        ("f_out", "P", f_out, "output node V_out", "1/(2pi.R3.C_L)"),
    ]
    sings.sort(key=lambda s: s[2])
    caps = {"f_in": d["C_T"], "f_aux": C_D2, "f_D1": C_D1, "f_out": d["C_L"]}
    print(" Poles (P) & zeros (Z), first-order, low -> high:")
    for nm, kind, f, where, expr in sings:
        cap = caps.get(nm)
        ann = f"   [C={cap*1e15:.1f} fF]" if cap else ""
        print(f"   {kind}  {nm:<6}{f/1e9:8.3f} GHz  {where:<18}{expr}{ann}")
    print(" Budget:")
    print(f"   P_total = VDD.(I1+I2+I3) = {Ptot*1e3:.2f} mW")
    print(f"   input-node thermal noise (R4) = {in_R4*1e12:.2f} pA/rtHz")
    print("=" * 68)

    # predicted metrics returned for the SPICE verify mode (see spice_verify)
    return dict(
        dev=dev,
        nodes=dict(V_in=V_vin, V_D1=V_D1, V_D2=V_D2, V_out=V_out, V_S3=V_S3),
        I=dict(M1=I1, M2=I2, M3=I3),
        ZT_dc=ZT_dc, ZT_dc_db=dbohm(ZT_dc),
        f_p=f_p, f_in=f_in, Ptot=Ptot,
    )


# ============================================================
#  SPICE verify mode  (--spice):  run the DESIGN through ngspice and
#  print predicted (hand-calc) vs actual (SPICE) side by side.
#  Must run inside the iic-osic-tools container (ngspice + $PDK_ROOT).
# ============================================================
_CORE = os.path.join(HERE, "tia_core.spice")


def _spice_deck(d, dev, acfile, dcfile):
    """Generate a self-contained deck: op + ac + dc-range on tia_core,
    with the DESIGN's W/R overridden on the Xtia line and C1 via alterparam."""
    w = {m["name"]: m["W"] for m in dev}
    return f"""* sizing_worksheet.py --spice verify (generated, temporary)
.lib $PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include {_CORE}
.param VDD={d['VDD']}
Vdd vdd 0 {{VDD}}
Iin 0 vin dc 0 ac 1
Xtia vin vout vdd 0 tia_core
+ W1={w['M1']:.4g} W2={w['M2']:.4g} W3={w['M3']:.4g}
+ R1={d['R1']:.6g} R2={d['R2']:.6g} R3={d['R3']:.6g} R4={d['R4']:.6g} R5={d['R5']:.6g}
CT vin  0 {d['C_T']:.6g}
CL vout 0 {d['C_L']:.6g}
.control
alterparam CDEG = {d['C1']:.6g}
reset
op
print v(vin) v(xtia.d1) v(xtia.d2) v(vout) v(xtia.s3) i(vdd)
ac dec 50 1k 10G
wrdata {acfile} vdb(vout)
dc Iin -600u 400u 5u
wrdata {dcfile} v(vout) v(vin) v(xtia.d1) v(xtia.s3)
.endc
.end
"""


def _fnum(text, name):
    m = re.search(re.escape(name) + r"\s*=\s*([-+0-9.eE]+)", text)
    return float(m.group(1)) if m else float("nan")


def _parse_spice(out, acfile, dcfile, d):
    VDD = d["VDD"]
    sp = {}
    # --- operating point node voltages ---
    Vin = _fnum(out, "v(vin)")
    Vd1 = _fnum(out, "v(xtia.d1)")
    Vd2 = _fnum(out, "v(xtia.d2)")
    Vout = _fnum(out, "v(vout)")
    Vs3 = _fnum(out, "v(xtia.s3)")
    ivdd = _fnum(out, "i(vdd)")
    sp["nodes"] = dict(V_in=Vin, V_D1=Vd1, V_D2=Vd2, V_out=Vout, V_S3=Vs3)
    # branch currents from node voltages (R values known)
    sp["I"] = dict(M1=Vin / d["R4"], M2=(VDD - Vd2) / d["R2"],
                   M3=(VDD - Vout) / d["R3"])
    sp["Ptot"] = abs(ivdd) * VDD
    sp["Vds"] = dict(M1=Vd1 - Vin, M2=Vd2, M3=Vout - Vs3)
    # --- AC: DC gain, peak, -3dB (relative to DC) ---
    try:
        a = np.loadtxt(acfile)
        f, mag = a[:, 0], a[:, 1]
        gdc = mag[0]
        ipk = int(np.argmax(mag))
        sp["gdc_db"] = gdc
        sp["gpk_db"] = mag[ipk]
        sp["fpk"] = f[ipk]
        below = f[mag >= gdc - 3.0]
        sp["f3db"] = below[-1] if below.size else float("nan")
    except Exception as e:
        sp["ac_err"] = str(e)
    # --- DC sweep: transimpedance + linear input range ---
    try:
        b = np.loadtxt(dcfile)
        iin, vout = b[:, 0], b[:, 1]
        vin, vd1, vs3 = b[:, 3], b[:, 5], b[:, 7]
        g = np.gradient(vout, iin)
        i0 = int(np.argmin(np.abs(iin)))
        g0 = g[i0]
        ok = ((np.abs(g) > 0.9 * abs(g0)) & (np.abs(g) < 1.1 * abs(g0)) &
              (vout < 1.75) & ((vd1 - vin) > 0.10) & ((vout - vs3) > 0.10))
        lo = hi = i0
        while lo - 1 >= 0 and ok[lo - 1]:
            lo -= 1
        while hi + 1 < ok.size and ok[hi + 1]:
            hi += 1
        sp["ZT_dc"] = g0
        sp["range"] = (iin[lo], iin[hi])
    except Exception as e:
        sp["dc_err"] = str(e)
    return sp


def _run_point(d, dev):
    """Write a temp deck for DESIGN d (widths from dev), run ngspice once,
    return the parsed SPICE result dict.  Cleans up all temp files."""
    tmp = [tempfile.NamedTemporaryFile(suffix=s, delete=False).name
           for s in ("_ac.dat", "_dc.dat", ".spice")]
    acfile, dcfile, deckfile = tmp
    with open(deckfile, "w") as fh:
        fh.write(_spice_deck(d, dev, acfile, dcfile))
    try:
        p = subprocess.run(["ngspice", "-b", deckfile], cwd=HERE,
                           capture_output=True, text=True, timeout=300)
        return _parse_spice(p.stdout + p.stderr, acfile, dcfile, d)
    finally:
        for f in tmp:
            try:
                os.remove(f)
            except OSError:
                pass


def _peaking(sp):
    """AC peak height above DC, in dB (nan if AC parse failed)."""
    if "gpk_db" not in sp:
        return float("nan")
    return sp["gpk_db"] - sp["gdc_db"]


def _bias_ok(sp, dev):
    return (all(sp["Vds"][m["name"]] > m["Vov"] + 0.05 for m in dev)
            and sp.get("gdc_db", 0) > 40 and sp["nodes"]["V_out"] < 1.75)


def spice_verify(d, pred):
    if shutil.which("ngspice") is None:
        print("\n[--spice] ngspice not found -- run this inside the "
              "iic-osic-tools container (see header).")
        return
    sp = _run_point(d, pred["dev"])

    def row(label, pv, sv, fmt="{:>10.3g}"):
        ps = fmt.format(pv) if pv == pv else "     --"
        ss = fmt.format(sv) if sv == sv else "     --"
        print(f"   {label:<28}{ps}   {ss}")

    print("=" * 68)
    print(" SPICE VERIFY  (ngspice, tt corner)      predicted      SPICE")
    print("-" * 68)
    row("I1  M1 branch [uA]", pred["I"]["M1"] * 1e6, sp["I"]["M1"] * 1e6)
    row("I2  M2 branch [uA]", pred["I"]["M2"] * 1e6, sp["I"]["M2"] * 1e6)
    row("I3  M3 branch [uA]", pred["I"]["M3"] * 1e6, sp["I"]["M3"] * 1e6)
    row("V_D1 (M3 gate) [V]", pred["nodes"]["V_D1"], sp["nodes"]["V_D1"])
    row("V_out          [V]", pred["nodes"]["V_out"], sp["nodes"]["V_out"])
    row("V_S3 (M3 src)  [V]", pred["nodes"]["V_S3"], sp["nodes"]["V_S3"])
    row("DC transimpedance [dBohm]", pred["ZT_dc_db"],
        20 * np.log10(abs(sp.get("ZT_dc", float("nan")))))
    row("Power [mW]", pred["Ptot"] * 1e3, sp["Ptot"] * 1e3)
    row("Bandwidth f_p / f-3dB [MHz]", pred["f_p"] / 1e6,
        sp.get("f3db", float("nan")) / 1e6)
    print("-" * 68)
    if "gpk_db" in sp:
        print(f"   AC peaking: {sp['gpk_db']-sp['gdc_db']:+.1f} dB @ "
              f"{sp['fpk']/1e6:.0f} MHz  (peak {sp['gpk_db']:.1f} dBohm)")
    print("   Device saturation (SPICE Vds vs predicted Vov):")
    for m in pred["dev"]:
        vds = sp["Vds"][m["name"]]
        flag = "ok" if vds > m["Vov"] + 0.05 else "LOW"
        print(f"     {m['name']}  Vds={vds:5.3f} V  (Vov~{m['Vov']:.3f})  {flag}")
    if "range" in sp:
        lo, hi = sp["range"]
        print(f"   Usable input range (SPICE): {lo*1e6:+.0f} .. {hi*1e6:+.0f} uA"
              f"   (span {(hi-lo)*1e6:.0f} uA)")
    print("=" * 68)


# ============================================================
#  C1/R4 damping sweep  (--sweep):  hold the sizing, sweep the two passive
#  knobs that shape the AC response, and find the best-damped point.
#    C1 large  -> zero cancels the 1 pF output pole (bandwidth) but re-exposes
#                 the RGC-loop peak;  C1 small -> damps the peak but loses BW.
#    R4        -> sets I1 / input-node loading, shifts the loop damping.
#  There is no single value that both cancels the output pole AND kills the
#  peak, so this maps the trade and picks the best compromise.
# ============================================================
def spice_sweep(d, pred, c1_list=None, r4_list=None, target_db=60.0):
    if shutil.which("ngspice") is None:
        print("\n[--sweep] ngspice not found -- run inside the container.")
        return
    if c1_list is None:
        c1_list = [13.5e-15, 30e-15, 60e-15, 150e-15, 400e-15, 1.02e-12]
    if r4_list is None:
        r4_list = [1e3, 2e3, 4e3]
    dev = pred["dev"]                      # hold the sizing; tune only C1, R4
    print("=" * 78)
    print(" C1/R4 DAMPING SWEEP  (ngspice tt; sizing held, tuning passives)")
    print(f"   loads: C_T={d['C_T']*1e15:.0f} fF in, C_L={d['C_L']*1e15:.0f} fF"
          f" out;  target DC ~ {target_db:.0f} dBohm; goal: min AC peaking")
    print("-" * 78)
    print("   C1_fF  R4_k   DCgain  peak    f_pk    f-3dB    Pwr   bias")
    print("                 dBohm    dB     MHz     MHz      mW")
    rows = []
    for r4 in r4_list:
        for c1 in c1_list:
            d2 = dict(d, C1=c1, R4=r4)
            sp = _run_point(d2, dev)
            r = dict(c1=c1, r4=r4, gdc=sp.get("gdc_db", float("nan")),
                     peak=_peaking(sp), fpk=sp.get("fpk", float("nan")),
                     f3=sp.get("f3db", float("nan")),
                     pw=sp.get("Ptot", float("nan")) * 1e3,
                     valid=_bias_ok(sp, dev))
            rows.append(r)
            print("  {:6.1f} {:4.1f}  {:7.1f} {:6.1f} {:7.0f} {:8.0f} {:6.2f}  {}"
                  .format(c1 * 1e15, r4 / 1e3, r["gdc"], r["peak"],
                          r["fpk"] / 1e6, r["f3"] / 1e6, r["pw"],
                          "ok" if r["valid"] else "BAD"))
    print("-" * 78)
    cand = [r for r in rows if r["valid"] and r["gdc"] >= target_db - 3]
    cand = cand or [r for r in rows if r["valid"]]
    if not cand:
        print(" no bias-valid point in sweep -- widen the ranges or fix bias.")
    else:
        damped = [r for r in cand if r["peak"] <= 1.0]
        if damped:                          # well-damped: take the most BW
            best = max(damped, key=lambda r: r["f3"])
            why = "peak <= 1 dB, max bandwidth"
        else:                               # else: least peaking available
            best = min(cand, key=lambda r: r["peak"])
            why = "least peaking (none reach <= 1 dB)"
        print(f" recommend ({why}):")
        print(f"   C1 = {best['c1']*1e15:.1f} fF,  R4 = {best['r4']/1e3:.1f} k"
              f"  ->  peak {best['peak']:+.1f} dB,  DC {best['gdc']:.1f} dBohm,"
              f"  f-3dB {best['f3']/1e6:.0f} MHz,  {best['pw']:.2f} mW")
        print("   (set these in DESIGN, then re-run --spice to confirm)")
    print("=" * 78)


if __name__ == "__main__":
    pred = run()
    if "--sweep" in sys.argv[1:]:
        spice_sweep(DESIGN, pred)
    elif "--spice" in sys.argv[1:]:
        spice_verify(DESIGN, pred)
