import pytest
from gnize.cog import find_gaps, reconcile, Error, Kind, EditStrategy
from copy import deepcopy


def as_str(it):
    k = {Kind.signal: "S", Kind.gap: "G", Kind.error: "E"}
    s = ""
    for interval in sorted(it.items(), key=lambda x: x.begin):
        s += "{}({})".format(k[interval.data.kind], str(interval.data.data))
        s += " "
    print(s.strip())
    return s.strip()


def test_nofix():
    noise = "abcd"
    signal = "abcd"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(abcd)"
    assert edits == {}


def test_strip_added():
    noise = "abcd"
    signal = "abxcd"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(abcd)"
    assert edits == {2: EditStrategy.ignore}


def test_raw_transpose():
    noise = "abcd"
    signal = "axcd"
    it = find_gaps(signal, noise)
    print(it)
    edits = reconcile(it)
    assert as_str(it) == "S(abcd)"
    assert edits == {1: EditStrategy.extend_signal}

def test_transpose_gap_one():
    noise = "abcdefg"
    signal = "abcxg"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(abc) G(de) S(fg)"
    assert edits == {5: EditStrategy.extend_signal}

def test_transpose_gap_two():
    noise = "abcdefg"
    signal = "abcxxg"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(abc) G(d) S(efg)"
    assert edits == {4: EditStrategy.extend_signal}

def test_transpose_gap_two_left():
    noise = "abcdefg"
    signal = "abcXXg"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(abcd) G(ef) S(g)"
    assert edits == {3: EditStrategy.extend_signal}


def test_transpose_gap_middle():
    noise = "abcdefg"
    signal = "axdxg"
    it = find_gaps(signal, noise)
    edits = reconcile(it)
    assert as_str(it) == "S(a) G(b) S(cd) G(e) S(fg)"
    print(edits)
    assert edits == {2: EditStrategy.extend_signal, 5: EditStrategy.extend_signal}
