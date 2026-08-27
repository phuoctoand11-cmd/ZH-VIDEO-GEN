from visuals.prompt_builder import build_avatar_prompt, build_scene_prompt


def test_build_scene_prompt_includes_icon_prompt_and_no_text_request():
    prompt = build_scene_prompt("a man walking into an office, waving")
    assert "a man walking into an office, waving" in prompt
    assert "no text" in prompt
    # Guards against unrelated decorative filler (plants, hearts) the model
    # was observed adding in production even when icon_prompt was followed.
    assert "no additional characters, people, animals, plants, or props" in prompt


def test_build_scene_prompt_never_mandates_a_character():
    # Regression test: this prompt used to say "chibi-style character design
    # where a person is shown", intended as conditional, but production
    # testing showed the model read it as an unconditional instruction —
    # every scene got the same anime girl inserted, even "con gà" (chicken),
    # which has no person in it at all. Style wording must describe
    # rendering technique only, never mandate a character existing.
    prompt = build_scene_prompt("a brown hen standing in a farmyard")
    assert "character design" not in prompt
    assert "where a person is shown" not in prompt


def test_build_scene_prompt_excludes_kawaii_and_repeats_subject():
    # Regression test: with the character-mandate and decorative-filler bugs
    # fixed, production testing ("con gà") showed every scene still rendered
    # as the same round-faced cat mascot regardless of icon_prompt — "kawaii"
    # is a strong stylistic anchor whose dominant training association is
    # cat-style mascots, which was outweighing the actual subject. icon_prompt
    # is now repeated to increase its weight instead.
    prompt = build_scene_prompt("a brown hen standing in a farmyard")
    assert "kawaii" not in prompt.lower()
    assert prompt.count("a brown hen standing in a farmyard") == 2


def test_build_avatar_prompt_excludes_speaker_name_and_includes_no_text_request():
    prompt = build_avatar_prompt("Minh")
    assert "Minh" not in prompt
    assert "no text" in prompt


def test_build_avatar_prompt_varies_by_speaker_name():
    prompt_a = build_avatar_prompt("Minh")
    prompt_b = build_avatar_prompt("Lan")
    assert prompt_a != prompt_b
