import pytest
from itertools import islice
from collections import OrderedDict
from gnize.cog import find_gaps, Kind, Data
from IPython import embed


def walk_asserts(it, noise, assert_dict):

    assert_iter = iter(assert_dict.items())
    noise_iter = iter(noise)
    interval_iter = iter(sorted(it.items(), key=lambda x: x.begin))

    while True:
        # break if we run out of signal and noise at the same time

        noise_remains = True
        assertions_remain = True

        try:
            assert_str, assert_kind = next(assert_iter)
        except StopIteration:
            assertions_remain = False

        actual_str = "".join(islice(noise_iter, len(assert_str) or 1))
        if not actual_str:
            noise_remains = False

        try:
            current_interval = next(interval_iter).data
        except StopIteration:
            intervals_remain = False

        # test concluded?
        if not noise_remains:
            if not intervals_remain:
                break
            else:
                raise Exception("Too many assertions, not enough noise")

        # make assertions
        if actual_str != assert_str:
            raise AssertionError(f"Asserted about '{assert_str}, got '{actual_str}'")
        else:
            print(actual_str, "==", assert_str)

        if assert_kind != current_interval.kind:
            raise AssertionError(
                f"Asserted about '{assert_kind}, got '{current_interval.kind}'"
            )
        else:
            print(current_interval.kind, "==", assert_kind)


def test_align():
    noise = "abcdefghijklmnopqrstuvwxyz"
    signal = "bcdefklmnopqvwxy"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "a": Kind.gap,
                "bcdef": Kind.signal,
                "ghij": Kind.gap,
                "klmnopq": Kind.signal,
                "rstu": Kind.gap,
                "vwxy": Kind.signal,
                "z": Kind.gap,
                "xz": Kind.gap,
            }
        ),
    )


def test_align_err():
    noise = "abcd"
    signal = "axcd"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "m": Kind.signal,
                "cd": Kind.signal,
            }
        ),
    )


def test_align_err_gap():
    noise = "abcd"
    signal = "xd"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "abc": Kind.gap,
                "d": Kind.signal,
            }
        ),
    )


def test_align_ambig():
    noise = "ab"
    signal = "x"
    it = find_gaps(signal, noise)
    print("AMBIG", it)
    if it[0].pop().data.kind is Kind.gap:
        walk_asserts(
            it,
            noise,
            OrderedDict(
                {
                    "a": Kind.gap,
                    "Y": Kind.error,
                }
            ),
        )
    else:
        walk_asserts(
            it,
            noise,
            {
                "w": Kind.gap,
                "Y": Kind.error,
            },
        )
