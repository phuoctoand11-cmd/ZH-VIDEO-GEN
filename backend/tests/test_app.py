from app import _load_templates


def test_load_templates_includes_expected_names():
    templates = _load_templates()
    assert "zh-zh-vi" in templates
    assert "zh-vi-zh" in templates
