import paho.mqtt.publish as publish
import paho.mqtt.subscribe as subscribe
import json
import sys
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", type=str, required=True)
    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)

    args = parser.parse_args()

    i = 0
    try:
        while True:
            print(f"[{i}] Requesting a code...", file=sys.stderr)

            publish.single(
                args.topic + "/set",
                '{"learn_ir_code": "ON"}',
                hostname=args.broker,
            )
#               auth={"username": args.username, "password": args.password},

            msg = subscribe.simple(
                args.topic,
                hostname=args.broker,
            )
#               auth={"username": args.username, "password": args.password},

            response = json.loads(msg.payload)
            print(response["learned_ir_code"])
            i += 1
    except KeyboardInterrupt:
        print("\nExiting.", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
