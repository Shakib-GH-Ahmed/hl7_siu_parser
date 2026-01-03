# HL7 SIU^S12 Appointment Parser (No HL7 Libraries)

## What this does
This project reads an HL7 `.hl7` file that may contain one or more **SIU^S12** scheduling messages and prints a **normalized JSON** appointment object per message.

It implements HL7 parsing manually (no external HL7 parsing libraries), and handles common real-world issues like missing fields, missing segments, extra segments, and malformed PV1/SCH positioning.

## Output format
Each parsed message produces a JSON object like:

```json
{
  "appointment_id": "123456",
  "appointment_datetime": "2025-05-02T13:00:00Z",
  "patient": {
    "id": "P12345",
    "first_name": "John",
    "last_name": "Doe",
    "dob": "1985-02-10",
    "gender": "M"
  },
  "provider": {
    "id": "D67890",
    "name": "Dr Jane Smith"
  },
  "location": "Clinic A Room 203",
  "reason": "General Consultation"
}

# Project structure

* `hl7_siu_parser/hl7.py`
  * Splits multiple messages in a file (each starts with `MSH`)
  * Reads separators from `MSH` (field/component/repetition/escape/subcomponent)
  * Parses segments and provides safe field/component getters
  * Normalizes HL7 timestamps to ISO 8601 UTC (`...Z`)

* `hl7_siu_parser/siu_s12.py`
  * Validates message type (`MSH-9` must be `SIU^S12`)
  * Maps `SCH`, `PID`, `PV1` into the normalized appointment JSON
  * Uses defensive fallbacks for shifted/malformed fields

* `hl7_siu_parser/cli.py`
  * CLI runner: reads file, parses each message, prints JSON

* `tests/`
  * Unit tests for valid parsing, missing segments, wrong message type, and timestamp conversion

# How to run (CLI)

From the project root:
```bash
python -m hl7_siu_parser.cli input.hl7
```

If the file contains multiple SIU messages, the program prints one JSON object per message.

Unsupported message types (not SIU^S12) are reported clearly to stderr.

# How to run tests

From the project root:
```bash
python -m unittest discover -s tests -p "test*.py" -q
```

# HL7 field mapping (best-effort)

Because vendor HL7 feeds vary, the parser uses practical fallbacks:

* **Validate type**: `MSH-9.1 == SIU` and `MSH-9.2 == S12`

* **appointment_id**: `SCH-1.1` fallback `SCH-2.1`

* **appointment_datetime**: from `SCH-11` (tries common TQ placements)

* **patient**
  * id: `PID-3.1` (fallbacks supported)
  * name: `PID-5.2` (first) and `PID-5.1` (last)
  * dob: `PID-7`
  * gender: `PID-8`

* **provider**
  * normally `PV1-7` (Attending Doctor)
  * fallback to `PV1-6` if the message is malformed/shifted

* **location**: `PV1-3` (facility/point-of-care/room/bed combined)

* **reason**
  * tries `SCH-7` first, then falls back to `SCH-8` / `SCH-6` (common vendor variations)

# Timestamp handling

HL7 TS is normalized to ISO 8601 UTC:

* Example: `20250502130000+0600` → `2025-05-02T07:00:00Z`

* If timezone is missing in the HL7 TS, the parser assumes UTC.

# Assumptions and tradeoffs

* This is not a full HL7 v2 implementation; it focuses on SIU^S12 scheduling needs.

* Missing `PID` / `PV1` results in missing/empty patient/provider fields; missing `SCH` fails because an appointment cannot be formed.

* Basic HL7 escape sequences are supported (`\F\`, `\S\`, `\R\`, `\E\`, `\T\`).