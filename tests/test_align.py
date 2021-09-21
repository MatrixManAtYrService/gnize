import pytest
from gnize.cog import align_and_fix

def test_align():
    noise = "abcdefghijklmnopqrstuvwxyz"
    signal = "bcdefklmnopqvwxyz"
    signals, gaps, fixed_buffer = align_and_fix(signal, noise)
    assert signals[0].content == "bcdef"
    assert signals[1].content == "klmnopq"
    assert signals[2].content == "vwxyz"
    assert gaps[0].content == "a"
    assert gaps[1].content == "ghij"
    assert gaps[2].content == "rstu"
    print(fixed_buffer)


