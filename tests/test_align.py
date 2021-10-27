import pytest
from gnize.cog import find_gaps, Kind

def pos_assert(it, i, kind, data):

    # only one interval per noise character
    print("    ", it[i], kind, data)
    assert len(it[i]) == 1
    interval = it[i].pop()
    assert interval.data.kind == kind
    assert interval.data.data == data

def walk_asserts(it, noise, assert_dict):

    # assert about their kinds and contents
    for i, char in enumerate(noise):
        print(i, char)
        for interval, kind in assert_dict.items():
            if char in interval:
                pos_assert(it, i, kind, interval)

def test_align():
    noise = "abcdefghijklmnopqrstuvwxyz"
    signal = "bcdefklmnopqvwxyz"
    it = find_gaps(signal, noise)
    walk_asserts(it, noise, { "a": Kind.gap,
                              "bcdef": Kind.signal,
                              "ghij": Kind.gap,
                              "klmnopq": Kind.signal,
                              "rstu": Kind.gap,
                              "vwxyz": Kind.signal
                            }
                 )
def test_align_err():
    noise = "abcd"
    signal = "axcd"
    it = find_gaps(signal, noise)
    walk_asserts(it, noise, { "a": Kind.signal,
                              "b": Kind.error,
                              "cd": Kind.signal,
                            }
                 )

def test_align_err_gap():
    noise = "abcd"
    signal = "xd"
    it = find_gaps(signal, noise)
    walk_asserts(it, noise, { "ab": Kind.gap,
                              "c": Kind.error,
                              "d": Kind.signal,
                            }
                 )

def test_align_ambig():
    noise = "ab"
    signal = "x"
    it = find_gaps(signal, noise)
    if it[0].pop().data.kind is Kind.gap:
        walk_asserts(it, noise, { "a": Kind.gap,
                                  "b": Kind.error,
                                }
                     )
    else:
        walk_asserts(it, noise, { "a": Kind.error,
                                  "b": Kind.gap,
                                }
                     )

