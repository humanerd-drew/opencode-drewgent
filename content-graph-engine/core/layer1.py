"""Layer 1: TF-IDF content similarity."""
from __future__ import annotations
import math
from typing import Optional
from core.models import Post, LinkSuggestion

MECAB_AVAILABLE = False
try:
    import MeCab
    import os as _os
    _rc = _os.path.expanduser("~/.config/mecab/mecabrc")
    if _os.path.exists(_rc):
        _os.environ.setdefault("MECABRC", _rc)
    MECAB_AVAILABLE = True
except ImportError:
    pass

_tagger = None


def _get_tagger():
    global _tagger
    if MECAB_AVAILABLE and _tagger is None:
        try:
            _tagger = MeCab.Tagger()
        except Exception:
            pass
    return _tagger


def tokenize(text: str) -> list[str]:
    tagger = _get_tagger()
    if tagger:
        import MeCab
        node = tagger.parseToNode(text)
        tokens = []
        while node:
            if node.surface and node.surface.strip() and len(node.surface) > 1:
                pos = node.feature.split(",")[0]
                if pos not in ("JOSA", "EOMI", "PU", "JKS", "JKO", "JKB", "JX", "JC",
                               "EP", "EF", "EC", "ETN", "ETM", "XSV", "XSA", "XSN"):
                    tokens.append(node.surface)
            node = node.next
        return tokens
    simple = []
    for t in text.lower().split():
        t = "".join(c for c in t if c.isalnum() or c in "-_")
        if len(t) > 1:
            simple.append(t)
    return simple


def compute_tfidf(posts: list[Post],
                  max_features: int = 5000) -> tuple[list[list[float]], list[str]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = []
    for p in posts:
        text = f"{p.title} {p.excerpt} {p.content}"
        text = " ".join(tokenize(text))
        docs.append(text)

    if len(docs) < 2:
        n = len(posts)
        return [[0.0] * n for _ in range(n)], []

    vec = TfidfVectorizer(max_features=max_features, max_df=0.85, min_df=1)
    tfidf = vec.fit_transform(docs)
    sim = cosine_similarity(tfidf)
    return sim.tolist(), vec.get_feature_names_out().tolist()


def suggest(posts: list[Post], similarity_matrix: list[list[float]],
            feature_names: list[str], top_n: int = 5,
            threshold: float = 0.15) -> list[LinkSuggestion]:
    n = len(posts)
    if n == 0:
        return []

    suggestions = []
    for i, source in enumerate(posts):
        scores = [(j, similarity_matrix[i][j]) for j in range(n)
                  if j != i and similarity_matrix[i][j] >= threshold]
        scores.sort(key=lambda x: -x[1])
        for j, score in scores[:top_n]:
            target = posts[j]
            suggestions.append(LinkSuggestion(
                source_id=source.id,
                target_id=target.id,
                source_title=source.title,
                target_title=target.title,
                score=round(score, 4),
                source_layer="layer1",
            ))

    return suggestions
