#!/usr/bin/env python3
"""ARD Registry Query Client — search any ARD-compliant registry.

Usage:
  python3 ard_query.py <registry-url> <query> [--filter key=val,key=val] [--limit N]

Examples:
  python3 ard_query.py https://agentfinder.github.com/api/v1 "find a weather MCP server"
  python3 ard_query.py https://huggingface-hf-discover.hf.space "code review agent" --filter type=application/opencode-subagent+json
  python3 ard_query.py https://ai-catalog.outshift.io "flight booking" --limit 5

Environment:
  ARD_REGISTRY  — default registry URL (optional)

See: https://agenticresourcediscovery.org/spec/#72-search-post-search
"""

import json, os, sys, urllib.request, urllib.error, urllib.parse


def search(registry_url, text, filters=None, page_size=10):
    """POST /search to an ARD-compliant registry."""
    body = {
        "query": {"text": text},
        "pageSize": page_size,
    }
    if filters:
        body["query"]["filter"] = {k: [v] for k, v in filters.items()}

    req = urllib.request.Request(
        url=f"{registry_url.rstrip('/')}/search",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ard-query-client/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] {e.reason}", file=sys.stderr)
        sys.exit(1)


def format_result(entry, i):
    """Format a single search result for display."""
    lines = [
        f"  [{i}] {entry.get('displayName', '(no name)')}",
        f"       Type: {entry.get('type', '?')}",
        f"       ID:   {entry.get('identifier', '?')}",
    ]
    if entry.get("description"):
        lines.append(f"       Desc: {entry['description']}")
    if entry.get("score") is not None:
        lines.append(f"       Score: {entry['score']}")
    if entry.get("capabilities"):
        lines.append(f"       Caps: {', '.join(entry['capabilities'][:5])}")
    if entry.get("url"):
        lines.append(f"       URL:  {entry['url']}")
    if entry.get("source"):
        lines.append(f"       From: {entry['source']}")
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Query an ARD-compliant agent registry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("registry", nargs="?", help="Registry URL (or $ARD_REGISTRY)")
    parser.add_argument("query", help="Natural-language search query")
    parser.add_argument("--filter", "-f", help="Comma-separated key=val filters")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max results (default 10)")
    parser.add_argument("--json", "-j", action="store_true", help="Raw JSON output")
    args = parser.parse_args()

    registry = args.registry or os.environ.get("ARD_REGISTRY")
    if not registry:
        print("Usage: ard_query.py <registry-url> <query>", file=sys.stderr)
        print("  or set ARD_REGISTRY env var.", file=sys.stderr)
        sys.exit(1)

    filters = {}
    if args.filter:
        for pair in args.filter.split(","):
            if "=" not in pair:
                print(f"[ERROR] Invalid filter: {pair} (use key=val)", file=sys.stderr)
                sys.exit(1)
            k, v = pair.split("=", 1)
            filters[k.strip()] = v.strip()

    result = search(registry, args.query, filters, args.limit)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    results = result.get("results", [])
    referrals = result.get("referrals", [])

    print(f"\n{'='*60}")
    print(f"  ARD Search: \"{args.query}\"")
    print(f"  Registry:   {registry}")
    print(f"  Results:    {len(results)}")
    print(f"{'='*60}\n")

    if not results and not referrals:
        print("  (no results)")
        return

    for i, entry in enumerate(results, 1):
        print(format_result(entry, i))
        print()

    if referrals:
        print(f"  -- Referrals ({len(referrals)}) --")
        for ref in referrals:
            print(f"     {ref.get('displayName','?')}  <{ref.get('url','?')}>")
        print()

    if "pageToken" in result:
        print(f"  (more results: pageToken={result['pageToken']})")


if __name__ == "__main__":
    main()
