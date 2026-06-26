# SEO Article Cross-Linking Pipeline (2026-06-14)

## Context

SEO-harvested articles in `P2-hippocampus/knowledge/seo-articles/` (2,500+ files) had a star topology: every article linked only to `index-by-topic` and `seo-article-harvester/SKILL`. No topic-based clustering, no article-to-article links.

The vault already had rich metadata: `cluster:`, `hub:`, `keyword:` fields in article frontmatter. 10 hub pages existed as `.md` files but articles referenced them as **plain text** (not wikilinks), so the graph didn't see the connections.

## Pipeline

### Phase 1: Article → Hub (974 articles)

The hub name appeared as plain text in the `links:` section of each article's frontmatter (e.g., `SEO_ai_llm_search_Hub`). Converted to proper wikilink:

```python
import os, glob, re

hub_map = {
    'ai_llm_search': 'SEO_ai_llm_search_Hub',
    'analytics_tools': 'SEO_analytics_tools_Hub',
    # ... 10 clusters total
}

for year_dir in ['2024', '2025']:
    path = f"/Users/drew/.drewgent/P2-hippocampus/knowledge/seo-articles/{year_dir}"
    for fpath in glob.glob(os.path.join(path, '*.md')):
        with open(fpath) as f:
            content = f.read()
        cluster_match = re.search(r'^cluster: (\w+)', content, re.MULTILINE)
        if not cluster_match:
            continue
        hub_name = hub_map[cluster_match.group(1)]
        if f'[[{hub_name}]]' in content:
            continue
        if hub_name in content:
            content = content.replace(f'\n- {hub_name}\n', f'\n- [[{hub_name}]]\n')
            with open(fpath, 'w') as f:
                f.write(content)
```

**Result**: 974 articles converted. Now every article links to its hub page.

### Phase 2: Hub → Hub (10 hubs, 20 links)

Hub pages had 0 cross-references to other hubs. Added related hub links based on topic affinity:

| Hub | Related hubs |
|-----|-------------|
| SEO_ai_llm_search_Hub | SEO_general_Hub, SEO_algorithm_updates_Hub |
| SEO_analytics_tools_Hub | SEO_technical_seo_Hub, SEO_onpage_seo_Hub |
| SEO_algorithm_updates_Hub | SEO_ai_llm_search_Hub, SEO_technical_seo_Hub |
| SEO_technical_seo_Hub | SEO_onpage_seo_Hub, SEO_analytics_tools_Hub |
| SEO_general_Hub | SEO_ai_llm_search_Hub, SEO_content_strategy_Hub |
| SEO_keyword_strategy_Hub | SEO_content_strategy_Hub, SEO_onpage_seo_Hub |
| SEO_local_international_Hub | SEO_offpage_seo_Hub, SEO_general_Hub |
| SEO_offpage_seo_Hub | SEO_local_international_Hub, SEO_technical_seo_Hub |
| SEO_onpage_seo_Hub | SEO_technical_seo_Hub, SEO_keyword_strategy_Hub |
| SEO_content_strategy_Hub | SEO_keyword_strategy_Hub, SEO_general_Hub |

**Result**: 10 hub pages with 2 hub-to-hub links each, forming a cross-connected hub mesh.

### Phase 3: Article ↔ Article (1,117 articles, ~3,350 links)

For each article in a cluster, randomly sampled 3 other articles from the same cluster and added wikilinks. Used a simple Python script that:

1. Groups all articles by `cluster:` field
2. For each article, finds candidates in same cluster (excluding self)
3. Picks 3 random non-duplicate targets
4. Adds to the YAML frontmatter `links:` section

```python
all_fnames = [fname for _, fname, _ in cluster_articles[cluster]]
for fpath, fname, content in articles:
    existing = set(re.findall(r'\[\[([^\]]+)\]\]', links_section))
    candidates = [fn for fn in all_fnames if fn != fname and fn not in existing]
    targets = random.sample(candidates, min(3, len(candidates)))
    # Add to links section
```

**Result**: 1,117 articles modified, ~3,350 new cross-links. Average 3 links per article.

### 2026 Articles: Source-Domain Grouping (429 articles)

The 2026 directory had articles without `cluster:` metadata but with source-domain tags (e.g., `tags: [seo, ahrefs.com]`). Applied a secondary grouping strategy:

**Technique**: Extract source domain from YAML `tags:` and group articles by the same source.

```python
tags_match = re.search(r'tags:\s*\[([^\]]+)\]', content)
tags = [t.strip() for t in tags_match.group(1).split(',')]
source = next((t for t in tags if t not in ['resource', 'seo', ''] and '.' in t), None)
```

**Sources with 10+ articles** (11 sources, ~430 articles):

| Source | Articles |
|--------|----------|
| growthmk.com | 157 |
| searchenginejournal.com | 49 |
| semrush.com | 38 |
| seopress.org | 36 |
| yoast.com | 33 |
| blog.google | 31 |
| searchengineland.com | 30 |
| letspl.me | 23 |
| masocampus.com | 12 |
| ahrefs.com | 10 |
| openschema.co.jp | 10 |

For each group, added 3 random cross-links per article within the same source group.

**Result**: 429 articles modified, 1,287 new links.

### Skills → P-Layer Rules Mapping (71 skills)

After the SEO work, all 121 identifiable SKILL.md files were linked to `[[@identity/brain/rules]]`:
- 50 already had the link
- 71 were missing it → added

This creates a universal upward link from every skill to the governing rules. The link was added to each file's `links:` section (or created if none existed).

## Key Numbers

| Metric | Before | After |
|--------|--------|-------|
| Articles with hub wikilink | 0 (plain text) | 974 |
| Hub-to-hub links | 0 | 20 |
| Article cross-links | 0 | ~3,350 |
| Articles processed | - | 1,117 |
| Clusters used | - | 10 |
