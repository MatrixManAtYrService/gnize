import pytest
from itertools import islice
from collections import OrderedDict
from gnize.cog import Error, find_gaps, Kind, Data
from IPython import embed


def walk_asserts(it, noise, assert_dict):

    assert_iter = iter(assert_dict.items())
    noise_iter = iter(noise)
    interval_iter = iter(sorted(it.items(), key=lambda x: x.begin))
    print()
    print("intervals:", it)
    print("noise:", noise)
    print("assert_dict:", assert_dict)

    while True:
        # break if we run out of signal, noise, and noise at the same time
        # otherwise there's a problem

        # initialize for this iteration
        assert_str = None
        actual_str = None
        current_interval = None

        # consume an assertion
        try:
            print(f"consume assertion: {assert_str}")
            assertion_consumed = True
            assert_str, assert_kind = next(assert_iter)
        except StopIteration:
            print("no more assertions")
            assertion_consumed = False
            assert_str = ""
            assert_kind = None

        if assert_kind == Kind.error:
            assert_len = len(assert_str.original)
        else:
            assert_len = len(assert_str)

        # consume noise
        actual_str = "".join(islice(noise_iter, assert_len))
        if not actual_str:
            noise_consumed = False
            print("no more nose")
        else:
            noise_consumed = True
            print(f"consume noise: {actual_str}")

        # consume signal
        current_interval = None
        try:
            interval_consumed = True
            current_interval = next(interval_iter).data
            print(f"consume interval: {current_interval}")
        except StopIteration:
            print("no more intervals")
            interval_consumed = False

        # summarize step
        print("assert:", assert_str, "actual:", current_interval)

        # test concluded?
        if not noise_consumed and not interval_consumed and not assertion_consumed:
            break
        elif assertion_consumed and not interval_consumed:
            print("leftover assertion", assert_str)
            raise Exception("More assertions than intervals")
        elif interval_consumed and not assertion_consumed:
            print("leftover interval", current_interval)
            raise Exception("More intervals than asserts")

        # make assertions
        if type(assert_str) == Error:
            if type(current_interval.data) != Error:
                raise AssertionError(
                    f"Expected error {assert_str}, got {current_interval.data}"
                )

            err_noise = current_interval.data.original
            err_signal = current_interval.data.user_change
            assert_noise = assert_str.original
            assert_signal = assert_str.user_change
            if assert_noise != err_noise:
                raise AssertionError(f"Expected error {assert_noise}, got {err_noise}")
            if assert_signal != err_signal:
                raise AssertionError(
                    f"Expected error {assert_signal}, got {err_signal}"
                )

        elif actual_str != assert_str:
            raise AssertionError(f"Asserted about '{assert_str}', got '{actual_str}'")

        if assert_kind != current_interval.kind:
            raise AssertionError(
                f"Asserted about '{assert_kind}', got '{current_interval.kind}'"
            )


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
                "a": Kind.signal,
                Error(original="b", user_change="x"): Kind.error,
                "cd": Kind.signal,
            }
        ),
    )


def test_align_err_gaponly():
    noise = "az"
    signal = "apqz"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "a": Kind.signal,
                Error(original="", user_change="pq"): Kind.error,
                "z": Kind.signal,
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
                "ab": Kind.gap,
                Error(original="c", user_change="x"): Kind.error,
                "d": Kind.signal,
            }
        ),
    )


def test_align_ambig_1():
    noise = "ab"
    signal = "x"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "a": Kind.gap,
                Error(original="b", user_change="x"): Kind.error,
            }
        ),
    )


def test_align_ambig_2():
    noise = "x"
    signal = "ab"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                Error(original="x", user_change="ab"): Kind.error,
            }
        ),
    )


def test_err_mult():
    noise = "aaabbb"
    signal = "aaxxxbb"
    it = find_gaps(signal, noise)
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "aa": Kind.signal,
                Error(original="ab", user_change="xxx"): Kind.error,
                "bb": Kind.signal,
            }
        ),
    )


def test_gap_mult():
    noise = "aaabbb"
    signal = "aabb"
    it = find_gaps(signal, noise)
    # TODO: fiddle with weights so that scattered gaps are
    # discouraged and continuous gaps preferred
    #    walk_asserts(
    #        it,
    #        noise,
    #        OrderedDict(
    #            {
    #                "aa": Kind.signal,
    #                "ab": Kind.gap,
    #                "bb": Kind.signal,
    #            }
    #        ),
    #    )
    walk_asserts(
        it,
        noise,
        OrderedDict(
            {
                "a": Kind.gap,
                "aa": Kind.signal,
                "b": Kind.gap,
                "bb": Kind.signal,
            }
        ),
    )
