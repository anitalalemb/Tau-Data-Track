#!/usr/bin/env python3
from pathlib import Path
import csv,re
rows=[]
def last_float(pat,text):
    vals=re.findall(pat,text,flags=re.M); return float(vals[-1].replace('D','E').replace('d','e')) if vals else None
for i in range(10):
  for j in range(10):
    lab=f'tau{i}{j}'; f=Path(lab)/f'sto_bi_{lab}.scf.out'; text=f.read_text(errors='replace') if f.exists() else ''
    rows.append({'tau':lab,'tau_x':i/10,'tau_y':j/10,'output_exists':f.exists(),'job_done':'JOB DONE' in text,'scf_converged':'convergence has been achieved' in text.lower() and 'convergence not achieved' not in text.lower(),'total_energy_Ry':last_float(r'!\s+total energy\s+=\s+([-+0-9.EeDd]+)\s+Ry',text),'total_force_Ry_Bohr':last_float(r'Total force\s*=\s*([-+0-9.EeDd]+)',text),'stress_present':'total   stress' in text})
with open('tau10x10_scf_audit.csv','w',newline='') as fh:
  w=csv.DictWriter(fh,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print('outputs',sum(r['output_exists'] for r in rows),'/100')
print('JOB DONE',sum(r['job_done'] for r in rows),'/100')
print('converged',sum(r['scf_converged'] for r in rows),'/100')
print('energy',sum(r['total_energy_Ry'] is not None for r in rows),'/100')
print('force',sum(r['total_force_Ry_Bohr'] is not None for r in rows),'/100')
print('stress',sum(r['stress_present'] for r in rows),'/100')
print('wrote tau10x10_scf_audit.csv')
