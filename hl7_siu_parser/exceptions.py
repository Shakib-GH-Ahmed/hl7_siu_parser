class HL7Error(Exception):
    """Base error for HL7 parsing."""


class HL7ParseError(HL7Error):
    """Malformed HL7 wire format."""


class UnsupportedMessageType(HL7Error):
    """Message is not SIU^S12 (or is otherwise unsupported)."""


class MissingSegment(HL7Error):
    """Required segment missing for this parser."""