#!/usr/bin/env python3
from pathlib import Path
import re, math, sys
A=3.9409499168; TOL=5e-8
TOP={1,3,5,7,9}; BOTTOM={0,2,4,6,8}

def pbc_delta(x,y,L=A): return (x-y+0.5*L)%L-0.5*L

def parse_atomic_positions(text):
    lines=text.splitlines(); start=None
    for k,line in enumerate(lines):
        if line.strip().upper().startswith('ATOMIC_POSITIONS'): start=k+1; break
    if start is None: raise ValueError('ATOMIC_POSITIONS not found')
    out=[]
    for line in lines[start:]:
        s=line.strip()
        if not s: break
        if s.upper().startswith(('K_POINTS','CELL_PARAMETERS','ATOMIC_SPECIES','&')): break
        p=s.split()
        if len(p)<4: break
        out.append((p[0],float(p[1]),float(p[2]),float(p[3])))
    return out

def parse_cell(text):
    lines=text.splitlines()
    for k,line in enumerate(lines):
        if line.strip().upper().startswith('CELL_PARAMETERS'):
            return [tuple(map(float,lines[q].split()[:3])) for q in range(k+1,k+4)]
    raise ValueError('CELL_PARAMETERS not found')

def set_key_in_block(text, block, key, value):
    m=re.search(rf'(?is)(&{block}\b)(.*?)(^\s*/\s*$)',text,flags=re.M)
    if not m: raise ValueError(f'&{block} block not found')
    body=m.group(2); pat=rf'(?im)^\s*{re.escape(key)}\s*=.*?,?\s*$'; line=f'  {key} = {value},'
    if re.search(pat,body): body=re.sub(pat,line,body)
    else:
        if not body.endswith('\n'): body+='\n'
        body+=line+'\n'
    return text[:m.start(2)]+body+text[m.end(2):]

def value(text,key):
    m=re.search(rf'(?im)^\s*{re.escape(key)}\s*=\s*([^,\n/]+)',text)
    return m.group(1).strip() if m else None

expected=[f'tau{i}{j}' for i in range(10) for j in range(10)]
missing=[d for d in expected if not Path(d).is_dir()]
if missing: sys.exit('Missing dirs: '+', '.join(missing))
refp=Path('tau00/sto_bi_tau00.scf.in'); ref=refp.read_text(); refatoms=parse_atomic_positions(ref); refcell=parse_cell(ref)
keys=['ibrav','nat','ntyp','input_dft','vdw_corr','ecutwfc','ecutrho','occupations','assume_isolated','nosym','noinv','conv_thr','mixing_beta','electron_maxstep','diagonalization']
refset={k:value(ref,k) for k in keys}
issues=[]; maxb=maxt=maxz=0.0
for i in range(10):
  for j in range(10):
    lab=f'tau{i}{j}'; f=Path(lab)/f'sto_bi_{lab}.scf.in'
    if not f.exists(): issues.append(f'{lab}: missing input'); continue
    txt=f.read_text(); atoms=parse_atomic_positions(txt); cell=parse_cell(txt)
    if len(atoms)!=len(refatoms): issues.append(f'{lab}: atom count differs'); continue
    for r1,r2 in zip(cell,refcell):
      if any(abs(x-y)>TOL for x,y in zip(r1,r2)): issues.append(f'{lab}: cell differs'); break
    sx=i*A/10; sy=j*A/10
    for idx,(a0,a1) in enumerate(zip(refatoms,atoms)):
      e0,x0,y0,z0=a0; e1,x1,y1,z1=a1; dz=abs(z1-z0); maxz=max(maxz,dz)
      if e0!=e1: issues.append(f'{lab}: species differs at atom {idx}')
      if idx in BOTTOM:
        err=math.hypot(pbc_delta(x1,x0),pbc_delta(y1,y0)); maxb=max(maxb,err)
        if err>TOL or dz>TOL: issues.append(f'{lab}: bottom atom {idx} changed dxy={err:.3e} dz={dz:.3e}')
      else:
        err=math.hypot(pbc_delta(x1,x0+sx),pbc_delta(y1,y0+sy)); maxt=max(maxt,err)
        if err>TOL or dz>TOL: issues.append(f'{lab}: top atom {idx} shift error dxy={err:.3e} dz={dz:.3e}')
    for k in keys:
      if value(txt,k)!=refset[k]: issues.append(f'{lab}: {k} differs ({value(txt,k)} vs {refset[k]})')
    patched=txt
    for k,v in [('verbosity',"'high'"),('tprnfor','.true.'),('tstress','.true.')]: patched=set_key_in_block(patched,'CONTROL',k,v)
    if patched!=txt:
      bak=f.with_suffix(f.suffix+'.bak')
      if not bak.exists(): bak.write_text(txt)
      f.write_text(patched)
print('===== STRUCTURAL SANITY CHECK =====')
print('tau directories checked : 100')
print(f'max bottom-layer error   : {maxb:.3e} A')
print(f'max top-shift error      : {maxt:.3e} A')
print(f'max z-coordinate change  : {maxz:.3e} A')
if issues:
  print(f'FAIL: {len(issues)} issue(s)')
  for x in issues[:100]: print(' ',x)
  sys.exit(2)
print('PASS: all 100 structures and key SCF settings are consistent.')
print("PATCHED: verbosity='high', tprnfor=.true., tstress=.true.")
