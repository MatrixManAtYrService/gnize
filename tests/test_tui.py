import pexpect
import yaml
from time import sleep

from yaml.loader import SafeLoader
from gnize import dotdir

config = dotdir.make_or_get()


def inject_run_extact(noise, control_chars):

    c = pexpect.spawn(f"""sh -c 'echo "{noise}" | cog -d'""")

    # send a string as many keystrokes
    if type(control_chars) is str:
        c.send(control_chars)

    # send keystrokes from a list of strings
    # but if you find a tuple, send "control+"
    # the first element
    elif type(control_chars) is list:
        for action in control_chars:
            if type(action) is str:
                c.send(action)
            if type(action) is tuple:
                c.sendcontrol(action[0])

    sleep(2)
    c.sendcontrol("c")
    sleep(2)
    print(c.read().decode())
    with open(config.runtime.debug_obj, "r") as f:
        obj = yaml.load(f.read(), Loader=yaml.SafeLoader)

    return obj


def test_delete_three():

    # this failure has something to do with having a repeated
    # char: "ll"

    obj = inject_run_extact("hello world", "xxx")

    h = obj["states"][0]
    e = obj["states"][1]
    l = obj["states"][2]

    assert h[0] == "h"
    assert h[1] == "noise"

    assert e[0] == "e"
    assert e[1] == "noise"

    assert l[0] == "l"
    assert l[1] == "noise"


def test_mode_prevention():

    # we don't want the user dropping into insert mode

    obj = inject_run_extact("hello world", "ia")

    h = obj["states"][0]

    assert h[0] == "h"
    assert h[1] == "signal"


def test_line_deletion():

    # deleting all the way to the end should be ok

    obj = inject_run_extact("ab\ncd", "ddjddkdd")

    a = obj["states"][0]
    b = obj["states"][1]
    newline = obj["states"][2]
    c = obj["states"][3]
    d = obj["states"][4]

    assert a[0] == "a"
    assert a[1] == "signal"

    assert b[0] == "b"
    assert b[1] == "signal"

    assert newline[0] == "\n"
    assert newline[1] == "signal"

    assert c[0] == "c"
    assert c[1] == "noise"

    assert d[0] == "d"
    assert d[1] == "noise"


def test_block_deletion():

    # delete a vertical block one character wide
    # the second char on the first row should be unaffected

    obj = inject_run_extact("abc\ndef\nghi", [("v"), "j", ("d")])

    a = obj["states"][0]
    b = obj["states"][1]

    assert a[1] == "noise"
    assert b[1] == "signal"
