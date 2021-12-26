import pytest
from gnize.cog import find_gaps, remove_transpositions
from copy import deepcopy

def related_at(i, orig_it, fixed_it, predicate, relation_string):
    orig = orig_it[i].pop()
    fix = fixed_it[i].pop()
    print('    ', orig, relation_string, fix, "?")
    assert predicate(orig, fix)

def test_nofix():
    noise = "abcd"
    signal = "abcd"
    orig_it = find_gaps(signal, noise)
    fixed_it = remove_transpositions(orig_it)
    assert orig_it == fixed_it

def test_fix_a():
    noise = "abcd"
    signal = "abcx"
    orig_it = find_gaps(signal, noise)
    fixed_it = remove_transpositions(deepcopy(orig_it))
    for i, _ in enumerate(signal[:-1]):
        related_at(i, orig_it, fixed_it, lambda o, f: o.data.signal == f.data.noise, "==")
    related_at(i + 1, orig_it, fixed_it, lambda o, f: o.data.signal != f.data.noise, "!=")
    related_at(i + 1, orig_it, fixed_it, lambda o, f: o.data.data == f.data.noise, "==")
