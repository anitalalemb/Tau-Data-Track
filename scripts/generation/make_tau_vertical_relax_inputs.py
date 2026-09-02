#!/usr/bin/env python3

from pathlib import Path
import re
import shutil

ROOT = Path(".")

made = 0

for idx in range(100):

    label = f"tau{idx:02d}"
    d = ROOT / label

    scf_in  = d / f"sto_bi_{label}.scf.in"
    scf_out = d / f"sto_bi_{label}.scf.out"

    old_save = d / "tmp" / f"sto_bi_{label}.save"
    new_tmp  = d / "tmp_vertical_relax"
    new_save = new_tmp / f"sto_bi_{label}.save"

    if not (scf_in.exists() and scf_out.exists() and old_save.exists()):
        print(f"SKIP {label}: missing SCF input/output/save")
        continue

    out = scf_out.read_text(errors="replace").lower()

    if "job done" not in out or "convergence has been achieved" not in out:
        print(f"SKIP {label}: SCF not confirmed converged")
        continue

    # ----------------------------------------------------------
    # Read ORIGINAL SCF input.
    # ----------------------------------------------------------
    original = scf_in.read_text()

    # Extract SYSTEM exactly from original SCF.
    m_system = re.search(
        r'(?ms)^\s*&SYSTEM\s*$.*?^\s*/\s*$',
        original
    )
    if not m_system:
        raise RuntimeError(f"{label}: &SYSTEM not found")

    system = m_system.group(0).strip()

    # Extract ELECTRONS body.
    m_elec = re.search(
        r'(?ms)^\s*&ELECTRONS\s*$\n(.*?)^\s*/\s*$',
        original
    )
    if not m_elec:
        raise RuntimeError(f"{label}: &ELECTRONS not found")

    elec_body = m_elec.group(1)

    # Remove any old startingpot / startingwfc if present.
    elec_body = re.sub(
        r'(?im)^\s*startingpot\s*=.*$\n?',
        '',
        elec_body
    )
    elec_body = re.sub(
        r'(?im)^\s*startingwfc\s*=.*$\n?',
        '',
        elec_body
    )

    elec_body = elec_body.rstrip()

    electrons = (
        "&ELECTRONS\n"
        + elec_body + "\n"
        + "  startingpot = 'file',\n"
        + "  startingwfc = 'file',\n"
        + "/"
    )

    # ----------------------------------------------------------
    # Extract everything from ATOMIC_SPECIES onward.
    # ----------------------------------------------------------
    m_cards = re.search(
        r'(?ms)^ATOMIC_SPECIES.*$',
        original
    )
    if not m_cards:
        raise RuntimeError(f"{label}: ATOMIC_SPECIES not found")

    cards = m_cards.group(0)

    # ----------------------------------------------------------
    # Determine nat.
    # ----------------------------------------------------------
    m_nat = re.search(
        r'(?im)^\s*nat\s*=\s*(\d+)',
        system
    )
    if not m_nat:
        raise RuntimeError(f"{label}: nat not found")

    nat = int(m_nat.group(1))

    # ----------------------------------------------------------
    # Add 0 0 1 to all atomic positions.
    # ----------------------------------------------------------
    lines = cards.splitlines()
    new_lines = []

    in_positions = False
    npos = 0

    for line in lines:

        if line.strip().upper().startswith("ATOMIC_POSITIONS"):
            in_positions = True
            npos = 0
            new_lines.append(line)
            continue

        if in_positions and npos < nat:

            parts = line.split()

            if len(parts) >= 4 and parts[0] in {"Sr", "Ti", "O"}:

                species = parts[0]
                x = parts[1]
                y = parts[2]
                z = parts[3]

                new_lines.append(
                    f"{species:2s}  "
                    f"{x:>16s}  "
                    f"{y:>16s}  "
                    f"{z:>16s}   0 0 1"
                )

                npos += 1

                if npos == nat:
                    in_positions = False

                continue

        new_lines.append(line)

    if npos != nat:
        raise RuntimeError(
            f"{label}: expected {nat} positions, found {npos}"
        )

    cards = "\n".join(new_lines)

    # ----------------------------------------------------------
    # Build CONTROL explicitly.
    # ----------------------------------------------------------
    control = f"""&CONTROL
  calculation = 'relax',
  prefix = 'sto_bi_{label}',
  outdir = './tmp_vertical_relax',
  pseudo_dir = '/pscratch/sd/a/anita14b/SAM/pseudo',
  tstress = .true.,
  tprnfor = .true.,
  verbosity = 'high',
  etot_conv_thr = 1.0d-4,
  forc_conv_thr = 1.0d-3,
  max_seconds = 170000,
/"""

    ions = """&IONS
  ion_dynamics = 'bfgs',
/"""

    # ----------------------------------------------------------
    # Assemble in QE's required namelist order.
    # ----------------------------------------------------------
    final = (
        control + "\n\n"
        + system + "\n\n"
        + electrons + "\n\n"
        + ions + "\n\n"
        + cards.rstrip()
        + "\n"
    )

    target = d / f"sto_bi_{label}.vertical_relax.in"
    target.write_text(final)

    # ----------------------------------------------------------
    # Seed independent relaxation outdir from converged SCF.
    # ----------------------------------------------------------
    new_tmp.mkdir(exist_ok=True)

    if new_save.exists():
        shutil.rmtree(new_save)

    shutil.copytree(old_save, new_save)

    made += 1
    print(f"MADE {label}")


print()
print("=" * 70)
print(f"Generated {made}/100 vertical pre-relaxation inputs.")
print("CONTROL : relaxation thresholds + max_seconds")
print("SYSTEM  : preserved from original SCF")
print("ELECTRONS: original settings + file initialization")
print("IONS    : BFGS")
print("POSITIONS: 0 0 1 -> x/y fixed, z free")
print("=" * 70)
