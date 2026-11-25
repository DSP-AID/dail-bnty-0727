"""Unit tests for the Elf Calculator rulebook checker and our scored_0002
program (DAiL bounty bnty_0727).  Run: python3 -m pytest test_elf.py -q
(no network, no Kaggle token needed — all data is vendored under data/)."""
from __future__ import annotations

import json
import os

import pytest

import elf_rules
from elf_rules import check_program, parse_puzzles

HERE = os.path.dirname(os.path.abspath(__file__))
PUZZLES = os.path.join(HERE, "data", "puzzles.csv")


def _n(starts, targets, vl, prog, nreg=10):
    """Instruction count if legal, else raise."""
    return check_program(starts, targets, vl, prog, nreg)[0]


# ---------------------------------------------------------------- rulebook

def test_simple_legal_program():
    # (2+3)*5 = 25 held in reg 4 after two instructions
    assert _n([2, 3, 5], [25], 10**9, [["+", 0, 1, 4], ["*", 4, 2, 5]]) == 2


def test_target_held_early_counts():
    # target 5 is a starting value; zero instructions needed
    assert _n([5, 7], [5], 10**9, []) == 0


def test_subtraction_requires_greater():
    with pytest.raises(Exception):
        _n([3, 5], [2], 10**9, [["-", 0, 1, 4]])  # 3-5 not allowed


def test_division_must_be_exact():
    with pytest.raises(Exception):
        _n([7, 3], [2], 10**9, [["/", 0, 1, 4]])


def test_intermediate_over_value_limit_fails():
    with pytest.raises(Exception):
        _n([10**6, 10**6], [1], 10**11, [["*", 0, 1, 4], ["-", 4, 0, 5]])


def test_result_must_be_positive():
    with pytest.raises(Exception):
        _n([2, 3], [1], 10**9, [["*", 0, 0, 4], ["-", 4, 4, 5]])


def test_missing_target_fails():
    with pytest.raises(Exception):
        _n([2, 3], [99], 10**9, [["+", 0, 1, 4]])


def test_register_index_out_of_range():
    with pytest.raises(Exception):
        _n([2, 3], [5], 10**9, [["+", 0, 1, 10]], nreg=10)


def test_instruction_cap():
    prog = [["+", 0, 1, 4]] * 4097
    with pytest.raises(Exception):
        _n([2, 3], [5, 99], 10**9, prog)


# ---------------------------------------------------------------- real data

@pytest.fixture(scope="module")
def puzzle():
    return parse_puzzles(PUZZLES)["scored_0002"]


def test_scored_0002_metadata(puzzle):
    starts, targets, vl, nreg = puzzle
    assert starts == [476, 1119, 1177, 1509]
    assert len(targets) == 28
    assert vl == 998363437601952921
    assert nreg == 48


BEST = os.path.join(HERE, "data", "program_scored_0002.json")


@pytest.mark.skipif(not os.path.exists(BEST), reason="program not built yet")
def test_best_program_beats_house_shipped(puzzle):
    starts, targets, vl, nreg = puzzle
    with open(BEST) as fh:
        prog = json.load(fh)
    # check_program raises on any illegal instruction or missed target
    n, _seen = check_program(starts, targets, vl, prog, nreg)
    assert n < 512, "must beat the house-shipped program (512 emitted)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
