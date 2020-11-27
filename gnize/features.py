import sys
import select
from pyfinite import ffield
from gnize import galois
import json

field = ffield.FField(15)
# consider a two-byte-wide utf-8 character, think of it like a 15th
# degree polynomial:
#
# field.ShowPolynomial(int.from_bytes('¢'.encode('utf-8'), byteorder='big'))
# 'x^15 + x^14 + x^9 + x^7 + x^5 + x^1'


class Params:
    def __init__(self, threshold=0x0050, channel=900):
        self.threshold = threshold
        self.channel = galois.channel[channel]
        self.channel_degree = 15
        self.min_substr = 100
        self.max_substr = 1000


def all_subs(target: str, params=Params()) -> dict:
    """
    Return a dictionary mapping from rabin fingerprints to substrings
    """

    output = {}

    for i, _ in enumerate(target):

        batch = from_start(target[i:], params)
        output.update(batch)

    return output


def from_start(target: str, params: Params) -> dict:
    """
    Return a dictionary mapping from rabin fingerprints to substrings
    Only substrings beginning at the first character are considered
    """

    output = {}

    # Store four bytes at a time.  division by a 15 degree polynomial
    # will produce remainders smaller than two bytes, so after each
    # digest, there will be (at least) two bytes zero's to shift away
    buffer = 0
    buffer_degree = 63

    # rolling hash:
    # replace the buffer with the rabin fingerprint of the buffer plus
    # the new data (at least I think it's a rabin fingerprint)
    def digest(d: bytes, buffer):

        data = int.from_bytes(d, byteorder="big")

        buffer <<= 16
        buffer ^= data
        _, fingerprint = field.FullDivision(
            buffer, params.channel, buffer_degree, params.channel_degree
        )
        buffer = fingerprint
        return buffer

    # for each character
    for i, c in enumerate(target):

        if i > params.max_substr:
            break

        if i >= params.min_substr:

            # digest in two-byte chunks
            cbytes = c.encode("utf-8")
            if len(cbytes) <= 2:
                buffer = digest(cbytes, buffer)
            else:
                buffer = digest(cbytes[0:2], buffer)
                buffer = digest(cbytes[2:], buffer)

            if buffer <= params.threshold:

                # store the fingerprint of the substring from the beginning of the
                # string to the current character
                output["0x" + "{0:x}".format(buffer).zfill(4)] = target[0:i]

    return output


def fromcli():

    # fmt: off
    if not select.select([sys.stdin,],[],[],0.0)[0]:
    # fmt: on
        call_str = ' '.join(sys.argv)
        print(f"write a message to stdin like:\n\techo foo | {call_str}")
        exit(1)

    params = Params()

    message = sys.stdin.read().strip()
    fingerprints = all_subs(message, params)

    print(json.dumps(fingerprints, indent=2, sort_keys=True))
