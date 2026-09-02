#!/usr/bin/env python3

from pathlib import Path
import argparse
import re


def inspect(path):
    path = Path(path)

    if not path.exists() or path.stat().st_size == 0:
        return None

    text = path.read_text(errors="ignore")
    low = text.lower()

    forces = [
        float(x.replace("D", "E").replace("d", "e"))
        for x in re.findall(
            r"Total force\s*=\s*([-+0-9.EeDd]+)",
            text,
            flags=re.I,
        )
    ]

    energies = re.findall(
        r"!\s+total energy\s*=\s*([-+0-9.EeDd]+)\s+Ry",
        text,
        flags=re.I,
    )

    bfgs = "bfgs converged" in low
    end_bfgs = "end of bfgs geometry optimization" in low
    job_done = "job done." in low
    max_time = "maximum cpu time exceeded" in low

    converged = bfgs and end_bfgs

    return {
        "path": path,
        "converged": converged,
        "bfgs": bfgs,
        "end_bfgs": end_bfgs,
        "job_done": job_done,
        "max_time": max_time,
        "n_forces": len(forces),
        "n_energies": len(energies),
        "final_force": forces[-1] if forces else None,
    }


def choose(tau_dir):
    tau_dir = Path(tau_dir)
    label = tau_dir.name

    candidates = [
        tau_dir / f"sto_bi_{label}.vertical_relax.out",
        tau_dir / f"sto_bi_{label}.vertical_relax_8h.out",
    ]

    runs = [
        r for r in (inspect(p) for p in candidates)
        if r is not None
    ]

    if not runs:
        return None, []

    # Scientific priority:
    # 1. completed/converged BFGS
    # 2. JOB DONE
    # 3. not max-time terminated
    # 4. more evaluated ionic configurations
    # 5. lower final QE total force
    def score(r):
        force_score = (
            -r["final_force"]
            if r["final_force"] is not None
            else float("-inf")
        )

        return (
            int(r["converged"]),
            int(r["job_done"]),
            int(not r["max_time"]),
            r["n_forces"],
            force_score,
        )

    selected = max(runs, key=score)
    return selected, runs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument(
        "--start",
        type=int,
        default=0,
    )
    p.add_argument(
        "--end",
        type=int,
        default=99,
    )
    args = p.parse_args()

    root = Path(args.root)

    print(
        "tau   selected branch"
        "                                  "
        "status      frames   final force"
    )
    print("-" * 100)

    for i in range(args.start, args.end + 1):
        label = f"tau{i:02d}"
        selected, runs = choose(root / label)

        if selected is None:
            print(f"{label}  NO OUTPUT")
            continue

        status = (
            "CONVERGED"
            if selected["converged"]
            else (
                "TIME_LIMIT"
                if selected["max_time"]
                else "INCOMPLETE"
            )
        )

        ff = (
            f"{selected['final_force']:.6f}"
            if selected["final_force"] is not None
            else "—"
        )

        print(
            f"{label}  "
            f"{selected['path'].name:<48} "
            f"{status:<11} "
            f"{selected['n_forces']:>5}   "
            f"{ff}"
        )

        if len(runs) > 1:
            for r in runs:
                if r["path"] == selected["path"]:
                    continue

                rstatus = (
                    "CONVERGED"
                    if r["converged"]
                    else (
                        "TIME_LIMIT"
                        if r["max_time"]
                        else "INCOMPLETE"
                    )
                )

                print(
                    f"       rejected: "
                    f"{r['path'].name} "
                    f"[{rstatus}, "
                    f"{r['n_forces']} frames, "
                    f"force={r['final_force']}]"
                )


if __name__ == "__main__":
    main()
