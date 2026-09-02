#!/usr/bin/env python3
from pathlib import Path

print(f"{'tau':6s} {'SCF out':7s} {'SCF conv':8s} {'relax jid':12s} {'traj':6s}")
print("-"*50)

for i in range(10):
    for j in range(10):
        label = f"tau{i}{j}"
        d = Path(label)
        out = d/f"sto_bi_{label}.scf.out"
        exists = out.exists()
        conv = False
        if exists:
            t = out.read_text(errors="replace").lower()
            conv = ("job done" in t and
                    "convergence has been achieved" in t and
                    "convergence not achieved" not in t)
        jf = d/"pipeline_state"/"relax_submitted.jobid"
        jid = jf.read_text().strip() if jf.exists() else "-"
        traj = (d/"relaxation"/"full_relaxation.traj").exists()
        print(f"{label:6s} {str(exists):7s} {str(conv):8s} {jid:12s} {str(traj):6s}")
