#!/usr/bin/env python3
"""Extract entities and relations from fact text.
Called by ingest_fact.py during remember().
Two modes: LLM (opencode flash) or fallback (regex).
"""
import json, re, sqlite3, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = "http://localhost:11434"

ENTITY_TYPES = {"tool", "pattern", "decision", "script", "project",
                "incident", "persona", "concept", "paper", "category", "doc",
                "fact"}
RELATION_TYPES = {"led_to", "caused", "fixed_by", "decided_in",
                  "implemented_in", "references", "contradicts",
                  "depends_on", "followed_by", "relates_to",
                  "belongs_to", "cites"}

INSTR_DIR = PROJECT / ".opencode" / "instructions"


def _build_topic_lookup():
    lookup = {}
    if not INSTR_DIR.exists():
        return lookup
    for f in sorted(INSTR_DIR.glob("*.md")):
        fname = f.name
        text = f.read_text()
        for m in re.finditer(r"^(#{2,3})\s+(.+)$", text, re.MULTILINE):
            heading = re.sub(r"[*_`\[\]]", "", m.group(2).strip())
            for phrase in re.split(r"\s*[/–—|,]\s*", heading):
                phrase = phrase.strip().lower()
                if len(phrase) > 2:
                    lookup[phrase] = fname
        title_m = re.match(r"^#\s+(.+)$", text.strip(), re.MULTILINE)
        if title_m:
            lookup[title_m.group(1).strip().lower()] = fname
    return lookup


TOPIC_LOOKUP = _build_topic_lookup()


def get_known_labels():
    db = sqlite3.connect(str(DB))
    rows = db.execute("SELECT id, label, type FROM entities").fetchall()
    db.close()
    return [{"id": r[0], "label": r[1], "type": r[2]} for r in rows]


def fuzzy_match(label, known):
    label_lower = label.lower().replace("-", " ").replace("_", " ")
    label_words = set(label_lower.split())
    for k in known:
        k_lower = k["label"].lower().replace("-", " ").replace("_", " ")
        k_words = set(k_lower.split())
        if label_lower == k_lower or label_lower in k_lower or k_lower in label_lower:
            return k
        if len(label_words) > 0 and len(k_words) > 0:
            overlap = len(label_words & k_words)
            if overlap / max(len(label_words), len(k_words)) >= 0.7:
                return k
    return None


def extract_fallback(text, known):
    text_lower = text.lower().replace("-", " ").replace("_", " ")
    found = set()
    for k in known:
        if k["label"].lower().replace("-", " ").replace("_", " ") in text_lower:
            found.add(k["label"])
    entities = [{"label": label, "type": next(
        e["type"] for e in known if e["label"] == label
    )} for label in sorted(found)]
    return {"entities": entities, "relations": []}


def resolve_and_store(result, known, text):
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")
    entity_map = {}
    new_e = 0
    new_r = 0
    for ent in result.get("entities", []):
        label = ent["label"]
        etype = ent["type"]
        if etype not in ENTITY_TYPES:
            etype = "concept"
        matched = fuzzy_match(label, known)
        if matched:
            entity_map[label] = matched["id"]
        else:
            existing = db.execute("SELECT id FROM entities WHERE label = ?", (label,)).fetchone()
            if existing:
                entity_map[label] = existing[0]
            else:
                cur = db.execute(
                    "INSERT INTO entities (label, type, properties) VALUES (?, ?, ?)",
                    (label, etype, json.dumps(
                        {"source": "extracted", "from_text": text[:200]}, ensure_ascii=False)),
                )
                entity_map[label] = cur.lastrowid
                new_e += 1
    for rel in result.get("relations", []):
        src, tgt, rtype = rel.get("source"), rel.get("target"), rel.get("type")
        if not src or not tgt or not rtype:
            continue
        if rtype not in RELATION_TYPES:
            rtype = "relates_to"
        src_id = entity_map.get(src)
        tgt_id = entity_map.get(tgt)
        if src_id and tgt_id:
            if not db.execute(
                "SELECT id FROM relations WHERE source_id = ? AND target_id = ? AND type = ?",
                (src_id, tgt_id, rtype),
            ).fetchone():
                db.execute(
                    "INSERT INTO relations (source_id, target_id, type, properties) VALUES (?, ?, ?, ?)",
                    (src_id, tgt_id, rtype,
                     json.dumps({"source": "extracted"}, ensure_ascii=False)),
                )
                new_r += 1
    db.commit()
    db.close()
    return new_e, new_r


def link_to_instructions(text, extracted_entities, fact_id=None):
    text_lower = text.lower()
    matched_topics = set()
    for keyword, fname in TOPIC_LOOKUP.items():
        if keyword in text_lower:
            matched_topics.add(fname)
    if not matched_topics:
        return 0, 0
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")
    new_r = 0
    new_e = 0
    instr_ids = {}
    for fname in matched_topics:
        label = f"instruction:{fname}"
        row = db.execute("SELECT id FROM entities WHERE label = ?", (label,)).fetchone()
        if row:
            instr_ids[fname] = row[0]
        else:
            cur = db.execute(
                "INSERT INTO entities (label, type, properties) VALUES (?, 'doc', ?)",
                (label, json.dumps({"source": "auto", "description": f"Instruction: {fname}"})),
            )
            instr_ids[fname] = cur.lastrowid
            new_e += 1
    for ent in extracted_entities:
        ent_label = ent["label"] if isinstance(ent, dict) else ent
        ent_row = db.execute("SELECT id FROM entities WHERE label = ?", (ent_label,)).fetchone()
        if not ent_row:
            continue
        for instr_id in instr_ids.values():
            if not db.execute(
                "SELECT id FROM relations WHERE source_id = ? AND target_id = ? AND type = 'references'",
                (ent_row[0], instr_id),
            ).fetchone():
                db.execute(
                    "INSERT INTO relations (source_id, target_id, type, properties) VALUES (?, ?, 'references', ?)",
                    (ent_row[0], instr_id, json.dumps({"source": "auto_topic_link"})),
                )
                new_r += 1
    if fact_id:
        fact_entity_label = f"fact:{fact_id}"
        fact_row = db.execute("SELECT id FROM entities WHERE label = ?", (fact_entity_label,)).fetchone()
        if not fact_row:
            cur = db.execute(
                "INSERT INTO entities (label, type, properties, knowledge_id) VALUES (?, 'fact', ?, ?)",
                (fact_entity_label, json.dumps({"source": "auto_link", "text_preview": text[:100]}), fact_id),
            )
            fact_entity_id = cur.lastrowid
            new_e += 1
        else:
            fact_entity_id = fact_row[0]
        for instr_id in instr_ids.values():
            if not db.execute(
                "SELECT id FROM relations WHERE source_id = ? AND target_id = ? AND type = 'references'",
                (fact_entity_id, instr_id),
            ).fetchone():
                db.execute(
                    "INSERT INTO relations (source_id, target_id, type, properties) VALUES (?, ?, 'references', ?)",
                    (fact_entity_id, instr_id, json.dumps({"source": "auto_topic_link"})),
                )
                new_r += 1
    db.commit()
    db.close()
    return new_e, new_r


def main():
    use_fallback = "--fallback" in sys.argv
    fact_id = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--fact-id" and i + 1 < len(sys.argv[1:]):
            fact_id = int(sys.argv[1:][i + 1])
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    text = " ".join(args) if args else sys.stdin.read().strip()
    if not text:
        print(json.dumps({"entities": [], "relations": [], "new_entities": 0, "new_relations": 0}))
        return
    known = get_known_labels()
    result = extract_fallback(text, known) if use_fallback else extract_fallback(text, known)
    new_e, new_r = resolve_and_store(result, known, text)
    link_e, link_r = link_to_instructions(text, result.get("entities", []), fact_id=fact_id)
    out = {"entities": result.get("entities", []), "relations": result.get("relations", []),
           "new_entities": new_e + link_e, "new_relations": new_r + link_r}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
