import tuya
import consts_daikin as consts
import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--on", action="store_const", const=True, default=True)
    parser.add_argument("--off", action="store_const", const=False, dest="on")
    parser.add_argument("--temp", type=int, default=18)
    parser.add_argument(
        "--mode", type=str.lower, choices=["auto", "cool", "heat", "dry", "fan"], default="auto"
    )
    parser.add_argument(
        "--fan", type=str.lower, choices=["quiet", "auto", "1", "2", "3", "4", "5"], default="auto"
    )
    parser.add_argument(
        "--swing", type=str.lower, choices=["auto", "1", "2", "3", "4", "5"], default="auto"
    )
    parser.add_argument(
        "--level", "-l", type=int, choices=[0, 1, 2, 3], default=2
    )

    parser.add_argument("--json", type=str.lower)

    args = parser.parse_args()
    if args.verbose:
        print(args, file=sys.stderr)

    if args.json is None:
        first = map_first(args.on, args.swing)
        message = encode_message(
            args.on,
            args.temp,
            args.mode,
            args.fan,
            args.swing,
        )
    else:
        params = json.loads(args.json)
        first = map_first(params.get("on", True),
                          params.get("swing", "auto"))
        message = encode_message(
            params.get("on", True),
            params.get("temp", 18),
            params.get("mode", "auto"),
            params.get("fan", "auto"),
            params.get("swing", "auto"),
        )

    if args.verbose:
        print(first, file=sys.stderr)
        print(
            "    148  144  140  136  132  128  124  120  116  112  108  104  100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0",
            file=sys.stderr,
        )
        print(f"   {message:0>189_b}", file=sys.stderr)

    ir_message = encode_ir_message(first, message)
#    assert len(ir_message) == (consts.MESSAGE_LENGTH_BITS * 2) + 3

    if args.verbose:
        print(ir_message)

    tuya_message = tuya.encode_ir(ir_message, args.level)
    print(tuya_message)

def map_first(on, swing):
    match swing:
        case "auto":
            return 114179815416476790484662877555959610919212276241 if on else 844930634081928249626119375171233289543950522897
        case "5":
            return 205523667749658224140043779828956701144411265553 if on else 936274486415109683281500277444230379769149512209
        case "4":
            return 296867520082839657795424682101953791369610254865 if on else 1027618338748291116936881179717227469994348501521
        case "3":
            return 388211372416021091450805584374950881594809244177 if on else 1118962191081472550592262081990224560219547490833
        case "2":
            return 479555224749202525106186486647947971820008233489 if on else 1210306043414653984247642984263221650444746480145
        case "1":
            return 570899077082383958761567388920945062045207222801 if on else 1301649895747835417903023886536218740669945469457

def encode_message(on, temp, mode, fan, swing):
    message = consts.BASE_MESSAGE

    message |= (1 if on else 0) << 40

    if mode == "fan":
        temp = 25

    message |= encode_mode(mode) << 44
    message |= encode_temp(temp, mode) << 49

    message |= (1 if mode in ["dry", "auto"] else 0) << 63
    message |= (15 if swing == "auto" else 0) << 64

    message |= encode_fan(fan) << 68

    message |= calc_checksum(message) << 144

    return message

def encode_temp(temp, mode):
    if mode == "auto":
        assert -5 <= temp <= 5, f"Invalid temp value: {temp}"
    elif mode == "cool":
        assert 18 <= temp <= 32, f"Invalid temp value: {temp}"
    elif mode == "heat":
        assert 14 <= temp <= 30, f"Invalid temp value: {temp}"
    elif mode == "dry":
        assert -2 <= temp <= 2, f"Invalid temp value: {temp}"

    if temp > 5:
        return temp

    if temp < 0:
        temp = 16 + temp
    # 1100000
    return 96 + temp

def encode_mode(mode):
    if mode == "auto":
        return 0
    elif mode == "cool":
        return 3
    elif mode == "heat":
        return 4
    elif mode == "dry":
        return 2
    elif mode == "fan":
        return 6

    print(f"WARN: Unknown mode: {mode}")
    return 0

def encode_fan(speed):
    if speed == "auto":
        return 10
    elif speed == "quiet":
        return 11

    try:
        value = int(speed)
        if 1 <= value <= 5:
            return value + 2
    except ValueError:
        print(f"WARN: Unknown fan speed: {speed}")
        return 10

    print(f"WARN: Unknown fan speed: {speed}")
    return 10

def calc_checksum(message):
    sum = 0
    for _ in range(0, consts.MESSAGE_LENGTH_BITS // 8):
        sum += message & 0xFF
        message >>= 8

    return sum & 0xFF


def encode_ir_message(first, message):
    # [428, 428, 428, 478, 428, 428, 428, 428, 428, 428, 428, 25388, 3507, 1749,
    # first
    # 34961, 3507, 1749, 
    # message]

    ir_message = [consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.SHORT, consts.DELIM1, consts.INTRO1, consts.INTRO2]

    append_ir_message(first, ir_message)

    ir_message.append(consts.DELIM2)
    ir_message.append(consts.INTRO1)
    ir_message.append(consts.INTRO2)

    append_ir_message(message, ir_message)

    return ir_message

def append_ir_message(message, ir_message):
    bit_length = max(8, -(-message.bit_length() // 8) * 8)
    for _ in range(0, bit_length):
        ir_message.append(consts.SHORT)
        ir_message.append(consts.LONG if message & 1 else consts.SHORT)
        message >>= 1

    # footer
    ir_message.append(consts.SHORT)
    return ir_message


if __name__ == "__main__":
    main()
