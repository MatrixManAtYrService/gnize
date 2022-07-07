import pexpect
import yaml
from time import sleep

from yaml.loader import SafeLoader
from gnize import dotdir

config = dotdir.make_or_get()


def inject_run_extact(noise, control_chars):

    c = pexpect.spawn(f"""sh -c 'echo "{noise}" | cog -d'""")
    c.send(control_chars)
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
