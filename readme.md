# HL7 SIU^S12 Appointment Parser (No HL7 Libraries)

## What this does
Reads an HL7 `.hl7` file containing one or more SIU^S12 scheduling messages and prints a normalized JSON appointment object per message.

## Project structure
- `hl7_siu_parser/hl7.py`: HL7 wire-format parsing (segments/fields/components), message splitting, timestamp parsing
- `hl7_siu_parser/siu_s12.py`: SIU^S12 validation + appointment JSON mapping
- `hl7_siu_parser/cli.py`: command line runner
- `tests/`: unit tests

## How to run
```bash
python -m hl7_siu_parser.cli input.hl7