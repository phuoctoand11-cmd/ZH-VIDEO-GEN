from content.manual import parse_dialogue_csv_input, parse_manual_input


def test_parse_manual_input_valid_rows():
    csv_text = "hanzi,pinyin,meaning_vi\n吃,chī,ăn\n喝,,uống\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 2
    assert errors == []
    assert items[0].hanzi == "吃"
    assert items[0].pinyin == "chī"
    assert items[1].pinyin is None


def test_parse_manual_input_skips_missing_hanzi():
    csv_text = "hanzi,pinyin,meaning_vi\n,chī,ăn\n喝,,uống\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 1
    assert len(errors) == 1
    assert errors[0].line_number == 2
    assert "hanzi" in errors[0].message


def test_parse_manual_input_skips_missing_meaning():
    csv_text = "hanzi,pinyin,meaning_vi\n吃,chī,\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 0
    assert len(errors) == 1
    assert "meaning_vi" in errors[0].message


def test_parse_manual_input_without_header_row():
    # Users often paste data rows straight away, without prefixing the
    # literal "hanzi,pinyin,meaning_vi" header line described in the label.
    csv_text = "你好,nǐ hǎo,xin chào\n谢谢,xiè xie,cảm ơn\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 2
    assert errors == []
    assert items[0].hanzi == "你好"
    assert items[0].pinyin == "nǐ hǎo"
    assert items[0].meaning_vi == "xin chào"
    assert items[1].hanzi == "谢谢"


def test_parse_manual_input_without_header_row_reports_correct_line_numbers():
    csv_text = ",chī,ăn\n喝,,uống\n"
    items, errors = parse_manual_input(csv_text)
    assert len(items) == 1
    assert len(errors) == 1
    assert errors[0].line_number == 1
    assert "hanzi" in errors[0].message


def test_parse_dialogue_csv_input_valid_rows():
    csv_text = "speaker,hanzi,pinyin,meaning_vi\nMinh,你好,nǐ hǎo,xin chào\nLan,你好吗,,khỏe không\n"
    turns, errors = parse_dialogue_csv_input(csv_text)
    assert len(turns) == 2
    assert errors == []
    assert turns[0].speaker_name == "Minh"
    assert turns[0].line.hanzi == "你好"
    assert turns[0].line.pinyin == "nǐ hǎo"
    assert turns[1].line.pinyin is None


def test_parse_dialogue_csv_input_without_header_row():
    csv_text = "Minh,你好,nǐ hǎo,xin chào\n"
    turns, errors = parse_dialogue_csv_input(csv_text)
    assert len(turns) == 1
    assert errors == []
    assert turns[0].speaker_name == "Minh"


def test_parse_dialogue_csv_input_skips_missing_speaker():
    csv_text = "speaker,hanzi,pinyin,meaning_vi\n,你好,nǐ hǎo,xin chào\nLan,你好吗,,khỏe không\n"
    turns, errors = parse_dialogue_csv_input(csv_text)
    assert len(turns) == 1
    assert len(errors) == 1
    assert "speaker" in errors[0].message


def test_parse_dialogue_csv_input_skips_missing_hanzi_and_meaning():
    csv_text = "speaker,hanzi,pinyin,meaning_vi\nMinh,,nǐ hǎo,xin chào\nLan,你好吗,,\n"
    turns, errors = parse_dialogue_csv_input(csv_text)
    assert len(turns) == 0
    assert len(errors) == 2
    assert "hanzi" in errors[0].message
    assert "meaning_vi" in errors[1].message
