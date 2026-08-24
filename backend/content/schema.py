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
