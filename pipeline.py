from pathlib import Path
import importlib
import conducto as co


def main() -> co.Serial:
    with co.Parallel() as tests:
        for testfile in (Path(__file__).parents[0] / "tests").iterdir():

            # ignore __init__.py
            if testfile[0:2] != "__":

                # foo.py -> foo
                modulename = testfile[:-2]
                test = importlib.import_module(".".join(["tests", modulename]))

            print(testfile)
            # with open(test, 'r') as r:
            # test = json.loads(testfile.read())
            # co.Exec("echo {r.read()}
    return tests


if __name__ == "__main__":
    co.main(default=main)
