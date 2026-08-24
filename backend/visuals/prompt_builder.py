from content.schema import LessonItem


def build_image_prompt(item: LessonItem) -> str:
    return (
        f"A simple, clear illustration representing the Chinese word '{item.hanzi}' "
        f"which means '{item.meaning_vi}' in Vietnamese. Flat vector style, "
        f"bright colors, no text, no watermark, educational flashcard style."
    )
