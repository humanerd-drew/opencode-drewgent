#!/usr/bin/env python3
"""content-graph-engine CLI.

Usage:
  python3 cli/main.py build           # build content graph
  python3 cli/main.py suggest          # show top suggestions
  python3 cli/main.py apply --limit 3  # apply top N suggestions
  python3 cli/main.py apply --id 49    # apply suggestions for post 49
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph import build, load_graph, apply_suggestion


def cmd_build():
    limit = int(os.environ.get("CGE_LIMIT", "100"))
    threshold = float(os.environ.get("CGE_THRESHOLD", "0.08"))
    top_n = int(os.environ.get("CGE_TOP_N", "5"))
    build(limit=limit, threshold=threshold, top_n=top_n)


def cmd_suggest():
    state = load_graph()
    if not state.suggested:
        print("No suggestions. Run `build` first.")
        return
    for s in sorted(state.suggested, key=lambda x: -x["score"])[:20]:
        print(f"  [{s['source_layer']}] "
              f"{s['source_id']} → {s['target_id']}  "
              f"score={s['score']:.3f}  "
              f"anchor='{s['anchor_text'][:50]}'")


def cmd_apply():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--id", type=int, default=None)
    args = parser.parse_args(sys.argv[2:])

    state = load_graph()
    candidates = state.suggested

    if args.id:
        candidates = [s for s in candidates if s["source_id"] == args.id]

    # Only layer1 (TF-IDF) suggestions have keyword overlap for in-content links
    # layer0 (taxonomy) suggestions are handled by Content Quicksand plugin footer
    candidates = [s for s in candidates if s.get("source_layer") == "layer1"]

    if not candidates:
        print("No applicable suggestions. Run `build` first.")
        return

    from core.models import LinkSuggestion
    for s in sorted(candidates, key=lambda x: -x["score"])[:args.limit]:
        sug = LinkSuggestion(
            source_id=s["source_id"], target_id=s["target_id"],
            source_title=s.get("source_title", ""),
            target_title=s.get("target_title", ""),
            anchor_text=s.get("anchor_text", ""),
            score=s.get("score", 0), verified=True,
        )
        apply_suggestion(sug)


if __name__ == "__main__":
    cmds = {"build": cmd_build, "suggest": cmd_suggest, "apply": cmd_apply}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(1)
    cmds[sys.argv[1]]()
