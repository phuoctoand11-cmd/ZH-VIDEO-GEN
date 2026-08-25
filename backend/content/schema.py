from pydantic import BaseModel, field_validator


class LessonItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str

    @field_validator("hanzi")
    @classmethod
    def hanzi_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hanzi must not be empty")
        return v.strip()

    @field_validator("meaning_vi")
    @classmethod
    def meaning_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("meaning_vi must not be empty")
        return v.strip()


class VocabCardItem(BaseModel):
    hanzi: str
    pinyin: str | None = None
    meaning_vi: str
    icon_prompt: str

    @field_validator("hanzi")
    @classmethod
    def hanzi_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hanzi must not be empty")
        return v.strip()

    @field_validator("meaning_vi")
    @classmethod
    def meaning_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("meaning_vi must not be empty")
        return v.strip()


class VocabTopicResult(BaseModel):
    radical: str | None = None
    radical_pinyin: str | None = None
    radical_meaning_vi: str | None = None
    items: list[VocabCardItem]


class DialogueTurn(BaseModel):
    speaker_name: str
    line: LessonItem


class DialogueResult(BaseModel):
    title: str
    turns: list[DialogueTurn]
