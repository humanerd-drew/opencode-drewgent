#!/usr/bin/env python3
"""
SEO Ontology Builder — LLM-based incremental update.
Scans article corpus, diffs against existing ontology, calls LLM for delta.
"""
import os, re, json, subprocess, sys, shutil
from datetime import datetime
from pathlib import Path
import yaml

DREW_HOME = Path(os.environ.get("DREW_HOME", os.path.expanduser("~/.drewgent")))
ONT_DIR = DREW_HOME / "P2-hippocampus" / "knowledge" / "seo-articles" / "ontology"
SEO_DIR = DREW_HOME / "P2-hippocampus" / "knowledge" / "seo-articles"
STATE_FILE = ONT_DIR / ".builder_state.json"
MAX_NEW_SUBJECTS = 5
MAX_NEW_CONCEPTS = 8

# Reference GEO (Generative Engine Optimization) concepts to prioritize in ontology deltas.
GEO_CONCEPTS = [
    "citability scoring",
    "AI crawler analysis",
    "brand authority",
    "platform-specific optimization",
    "schema markup for AI",
]

def load_yaml(path):
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}

def dump_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_article_count": 0, "last_run": None, "version": 0}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def scan_corpus():
    sources = {}
    topics = set()
    total = 0
    for year_dir in sorted(SEO_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for f in year_dir.iterdir():
            if not f.name.endswith(".md"):
                continue
            total += 1
            text = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^source_domain:\s*(.+)$", text, re.MULTILINE)
            if m:
                domain = m.group(1).strip()
                sources[domain] = sources.get(domain, 0) + 1
            tm = re.findall(r"^tags:\s*\[(.+?)\]", text, re.MULTILINE)
            for t in tm:
                for tag in t.split(","):
                    tag = tag.strip().strip("'\"").strip()
                    if tag and tag not in ("seo", "www.semrush.com"):
                        topics.add(tag)
    return total, sources, topics

def known_subjects(ontology):
    return {n["id"] for n in ontology.get("nodes", []) if n.get("type") == "subject"}

def known_resources(ontology):
    return {n["id"] for n in ontology.get("nodes", []) if n.get("type") == "resource"}

def known_concepts(ontology):
    return {n["id"] for n in ontology.get("nodes", []) if n.get("type") == "concept"}

def domain_to_subject_id(domain):
    base = domain.replace("www.", "").split(".")[0]
    safe = re.sub(r"[^a-z0-9-]", "", base.lower())[:20]
    return f"subj-{safe}" if safe else None

def resource_id_from_domain(domain):
    safe = re.sub(r"[^a-z0-9]", "_", domain.lower())
    return f"res-auto-{safe}"

def build_delta_prompt(ontology, total, sources, topics, known_subj_ids):
    existing_node_ids = {n["id"] for n in ontology.get("nodes", [])}
    existing_source_domains = set()
    for n in ontology.get("nodes", []):
        props = n.get("properties", {})
        if props.get("site"):
            existing_source_domains.add(props["site"].rstrip("/"))

    new_sources = {d: c for d, c in sorted(sources.items(), key=lambda x: -x[1])
                   if d not in existing_source_domains and domain_to_subject_id(d) not in existing_node_ids}
    new_topics = topics - {n["name"].lower() for n in ontology.get("nodes", []) if n.get("type") == "concept"}
    new_topics = {t for t in new_topics if len(t) > 2}
    new_topics = sorted(new_topics)[:MAX_NEW_CONCEPTS * 2]

    existing_summary = "\n".join(
        f"  - {n['id']}: {n.get('name', '?')} ({n.get('type', '?')})"
        for n in ontology.get("nodes", [])[:50]
    )

    return f"""You are an SEO ontology curator. Given the existing ontology and new corpus data, suggest minimal additions.

EXISTING ONTOLOGY:
- Total nodes: {len(ontology.get('nodes', []))}
- Subjects: {len([n for n in ontology.get('nodes', []) if n.get('type') == 'subject'])}
- Resources: {len([n for n in ontology.get('nodes', []) if n.get('type') == 'resource'])}
- Concepts: {len([n for n in ontology.get('nodes', []) if n.get('type') == 'concept'])}
- Edges: {len(ontology.get('edges', []))}

CURRENT CORPUS:
- Total articles: {total}
- Active sources (domain → count): {json.dumps(new_sources, indent=2)}
- Emerging topics not in ontology: {json.dumps(new_topics, indent=2)}
- GEO concepts to prioritize: {json.dumps(GEO_CONCEPTS, indent=2)}

Respond with ONLY valid JSON (no markdown):
{{
  "add_nodes": [
    {{
      "id": "subj-<slug>",
      "name": "<display name>",
      "type": "subject",
      "properties": {{"type": "SEO_publication", "site": "<domain>", "description": "<40 chars>"}}
    }}
  ],
  "add_edges": [
    {{"from": "<subject id>", "relation": "publishes", "to": "<resource id>", "properties": {{"date": "YYYY-MM-DD"}}}}
  ],
  "new_resource_topics": [["<resource id>", "<concept id>"], ...],
  "summary": "1 sentence describing what changed"
}}

Rules:
- IDs: subj-<shortname>, con-<kebab-topic>, res-auto-<domain>
- Only suggest nodes for NEW sources with ≥3 articles
- Only suggest NEW concepts from emerging topics list if clearly SEO-relevant
- Reference GEO concepts when evaluating emerging topics (especially "citability scoring"); add them as `con-<kebab-topic>` nodes when the corpus supports them
- Each new subject needs exactly 1 edge (publishes → resource)
- Each new resource needs 1 edge (is_about → concept)
- Do NOT suggest changes to existing nodes/edges
- Keep additions minimal: max {MAX_NEW_SUBJECTS} new subjects, {MAX_NEW_CONCEPTS} new concepts
- If nothing new: {{"add_nodes": [], "add_edges": [], "new_resource_topics": [], "summary": "no changes needed"}}'""

def call_llm(prompt):
    result = subprocess.run(
        ["opencode", "run", "--model", "opencode-go/deepseek-v4-flash", prompt],
        capture_output=True, text=True, timeout=180,
    )
    stdout = result.stdout.strip()
    json_match = re.search(r"```(?:json)?\s*\n?(\{.*?\n?\})\s*```", stdout, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    brace_start = stdout.find("{")
    brace_end = stdout.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return json.loads(stdout[brace_start:brace_end + 1])
    raise ValueError(f"No JSON in LLM output:\n{stdout[:500]}")

def apply_delta(ontology, delta):
    existing_ids = {n["id"] for n in ontology["nodes"]}
    for n in delta.get("add_nodes", []):
        if n["id"] not in existing_ids:
            ontology["nodes"].append(n)
            existing_ids.add(n["id"])
    existing_edge_keys = {(e["from"], e["relation"], e["to"]) for e in ontology["edges"]}
    for e in delta.get("add_edges", []):
        key = (e["from"], e["relation"], e["to"])
        if key not in existing_edge_keys:
            ontology["edges"].append(e)
            existing_edge_keys.add(key)
    return ontology

def main():
    dry_run = "--dry-run" in sys.argv

    state = load_state()
    ontology = {
        "nodes": load_yaml(ONT_DIR / "nodes.yaml").get("nodes", []),
        "edges": load_yaml(ONT_DIR / "edges.yaml").get("edges", []),
    }
    if not ontology["nodes"]:
        print("[seo-ontology-builder] ERROR: No existing ontology found")
        sys.exit(1)

    total, sources, topics = scan_corpus()
    if total == state.get("last_article_count", 0):
        print(f"[seo-ontology-builder] No new articles since last run ({total}). Skipping.")
        return

    known_subj_ids = known_subjects(ontology)
    known_concept_ids = known_concepts(ontology)

    prompt = build_delta_prompt(ontology, total, sources, topics, known_subj_ids)
    print(f"[seo-ontology-builder] Scanning corpus: {total} articles, {len(sources)} sources, {len(topics)} topics")
    print(f"[seo-ontology-builder] Current ontology: {len(ontology['nodes'])} nodes, {len(ontology['edges'])} edges")
    print("[seo-ontology-builder] Calling LLM for ontology delta...")

    delta = call_llm(prompt)
    print(f"[seo-ontology-builder] LLM response: {delta.get('summary', '')}")
    print(f"[seo-ontology-builder]   +{len(delta.get('add_nodes', []))} nodes, +{len(delta.get('add_edges', []))} edges")

    if not delta.get("add_nodes") and not delta.get("add_edges"):
        print("[seo-ontology-builder] No changes needed.")
        update_pack(ontology, total, state)
        save_state({**state, "last_article_count": total, "last_run": datetime.now().isoformat()})
        return

    if dry_run:
        print("[seo-ontology-builder] DRY RUN — would apply:")
        print(json.dumps(delta, indent=2, ensure_ascii=False))
        return

    ontology = apply_delta(ontology, delta)

    nodes_data = {"nodes": ontology["nodes"]}
    edges_data = {"edges": ontology["edges"]}

    with open(ONT_DIR / "nodes.yaml", "w") as f:
        f.write(f"# SEO Knowledge Ontology — Nodes\n# Generated: {datetime.now().strftime('%Y-%m-%d')}\n# Source corpus: {total} articles\n# auto-updated by seo_ontology_builder.py\n\n")
        yaml.dump(nodes_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    with open(ONT_DIR / "edges.yaml", "w") as f:
        f.write(f"# SEO Knowledge Ontology — Edges\n# Generated: {datetime.now().strftime('%Y-%m-%d')}\n# Source corpus: {total} articles\n# auto-updated by seo_ontology_builder.py\n\n")
        yaml.dump(edges_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    update_pack(ontology, total, state)
    save_state({**state, "last_article_count": total, "last_run": datetime.now().isoformat(), "version": state.get("version", 0) + 1})
    print(f"[seo-ontology-builder] Done. Ontology: {len(ontology['nodes'])} nodes, {len(ontology['edges'])} edges")

def update_pack(ontology, total, state):
    raw = load_yaml(ONT_DIR / "pack.yaml")
    inner = raw.get("pack", raw)
    new_ver = f"0.{state.get('version', 0) + 1}.0"
    inner["version"] = new_ver
    inner["updated"] = datetime.now().strftime("%Y-%m-%d")
    inner["counts"] = {"nodes": len(ontology["nodes"]), "edges": len(ontology["edges"])}
    desc = (inner.get("description", "") or "").split("Auto-updated")[0].split("Rules are derived")[0].strip()
    inner["description"] = desc + f"\n  Auto-updated: {datetime.now().strftime('%Y-%m-%d')}. Corpus: {total} articles."
    cleaned = {"pack": inner}
    dump_yaml(ONT_DIR / "pack.yaml", cleaned)

if __name__ == "__main__":
    main()
