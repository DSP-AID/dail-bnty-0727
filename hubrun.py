"""Build a low-instruction Elf Calculator program for Kaggle Santa 2026 puzzle
`scored_0002`, the target of DAiL bounty `bnty_0727` (bar: <=450 instructions).

Strategy: a pool of shared "hub" values (factor-chain prefixes of the targets,
additive ladders between their large cofactors, and register values harvested
from the previous best program) is added to the target list, so the width-aware
MCM search in elf_solver builds one shared DAG covering hubs + all 28 targets.
Each round feeds the current solution's register contents back into the pool
(hub-pool enrichment), which keeps shrinking the total.

Every candidate program is hard-gated with elf_rules.check_program before it
can become the new best.  Deterministic: fixed seeds.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from elf_rules import parse_puzzles, check_program  # noqa: E402
from elf_solver import solve_puzzle, to_submission_rows  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PUZZLES = os.path.join(HERE, "data", "puzzles.csv")
OUTS = [os.path.join(HERE, "..", "tmp", "best_scored_0002.json"),
        os.path.join(HERE, "..", "dist", "program_scored_0002.json"),
        "/tmp/opencode/bnty0727_bak/best_scored_0002.json"]


def factor_small(n: int, cap: int = 10_000_000):
    """Split ``n`` into its small-factor prefix and the remaining cofactor."""
    rem, factors = n, []
    for p in [2] + [k for k in range(3, cap, 2)]:
        if p * p > rem:
            break
        while rem % p == 0:
            factors.append(p)
            rem //= p
    return factors, rem


def mul_chain(factors):
    """Running products of a factor list (prefix values, excluding n itself)."""
    out, acc = [], 1
    for f in factors:
        acc *= f
        out.append(acc)
    return out[:-1]


def reachable_seeds(starts, cap_mult=30):
    """Products of start values that can seed a factor chain."""
    vals, lim = set(), cap_mult * max(starts)
    n = len(starts)
    for i in range(n):
        vals.add(starts[i])
        for j in range(i, n):
            v2 = starts[i] * starts[j]
            if v2 <= lim:
                vals.add(v2)
    return sorted(vals)


def build_hubs(starts, targets, vl):
    """Shared intermediate values likely to be useful for many targets."""
    factors_of, residual = {}, {}
    for t in targets:
        fac, rem = factor_small(t)
        factors_of[t], residual[t] = fac, rem

    hubs = set()
    seeds = reachable_seeds(starts)
    for t in targets:
        fac, rem = factors_of[t], residual[t]
        prods = set(mul_chain(fac))
        hubs.update(prods)
        best_p, best_seg = 0, None
        for s in seeds:
            g = math.gcd(rem, s)
            if g > best_p:
                seg = mul_chain(fac + [g])
                if all(v <= vl for v in seg):
                    best_p, best_seg = g, seg
        if best_seg is not None and best_p > 1:
            hubs.update(best_seg)
            quot = rem // best_p
            hubs.update(quot * p for p in prods if quot * p <= vl)
        hubs.add(rem)
        hubs.update(rem * p for p in prods if rem * p <= vl)

    # additive ladders between the large cofactors (they are close together)
    big = sorted(set(residual.values()))
    for a in range(len(big)):
        for b in range(a + 1, len(big)):
            d = big[b] - big[a]
            if 0 < d <= vl:
                hubs.add(d)
    for i in range(len(big) - 1):
        lo, hi = big[i], big[i + 1]
        for k in (2, 3, 4, 5):
            d = (hi - lo) // k
            if d > 1:
                hubs.add(d)
        for m in (2, 3):
            d = hi - m * lo
            if 1 < d <= vl:
                hubs.add(d)

    for t in targets:
        hubs.update(factors_of[t])
    hubs.discard(1)
    hubs = {h for h in hubs if 1 < h <= vl and h not in set(starts)}

    # BFS closure: cheap intermediates shared by many hubs (depth <= 3)
    start_set = set(starts) | hubs
    frontier = deque(sorted(start_set))
    seen = dict((v, 0) for v in start_set)
    additions = {}
    while frontier and len(additions) < 400:
        for _ in range(len(frontier)):
            a = frontier.popleft()
            if seen[a] >= 3:
                continue
            for b in list(start_set):
                v = a + b
                if v <= vl and v not in seen and v not in additions:
                    additions[v] = (a, b)
        for v, (a, b) in additions.items():
            if v not in seen:
                seen[v] = min(seen[a], seen[b]) + 1
                start_set.add(v)
                frontier.append(v)
    hubs |= set(additions)
    return sorted(hubs), factors_of, residual


def synth(starts, targets, vl, nr, hub_list, seed, budget_s, refine=False):
    """One solver pass over hubs+targets; returns verified rows or None.

    refine=False (default): first solution wins (fast lottery tickets).
    refine=True: keep solving until the deadline and return the best found."""
    tgs = list(dict.fromkeys(list(hub_list) + list(targets)))
    deadline = time.time() + budget_s
    attempt = 0
    best = None
    best_n = 10**9
    while time.time() < deadline:
        prog, _cost = solve_puzzle(starts, tgs, vl, seed=seed + 97 * attempt,
                                   budget_s=max(20.0, deadline - time.time()),
                                   restarts=6)
        attempt += 1
        if prog is None:
            continue
        try:
            inst, _pk = to_submission_rows(prog, starts)
            n, _ = check_program(starts, targets, vl, inst, nr)
        except Exception:
            continue
        if not refine:
            return inst
        if n < best_n:
            best_n, best = n, inst
    return best


def register_values(starts, nr, prog):
    """Live register contents after running ``prog`` (harvest for enrichment)."""
    regv = list(starts) + [None] * (nr - len(starts))
    for op, i, j, d in prog:
        a, b = regv[i], regv[j]
        if op == "/":
            regv[d] = a // b
        else:
            regv[d] = {"+": a + b, "-": a - b, "*": a * b}[op]
    return [v for v in regv if v and v > 1]


def save(best):
    """Write best to all outputs, but never clobber a file holding a SHORTER program
    (parallel hunt processes each compare against their own in-memory best)."""
    for path in OUTS:
        try:
            cur = None
            if os.path.exists(path):
                with open(path) as fh:
                    cur = json.load(fh)
            if cur is not None and len(cur) <= len(best):
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                json.dump(best, fh)
        except (OSError, ValueError):
            pass


def main():
    puzzles = parse_puzzles(PUZZLES)
    starts, targets, vl, nr = puzzles["scored_0002"]
    hubs, factors_of, residual = build_hubs(starts, targets, vl)

    # rank hubs by how many target factor chains / residuals need them
    chain_of = {t: set(mul_chain(factors_of[t])) for t in targets}

    def score(h):
        sc = sum(1 for t in targets if h in chain_of[t] or h == residual[t])
        sc += sum(1 for t in targets if any(h * p == t for p in (2, 3, 5, 7)))
        return (-sc, h)

    ranked = sorted(hubs, key=score)

    best = None

    def consider(inst, tag):
        nonlocal best
        if inst is None:
            print(f"{tag}: no solution", flush=True)
            return
        n = len(inst)
        if best is None or n < len(best):
            print(f"{tag}: {n}  *best*", flush=True)
            best = inst
            save(best)
        else:
            print(f"{tag}: {n} (keep {len(best)})", flush=True)

    # baseline: no hubs at all
    consider(synth(starts, targets, vl, nr, [], 4242, 90), "baseline")

    # hub-seeded passes over a few pool sizes and seeds
    for k in (20, 32, 44):
        for seed in (4242, 5353):
            if best is not None and len(best) <= 416:
                break
            consider(synth(starts, targets, vl, nr, ranked[:k], seed, 90),
                     f"hubs{k}-s{seed}")

    # hub-pool enrichment: feed the current solution's registers back in
    for it in range(6):
        if best is None:
            break
        extra = register_values(starts, nr, best)
        pool = extra + [h for h in ranked if h not in set(extra)]
        consider(synth(starts, targets, vl, nr, pool[:48], 7000 + it, 90),
                 f"enrich{it}")

    n = check_program(starts, targets, vl, best, nr)[0]
    print(f"FINAL VERIFIED emitted instructions: {n}", flush=True)
    save(best)


if __name__ == "__main__":
    main()
