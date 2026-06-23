#!/usr/bin/env python3
"""Vault health audit — wikilink resolution, backlink density, orphan detection, file size analysis.

Run from anywhere: python3 references/vault-audit.py

Output: structured report of vault graph health.
"""
import os
import re
from collections import defaultdict, Counter

VAULT = os.path.expanduser("~/.drewgent")
CORE_ZONES = ['P0-brainstem', 'P1-limbic', 'P3-sensors', 'P4-cortex', 'P5-ego', 'P6-prefrontal']
WIKILINK_RE = re.compile(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]')
NON_FILE_RE = re.compile(r'^(read-time|elapsedTime|totalTime|duration|pagename|publish|draft|type|space|domain|tags?|created|updated|status)$')

def get_vault_files(zones):
    files = []
    for zone in zones:
        for root, dirs, fnames in os.walk(os.path.join(VAULT, zone)):
            if 'node_modules' in root or '.git' in root:
                continue
            for f in fnames:
                if f.endswith(('.md', '.neuron')):
                    files.append(os.path.join(root, f))
    return files

def audit():
    files = get_vault_files(CORE_ZONES)
    print(f"Core vault files: {len(files)}")

    # Build slug map
    slug_map = {}
    for fp in files:
        slug = os.path.splitext(os.path.basename(fp))[0]
        if slug not in slug_map:
            slug_map[slug] = fp
        rel = os.path.relpath(fp, VAULT)
        rel_slug = os.path.splitext(rel)[0].replace(os.sep, '/')
        if rel_slug not in slug_map:
            slug_map[rel_slug] = fp

    # Scan all wikilinks
    incoming = defaultdict(set)
    outgoing = defaultdict(set)
    broken = []
    total_links = 0
    total_resolved = 0

    for fp in files:
        try:
            content = open(fp, 'r', errors='ignore').read()
        except:
            continue
        rel = os.path.relpath(fp, VAULT)
        targets = set()
        for m in WIKILINK_RE.finditer(content):
            total_links += 1
            t = m.group(1).split('|')[0].split('#')[0].strip()
            if not t or NON_FILE_RE.match(t):
                continue
            targets.add(t)
            incoming[t].add(rel)
            
            # Check resolution
            resolved = False
            base = os.path.basename(t)
            if base in slug_map or t in slug_map:
                resolved = True
            else:
                for p in [t + '.md', t + '.neuron', t]:
                    if os.path.exists(os.path.join(VAULT, p)):
                        resolved = True
                        break
            if resolved:
                total_resolved += 1
            else:
                broken.append((rel, t))
        outgoing[rel] = targets

    print(f"Body wikilinks: {total_links}")
    print(f"  Resolved: {total_resolved}")
    print(f"  Broken: {len(broken)}")
    if broken:
        print("  Top broken:")
        for src, tgt in broken[:10]:
            print(f"    {os.path.basename(src)} → [[{tgt}]]")

    # Backlink density
    print(f"\nBacklink density:")
    files_with_inbound = len(set().union(*[incoming[v] for v in incoming]))
    print(f"  Files with ≥1 inbound: {files_with_inbound}")
    print(f"  Files with 0 inbound: {len(files) - files_with_inbound}")
    
    # Top-linked
    print(f"\nTop referenced targets (by inbound count):")
    for tgt, srcs in sorted(incoming.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  [[{tgt}]]: {len(srcs)}")

    # File size health
    print(f"\nFile size health:")
    tiny = []
    huge = []
    for fp in files:
        try:
            sz = os.path.getsize(fp)
            if sz < 50:
                tiny.append((os.path.relpath(fp, VAULT), sz))
            elif sz > 100000:
                huge.append((os.path.relpath(fp, VAULT), sz))
        except:
            pass
    print(f"  <50 bytes: {len(tiny)}")
    if tiny:
        for p, s in tiny[:5]:
            print(f"    {p} ({s}B)")
    print(f"  >100 KB: {len(huge)}")

if __name__ == '__main__':
    audit()
