v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 360 -620 360 -550 {lab=VDD}
N 560 -620 560 -550 {lab=VDD}
N 800 -620 800 -550 {lab=VDD}
N 360 -490 360 -370 {lab=d1}
N 560 -490 560 -370 {lab=d2}
N 800 -490 800 -370 {lab=vout}
N 300 -430 300 -340 {lab=d2}
N 720 -450 720 -340 {lab=d1}
N 360 -310 360 -280 {lab=Iin}
N 480 -340 520 -340 {lab=Iin}
N 800 -310 800 -280 {lab=s3}
N 800 -430 940 -430 {lab=vout}
N 560 -640 560 -620 {lab=VDD}
N 360 -620 560 -620 {lab=VDD}
N 560 -620 800 -620 {lab=VDD}
N 310 -300 360 -300 {lab=Iin}
N 360 -300 480 -300 {lab=Iin}
N 480 -340 480 -300 {lab=Iin}
N 300 -430 560 -430 {lab=d2}
N 300 -340 320 -340 {lab=d2}
N 360 -450 720 -450 {lab=d1}
N 720 -340 760 -340 {lab=d1}
N 360 -220 360 -200 {lab=VSS}
N 360 -200 800 -200 {lab=VSS}
N 800 -220 800 -200 {lab=VSS}
N 560 -310 560 -200 {lab=VSS}
N 560 -200 560 -170 {lab=VSS}
N 560 -340 600 -340 {lab=VSS}
N 600 -340 600 -300 {lab=VSS}
N 560 -300 600 -300 {lab=VSS}
N 360 -340 400 -340 {lab=VSS}
N 800 -340 840 -340 {lab=VSS}
N 960 -300 960 -280 {lab=s3}
N 960 -220 960 -200 {lab=VSS}
N 800 -300 960 -300 {lab=s3}
N 800 -200 960 -200 {lab=VSS}
N 765 -250 780 -250 {lab=VSS}
N 765 -250 765 -200 {lab=VSS}
N 325 -250 340 -250 {lab=VSS}
N 325 -250 325 -200 {lab=VSS}
N 325 -200 360 -200 {lab=VSS}
N 325 -520 340 -520 {lab=VSS}
N 525 -520 540 -520 {lab=VSS}
N 765 -520 780 -520 {lab=VSS}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 340 -340 0 0 {name=M1 model=nfet_01v8_lvt W=7.3 L=0.15 nf=4 mult=1 ad=0 as=0 pd=0 ps=0 nrd=0 nrs=0 sa=0 sb=0 sd=0 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 540 -340 0 0 {name=M2 model=nfet_01v8_lvt W=7.9 L=0.15 nf=4 mult=1 ad=0 as=0 pd=0 ps=0 nrd=0 nrs=0 sa=0 sb=0 sd=0 spiceprefix=X}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 780 -340 0 0 {name=M3 model=nfet_01v8_lvt W=19.1 L=0.15 nf=4 mult=1 ad=0 as=0 pd=0 ps=0 nrd=0 nrs=0 sa=0 sb=0 sd=0 spiceprefix=X}
C {devices/ipin.sym} 310 -300 0 0 {name=P_vin  lab=Iin}
C {devices/opin.sym} 940 -430 0 0 {name=P_vout lab=vout}
C {devices/iopin.sym} 560 -640 3 0 {name=P_vdd  lab=VDD}
C {devices/iopin.sym} 560 -170 1 0 {name=P_vss  lab=VSS}
C {devices/lab_pin.sym} 360 -450 0 0 {name=l_d1 lab=d1}
C {devices/lab_pin.sym} 560 -430 0 1 {name=l_d2 lab=d2}
C {devices/lab_pin.sym} 800 -300 0 0 {name=l_s3 lab=s3}
C {devices/lab_pin.sym} 400 -340 0 1 {name=l_m1b lab=VSS}
C {devices/lab_pin.sym} 840 -340 0 1 {name=l_m3b lab=VSS}
C {sky130_fd_pr/res_high_po_0p35.sym} 360 -520 0 0 {name=R1
L=5.36
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_high_po_0p35.sym} 560 -520 0 0 {name=R2
L=4.91
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_high_po_0p35.sym} 800 -520 0 0 {name=R3
L=3.1
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_high_po_0p35.sym} 360 -250 0 0 {name=R4
L=7.62
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_xhigh_po_0p69.sym} 800 -250 0 0 {name=R5
L=7.87
model=res_xhigh_po_0p69
spiceprefix=X
mult=1}
C {sky130_fd_pr/cap_mim_m3_1.sym} 960 -250 2 1 {name=C1 model=cap_mim_m3_1 W=17 L=5 MF=1 spiceprefix=X}
C {devices/lab_pin.sym} 765 -520 0 0 {name=l_m1 lab=VSS}
C {devices/lab_pin.sym} 525 -520 0 0 {name=l_m2 lab=VSS}
C {devices/lab_pin.sym} 325 -520 0 0 {name=l_m3 lab=VSS}
C {sky130_fd_pr/res_high_po_0p35.sym} 1100 -520 0 0 {name=Rdum1
L=7.62
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {devices/lab_pin.sym} 1100 -490 0 0 {name=l_du1a lab=VSS}
C {devices/lab_pin.sym} 1100 -550 0 0 {name=l_du1b lab=VSS}
C {devices/lab_pin.sym} 1080 -520 0 0 {name=l_du1c lab=VSS}
C {sky130_fd_pr/res_high_po_0p35.sym} 1300 -520 0 0 {name=Rdum2
L=5.36
model=res_high_po_0p35
spiceprefix=X
mult=1}
C {devices/lab_pin.sym} 1300 -490 0 0 {name=l_du2a lab=VSS}
C {devices/lab_pin.sym} 1300 -550 0 0 {name=l_du2b lab=VSS}
C {devices/lab_pin.sym} 1280 -520 0 0 {name=l_du2c lab=VSS}
