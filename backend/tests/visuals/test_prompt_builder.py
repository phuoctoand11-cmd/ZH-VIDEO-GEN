from visuals.prompt_builder import build_avatar_prompt, build_mascot_prompt


def test_build_mascot_prompt_includes_icon_prompt_and_no_text_request():
    prompt = build_mascot_prompt("cute ice cube character")
    assert "cute ice cube character" in prompt
    assert "no text" in prompt


def test_build_avatar_prompt_excludes_speaker_name_and_includes_no_text_request():
    prompt = build_avatar_prompt("Minh")
    assert "Minh" not in prompt
    assert "no text" in prompt


def test_build_avatar_prompt_varies_by_speaker_name():
    prompt_a = build_avatar_prompt("Minh")
    prompt_b = build_avatar_prompt("Lan")
    assert prompt_a != prompt_b
