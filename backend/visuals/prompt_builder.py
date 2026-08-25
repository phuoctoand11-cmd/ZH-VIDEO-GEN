def build_mascot_prompt(icon_prompt: str) -> str:
    return (
        f"A cute chibi sticker illustration of {icon_prompt}. Flat vector style, "
        f"bright pastel colors, thick outline, centered on a plain white background, "
        f"no text, no letters, no watermark, kawaii mascot style."
    )


def build_avatar_prompt(speaker_name: str) -> str:
    # speaker_name is intentionally unused in the prompt text: quoted proper
    # nouns are a known trigger for diffusion models to render the string as
    # visible text, which fights the "no text" instruction below. The name
    # is already drawn as real text separately by render/dialogue_card.py,
    # so the AI avatar doesn't need it. Kept as a parameter for call-site
    # API compatibility.
    del speaker_name
    return (
        "A cute chibi avatar portrait of a friendly cartoon character. Flat vector "
        "style, bright pastel colors, thick outline, centered on a plain white "
        "background, no text, no letters, no watermark, kawaii mascot style, head "
        "and shoulders only."
    )
