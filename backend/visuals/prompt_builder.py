import hashlib

_AVATAR_VARIANTS = [
    "with short black hair and a blue shirt",
    "with curly brown hair and a yellow sweater",
    "with a ponytail and a green jacket",
    "with glasses and a red hoodie",
    "with a bob haircut and an orange scarf",
    "with spiky hair and a purple t-shirt",
]


def build_scene_prompt(icon_prompt: str) -> str:
    return (
        f"A colorful children's-book illustration that clearly and literally depicts: "
        f"{icon_prompt}. The scene must unambiguously show this exact action, object, "
        f"or person so a viewer instantly recognizes what it is — accuracy to the "
        f"description matters more than decoration. Cute semi-realistic cartoon "
        f"characters, soft shading, warm friendly color palette, simple uncluttered "
        f"background, landscape orientation, no text, no letters, no numbers, no "
        f"watermark."
    )


def build_avatar_prompt(speaker_name: str) -> str:
    # speaker_name is intentionally never spliced into the prompt as a literal
    # proper noun: quoted proper nouns are a known trigger for diffusion
    # models to render the string as visible text, which fights the "no
    # text" instruction below. The name is already drawn as real text
    # separately by render/dialogue_card.py, so the AI avatar doesn't need
    # it. Instead, the name is hashed to deterministically pick a short
    # visual-variant descriptor phrase, so different speakers still get
    # different prompts (and therefore different cached avatar images via
    # visuals/image.py's sha256(prompt) cache) without ever naming them.
    variant_index = int(hashlib.sha256(speaker_name.encode()).hexdigest(), 16) % len(
        _AVATAR_VARIANTS
    )
    variant = _AVATAR_VARIANTS[variant_index]
    return (
        f"A cute chibi avatar portrait of a friendly cartoon character {variant}. "
        f"Flat vector style, bright pastel colors, thick outline, centered on a plain "
        f"white background, no text, no letters, no watermark, kawaii mascot style, "
        f"head and shoulders only."
    )
