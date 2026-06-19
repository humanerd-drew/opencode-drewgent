#!/usr/bin/env python3
"""
DeepSeek Korean Text Humanization Script
=========================================
content-pipeline Phase 4-5: MiniMax-M3가 쓴 한글 초안을 DeepSeek로 윤문.

Usage:
    python3 deepseek_humanize.py --input <draft_file> [--output <output_file>]
    python3 deepseek_humanize.py --input ~/.drewgent/P2-hippocampus/memories/insights/2026-05-test.md

Output:
    윤문된 텍스트를 output 파일에写入 (기본: --input 파일 직접 덮어쓰기)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from modules.secrets_vault import vault

# =============================================================================
# DeepSeek API Call
# =============================================================================

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def call_deepseek(messages: list, api_key: str, temperature: float = 0.7) -> str:
    """Call DeepSeek API and return the response text."""
    import urllib.request

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"]


# =============================================================================
# Prompt Engineering
# =============================================================================

HUMANIZATION_PROMPT = """You are a Korean text humanizer. Your task is to revise the given Korean text to make it sound natural, warm, and human-written — as if written by a thoughtful Korean person, not by an AI.

## Rules (MUST follow)
1. Preserve the ORIGINAL meaning and structure — do NOT add new ideas
2. Fix AI-characteristic patterns:
   - Remove stiff/formal AI phrasing
   - Replace overused connectors (그리고, 또한, 따라서, 즉) with natural alternatives
   - Break overly long compound sentences into shorter, natural ones
   - Fix unnatural spacing or punctuation patterns
   - Remove repetitive structures
3. Keep the writing style: bold section dividers, direct "당신" address, 1st person ("저"/"나"), informal/hybrid tone
4. For Hanja (한자) words: convert common ones to Korean unless it's a well-known term
   - Exception: keep proper nouns, technical terms, and quotes
5. Maintain the original frontmatter and SEO section intact (only revise body content)

## Input text (below the --- frontmatter separator):
The text between the last ``` (closing code block) and the end is the body to revise.
Only revise the body. Leave frontmatter, code blocks, and SEO section completely unchanged.

## Output:
Return the COMPLETE revised text with frontmatter untouched and body replaced.
Do NOT wrap output in markdown code blocks. Return raw text."""


def build_user_message(draft_text: str) -> str:
    """Build the user message for DeepSeek."""
    return f"""## Original Korean Text:

{draft_text}

---

Revise this text following the rules above. Return the complete text with only the body revised."""


# =============================================================================
# Stats Tracking
# =============================================================================

def count_stats(original: str, revised: str) -> dict:
    """Count various metrics about the changes."""
    # Count Hanyang (한자) - simplified check for common patterns
    hanja_pattern = re.compile(r"[一-鿿]{2,}")  # CJK Unified Ideographs blocks
    original_hanja = len(hanja_pattern.findall(original))
    revised_hanja = len(hanja_pattern.findall(revised))

    # Count sentence-level changes (rough)
    original_sents = re.split(r"[.\n]+", original)
    revised_sents = re.split(r"[.\n]+", revised)

    # Count AI characteristic patterns
    ai_patterns = ["그리고", "또한", "따라서", "즉", "이 글은", "이것은", "에 대해", "주목할 만한"]
    original_ai = sum(original.lower().count(p) for p in ai_patterns)
    revised_ai = sum(revised.lower().count(p) for p in ai_patterns)

    return {
        "original_chars": len(original),
        "revised_chars": len(revised),
        "original_hanja_count": original_hanja,
        "revised_hanja_count": revised_hanja,
        "hanja_converted": original_hanja - revised_hanja,
        "original_ai_phrases": original_ai,
        "revised_ai_phrases": revised_ai,
        "ai_phrases_reduced": original_ai - revised_ai,
        "sentences_changed": abs(len(original_sents) - len(revised_sents)),
    }


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="DeepSeek Korean Text Humanizer")
    parser.add_argument("--input", required=True, help="Input draft file path")
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: overwrite input)",
    )
    args = parser.parse_args()

    input_path = Path(os.path.expanduser(args.input))
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.stat().st_size < 100:
        print("ERROR: Input file too small (< 100 bytes)", file=sys.stderr)
        sys.exit(1)

    output_path = Path(os.path.expanduser(args.output)) if args.output else input_path

    # Load draft
    original_text = input_path.read_text(encoding="utf-8")
    original_stripped = original_text.strip()

    # Resolve DeepSeek API key from vault
    api_key_ref = "vault_948a246f"
    api_key = vault.resolve(api_key_ref)

    if not api_key:
        print("ERROR: DeepSeek API key not found in vault (vault_948a246f)", file=sys.stderr)
        sys.exit(1)

    # Build messages
    system_msg = {"role": "system", "content": HUMANIZATION_PROMPT}
    user_msg = {
        "role": "user",
        "content": build_user_message(original_text),
    }

    # Call DeepSeek
    try:
        revised_text = call_deepseek([system_msg, user_msg], api_key)
    except Exception as e:
        print(f"ERROR: DeepSeek API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Post-process: ensure frontmatter is preserved
    # If the original has frontmatter, make sure frontmatter is at the top of output
    if original_text.startswith("---"):
        # Find frontmatter boundary
        fm_end = original_text.find("\n---\n", 3)  # skip first ---
        if fm_end != -1:
            fm_end += 5  # include the \n---\n
            original_frontmatter = original_text[:fm_end]
            # If revised doesn't start with frontmatter, prepend it
            if not revised_text.strip().startswith("---"):
                revised_text = original_frontmatter + "\n" + revised_text.strip() + "\n"

    # Count stats
    stats = count_stats(original_text, revised_text)

    # Write output
    output_path.write_text(revised_text, encoding="utf-8")

    # Print stats
    print(f"DeepSeek Humanization: DONE")
    print(f"  Input chars: {stats['original_chars']}")
    print(f"  Output chars: {stats['revised_chars']}")
    print(f"  Hanyang converted: {stats['hanja_converted']}")
    print(f"  AI phrases reduced: {stats['ai_phrases_reduced']}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()