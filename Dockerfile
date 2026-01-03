FROM python:3.11-slim

WORKDIR /app

COPY hl7_siu_parser/ hl7_siu_parser/
COPY tests/ tests/
COPY readme.md README.md

CMD ["python", "-m", "hl7_siu_parser.cli", "input.hl7"]