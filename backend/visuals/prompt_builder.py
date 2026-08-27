import hashlib

_AVATAR_VARIANTS = [
    "with short black hair and a blue shirt",
    "with curly brown hair and a yellow sweater",
    "with a ponytail and a green jacket",
    "with glasses and a red hoodie",
    "with a bob haircut and an orange scarf",
    "with spiky hair and a purple t-shirt",
]


# Passed as negative_prompt alongside build_scene_prompt's output. Verified on
# production (Cloudflare phoenix-1.0) across two separate rounds: round 1
# (no "unrelated ..." entries) let the model fill scenes with generic
# decorative filler (potted plants, hearts, pumpkins); round 2 (those
# entries added, but the positive prompt still said "chibi-style character
# design") produced a random anime girl in EVERY scene regardless of topic —
# including "con gà" (chicken), which has no person in it at all — plus
# garbled embedded text despite the "no text" entries already here. This
# round adds "random person"/"unrelated character" and strengthens the text
# entries; the actual fix for the random-character problem is in the
# positive prompt below (it was instructing one into existence).
SCENE_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, deformed, extra limbs, extra fingers, "
    "text, letters, words, watermark, logo, signature, caption, jpeg artifacts, "
    "unrelated background objects, random potted plants, decorative hearts, "
    "generic scenery unrelated to the description, random person, "
    "unrelated character, signage, handwriting, gibberish text, sticker text"
)


def build_scene_prompt(icon_prompt: str) -> str:
    # History of this prompt (each change verified on production, not
    # guessed): "children's-book illustration" biased FLUX toward generic
    # kid-in-nature scenes with storybook captions. Reusing the
    # flat-vector/kawaii framing fixed that, but Cloudflare phoenix-1.0 then
    # padded scenes with unrelated decorative filler (plants, hearts) even
    # with icon_prompt first for strongest weight — fixed by the explicit
    # "nothing else in the frame" constraint below. That in turn revealed
    # the current bug: this prompt used to say "chibi-style character design
    # where a person is shown", intending it as conditional, but the model
    # read it as an instruction to always add a character — every scene got
    # the same anime girl, even for "con gà" (chicken), which has no person
    # in it. Style words now describe rendering technique only (how to draw
    # whatever the subject is), never content (what to draw).
    return (
        f"{icon_prompt}. Depict only the exact subject described above — no "
        f"additional characters, people, animals, plants, or props unless "
        f"they are explicitly part of that description. Flat-vector kawaii "
        f"illustration style, soft shading, bright warm colors, thick clean "
        f"outlines, plain simple background, landscape orientation, no text, "
        f"no letters, no words, no numbers, no captions, no watermark, no "
        f"logos, no signage."
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
