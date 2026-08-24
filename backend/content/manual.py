import csv
import io

from content.schema import LessonItem


class ManualParseError(Exception):
    def __init__(self, line_number: int, message: str):
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")


def parse_manual_input(csv_text: str) -> tuple[list[LessonItem], list[ManualParseError]]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    items: list[LessonItem] = []
    errors: list[ManualParseError] = []
    for line_number, row in enumerate(reader, start=2):
        hanzi = (row.get("hanzi") or "").strip()
        meaning_vi = (row.get("meaning_vi") or "").strip()
        pinyin_value = (row.get("pinyin") or "").strip() or None
        if not hanzi:
            errors.append(ManualParseError(line_number, "missing hanzi"))
            continue
        if not meaning_vi:
            errors.append(ManualParseError(line_number, "missing meaning_vi"))
            continue
        items.append(LessonItem(hanzi=hanzi, pinyin=pinyin_value, meaning_vi=meaning_vi))
    return items, errors
