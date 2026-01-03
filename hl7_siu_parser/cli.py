import json
import sys
from typing import List

from .hl7 import split_messages, parse_message
from .siu_s12 import parse_siu_s12_appointment
from .exceptions import HL7Error


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m hl7_siu_parser.cli input.hl7", file=sys.stderr)
        return 2

    path = argv[1]
    raw = ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    msgs = split_messages(raw)
    if not msgs:
        print("No HL7 messages found (no MSH segments).", file=sys.stderr)
        return 1

    exit_code = 0
    for i, raw_msg in enumerate(msgs, start=1):
        try:
            msg = parse_message(raw_msg)
            appt = parse_siu_s12_appointment(msg)
            print(json.dumps(appt, ensure_ascii=False))
        except HL7Error as e:
            exit_code = 1
            err_obj = {"message_index": i, "error": type(e).__name__, "detail": str(e)}
            print(json.dumps(err_obj, ensure_ascii=False), file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
