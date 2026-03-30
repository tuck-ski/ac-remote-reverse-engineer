import tuya
import consts
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("code_file", type=argparse.FileType())
    args = parser.parse_args()

    print(
        "      100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0"
    )

    diff = 0
    previous = 0

    for i, tuya_code in enumerate(args.code_file.readlines()):
        try:
            payload = decode_tuya_code(tuya_code)
            print(payload)
        except AssertionError as a:
            print(a)
            continue

        if i > 0:
            diff |= payload ^ previous
            print(f"{i:>3}: {payload:0>129_b}")
            diff_str = f"{diff:0>129_b}".replace("0", " ").replace("_", " ").replace("1", "^")
            print(f"     {diff_str}")
            diff = 0
        previous = payload

    # highlight bit differences across all codes
    diff_str = f"{diff:0>129_b}".replace("0", " ").replace("_", " ").replace("1", "^")
    print(f"     {diff_str}")
    print(
        "      100   96   92   88   84   80   76   72   68   64   60   56   52   48   44   40   36   32   28   24   20   16   12    8    4    0"
    )

    print()

def decode_tuya_code(line):
    ir_code = tuya.decode_ir(line)
    print(ir_code)

    # if 65535 in ir_code:
    #     code_1 = ir_code[:ir_code.index(65535)]
    #     response_1 = decode_single_code(code_1)
    #     code_2 = ir_code[ir_code.index(65535)+1:]
    #     try:
    #         response_2 = decode_single_code(code_2)
    #         print(response_1 == response_2)
    #     except AssertionError as a:
    #         print("2nd code too long")
    #
    #     return response_1
    # else:
    return decode_single_code(ir_code)

def decode_single_code(ir_code):
    # skip the first two entries, they're a preamble that doesn't contain any data
    ir_code = ir_code[2:]

    encoded_bits = (len(ir_code) - 1) // 2
#    assert (
#        encoded_bits == consts.MESSAGE_LENGTH_BITS
#    ), f"IR code doesn't contain exact bits for a full message: {encoded_bits}/{consts.MESSAGE_LENGTH_BITS}\n{line.strip()}\n{ir_code}"

    payload = 0
    # zipping something with itself will iterate through adjacent pairs. the message is of odd length because of the
    # SHORT-length footer at the end. this method of zipping will deliberately ignore it
    code_iter = iter(ir_code)
    for i, (v1, v2) in enumerate(zip(code_iter, code_iter)):
        bit = decode_pair(v1, v2)
        assert (
            bit is not None
        ), f"Bit failed to decode: {v1}, {v2}"
# \n{line.strip()}\n{ir_code}"

        payload |= bit << i

    return payload


def decode_pair(i1, i2):
    if i1 <= consts.LENGTH_CUTOFF and i2 <= consts.LENGTH_CUTOFF:
        return 0

    if i1 <= consts.LENGTH_CUTOFF and i2 > consts.LENGTH_CUTOFF:
        return 1


def decode_settings(payload):
    # the temperature is offset by 8 probably to save one bit in the message
    temp_c = ((payload >> 11) & 0x1F) + 8
    # no idea why F is off by 8 but in the other direction, it doesn't save any space?
    temp_f = ((payload >> 81) & 0x7F) - 8
    # other models have multiple swing values, this one's just on/off
    swing = not bool((payload >> 8) & 0x7)
    speed = decode_speed_value((payload >> 37) & 0x7)
    unit = "F" if ((payload >> 49) & 1) else "C"
    sleep = bool((payload >> 50) & 1)
    mode = decode_mode_value((payload >> 53) & 0x7)
    on = bool((payload >> 77) & 1)
    button = decode_button_value((payload >> 88) & 0xF)

    actual_csum = (payload >> 96) & 0xFF
    our_csum = calc_checksum(payload)
    assert (
        actual_csum == our_csum
    ), f"Checksum mismatch: {actual_csum:0>9_b} vs {our_csum:0>9_b}"

    return (
        f"on:{on:>1}  temp:{temp_c if unit == 'C' else temp_f:>2}{unit}  mode:{mode:>4}  speed:{speed:>4}  "
        f"swing:{swing:>1}  sleep:{sleep:>1}  button:{button:>5}  csum:{actual_csum:0>9_b}"
    )


def decode_mode_value(v):
    assert v in [0, 1, 2, 6], f"Unknown mode value: {v} ({v:03b})"

    if v == 0:
        return "AUTO"
    elif v == 1:
        return "COOL"
    elif v == 2:
        return "DRY"
    elif v == 6:
        return "FAN"


def decode_speed_value(v):
    assert v in [1, 2, 3, 5], f"Unknown fan speed value: {v} ({v:03b})"

    if v == 1:
        return "HIGH"
    elif v == 2:
        return "MID"
    elif v == 3:
        return "LOW"
    elif v == 5:
        return "AUTO"


def decode_button_value(v):
    assert v in [
        0,
        1,
        2,
        4,
        5,
        6,
        7,
        11,
        13,
    ], f"Unknown button value: {v} ({v:04b})"

    if v == 0:
        return "PLUS"
    elif v == 1:
        return "MINUS"
    elif v == 2:
        return "SWING"
    elif v == 4:
        return "SPEED"
    elif v == 5:
        return "ONOFF"
    elif v == 6:
        return "MODE"
    elif v == 7:
        return "UNIT"
    elif v == 11:
        return "SLEEP"
    elif v == 13:
        return "TIMER"


def calc_checksum(payload):
    payload &= ~(0xFF << 96)  # zero the included checksum from the payload
    sum = 0
    while payload > 0:
        sum += payload & 0xFF
        payload >>= 8

    return sum & 0xFF


if __name__ == "__main__":
    main()
