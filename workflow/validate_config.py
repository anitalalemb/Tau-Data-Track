#!/usr/bin/env python3

"""
Minimal configuration validator for the portable Tau-Data-Track workflow.

This does not generate calculations yet. Its purpose is to establish a
machine-independent configuration interface without modifying the proven
production scripts.
"""

from pathlib import Path
import argparse

try:
    import yaml
except ImportError:
    raise SystemExit(
        "PyYAML is required.\n"
        "Install dependencies with:\n"
        "  python -m pip install -r requirements.txt"
    )


REQUIRED = {
    "system": ["name"],
    "paths": [
        "calculation_root",
        "pseudo_dir",
    ],
    "tau_grid": [
        "nx",
        "ny",
    ],
    "qe": [
        "executable",
        "ecutwfc",
        "ecutrho",
        "conv_thr",
        "kmesh",
    ],
    "vertical_relax": [
        "etot_conv_thr",
        "forc_conv_thr",
        "max_seconds",
        "atomic_constraint",
    ],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    args = parser.parse_args()

    path = Path(args.config)

    if not path.exists():
        raise SystemExit(f"Configuration not found: {path}")

    with path.open() as fh:
        cfg = yaml.safe_load(fh)

    problems = []

    for section, keys in REQUIRED.items():
        if section not in cfg:
            problems.append(f"missing section: {section}")
            continue

        for key in keys:
            if key not in cfg[section]:
                problems.append(
                    f"missing parameter: {section}.{key}"
                )

    if not problems:
        constraint = cfg[
            "vertical_relax"
        ]["atomic_constraint"]

        if constraint != [0, 0, 1]:
            problems.append(
                "Stage-B atomic_constraint must be [0, 0, 1]"
            )

    if problems:
        print("CONFIGURATION: FAIL")
        for p in problems:
            print(" -", p)
        raise SystemExit(1)

    print("============================================")
    print("TAU-DATA-TRACK CONFIGURATION")
    print("============================================")
    print("CONFIGURATION: PASS")
    print()
    print("system       :", cfg["system"]["name"])
    print(
        "tau grid     :",
        f'{cfg["tau_grid"]["nx"]} x '
        f'{cfg["tau_grid"]["ny"]}',
    )
    print(
        "ecutwfc      :",
        cfg["qe"]["ecutwfc"],
        "Ry",
    )
    print(
        "ecutrho      :",
        cfg["qe"]["ecutrho"],
        "Ry",
    )
    print(
        "k mesh       :",
        cfg["qe"]["kmesh"],
    )
    print(
        "Stage-B mask :",
        cfg["vertical_relax"]["atomic_constraint"],
    )


if __name__ == "__main__":
    main()
