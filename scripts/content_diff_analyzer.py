#!/usr/bin/env python3
"""content_diff_analyzer.py — Detect user edits on published WP posts, extract taste signals.

1st run per post:  stores original content as baseline.
2nd+ run:          compares current WP content vs baseline, detects edits.
                  Extracts patterns from diffs → appends to taste-signals.md.
                  Updates baseline to current content for next cycle.

Usage:
  python3 content_diff_analyzer.py                # daily check (cron)
  python3 content_diff_analyzer.py --post 49      # check specific post
  python3 content_diff_analyzer.py --force-all     # re-check all even if cached
"""

import json, os, re, subprocess, sys
from datetime import datetime, timezone

WP = ["docker", "exec", "humanerd-wp", "wp", "--allow-root"]
BASE = os.path.expanduser("~/.drewgent")
CACHE_FILE = os.path.join(BASE, "P4-cortex/content/published-cache.json")
TASTE_FILE = os.path.join(BASE, "P4-cortex/content/taste-signals.md")


def wp(*args):
    r = subprocess.run([*WP, *args], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        print(f"  [WP] error: {r.stderr.strip()[:120]}")
        return None
    return r.stdout.strip()


def get_published():
    raw = wp("post", "list", "--posts_per_page=50", "--post_status=publish", "--format=json")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def load_cache():
    try:
        return json.load(open(CACHE_FILE))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    json.dump(cache, open(CACHE_FILE, "w"), indent=2, ensure_ascii=False)


def extract_plain(content):
    return re.sub(r"<[^>]+>", "", content).strip()


def compute_diff(original, current):
    o_lines = set(original.split("\n"))
    c_lines = set(current.split("\n"))
    added = [l.strip() for l in (c_lines - o_lines) if l.strip() and len(l.strip()) > 15]
    removed = [l.strip() for l in (o_lines - c_lines) if l.strip() and len(l.strip()) > 15]
    return added, removed


def classify_edit_patterns(added, removed):
    signals = []

    # Category: tone/voice shifts
    honorific_removed = [l for l in removed if re.search(r"요$|죠$|습니다$|ㅂ니다$", l)]
    honorific_added = [l for l in added if re.search(r"요$|죠$|습니다$|ㅂ니다$", l)]
    if honorific_removed:
        signals.append(f"tone: dropped honorifics ({len(honorific_removed)} lines)")
    if honorific_added:
        signals.append(f"tone: added honorifics ({len(honorific_added)} lines)")

    # Category: facts/sources added
    ref_added = [l for l in added if re.search(r"https?://|참고|출처|\[.+\]\(|관련 글|참조", l)]
    if ref_added:
        signals.append(f"reference: added {len(ref_added)} external links/refs")

    # Category: length changes
    adj_removed = [l for l in removed if re.search(r"매우|정말|굉장히|진짜|아주|약간|조금", l)]
    adj_added = [l for l in added if re.search(r"매우|정말|굉장히|진짜|아주|약간|조금", l)]
    if adj_removed:
        signals.append(f"modifier: removed {len(adj_removed)} adj/adv words")
    if adj_added:
        signals.append(f"modifier: added {len(adj_added)} adj/adv words")

    # Category: structure
    header_removed = [l for l in removed if l.startswith("#")]
    header_added = [l for l in added if l.startswith("#")]
    if header_removed:
        signals.append(f"structure: removed {len(header_removed)} headers")
    if header_added:
        signals.append(f"structure: added {len(header_added)} headers")

    # Category: personal voice (이/가/는/ㄴ데 patterns - user often adjusts these)
    connective_removed = [l for l in removed if re.search(r"~는데$|~니까$|~서$|~면$", l)]
    connective_added = [l for l in added if re.search(r"~는데$|~니까$|~서$|~면$", l)]
    if connective_removed or connective_added:
        signals.append(
            f"connective: adjusted {len(connective_removed)} sentences ending style"
        )

    return signals


def update_taste_signals(post_id, title, added, removed, pattern_signals):
    if not os.path.exists(TASTE_FILE):
        return

    with open(TASTE_FILE) as f:
        content = f.read()

    date = datetime.now().strftime("%Y-%m-%d")
    added_sample = " / ".join(a[:60] for a in added[:3]) if added else "-"
    removed_sample = " / ".join(r[:60] for r in removed[:3]) if removed else "-"
    signal_text = "; ".join(pattern_signals[:4]) if pattern_signals else "minor edit"

    entry = (
        f"| {date} | #{post_id} {title[:30]} "
        f"| +{len(added)} -{len(removed)} | {signal_text[:80]} | "
        f"added: {added_sample[:60]} | removed: {removed_sample[:60]} |\n"
    )

    if "## Post-Audit Trail" in content:
        content = content.replace("## Post-Audit Trail", f"{entry}\n## Post-Audit Trail")
    else:
        content += f"\n{entry}"

    with open(TASTE_FILE, "w") as f:
        f.write(content)


def analyze_post(post, cache, force=False):
    pid = post.get("ID")
    title = post.get("post_title", "")
    slug = post.get("post_name", "")
    entry = cache.get(str(pid))

    current_content = wp("post", "get", str(pid), "--field=post_content")
    if not current_content:
        return

    current_plain = extract_plain(current_content)

    # First time seeing this post → store baseline, skip
    if entry is None and not force:
        cache[str(pid)] = {
            "title": title,
            "slug": slug,
            "original": current_plain,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  [{pid}] {title[:40]:40} → cached as baseline")
        return

    original = entry.get("original", "")
    if original == current_plain and not force:
        print(f"  [{pid}] {title[:40]:40} → no change")
        return

    # Detect edit
    added, removed = compute_diff(original, current_plain)
    if not added and not removed:
        print(f"  [{pid}] {title[:40]:40} → minor change (whitespace/non-text)")
        return

    signals = classify_edit_patterns(added, removed)
    update_taste_signals(pid, title, added, removed, signals)

    # Update baseline to current version for next cycle
    cache[str(pid)] = {
        "title": title,
        "slug": slug,
        "original": current_plain,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"  [{pid}] {title[:40]:40} → +{len(added)} -{len(removed)} lines")
    report = [s[:80] for s in signals[:3]]
    if report:
        print(f"         signals: {'; '.join(report)}")
    print(f"         added sample: {(added[0] if added else '-')[:80]}")


def main():
    argv = set(sys.argv[1:])
    force = "--force-all" in argv or "-f" in argv
    check_id = None
    if "--post" in argv:
        idx = argv.index("--post") + 1
        if idx < len(sys.argv):
            check_id = sys.argv[idx]

    cache = load_cache()
    posts = get_published()
    print(f"Published posts: {len(posts)}, cached: {len(cache)}")

    for post in posts:
        pid = post.get("ID")
        if check_id and str(pid) != check_id:
            continue
        analyze_post(post, cache, force)

    save_cache(cache)
    print("done")


if __name__ == "__main__":
    main()
