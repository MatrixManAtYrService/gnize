from gnize.cog import DeletedSelection, DeletedMotion
from textwrap import dedent


def test_deleted_selection():
    original = "abcdefghijklmnop"
    edited = "abcghijkop"
    prev_selection = [(3, 6), (11,14)]

    theory = DeletedSelection(original, edited, 0, prev_selection)
    assert theory.evaluate() == {"def" : (3,6), "lmn": (11, 14)}

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

    theory = DeletedMotion(original, edited, 4, [])
    assert theory.evaluate() == {"\ndef": (3, 7)}

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

    theory = DeletedMotion(original, edited, 4, [])
    assert theory.evaluate() == {" def": (3, 7)}


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

    theory = DeletedMotion(original, edited, 0, [])
    assert theory.evaluate() == {"abc ": (0, 4)}


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

    theory = DeletedMotion(original, edited, 4, [])
    assert theory.evaluate() == {" def": (3, 7)}

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

    theory = DeletedMotion(original, edited, 1, [])
    assert theory.evaluate() == {"b": (1, 2)}
