"""Layer 0: WordPress taxonomy-based similarity."""
from __future__ import annotations
from core.models import Post, LinkSuggestion


def suggest(posts: list[Post], cat_names: dict[int, str], tag_names: dict[int, str],
            max_per_post: int = 5) -> list[LinkSuggestion]:
    suggestions = []
    cat_to_posts: dict[int, list[int]] = {}
    tag_to_posts: dict[int, list[int]] = {}

    for p in posts:
        for c in p.categories:
            cat_to_posts.setdefault(c, []).append(p.id)
        for t in p.tags:
            tag_to_posts.setdefault(t, []).append(p.id)

    for source in posts:
        scored: dict[int, float] = {}

        for c in source.categories:
            for pid in cat_to_posts.get(c, []):
                if pid == source.id:
                    continue
                scored[pid] = scored.get(pid, 0) + 1.0

        for t in source.tags:
            for pid in tag_to_posts.get(t, []):
                if pid == source.id:
                    continue
                scored[pid] = scored.get(pid, 0) + 0.6

        targets = {p.id: p for p in posts}
        ranked = sorted(scored.items(), key=lambda x: -x[1])[:max_per_post]

        for pid, score in ranked:
            target = targets.get(pid)
            if not target:
                continue
            suggestions.append(LinkSuggestion(
                source_id=source.id,
                target_id=pid,
                source_title=source.title,
                target_title=target.title,
                score=min(score, 1.0),
                source_layer="layer0",
            ))

    return suggestions
