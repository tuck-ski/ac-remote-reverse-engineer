import tuya
import consts_daikin
import argparse
import pdb

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("code_file", type=argparse.FileType())
    args = parser.parse_args()

    print(
        "      148  144  140  136  132  128  124  120  116  112  108  104  100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0"
    )

    all_settings = []
    diff = 0
    previous = 0

    for i, tuya_code in enumerate(args.code_file.readlines()):
        try:
            payload = decode_tuya_code(tuya_code)
            settings = decode_settings(payload)
        except AssertionError as a:
            print(a)
            continue

        print(f"{payload[0]:0>_b}")
        print(f"{i:>3}: {payload[1]:0>189_b}")

        if i > 0:
            local_diff |= payload ^ previous
            diff |= payload[1] ^ previous
            diff_str = f"{local_diff:0>189_b}".replace("0", " ").replace("_", " ").replace("1", "^")
            print(f"     {diff_str}")
            local_diff = 0
        previous = payload[1]

#        print(f"{i:>3}: {payload:0>129_b}")
        all_settings.append((i, settings))
        # print(f"    {tuya_code}")

    # highlight bit differences across all codes
    diff_str = f"{diff:0>189_b}".replace("0", " ").replace("_", " ").replace("1", "^")
    print(f"     {diff_str}")
    print(
        "      148  144  140  136  132  128  124  120  116  112  108  104  100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0"   )

    print()

    for i, s in all_settings:
        print(f"{i:>3}: {s}")


def decode_tuya_code(line):
    ir_code = tuya.decode_ir(line)
    # print(ir_code)

    if 65535 in ir_code:
        index_pos = ir_code.index(65535)
        relative_pos = index_pos / len(ir_code)
        if relative_pos < 0.45:
            ir_code = ir_code[index_pos+1:]
        elif relative_pos > 0.55:
            ir_code = ir_code[:index_pos]
        # pretty much in the middle, could try and split it to read both?

    delimiter_pos = []
    ir_iter = iter(ir_code)
    for i, span in enumerate(ir_iter):
        if span < consts_daikin.DELIMITER_MIN_LENGTH:
            continue
        delimiter_pos.append(i)

    assert (
            len(delimiter_pos) > 0
            ), "Malformed code, expected delimiter not found"
    assert (
            len(delimiter_pos) < 3
            ), "Malformed code, too many delimiters"

    if len(delimiter_pos) == 1:
        return [0, decode_single_code(ir_code[delimiter_pos[0]+3:])]
    else:
        first_decode = decode_single_code(ir_code[delimiter_pos[0]+3:delimiter_pos[1]])
        second_decode = decode_single_code(ir_code[delimiter_pos[1]+3:])
        print(f" {first_decode}")
#        print(second_decode)
        return [first_decode, second_decode]

def decode_single_code(ir_code):
#    encoded_bits = (len(ir_code) - 1) // 2
#    assert (
#        encoded_bits == consts_daikin.MESSAGE_LENGTH_BITS
#    ), f"IR code doesn't contain exact bits for a full message: {encoded_bits}/{consts_daikin.MESSAGE_LENGTH_BITS}\n{line.strip()}\n{ir_code}"

    payload = 0
    # zipping something with itself will iterate through adjacent pairs. the message is of odd length because of the
    # SHORT-length footer at the end. this method of zipping will deliberately ignore it
    code_iter = iter(ir_code)
    for i, (v1, v2) in enumerate(zip(code_iter, code_iter)):
        bit = decode_pair(v1, v2)
        assert (
            bit is not None
        ), f"Bit failed to decode: {v1}, {v2}"

        payload |= bit << i

    return payload


def decode_pair(i1, i2):
    if i1 <= consts_daikin.LENGTH_CUTOFF and i2 <= consts_daikin.LENGTH_CUTOFF:
        return 0

    if i1 <= consts_daikin.LENGTH_CUTOFF and i2 > consts_daikin.LENGTH_CUTOFF:
        return 1


def decode_settings(payload):
    first = payload[0]
    data = payload[1]
    mode = decode_mode_value((data >> 44) & 0x7)
    temp = decode_temp((data >> 49) & 0x7F)
    speed = decode_speed_value((data >> 68) & 0xF)

    swing = decode_swing((first >> 100) & 0x7)
    on = not bool((first >> 95) & 1)

    actual_csum = (data >> 144) & 0xFF
    our_csum = calc_checksum(data)
    assert (
        actual_csum == our_csum
    ), f"Checksum mismatch: {actual_csum:0>9_b} vs {our_csum:0>9_b}"

    return (
        f"temp:{temp} mode:{mode:>4}  speed:{speed:>4}  "
        f"swing:{swing:>4} on:{on} csum:{actual_csum:0>9_b}"
    )

def decode_temp(v):
    relative_temp = bool((v >> 6) & 1)
    if not relative_temp:
        return v & 0x3F
    nibble = v & 0xF
    if nibble > 8:
        nibble = nibble - 16
    return nibble

def decode_mode_value(v):
    assert v in [0, 2, 3, 4, 6], f"Unknown mode value: {v} ({v:03b})"

    if v == 0:
        return "AUTO"
    elif v == 3:
        return "COOL"
    elif v == 4:
        return "HEAT"
    elif v == 2:
        return "DRY"
    elif v == 6:
        return "FAN"

def decode_speed_value(v):
    assert v in [3, 4, 5, 6, 7, 10, 11], f"Unknown fan speed value: {v} ({v:03b})"

    if v == 11:
        return "QUIET"
    elif v == 10:
        return "AUTO"
    return str(v - 2)

def decode_swing(v):
    assert v in [0, 1, 2, 3, 4, 5], f"Unknown fan swing value: {v} ({v:03b})"

    if v == 0:
        return "AUTO"
    return v

def calc_checksum(payload):
    payload &= ~(0xFF << 144)  # zero the included checksum from the payload
    sum = 0
    while payload > 0:
        sum += payload & 0xFF
        payload >>= 8

    return sum & 0xFF


if __name__ == "__main__":
    main()
