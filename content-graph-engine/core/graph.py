"""Content Graph orchestrator: build similarity graph, suggest + verify links."""
from __future__ import annotations
import json, os, re, time
from core.models import Post, LinkSuggestion, GraphState, now
from core.wp_client import get_categories, get_tags, get_posts, strip_html
from core import layer0, layer1, gate

BASE = os.path.expanduser("~/.drewgent/P4-cortex/content")
GRAPH_FILE = os.path.join(BASE, "content-graph.json")


def load_graph() -> GraphState:
    try:
        data = json.load(open(GRAPH_FILE))
        return GraphState(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        return GraphState()


def save_graph(state: GraphState):
    os.makedirs(BASE, exist_ok=True)
    json.dump(state.to_dict(), open(GRAPH_FILE, "w"), indent=2, ensure_ascii=False)


def build(limit: int = 100, threshold: float = 0.08,
          top_n: int = 5, max_features: int = 5000) -> GraphState:
    print("[graph] fetching categories & tags...")
    cats = get_categories()
    tags = get_tags()

    print(f"[graph] fetching posts (limit={limit})...")
    pub = get_posts(status="publish", limit=limit)
    draft = get_posts(status="draft", limit=limit)
    raw_posts = pub + draft
    print(f"[graph]   got {len(pub)} published + {len(draft)} drafts = {len(raw_posts)} total")

    if not raw_posts:
        print("[graph] no posts at all")
        return GraphState()

    post_map = {p.id: p for p in raw_posts}

    state = GraphState()
    state.generated_at = now()

    for p in post_map.values():
        state.posts[p.id] = {
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "status": p.status,
            "categories": [cats.get(c, str(c)) for c in p.categories],
            "tags": [tags.get(t, str(t)) for t in p.tags],
        }

    print("[graph] layer0: taxonomy similarity (all posts)...")
    l0 = layer0.suggest(raw_posts, cats, tags, max_per_post=top_n)
    print(f"[graph]   layer0: {len(l0)} candidates")

    print("[graph] layer1: TF-IDF similarity (all posts)...")
    matrix, features = layer1.compute_tfidf(raw_posts, max_features=max_features)
    state.matrix = matrix
    l1 = layer1.suggest(raw_posts, matrix, features, top_n=top_n, threshold=threshold)
    print(f"[graph]   layer1: {len(l1)} candidates")

    merged = _merge(l0, l1, top_n=top_n)
    print(f"[graph] merged: {len(merged)} deduplicated candidates")

    print("[graph] verification gate (target must be published)...")
    existing = _existing_links(list(post_map.values()))
    verified = gate.verify_batch(merged, post_map, existing)
    passed = [s for s in verified if s.verified]
    print(f"[graph]   {len(passed)} passed, {len(verified) - len(passed)} failed")

    state.suggested = [
        {"source_id": s.source_id, "target_id": s.target_id,
         "source_title": s.source_title, "target_title": s.target_title,
         "anchor_text": s.anchor_text, "score": s.score,
         "source_layer": s.source_layer}
        for s in passed
    ]

    save_graph(state)

    print(f"[graph] saved to {GRAPH_FILE}")
    pub_count = sum(1 for p in post_map.values() if p.status == "publish")
    print(f"[graph] {pub_count} published, {len(passed)} verified suggestions")
    if passed:
        print(f"[graph] top suggestions by score:")
    for s in sorted(passed, key=lambda x: -x.score)[:10]:
        print(f"  {s.source_id} → {s.target_id}  score={s.score:.3f}  "
              f"layer={s.source_layer}  anchor='{s.anchor_text[:50]}'")

    return state


def _merge(l0: list[LinkSuggestion], l1: list[LinkSuggestion],
           top_n: int = 5) -> list[LinkSuggestion]:
    seen: set[tuple[int, int]] = set()
    result = []
    key = lambda x: (x.source_id, x.target_id)

    # layer1 first (semantic), then layer0 (taxonomy) to fill gaps
    for s in sorted(l1 + l0, key=lambda x: -x.score):
        k = key(s)
        if k in seen:
            continue
        seen.add(k)
        result.append(s)

    # per-source cap
    per_source: dict[int, int] = {}
    final = []
    for s in result:
        per_source[s.source_id] = per_source.get(s.source_id, 0) + 1
        if per_source[s.source_id] <= top_n:
            final.append(s)

    return final


def _existing_links(posts: list[Post]) -> set[tuple[int, int]]:
    links = set()
    for post in posts:
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', post.content)
        for href in hrefs:
            for p in posts:
                if p.permalink in href or p.slug in href:
                    a, b = min(post.id, p.id), max(post.id, p.id)
                    links.add((a, b))
    return links


def apply_suggestion(sug: dict | LinkSuggestion) -> bool:
    if isinstance(sug, dict):
        sug = LinkSuggestion(**{k: v for k, v in sug.items() if k in LinkSuggestion.__dataclass_fields__})
    from core.wp_client import update_post, get_posts
    all_posts = get_posts(status="publish") + get_posts(status="draft")
    posts = {p.id: p for p in all_posts}
    source = posts.get(sug.source_id)
    target = posts.get(sug.target_id)
    if not source or not target:
        print(f"[apply] source({sug.source_id}) or target({sug.target_id}) not found")
        return False

    # Extract meaningful keywords from target title
    stopwords = {'—', '–', '-', '·', '의', '에', '를', '이', '가', '은', '는', '과', '와', '도',
                 'the', 'a', 'an', 'and', 'or', 'for'}
    keywords = [w.strip() for w in re.split(r'[\s—–\-·,()""''「」]+', target.title)
                if w.strip() not in stopwords and len(w.strip()) > 2]
    if not keywords:
        keywords = [target.title]

    anchor = None
    for n in [3, 2, 1]:
        for i in range(len(keywords) - n + 1):
            phrase = ' '.join(keywords[i:i+n])
            if len(phrase) < 4:
                continue
            idx = source.content.lower().find(phrase.lower())
            if idx >= 0:
                anchor = source.content[idx:idx+len(phrase)]
                break
        if anchor:
            break

    if not anchor:
        print(f"[skip] no keyword overlap")
        return False

    link_html = f' <a href="{target.permalink}">{anchor}</a> '
    new_content = source.content.replace(anchor, link_html, 1)
    print(f"[apply]")

    update_post(source.id, new_content)
    print(f"[apply] {source.title} → {target.title} ('{anchor[:40]}')")

    state = load_graph()
    state.applied.append({
        "source_id": sug.source_id,
        "target_id": sug.target_id,
        "anchor_text": anchor,
        "applied_at": now(),
    })
    save_graph(state)
    return True
