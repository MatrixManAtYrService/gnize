import pexpect
import yaml
from time import sleep

from yaml.loader import SafeLoader
from gnize import dotdir

config = dotdir.make_or_get()


def inject_run_extact(noise, control_chars):

    c = pexpect.spawn(f"""sh -c 'echo "{noise}" | cog -d'""")
    c.send(control_chars)
    sleep(0.5)
    c.sendcontrol("c")
    sleep(0.5)
    print(c.read().decode())
    with open(config.runtime.debug_obj, "r") as f:
        obj = yaml.load(f.read(), Loader=yaml.SafeLoader)

    return obj


def test_delete_two():
    obj = inject_run_extact("hello world", "xx")

    h = obj["states"][0]
    e = obj["states"][1]
    l = obj["states"][2]

    assert h[0] == "h"
    assert h[1] == "noise"

    assert e[0] == "e"
    assert e[1] == "noise"

    assert l[0] == "l"
    assert l[1] == "signal"


def test_delete_three():

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
