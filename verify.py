"""Reproduce the verification of our scored_0002 program with no network and
no Kaggle account: replay the shipped CSV against the vendored puzzle data.

    python3 verify.py [path/to/submission.csv]

The submission CSV has header `puzzle_id,program`, one row per puzzle, where
`program` is a JSON list of `[op, i, j, d]` instructions.  Prints the emitted
instruction count for every row; exit code 0 only if every row is a legal
program that holds all targets of its puzzle.
"""
from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elf_rules import parse_puzzles, check_program  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PUZZLES = os.path.join(HERE, "data", "puzzles.csv")
DEFAULT_SUB = os.path.join(HERE, "data", "submission_scored_0002.csv")


def main() -> int:
    sub = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUB
    puzzles = parse_puzzles(PUZZLES)
    csv.field_size_limit(10**9)
    total, ok = 0, True
    with open(sub, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pid = row["puzzle_id"]
            prog = json.loads(row["program"])
            if pid not in puzzles:
                print(f"{pid}: unknown puzzle id")
                ok = False
                continue
            starts, targets, vl, nreg = puzzles[pid]
            try:
                n_inst, _seen = check_program(starts, targets, vl, prog, nreg)
            except Exception as exc:  # noqa: BLE001
                print(f"{pid}: INVALID ({exc})")
                ok = False
                continue
            total += n_inst
            print(f"{pid}: VERIFIED emitted={n_inst}")
    print(f"TOTAL emitted instructions: {total}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
