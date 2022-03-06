import pytest
from gnize.cog import find_gaps, remove_transpositions
from copy import deepcopy


def get_data(i, it, predicate, relation_string):
    orig = orig_it[i].pop()
    fix = fixed_it[i].pop()


def test_nofix():
    noise = "abcd"
    signal = "abcd"
    orig_it = find_gaps(signal, noise)
    fixed_it = orig_it.copy()
    remove_transpositions(fixed_it, noise)
    assert orig_it == fixed_it


def test_fix_a():
    noise = "abcd"
    signal = "abcx"
    fixed = find_gaps(signal, noise)
    removals = remove_transpositions(fixed, noise)
    for i, _ in enumerate(signal[:-1]):
        data = fixed[i].pop().data.data
        assert data[i] == noise[i]
    assert fixed[3].pop().data.data == "d"
    assert removals[0].corrected == "d"
    assert removals[0].injected == "d"
