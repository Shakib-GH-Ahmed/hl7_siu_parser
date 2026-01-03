import unittest

from hl7_siu_parser.hl7 import split_messages, parse_message, parse_hl7_ts_to_datetime, to_iso8601_z
from hl7_siu_parser.siu_s12 import parse_siu_s12_appointment
from hl7_siu_parser.exceptions import UnsupportedMessageType, MissingSegment


VALID_SIU = (
    "MSH|^~\\&|SEND|FAC|RECV|FAC|20250101120000+0600||SIU^S12|MSG0001|P|2.3\r"
    "SCH|123456|FILL123||||||^General Consultation|||^^^20250502130000+0600\r"
    "PID|1||P12345^^^HOSP^MR||Doe^John||19850210|M\r"
    "PV1|1|O|ClinicA^203^^MainFacility|||D67890^Smith^Jane^^^Dr\r"
)

WRONG_TYPE = (
    "MSH|^~\\&|SEND|FAC|RECV|FAC|20250101120000+0600||ADT^A01|MSG0002|P|2.3\r"
)

MISSING_SCH = (
    "MSH|^~\\&|SEND|FAC|RECV|FAC|20250101120000+0600||SIU^S12|MSG0003|P|2.3\r"
    "PID|1||P12345^^^HOSP^MR||Doe^John||19850210|M\r"
)


class TestSIUS12(unittest.TestCase):
    def test_split_multiple_messages(self):
        raw = VALID_SIU + "\r" + WRONG_TYPE
        msgs = split_messages(raw)
        self.assertEqual(len(msgs), 2)

    def test_parse_valid_siu(self):
        msg = parse_message(VALID_SIU)
        appt = parse_siu_s12_appointment(msg)
        self.assertEqual(appt["appointment_id"], "123456")
        self.assertEqual(appt["patient"]["id"], "P12345")
        self.assertEqual(appt["patient"]["first_name"], "John")
        self.assertEqual(appt["patient"]["last_name"], "Doe")
        self.assertEqual(appt["patient"]["dob"], "1985-02-10")
        self.assertEqual(appt["patient"]["gender"], "M")
        self.assertEqual(appt["provider"]["id"], "D67890")
        # Location is best-effort from PV1-3
        self.assertIn("MainFacility", appt["location"])

    def test_reject_wrong_message_type(self):
        msg = parse_message(WRONG_TYPE)
        with self.assertRaises(UnsupportedMessageType):
            parse_siu_s12_appointment(msg)

    def test_missing_sch_segment(self):
        msg = parse_message(MISSING_SCH)
        with self.assertRaises(MissingSegment):
            parse_siu_s12_appointment(msg)

    def test_timestamp_normalization(self):
        dt = parse_hl7_ts_to_datetime("20250502130000+0600")
        self.assertIsNotNone(dt)
        self.assertEqual(to_iso8601_z(dt), "2025-05-02T07:00:00Z")  # 13:00 at +06:00 is 07:00Z


if __name__ == "__main__":
    unittest.main()
