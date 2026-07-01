from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Post:
    id: int
    title: str
    content: str
    excerpt: str
    slug: str
    status: str
    categories: list[int] = field(default_factory=list)
    tags: list[int] = field(default_factory=list)
    permalink: str = ""


@dataclass
class LinkSuggestion:
    source_id: int
    target_id: int
    source_title: str = ""
    target_title: str = ""
    anchor_text: str = ""
    para_index: int = 0
    score: float = 0.0
    source_layer: str = ""
    verified: bool = False
    verification_log: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class GraphState:
    version: int = 1
    generated_at: str = ""
    posts: dict[int, dict] = field(default_factory=dict)
    matrix: list[list[float]] = field(default_factory=list)
    suggested: list[dict] = field(default_factory=list)
    applied: list[dict] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
