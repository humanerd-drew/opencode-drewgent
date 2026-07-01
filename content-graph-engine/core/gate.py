"""Verification gate: validate every link suggestion before applying."""
from __future__ import annotations
import re, html
from typing import Optional
from core.models import Post, LinkSuggestion


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _get_paragraphs(content: str) -> list[str]:
    parts = re.split(r"</?(?:p|h[1-6]|li|blockquote|div|section)(?:\s[^>]*)?>", content)
    return [re.sub(r"<[^>]+>", "", p).strip() for p in parts if len(p.strip()) > 50]


def verify_suggestion(sug: LinkSuggestion,
                      source_post: Optional[Post],
                      target_post: Optional[Post],
                      existing_links: set[tuple[int, int]],
                      max_links_per_post: int = 10,
                      min_anchor_length: int = 4) -> LinkSuggestion:
    log = []

    if target_post is None:
        sug.verified = False
        sug.verification_log = ["target post not found"]
        return sug

    if target_post.status != "publish":
        log.append(f"target not published (status={target_post.status})")

    if sug.source_id == sug.target_id:
        log.append("self-loop rejected")

    key = (min(sug.source_id, sug.target_id), max(sug.source_id, sug.target_id))
    if key in existing_links:
        log.append(f"link {sug.source_id}→{sug.target_id} already exists")

    existing_count = sum(1 for k in existing_links if k[0] == sug.source_id)
    if existing_count >= max_links_per_post:
        log.append(f"source already has {existing_count} links (max {max_links_per_post})")

    anchor = sug.anchor_text
    if anchor:
        if len(anchor) < min_anchor_length:
            log.append(f"anchor too short ({len(anchor)} < {min_anchor_length})")
        elif source_post:
            plain = _strip_tags(source_post.content)
            if anchor.lower() not in plain.lower():
                log.append(f"anchor '{anchor[:40]}' not found in source content")

    if not anchor and source_post:
        paras = _get_paragraphs(source_post.content)
        if paras:
            best = ""
            best_len = 999
            for para in paras:
                # find overlapping words with target title
                target_words = set(target_post.title.lower().split())
                for word in target_words:
                    if len(word) < 3:
                        continue
                    idx = para.lower().find(word)
                    if idx >= 0 and len(para[idx:idx+len(word)+20]) < best_len:
                        best = para[idx:idx+len(word)+40]
                        best_len = len(best)
            sug.anchor_text = best if best else target_post.title[:60]
            anchor = sug.anchor_text

    sug.verified = len(log) == 0
    sug.verification_log = log
    return sug


def verify_batch(suggestions: list[LinkSuggestion],
                 posts: dict[int, Post],
                 existing_links: set[tuple[int, int]],
                 max_links_per_post: int = 10) -> list[LinkSuggestion]:
    return [
        verify_suggestion(
            s,
            source_post=posts.get(s.source_id),
            target_post=posts.get(s.target_id),
            existing_links=existing_links,
            max_links_per_post=max_links_per_post,
        )
        for s in suggestions
    ]
