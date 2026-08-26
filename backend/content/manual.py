import csv
import io

from content.schema import DialogueTurn, LessonItem

EXPECTED_HEADER = ["hanzi", "pinyin", "meaning_vi"]
DIALOGUE_EXPECTED_HEADER = ["speaker", "hanzi", "pinyin", "meaning_vi"]


class ManualParseError(Exception):
    def __init__(self, line_number: int, message: str):
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")


def _looks_like_header(row: list[str]) -> bool:
    normalized = [cell.strip().lower() for cell in row]
    return normalized[: len(EXPECTED_HEADER)] == EXPECTED_HEADER


def parse_manual_input(csv_text: str) -> tuple[list[LessonItem], list[ManualParseError]]:
    raw_rows = list(csv.reader(io.StringIO(csv_text.strip())))

    # The UI label only describes the column order ("hanzi,pinyin,meaning_vi");
    # it doesn't tell users a literal header line is required. Auto-detect one
    # instead of silently discarding a user's first data row as a header.
    if raw_rows and _looks_like_header(raw_rows[0]):
        data_rows = raw_rows[1:]
        start_line = 2
    else:
        data_rows = raw_rows
        start_line = 1

    items: list[LessonItem] = []
    errors: list[ManualParseError] = []
    for offset, row in enumerate(data_rows):
        line_number = start_line + offset
        row_dict = dict(zip(EXPECTED_HEADER, row))
        hanzi = (row_dict.get("hanzi") or "").strip()
        meaning_vi = (row_dict.get("meaning_vi") or "").strip()
        pinyin_value = (row_dict.get("pinyin") or "").strip() or None
        if not hanzi:
            errors.append(ManualParseError(line_number, "missing hanzi"))
            continue
        if not meaning_vi:
            errors.append(ManualParseError(line_number, "missing meaning_vi"))
            continue
        items.append(LessonItem(hanzi=hanzi, pinyin=pinyin_value, meaning_vi=meaning_vi))
    return items, errors


def _looks_like_dialogue_header(row: list[str]) -> bool:
    normalized = [cell.strip().lower() for cell in row]
    return normalized[: len(DIALOGUE_EXPECTED_HEADER)] == DIALOGUE_EXPECTED_HEADER


def parse_dialogue_csv_input(
    csv_text: str,
) -> tuple[list[DialogueTurn], list[ManualParseError]]:
    raw_rows = list(csv.reader(io.StringIO(csv_text.strip())))

    if raw_rows and _looks_like_dialogue_header(raw_rows[0]):
        data_rows = raw_rows[1:]
        start_line = 2
    else:
        data_rows = raw_rows
        start_line = 1

    turns: list[DialogueTurn] = []
    errors: list[ManualParseError] = []
    for offset, row in enumerate(data_rows):
        line_number = start_line + offset
        row_dict = dict(zip(DIALOGUE_EXPECTED_HEADER, row))
        speaker = (row_dict.get("speaker") or "").strip()
        hanzi = (row_dict.get("hanzi") or "").strip()
        meaning_vi = (row_dict.get("meaning_vi") or "").strip()
        pinyin_value = (row_dict.get("pinyin") or "").strip() or None
        if not speaker:
            errors.append(ManualParseError(line_number, "missing speaker"))
            continue
        if not hanzi:
            errors.append(ManualParseError(line_number, "missing hanzi"))
            continue
        if not meaning_vi:
            errors.append(ManualParseError(line_number, "missing meaning_vi"))
            continue
        turns.append(
            DialogueTurn(
                speaker_name=speaker,
                line=LessonItem(hanzi=hanzi, pinyin=pinyin_value, meaning_vi=meaning_vi),
            )
        )
    return turns, errors
