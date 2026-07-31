import sizing_worksheet as sw

# MAX-BW / MIN-CURRENT, single-sided input:
#  - starve the front-end (I1,I2): it sets no bandwidth, only Zin margin.
#  - output stage: large R5 + small I3 -> high gm3*R5=(gm/Id)*V_S3 (big f_p)
#    at low current, and parks V_out near VDD (max down-swing for a sourcing
#    input).  Keep the zero on the output pole: C1 = R3*C_L/R5.
#  - high gm/Id on M3 (weak inv) for max gm3*R5 per volt of headroom.
d = dict(sw.DESIGN)
d.update(
    M1=dict(Id=60e-6, gmid=18.0),    # starved input branch
    M2=dict(Id=55e-6, gmid=18.0),    # starved aux branch
    M3=dict(Id=40e-6, gmid=22.0),    # low I3, weak inversion
    R1=6.5e3,                        # low I1 gives headroom -> 60 dBohm
    R2=6.0e3,
    R3=4.0e3,                        # low R3 -> high f_out -> push f_p
    R4=9.0e3,                        # low I1 -> raises V_D1 -> more I3/V_S3
    R5=22.5e3,                       # large: V_S3~0.9 V, big gm3*R5 -> big f_p
    C1=178e-15,                      # R5*C1 = R3*C_L = 4 ns (zero on f_out)
)
pred = sw.run(d)
sw.spice_verify(d, pred)
