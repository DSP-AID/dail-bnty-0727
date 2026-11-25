"""Turn our best-scored_0002 JSON program into the bounty submission CSV.

    python3 make_csv.py [in.json] [out.csv]

CSV format required by DAiL bounty bnty_0727: header `puzzle_id,program`,
one row; `program` is a JSON list of `[op, i, j, d]` instructions.
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_IN = os.path.join(HERE, "data", "program_scored_0002.json")
DEF_OUT = os.path.join(HERE, "data", "submission_scored_0002.csv")


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else DEF_IN
    dst = sys.argv[2] if len(sys.argv) > 2 else DEF_OUT
    with open(src) as fh:
        prog = json.load(fh)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["puzzle_id", "program"])
        w.writerow(["scored_0002", json.dumps(prog, separators=(",", ":"))])
    print(f"wrote {dst}: {len(prog)} instructions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
