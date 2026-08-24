import json
from pathlib import Path

from pydantic import BaseModel


class TemplateSegment(BaseModel):
    lang: str
    field: str


class AudioTemplate(BaseModel):
    name: str
    segments: list[TemplateSegment]


def load_template(path: str | Path) -> AudioTemplate:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AudioTemplate(**data)


def list_templates(templates_dir: str | Path) -> list[AudioTemplate]:
    dir_path = Path(templates_dir)
    return [load_template(p) for p in sorted(dir_path.glob("*.json"))]
