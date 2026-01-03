from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import re
from datetime import datetime, date, timezone, timedelta

from .exceptions import HL7ParseError


@dataclass(frozen=True)
class Separators:
    field: str
    component: str
    repetition: str
    escape: str
    subcomponent: str


class HL7Message:
    """
    Stores segments as: segments["PID"] -> list of occurrences (each occurrence is a list[str] fields)
    Fields indexing aligns with HL7 field numbers:
      - For non-MSH: fields[0] = segment name, fields[1] = SEG-1, fields[2] = SEG-2, ...
      - For MSH: fields[0] = "MSH", fields[1] = MSH-1 (field sep), fields[2] = MSH-2 (encoding chars), ...
    """

    def __init__(self, seps: Separators, segments: Dict[str, List[List[str]]]):
        self.seps = seps
        self.segments = segments

    def get_field(
        self,
        seg: str,
        field_num: int,
        seg_index: int = 0,
        default: str = "",
    ) -> str:
        occs = self.segments.get(seg)
        if not occs or seg_index >= len(occs):
            return default
        fields = occs[seg_index]
        if field_num >= len(fields):
            return default
        return fields[field_num] or default

    def get_component(
        self,
        seg: str,
        field_num: int,
        comp_num: int,
        seg_index: int = 0,
        rep_index: int = 0,
        default: str = "",
    ) -> str:
        raw = self.get_field(seg, field_num, seg_index=seg_index, default=default)
        if not raw:
            return default

        reps = raw.split(self.seps.repetition) if self.seps.repetition else [raw]
        if rep_index >= len(reps):
            return default

        rep_val = reps[rep_index]
        comps = rep_val.split(self.seps.component) if self.seps.component else [rep_val]
        if comp_num <= 0:
            return default
        idx = comp_num - 1
        if idx >= len(comps):
            return default

        return unescape_hl7(comps[idx], self.seps) or default


def normalize_newlines(raw: str) -> str:
    # HL7 segments are carriage-return separated, but real files vary.
    raw = raw.replace("\r\n", "\r").replace("\n", "\r")
    # Remove BOM or weird leading whitespace without breaking HL7 positions
    return raw.lstrip("\ufeff")


def split_messages(raw: str) -> List[str]:
    """
    Split a file that may contain multiple HL7 messages.
    Uses 'MSH' at the start of a segment line as the boundary.
    """
    raw = normalize_newlines(raw)
    segments = [s for s in raw.split("\r") if s.strip()]

    msh_indexes = [i for i, seg in enumerate(segments) if seg.startswith("MSH")]
    if not msh_indexes:
        return []

    messages: List[str] = []
    for idx, start in enumerate(msh_indexes):
        end = msh_indexes[idx + 1] if idx + 1 < len(msh_indexes) else len(segments)
        messages.append("\r".join(segments[start:end]) + "\r")
    return messages


def parse_message(message: str) -> HL7Message:
    message = normalize_newlines(message)
    seg_lines = [s for s in message.split("\r") if s.strip()]
    if not seg_lines or not seg_lines[0].startswith("MSH"):
        raise HL7ParseError("Message does not start with MSH segment.")

    # Field separator is the 4th character in MSH line: MSH|^~\&
    if len(seg_lines[0]) < 4:
        raise HL7ParseError("MSH segment too short to contain field separator.")
    field_sep = seg_lines[0][3]

    msh_parts = seg_lines[0].split(field_sep)
    # msh_parts[0] = 'MSH', msh_parts[1] = encoding chars usually '^~\\&'
    if len(msh_parts) < 2 or not msh_parts[1]:
        enc = "^~\\&"
    else:
        enc = msh_parts[1]

    component_sep = enc[0] if len(enc) > 0 else "^"
    repetition_sep = enc[1] if len(enc) > 1 else "~"
    escape_sep = enc[2] if len(enc) > 2 else "\\"
    subcomponent_sep = enc[3] if len(enc) > 3 else "&"

    seps = Separators(
        field=field_sep,
        component=component_sep,
        repetition=repetition_sep,
        escape=escape_sep,
        subcomponent=subcomponent_sep,
    )

    segments: Dict[str, List[List[str]]] = {}

    for line in seg_lines:
        if len(line) < 3:
            continue
        name = line[:3]
        parts = line.split(field_sep)

        # Align fields with HL7 numbering conventions
        if name == "MSH":
            # Insert MSH-1 (field separator) at fields[1], keep encoding chars as fields[2]
            fields = ["MSH", field_sep] + parts[1:]
        else:
            fields = parts  # fields[1] -> SEG-1

        segments.setdefault(name, []).append(fields)

    return HL7Message(seps=seps, segments=segments)


_ESCAPE_MAP_KEYS = {
    "F": "field",
    "S": "component",
    "R": "repetition",
    "E": "escape",
    "T": "subcomponent",
}


def unescape_hl7(value: str, seps: Separators) -> str:
    r"""
    Basic HL7 unescape for \F\ \S\ \R\ \E\ \T\.
    This is intentionally small; enough for most scheduling fields.
    """
    if not value or seps.escape not in value:
        return value

    esc = re.escape(seps.escape)
    pattern = re.compile(rf"{esc}(.+?){esc}")

    def repl(m: re.Match) -> str:
        code = m.group(1)
        if code in _ESCAPE_MAP_KEYS:
            key = _ESCAPE_MAP_KEYS[code]
            return getattr(seps, key)
        return m.group(0)

    return pattern.sub(repl, value)


_TS_RE = re.compile(
    r"""
    ^
    (?P<yyyy>\d{4})
    (?P<mm>\d{2})?
    (?P<dd>\d{2})?
    (?P<hh>\d{2})?
    (?P<mi>\d{2})?
    (?P<ss>\d{2})?
    (?P<fraction>\.\d+)?     # .S...
    (?P<tz>[+-]\d{4})?       # +0600
    $
    """,
    re.VERBOSE,
)


def parse_hl7_date(value: str) -> Optional[date]:
    if not value:
        return None
    m = _TS_RE.match(value)
    if not m:
        return None
    yyyy = int(m.group("yyyy"))
    mm = int(m.group("mm") or "01")
    dd = int(m.group("dd") or "01")
    return date(yyyy, mm, dd)


def parse_hl7_ts_to_datetime(value: str) -> Optional[datetime]:
    """
    Parse HL7 TS -> timezone-aware datetime.
    If tz missing, assume UTC. (Document this assumption in README.)
    """
    if not value:
        return None
    m = _TS_RE.match(value)
    if not m:
        return None

    yyyy = int(m.group("yyyy"))
    mm = int(m.group("mm") or "01")
    dd = int(m.group("dd") or "01")
    hh = int(m.group("hh") or "00")
    mi = int(m.group("mi") or "00")
    ss = int(m.group("ss") or "00")

    micro = 0
    frac = m.group("fraction")
    if frac:
        frac_digits = frac[1:]
        frac_digits = (frac_digits + "000000")[:6]
        micro = int(frac_digits)

    tz = m.group("tz")
    if tz:
        sign = 1 if tz[0] == "+" else -1
        hours = int(tz[1:3])
        mins = int(tz[3:5])
        tzinfo = timezone(sign * timedelta(hours=hours, minutes=mins))
    else:
        tzinfo = timezone.utc

    return datetime(yyyy, mm, dd, hh, mi, ss, microsecond=micro, tzinfo=tzinfo)


def to_iso8601_z(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
