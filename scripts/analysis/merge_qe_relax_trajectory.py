#!/usr/bin/env python3
from pathlib import Path
import argparse,csv
import numpy as np
from ase.io import read,write
from ase.io.trajectory import Trajectory
p=argparse.ArgumentParser(); p.add_argument('outputs',nargs='+'); p.add_argument('--extxyz',default='full_relaxation.extxyz'); p.add_argument('--traj',default='full_relaxation.traj'); p.add_argument('--csv',default='ionic_trajectory.csv'); a=p.parse_args()
frames=[]; sources=[]
for name in a.outputs:
 f=Path(name)
 if not f.exists(): print('WARNING missing',f); continue
 try: fs=read(str(f),index=':',format='espresso-out')
 except Exception as e: print('WARNING parse failed',f,e); continue
 if not isinstance(fs,list): fs=[fs]
 for fr in fs: frames.append(fr); sources.append(f.name)
uniq=[]; usrc=[]
for fr,src in zip(frames,sources):
 dup=False
 if uniq and len(uniq[-1])==len(fr): dup=np.max(np.abs(uniq[-1].positions-fr.positions))<1e-8 and np.max(np.abs(uniq[-1].cell.array-fr.cell.array))<1e-8
 if not dup: uniq.append(fr); usrc.append(src)
if not uniq: raise SystemExit('No frames parsed')
write(a.extxyz,uniq,format='extxyz')
with Trajectory(a.traj,'w') as tr:
 for fr in uniq: tr.write(fr)
fields=['global_step','source_file','energy_eV','max_force_eV_A','rms_force_eV_A','stress_xx_eV_A3','stress_yy_eV_A3','stress_zz_eV_A3','stress_yz_eV_A3','stress_xz_eV_A3','stress_xy_eV_A3','max_step_displacement_A','rms_step_displacement_A']
rows=[]
for k,(fr,src) in enumerate(zip(uniq,usrc)):
 energy=maxf=rmsf=None; stress=[None]*6
 try: energy=fr.get_potential_energy()
 except: pass
 try:
  ff=fr.get_forces(); mm=np.linalg.norm(ff,axis=1); maxf=float(mm.max()); rmsf=float(np.sqrt(np.mean(mm**2)))
 except: pass
 try: stress=list(map(float,fr.get_stress(voigt=True)))
 except: pass
 maxd=rmsd=None
 if k>0 and len(uniq[k-1])==len(fr):
  dd=fr.positions-uniq[k-1].positions; mm=np.linalg.norm(dd,axis=1); maxd=float(mm.max()); rmsd=float(np.sqrt(np.mean(mm**2)))
 rows.append(dict(zip(fields,[k,src,energy,maxf,rmsf,*stress,maxd,rmsd])))
with open(a.csv,'w',newline='') as fh:
 w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)
print('parsed',len(frames),'frames; unique',len(uniq)); print('wrote',a.extxyz,a.traj,a.csv)
