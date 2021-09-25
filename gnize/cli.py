import sys
import select
import argparse
from gnize.features import all_subs, Params as GnizeParams
from gnize.cog import make_canvas
from gnize import galois

def _read_stdin():

    # fmt: off
    if not select.select([sys.stdin, ], [], [], 0.0)[0]:
        # fmt: on
        call_str = ' '.join(sys.argv)
        print(f"write a message to stdin like:\n\techo foo | {call_str}")
        exit(1)

    return sys.stdin.read().strip()


def gn():

    parser = argparse.ArgumentParser(description="read stdin, write gnize fingerprints")
    parser.add_argument("-t", "--stats", action="store_true")
    parser.add_argument("-n", "--no-prints", action="store_true")
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-s", "--serial", action="store_true")

    args = parser.parse_args()
    params = GnizeParams()

    message = _read_stdin()

    # -a => print every fingerprint, not just the interesting ones
    if args.all:
        params.max_prefix_len = 0
        params.skip_prefix = True
        params.prefix_threshold = 0xFFFF
        params.feature_threshold = 0xFFFF

    if args.serial:
        params.parallel = False

    fingerprints, stats = all_subs(message, params)

    # -n => don't print fingerprints
    if not args.no_prints:
        if sys.stdout.isatty():
            print(fingerprints)
        else:
            print(fingerprints.as_json())

    # -s => print stats
    stats.finalize()
    if args.stats:
        print(stats, file=sys.stderr)

def cog():
    noise = _read_stdin()

    parser = argparse.ArgumentParser(description="read stdin, identify a signal in the noise")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    signal = make_canvas(noise, args)

