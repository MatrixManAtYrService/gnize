from gnize.cog import DeletedSelection, DeletedMotion
from textwrap import dedent


def test_deleted_selection():
    original = "abcdefghijklmnop"
    edited = "abcghijkop"
    prev_selection = [(3, 6), (11,14)]

    theory = DeletedSelection(original, edited, 10, 11, prev_selection)
    assert theory.evaluate() == (15, {"def" : (3,6), "lmn": (11, 14)})

def test_not_deleted_motion():
    original = dedent(
        """
        abcd
        efgh
        """
    ).strip()
    edited = dedent(
        """
        bcd
        fgh
        """
    ).strip()
    prev_selection = [(0, 1), (5, 6)]
    theory = DeletedMotion(original, edited, 12, 13, prev_selection)
    assert theory.evaluate() == (None, {})

def test_deleted_line():
    original = dedent(
        """
        abc
        def
        ghi
        """
    ).strip()
    edited = dedent(
        """
        abc
        ghi
        """
    ).strip()

    theory = DeletedMotion(original, edited, 4, 4, [])
    assert theory.evaluate() == (7, {"\ndef": (3, 7)})

def test_deleted_word():
    original = dedent(
        """
        abc def ghi
        """
    ).strip()
    edited = dedent(
        """
        abc ghi
        """
    ).strip()

    theory = DeletedMotion(original, edited, 3, 4, [])
    assert theory.evaluate() == (7, {" def": (3, 7)})


def test_deleted_linebegin():
    original = dedent(
        """
        abc def ghi
        """
    ).strip()
    edited = dedent(
        """
        def ghi
        """
    ).strip()

    theory = DeletedMotion(original, edited, 0, 0, [])
    assert theory.evaluate() == (4, {"abc ": (0, 4)})


def test_deleted_innerword():
    original = dedent(
        """
        abc def ghi
        """
    ).strip()
    edited = dedent(
        """
        abc ghi
        """
    ).strip()

    theory = DeletedMotion(original, edited, 3, 4, [])
    assert theory.evaluate() == (7, {" def": (3, 7)})

def test_deleted_lineend():
    original = dedent(
        """
        ab
        cd
        """
    ).strip()
    edited = dedent(
        """
        a
        cd
        """
    ).strip()

    theory = DeletedMotion(original, edited, 0, 1, [])
    assert theory.evaluate() == (2, {"b": (1, 2)})
