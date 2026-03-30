import tuya
import consts
import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--level", "-l", type=int, choices=[0, 1, 2, 3], default=2)
    parser.add_argument("payload", action='extend', nargs="+", type=int)

    args = parser.parse_args()
    if args.verbose:
        print(args, file=sys.stderr)

    for message in args.payload:

#    if args.verbose:
#        print(
#            "    100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0",
#            file=sys.stderr,
#        )
#        print(f"   {message:0>129_b}", file=sys.stderr)

        ir_message = encode_ir_message(message)
#    assert len(ir_message) == (consts.MESSAGE_LENGTH_BITS * 2) + 3

        if args.verbose:
            print(ir_message)

        tuya_message = tuya.encode_ir(ir_message, args.level)
        print(tuya_message)


def encode_raw(payload):
    message = consts.PREAMBLE
    message |= payload

    return message


def encode_ir_message(message):
    bit_length = max(4, -(-message.bit_length() // 4) * 4)  # ceiling division trick
    ir_message = [consts.INTRO1, consts.INTRO2]

    for _ in range(0, bit_length):
        ir_message.append(consts.SHORT)
        ir_message.append(consts.LONG if message & 1 else consts.SHORT)
        message >>= 1

    # footer
    ir_message.append(consts.SHORT)
    return ir_message


if __name__ == "__main__":
    main()
