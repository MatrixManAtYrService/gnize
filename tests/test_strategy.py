from gnize.cog import DeletedSelection, DeletedLine
from textwrap import dedent

def test_deleted_selection():
    original = "abcdefghijklmnop"
    edited = "abcghijkop"
    prev_selection = [(3, 5), (11,13)]

    theory = DeletedSelection(original, edited, 0, 0, prev_selection)
    assert theory.replay_change() == edited

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
    prev_cursor_pos = 4

    theory = DeletedLine(original, edited, 4, 4, [])
    assert theory.replay_change() == edited




