import json
from audio.templates import load_template, list_templates


def test_load_template(tmp_path):
    template_path = tmp_path / "test.json"
    template_path.write_text(json.dumps({
        "name": "zh-zh-vi",
        "segments": [
            {"lang": "zh", "field": "hanzi"},
            {"lang": "vi", "field": "meaning_vi"},
        ],
    }), encoding="utf-8")
    template = load_template(template_path)
    assert template.name == "zh-zh-vi"
    assert len(template.segments) == 2
    assert template.segments[0].lang == "zh"


def test_list_templates(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "name": "a", "segments": [{"lang": "zh", "field": "hanzi"}]
    }), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({
        "name": "b", "segments": [{"lang": "vi", "field": "meaning_vi"}]
    }), encoding="utf-8")
    templates = list_templates(tmp_path)
    assert [t.name for t in templates] == ["a", "b"]
