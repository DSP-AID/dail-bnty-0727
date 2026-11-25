# Santa 2026 Elf Calculator — `scored_0002` (DAiL bounty bnty_0727)

Straight-line integer-arithmetic program synthesis (Multiple Constant
Multiplication) for Kaggle Santa 2026 "The Elf Calculator", puzzle
`scored_0002` (4 starting values, 28 targets, 48 registers, value limit
998363437601952921).

## Result

| program | emitted instructions | replay status |
|---|---|---|
| house-shipped (per bounty text) | 512 | baseline |
| **ours** (`data/program_scored_0002.json`) | **490** | VERIFIED — all 28 targets held, every intermediate ≤ value_limit |

The bounty acceptance bar is **≤450 emitted instructions**. Our best after a
large randomized search (hundreds of seeded MCM-solver restarts with hub-pool
enrichment, deep refine passes and register-value harvesting) is **490**: it
beats the house-shipped 512 but does not reach the 450 bar. The program is
fully compact (backward-liveness dead-code elimination removes nothing) and is
hard-gated by our own verifier at every search step.

## Files

- `elf_rules.py` — independent implementation of the machine rulebook + replay verifier
- `elf_solver.py` — width-aware MCM / shared-DAG program synthesizer
- `hubrun.py` — hub-pool construction + iterative best-shrinking loop (deterministic seeds)
- `verify.py` — replays `data/submission_scored_0002.csv` against vendored puzzle data
- `make_csv.py` — regenerates the submission CSV from `data/program_scored_0002.json`
- `test_elf.py` — rulebook unit tests + verification of the shipped program
- `data/puzzles.csv`, `data/practice_puzzles.csv` — real Kaggle Santa 2026 data (vendored, public)

## Reproduce (no network, no Kaggle token)

```bash
python3 -m pytest test_elf.py -q     # rulebook tests + shipped-program check
python3 verify.py                    # replays the CSV: "scored_0002: VERIFIED emitted=490"
```

## Submission format

`data/submission_scored_0002.csv` — header `puzzle_id,program`, one row;
`program` is a JSON list of `[op, i, j, d]` instructions with
`op ∈ + - * /`.
