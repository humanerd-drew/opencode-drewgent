#!/usr/bin/env python3
"""
Drewgent — Brain Rule Growth Monitor
새로운 .neuron 규칙 파일이 추가되면 감지하여 Discord로 알림
매 crontab 실행마다 상태를 brain_rule_state.json에 저장
"""

from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json, subprocess, sys, urllib.request

DATA_DIR   = Path.home() / ".drewgent"
SCRIPT_DIR = DATA_DIR / "scripts"
BRAIN_DIR  = DATA_DIR / "brain" / "Drewgent-brain"
STATE_FILE = DATA_DIR / "brain_rule_state.json"
DISCORD_CFG = DATA_DIR / "config" / "discord.json"

LAYER_NAMES = {
    "P0-brainstem": "P0-Brainstem",
    "P1-limbic":    "P1-Limbic",
    "P2-hippocampus": "P2-Hippocampus",
    "P3-sensors":   "P3-Sensors",
    "P4-cortex":    "P4-Cortex",
    "P5-ego":       "P5-Ego",
    "P6-prefrontal": "P6-Prefrontal",
}

def scan_brain():
    layers = defaultdict(list)
    if BRAIN_DIR.exists():
        for p0_dir in BRAIN_DIR.iterdir():
            if not p0_dir.is_dir():
                continue
            layer = p0_dir.name
            for f in p0_dir.rglob("*.neuron"):
                layers[layer].append(f.stem)
    return dict(layers)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def notify_discord(new_rules, layer_stats, total_brain):
    """새 규칙 추가 Discord 알림"""
    if not DISCORD_CFG.exists():
        print("No Discord config — skipping notification")
        return

    with open(DISCORD_CFG) as f:
        cfg = json.load(f)
    webhook_url = cfg.get("webhook_url")
    if not webhook_url:
        print("No webhook URL configured")
        return

    # Build embed message
    rules_lines = []
    for layer, rules in new_rules.items():
        layer_name = LAYER_NAMES.get(layer, layer)
        for rule in rules:
            rules_lines.append(f"• **{layer_name}**: `{rule}`")

    total_rules = sum(len(r) for r in new_rules.values())

    payload = {
        "content": f"🧠 **Brain New Rules Detected!** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
        "embeds": [{
            "title": f"🧬 +{total_rules} New Rule(s) Added",
            "color": 3447003,
            "fields": [
                {
                    "name": "Total Brain Rules",
                    "value": str(total_brain),
                    "inline": True
                },
                {
                    "name": "Layer Breakdown",
                    "value": "\n".join(f"`{k.split('-')[0]}`: +{len(v)}" for k, v in new_rules.items()),
                    "inline": True
                }
            ],
            "fields_extra": [
                {
                    "name": "New Rules",
                    "value": "\n".join(rules_lines[:10]),
                    "inline": False
                }
            ],
            "footer": {"text": "Drewgent Brain Growth Monitor"}
        }]
    }

    # Simplify — no fields_extra in basic discord webhook
    embed_fields = [
        {"name": "🧠 Total Rules", "value": str(total_brain), "inline": True},
        {"name": "🧬 New Rules", "value": str(total_rules), "inline": True},
        {"name": "📋 New Rule List", "value": "\n".join(rules_lines[:8]) or "—", "inline": False},
    ]

    payload = {
        "content": f"🧠 **Brain New Rules** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
        "embeds": [{
            "title": f"🧬 +{total_rules} New Neuron Rule(s)",
            "color": 3447003,
            "fields": embed_fields,
            "footer": {"text": "Drewgent Brain Growth Monitor"}
        }]
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            print("Discord notification sent ✓")
    except Exception as e:
        print(f"Discord notification failed: {e}")

def run_dashboard():
    """brain_nodes.py 실행"""
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "brain_nodes.py")],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout

def monitor():
    current = scan_brain()
    state   = load_state()

    # 이전 상태
    prev_layers = state.get("layers", {})
    prev_total  = state.get("total", 0)

    # 신규 규칙 탐지
    new_rules = {}
    total_now = 0
    for layer, items in current.items():
        prev_items = set(prev_layers.get(layer, []))
        curr_items = set(items)
        added = curr_items - prev_items
        if added:
            new_rules[layer] = sorted(added)
        total_now += len(items)

    # ── 결과 ───────────────────────────────────────────
    added_total = sum(len(v) for v in new_rules.values())

    # 상태 저장 (항상)
    save_state({
        "layers": {k: v for k, v in current.items()},
        "total": total_now,
        "updated": datetime.now().isoformat()
    })

    # 변화 없으면 아무것도 출력하지 않음 — cron deliver가 전송 안함
    if added_total == 0:
        return

    # 새 규칙 있을 때만 출력
    print(f"  🧠 Brain Growth Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  ─────────────────────────────────────────────────────")
    print(f"  Total rules: {prev_total} → {total_now} ({'+' if total_now >= prev_total else ''}{total_now - prev_total})")
    print(f"  🧬 NEW RULES DETECTED: {added_total}")
    for layer, rules in new_rules.items():
        lname = LAYER_NAMES.get(layer, layer)
        print(f"    {lname}: {', '.join(rules)}")

    # Discord 알림
    notify_discord(new_rules, {}, total_now)

    # Dashboard 실행
    print()
    print(run_dashboard())

if __name__ == "__main__":
    if "--check" in sys.argv:
        state = load_state()
        print("Current state:")
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        monitor()