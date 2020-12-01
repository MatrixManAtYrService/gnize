"""
# Purpose

This module implements a rolling hash algorithm which produces a value
for every substring in the input.  Given "abcd" it will calculate the
following:

substring: a    | fingerprint: 0x0061 |score: 98
substring: b    | fingerprint: 0x0062 |score: 99
substring: c    | fingerprint: 0x0063 |score: 100
substring: d    | fingerprint: 0x0064 |score: 101
substring: bc   | fingerprint: 0x23e3 |score: 9188
substring: ab   | fingerprint: 0x32fe |score: 13055
substring: bcd  | fingerprint: 0x5b2e |score: 23343
substring: abc  | fingerprint: 0x6465 |score: 25702
substring: cd   | fingerprint: 0x6f2d |score: 28462
substring: abcd | fingerprint: 0x7d9b |score: 32156

This algorithm ignores uninteresting fingprints (more leading 0's ->
more interesting). So despite calculating the hash for every substring,
it will select just a few.

This means that two people looking at the same data, but separated by space
and time, will generate the same limited set of fingerprints. They can
use those fingerprints to identify and annotate that data.

The criteria for which substrings end up with interesting fingerprints
will depend on which channel was used to generate fingerprints.

If the data you want to cognize doesn't have fingerprints in the right
places, try a different channel.  Alternatively, if you're the
recognizer, be sure to use the channel that the cognizer used.

This strategy may seem intractable (and indeed, it's not fast), but keep
in mind that humans hardly ever look at more than a few pages of text at
once. So it isn't likely that there will be a need for this to scale
beyond 10k characters.

# Example

Consider a two-byte-wide utf-8 character: "¢"
Its binary representation is 1100001010100010
Think of it like a 15th degree polynomial:

    'x^15 + x^14 + x^9 + x^7 + x^5 + x^1'

By the way, you can have pyfinite print that polynomial like so:

>> centsymbol = int.from_bytes('¢'.encode('utf-8'), byteorder='big')
>> pyfinite.ffield.FField(15).ShowPolynomial(centsymbol)

Fingerprinting in channel 964 involves division by the the irreducible
polynomial:

    1100010001001011

(Irreducible polynomials act like prim numbers in this space, dividing
by them is likely to create remainers.)

Viewed through channel 964, ¢'s fingerprint is...

>> F = pyfinite.ffield.FField(15)
>> channel = galois.channel[964]
>> _, fingerprint = F.FullDivision(centsymbol, channel, 15, 15)
>> hex(fingerprint)

    '0x6e9'

Suppose we want the fingerprint of "¢‽" instead.  That character is
three bytes wide.

>> interrobang = '‽'.encode('utf-8')
>> len(interrobang)

    '3'

utf-8 characters are never more then 4 bytes wide, so some characters
need to be split at the two-byte boundary.  The interrobang is one of
them.

>> interrobang_font = int.frombytes(iterrobang[0:2], byteorder='big')
>> interrobang_back = int.frombytes(iterrobang[2:0], byteorder='big')

Start with the fingerprint for "¢" and left-shift to make room for the
first part of the second character

>> bin(fingerprint<<16)

    '0b110111010010000000000000000'

Then add it, and divide by the channel polynomial once more:

>> _, interim_remainder = F.FullDivision((fingerprint<<16) + interrobang_front,
>>                                    channel,
>>                                    31,      # degree of divisor
>>                                    15)      # degree of dividend

Repeat for the second half of the second character to get the
fingerprint of "¢‽" in channel 964

>> _, fingerprint = F.FullDivision((interrim_remainder<<16) + interrobang_back,
>>                                    channel,
>>                                    31,      # degree of divisor
>>                                    15)      # degree of dividend
>> hex(fingerprint)

    '0xcb3'
"""

import sys
import select
import json
import argparse
import math
import logging
import timeit
from multiprocessing import Manager, Queue, Process
from copy import deepcopy
from pyfinite import ffield
from gnize import galois
from sortedcontainers import SortedDict
from collections import namedtuple
from textwrap import indent

field = ffield.FField(15)

Result = namedtuple("Result", "fingerprints stats")


class Params:

    defaults = {
        "channel": 963,
        "max_prefix_len": 15,
        "retry_percent": 0.01,
        "prefix_thresholds": [0x002F, 0x004F, 0x008F],
        "prefix_threshold": 0x002F,
        "skip_prefix": False,
        "feature_threshold": 0x00FF,
        "max_feature_len": 150,
        "parallel": True,
        "batch_size_divisor": 100,
        "batch_increase_divisor": 1000,
    }

    def __init__(self, **kwargs):

        # apply defaults, then override with user args
        self.__dict__.update(Params.defaults)
        self.__dict__.update(kwargs)

        # resolve channel number
        self.channel_polynomial = galois.channel[self.channel]
        self.channel_degree = math.floor(math.log(self.channel_polynomial, 2))


class Stats:
    """
    Useful details for parameter tuning
    """

    counters = [
        "fruitful_prefix_searches",
        "fruitless_prefix_searches",
        "fruitless_feature_searches",
        "features_found",
        "passes",
        "processes_used",
        "start_batch_size",
        "batch_size_increase",
    ]

    def __init__(self):
        for counter in Stats.counters:
            setattr(self, counter, 0)
            self.start = timeit.default_timer()

    def finalize(self):
        self.time = timeit.default_timer() - self.start

    def update(self, other):
        for counter in Stats.counters:
            old_value = getattr(self, counter)
            addition = getattr(other, counter)
            setattr(self, counter, old_value + addition)

    def __repr__(self):
        return "[" + self.__str__().replace("\n", "|") + "]"

    def __str__(self):
        lines = []
        for counter in Stats.counters:
            lines.append(f"{counter} = {getattr(self, counter)}")
        lines.append(f"time = {self.time}")
        return "\n".join(lines)


class Fingerprints:
    """
    A container for collecting fingerprints
    """

    def __init__(self):
        self.dict = SortedDict()

    def add(self, channel, prefix, feature, substring_range):

        subprints = "".join(
            [
                "[",
                str(channel),
                ":",
                "{0:x}".format(prefix).zfill(4),
                "->",
                "{0:x}".format(feature).zfill(4),
                "]",
            ]
        )

        score = (prefix + 1) * (feature + 1)

        self.dict.setdefault(score, {})[(substring_range, subprints)] = None

    def merge(self, other):

        for score, d in other.dict.items():
            for coords, substring in d.items():
                self.dict.setdefault(score, {})[coords] = substring

    def __str__(self):

        string = ""
        for score, d in self.dict.items():
            string += f"{score}:\n"
            for coords, substring in d.items():
                string += indent(f"{coords}\n", "    ")
                string += indent(f"{substring}\n", "        ")
        return string

    def as_json(self):

        out = {}

        for score, d in self.dict.items():
            for coords, substring in d.items():
                out.setdefault(score, {}).setdefault(coords[0][0], {})[coords[0][1]] = {
                    "fingerprint": coords[1],
                    "substring": substring,
                }

        return json.dumps(out, sort_keys=True, indent=2)

    def set_substrings(self, text):

        for score, d in self.dict.items():
            for coords, substring in d.items():
                start = coords[0][0]
                end = coords[0][1]
                self.dict[score][coords] = text[start:end]


def batch_worker(batch):
    """
    Called by the multiprocessing module, does a portion of the work
    parceled out by all_subs
    """

    start = timeit.default_timer()

    return_queue, tasks, params, batch_num = batch

    op_count = sum(map(len, [task[1] for task in tasks]))
    logging.debug(f"Batch: {batch_num} Size:{op_count}")

    _fingerprints = Fingerprints()
    _stats = Stats()

    for offset, target_substr in tasks:
        result = from_start(offset, target_substr, params)
        _fingerprints.merge(result.fingerprints)
        _stats.update(result.stats)

    return_queue.put(Result(_fingerprints, _stats))

    stop = timeit.default_timer()

    logging.debug("Batch: {}, Finished In: {}".format(batch_num, stop - start))


def all_subs(target: str, params=Params()) -> dict:
    """
    Scan all substrings of the target for fingerprints, return only the
    interesting ones (where interesting is determined by params.*_threshold)
    """

    fingerprints = Fingerprints()
    stats = Stats()

    # try a sparse scan first
    # accept weaker prefixes if nothing is found
    for attempt in params.prefix_thresholds:

        current_params = deepcopy(params)
        current_params.prefix_threshold = attempt
        stats.passes += 1

        offset_front_anchored_substrings = []
        # suppose target="abcdefghijklmnopqrstuvwxyz", then this loop creates:
        # abcdefghijklmnopqrstuvwxyz
        # bcdefghijklmnopqrstuvwxyz
        # cdefghijklmnopqrstuvwxyz
        # ...
        # xyz
        # yz
        # z
        for i in range(len(target)):
            offset_front_anchored_substrings.insert(0, (i, target[i:]))

        # this seems like a problem that would benefit from parallelism
        # but I can't get parallel to go faster than serial
        # why?

        if not current_params.parallel:

            # single threaded
            for offset, task in offset_front_anchored_substrings:
                result = from_start(offset, task, current_params)
                fingerprints.merge(result.fingerprints)
                stats.update(result.stats)

            stats.threads_used = 1

        else:

            logging.basicConfig(
                level=logging.DEBUG,
                format="%(relativeCreated)6d %(threadName)s %(message)s",
            )

            processes = []
            prepared_batches = []
            batch_num = 0
            return_queue = Queue()

            # the first chunks of work ar the heaviest, so carve off
            # larger chunks later
            batch_size = max(
                5, math.ceil(len(target) / current_params.batch_size_divisor)
            )
            batch_size_increase = max(
                1, math.ceil(len(target) / current_params.batch_increase_divisor)
            )

            stats.start_batch_size = batch_size
            stats.batch_size_increase = batch_size_increase

            # assign the work to batches
            while offset_front_anchored_substrings:

                # as tasks get smaller, allocate more of them to a thread
                work = []
                for _ in range(batch_size):
                    try:
                        work.append(offset_front_anchored_substrings.pop())
                        work.append(offset_front_anchored_substrings.pop())
                    except IndexError:
                        pass

                batch_size += batch_size_increase

                prepared_batches.append((return_queue, work, current_params, batch_num))
                batch_num += 1

            # start processing batches
            for batch in prepared_batches:
                p = Process(target=batch_worker, args=(batch,))
                processes.append(p)
                p.start()

            # aggregate results
            for result in [return_queue.get() for p in processes]:
                fingerprints.merge(result.fingerprints)
                stats.update(result.stats)

            # clean up processes
            # for process in processes:
            # p.join()

        fingerprints.set_substrings(target)

        # return if enough fingerprints were found
        if len(fingerprints.dict) > (current_params.retry_percent * len(target)):
            return Result(fingerprints, stats)

    # all scans exhausted, return what we foun
    return Result(fingerprints, stats)


def from_start(offset: int, target: str, params: Params) -> Result:
    """
    Return a dictionary mapping from scores to found fingerprints
    Only substrings beginning at the first character are considered:

    if target is 'tuvwxyz'
    fingerprints:
    t, tu, tuv, tuvw, tuvwx, tuvwxy, tuvwxyz
    """

    fingerprints = Fingerprints()
    stats = Stats()
    buffer = 0
    buffer_degree = 63

    # digest in two-byte chunks
    # buf(n) = mod(cat(buf(n-1),newdata), channelpolynomial)
    # This yields the rabin fingerprint of the bits digested so far (I think)
    def digest(d: bytes, buffer):

        data = int.from_bytes(d, byteorder="big")

        buffer <<= 16
        buffer ^= data
        _, fingerprint = field.FullDivision(
            buffer, params.channel_polynomial, buffer_degree, params.channel_degree
        )
        buffer = fingerprint
        return buffer

    # digest character-at-a-time
    # some unicode characters may require two digestions
    # others might involve superfluous zeros
    def digest_char(c: str, buffer):

        cbytes = c.encode("utf-8")
        if len(cbytes) <= 2:
            buffer = digest(cbytes, buffer)
        else:
            buffer = digest(cbytes[0:2], buffer)
            buffer = digest(cbytes[2:], buffer)

        return buffer

    # Prefixes are more plentiful than features. This lets recognizers
    # do a shallow first pass quickly and only do a deep second pass one
    # the substrings found by the first pass

    # start high, find the lowest as we go
    prefix_candidate_fingerprint = 0xFFFF
    prefix_fingerprint = None
    feature_found = False

    if params.skip_prefix:
        prefix_fingerprint = 0

    # for each character
    for i, c in enumerate(target):

        buffer = digest_char(c, buffer)

        if prefix_fingerprint is None:

            # update prefix candiate if updated fingerprint beats it
            if buffer < prefix_candidate_fingerprint:
                prefix_candidate_fingerprint = buffer

            # at the end of the prefix window
            if i == params.max_prefix_len:

                # did we find an interesting prefix?
                if prefix_candidate_fingerprint < params.prefix_threshold:

                    # save the best prefix so far
                    prefix_fingerprint = prefix_candidate_fingerprint
                    stats.fruitful_prefix_searches += 1

                else:
                    # prefix is boring, don't bother searching further
                    stats.fruitless_prefix_searches += 1
                    break
        else:
            # by this point we have a good prefix and are looking
            # features in subsequent substrings

            # don't look for gigantic features
            if i > params.max_feature_len:
                if not feature_found:
                    stats.fruitless_feature_searches += 1
                break

            # only register "interesting" features
            if buffer < params.feature_threshold:

                fingerprints.add(
                    params.channel, prefix_fingerprint, buffer, (offset, offset + i + 1)
                )
                feature_found = True
                stats.features_found += 1

    # ran out of message to search in
    if not feature_found:
        stats.fruitless_feature_searches += 1

    return Result(fingerprints, stats)


def fromcli():

    parser = argparse.ArgumentParser(description="read stdin, write gnize fingerprints")
    parser.add_argument("-t", "--stats", action="store_true")
    parser.add_argument("-n", "--no-prints", action="store_true")
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-s", "--serial", action="store_true")

    args = parser.parse_args()
    params = Params()

    # fmt: off
    if not select.select([sys.stdin, ], [], [], 0.0)[0]:
        # fmt: on
        call_str = ' '.join(sys.argv)
        print(f"write a message to stdin like:\n\techo foo | {call_str}")
        exit(1)

    message = sys.stdin.read().strip()

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
