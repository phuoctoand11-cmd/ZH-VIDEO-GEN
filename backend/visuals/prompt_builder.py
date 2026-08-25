def build_mascot_prompt(icon_prompt: str) -> str:
    return (
        f"A cute chibi sticker illustration of {icon_prompt}. Flat vector style, "
        f"bright pastel colors, thick outline, centered on a plain white background, "
        f"no text, no letters, no watermark, kawaii mascot style."
    )


def build_avatar_prompt(speaker_name: str) -> str:
    return (
        f"A cute chibi avatar portrait of a friendly cartoon character named "
        f"'{speaker_name}'. Flat vector style, bright pastel colors, thick outline, "
        f"centered on a plain white background, no text, no letters, no watermark, "
        f"kawaii mascot style, head and shoulders only."
    )
