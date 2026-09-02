#!/usr/bin/env python3
from pathlib import Path
import re

def setk(text,block,key,value):
 m=re.search(rf'(?is)(&{block}\b)(.*?)(^\s*/\s*$)',text,flags=re.M)
 if not m: raise ValueError(f'&{block} not found')
 body=m.group(2); pat=rf'(?im)^\s*{re.escape(key)}\s*=.*?,?\s*$'; line=f'  {key} = {value},'
 body=re.sub(pat,line,body) if re.search(pat,body) else body+('' if body.endswith('\n') else '\n')+line+'\n'
 return text[:m.start(2)]+body+text[m.end(2):]
made=0
for i in range(10):
 for j in range(10):
  lab=f'tau{i}{j}'; d=Path(lab); sin=d/f'sto_bi_{lab}.scf.in'; sout=d/f'sto_bi_{lab}.scf.out'
  if not (sin.exists() and sout.exists()): continue
  o=sout.read_text(errors='replace').lower()
  if 'job done' not in o or 'convergence has been achieved' not in o: continue
  t=sin.read_text()
  for k,v in [('calculation',"'relax'"),('verbosity',"'high'"),('tprnfor','.true.'),('tstress','.true.'),('forc_conv_thr','1.0d-3'),('etot_conv_thr','1.0d-5'),('nstep','300')]: t=setk(t,'CONTROL',k,v)
  for k,v in [('startingpot',"'file'"),('startingwfc',"'file'")]: t=setk(t,'ELECTRONS',k,v)
  if not re.search(r'(?im)^\s*&IONS\b',t): t=t.replace('\nATOMIC_SPECIES',"\n&IONS\n  ion_dynamics = 'bfgs',\n/\n\nATOMIC_SPECIES",1)
  (d/f'sto_bi_{lab}.relax.in').write_text(t); made+=1
print('Generated',made,'relax inputs.')
print('WARNING: plain QE relax can change tau by rigid layer sliding. For fixed-tau relaxation use the projected-force ASE/FIRE workflow.')
