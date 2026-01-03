from __future__ import annotations

from typing import Any, Dict, Optional

from .hl7 import HL7Message, parse_hl7_date, parse_hl7_ts_to_datetime, to_iso8601_z
from .exceptions import MissingSegment, UnsupportedMessageType


def _first_nonempty(*vals: str) -> str:
    for v in vals:
        if v:
            return v
    return ""


def validate_siu_s12(msg: HL7Message) -> None:
    # MSH-9 is message type (composite)
    mt_1 = msg.get_component("MSH", 9, 1, default="")  # e.g., SIU
    mt_2 = msg.get_component("MSH", 9, 2, default="")  # e.g., S12
    if (mt_1, mt_2) != ("SIU", "S12"):
        raw = msg.get_field("MSH", 9, default="")
        raise UnsupportedMessageType(f"Unsupported message type in MSH-9: '{raw}'")


def parse_siu_s12_appointment(msg: HL7Message) -> Dict[str, Any]:
    validate_siu_s12(msg)

    if "SCH" not in msg.segments:
        raise MissingSegment("Missing SCH segment (required for appointment).")

    # Appointment ID: prefer SCH-1.1 (EI.1), fallback SCH-2.1
    appt_id = _first_nonempty(
        msg.get_component("SCH", 1, 1, default=""),
        msg.get_component("SCH", 2, 1, default=""),
        msg.get_field("SCH", 1, default=""),
        msg.get_field("SCH", 2, default=""),
    )

    # Appointment start datetime:
    # Commonly SCH-11 is TQ; component 4 is start datetime.
    dt_raw = _first_nonempty(
        msg.get_component("SCH", 11, 4, default=""),
        msg.get_component("SCH", 11, 1, default=""),
        msg.get_field("SCH", 11, default=""),
    )
    dt_obj = parse_hl7_ts_to_datetime(dt_raw)
    appt_datetime_iso = to_iso8601_z(dt_obj) if dt_obj else ""

    # Patient: PID can be missing; handle gracefully by empty strings
    pid_present = "PID" in msg.segments
    patient_id = (
        _first_nonempty(
            msg.get_component("PID", 3, 1, default=""),
            msg.get_component("PID", 2, 1, default=""),
            msg.get_field("PID", 3, default=""),
        )
        if pid_present
        else ""
    )
    patient_last = msg.get_component("PID", 5, 1, default="") if pid_present else ""
    patient_first = msg.get_component("PID", 5, 2, default="") if pid_present else ""
    dob_raw = msg.get_field("PID", 7, default="") if pid_present else ""
    dob = parse_hl7_date(dob_raw)
    gender = msg.get_field("PID", 8, default="") if pid_present else ""

    # Provider: PV1 can be missing; handle gracefully
    pv1_present = "PV1" in msg.segments
    prov_id = msg.get_component("PV1", 7, 1, default="") if pv1_present else ""
    prov_family = msg.get_component("PV1", 7, 2, default="") if pv1_present else ""
    prov_given = msg.get_component("PV1", 7, 3, default="") if pv1_present else ""
    prov_prefix = msg.get_component("PV1", 7, 6, default="") if pv1_present else ""

    prov_name_parts = [p for p in [prov_prefix, prov_given, prov_family] if p]
    prov_name = " ".join(prov_name_parts)

    # Location: prefer PV1-3 (Assigned Patient Location) then SCH-? best-effort
    # PV1-3 is PL: point of care ^ room ^ bed ^ facility ...
    if pv1_present:
        loc_poc = msg.get_component("PV1", 3, 1, default="")
        loc_room = msg.get_component("PV1", 3, 2, default="")
        loc_bed = msg.get_component("PV1", 3, 3, default="")
        loc_fac = msg.get_component("PV1", 3, 4, default="")
        location = " ".join([p for p in [loc_fac, loc_poc, loc_room, loc_bed] if p]).strip()
    else:
        location = ""

    # Reason: SCH-7 is commonly "Appointment Reason" (CE) -> prefer text (comp2), else identifier (comp1)
    reason = _first_nonempty(
        msg.get_component("SCH", 7, 2, default=""),
        msg.get_component("SCH", 7, 1, default=""),
        msg.get_field("SCH", 7, default=""),
    )

    return {
        "appointment_id": appt_id,
        "appointment_datetime": appt_datetime_iso,
        "patient": {
            "id": patient_id,
            "first_name": patient_first,
            "last_name": patient_last,
            "dob": dob.isoformat() if dob else "",
            "gender": gender,
        },
        "provider": {
            "id": prov_id,
            "name": prov_name,
        },
        "location": location,
        "reason": reason,
    }