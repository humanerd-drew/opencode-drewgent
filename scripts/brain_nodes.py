#!/usr/bin/env python3
"""
Drewgent Brain — Biological Brain Visualization v3
실제 뇌 해부학적 구조를 반영한 ASCII 아트
"""

from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json, os

DREWGENT_HOME = Path.home() / ".drewgent"
BRAIN_DIR  = DREWGENT_HOME / "brain" / "Drewgent-brain"
SKILLS_DIR = DREWGENT_HOME / "skills"
DATA_DIR   = DREWGENT_HOME
SNAPSHOT   = DATA_DIR / "brain_snapshot.json"

# 해부학 레이어 순서 (뒤통수→앞이마 방향)
LAYER_ORDER = [
    "P0-brainstem",    # 뇌줄기 (연속）
    "P1-limbic",       # 변연계 (중간)
    "P2-hippocampus",  # 해마
    "P3-sensors",      # 감각/투피alamus
    "P4-cortex",       # 대뇌피질 (상단)
    "P5-ego",          # 측두엽 (옆)
    "P6-prefrontal",   # 전전두엽 (맨 앞)
]

LAYER_NAMES = {
    "P0-brainstem": "Brainstem",
    "P1-limbic": "Limbic",
    "P2-hippocampus": "Hippocampus",
    "P3-sensors": "Thalamus",
    "P4-cortex": "Cortex",
    "P5-ego": "Temporal",
    "P6-prefrontal": "Prefrontal",
}

LAYER_COLORS = {
    "P0-brainstem": "\033[91m",  # 빨강
    "P1-limbic":    "\033[95m",  # 보라
    "P2-hippocampus":"\033[36m",  # 청록
    "P3-sensors":   "\033[93m",  # 노랑
    "P4-cortex":    "\033[92m",  # 초록
    "P5-ego":       "\033[94m",  # 파랑
    "P6-prefrontal": "\033[97m", # 흰색
}

RESET = "\033[0m"
DIM   = "\033[90m"
W = RESET

def c(text, color=""):
    return f"{color}{text}{RESET}" if color else text

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

def scan_skills():
    count = 0
    cats = []
    if SKILLS_DIR.exists():
        for d in SKILLS_DIR.iterdir():
            if d.is_dir() and d.name not in ("__pycache__", ".cache"):
                count += 1
                cats.append(d.name)
    return count, sorted(cats)

def scan_knowledge():
    for path in [DATA_DIR / "P4-cortex" / "drewgent_knowledge.json", DATA_DIR / "knowledge.json"]:
        if path.exists():
            with open(path) as f:
                d = json.load(f)
                return len(d.get("knowledge_store", []))
    return 0

def scan_sessions():
    sd = DATA_DIR / "checkpoints"
    if sd.exists():
        return len(list(sd.glob("session_*.json")))
    return 0

def get_snapshot():
    if SNAPSHOT.exists():
        with open(SNAPSHOT) as f:
            return json.load(f)
    return {}

def save_snapshot(now):
    with open(SNAPSHOT, "w") as f:
        json.dump(now, f, indent=2)

def delta_str(key, now, prev):
    if key in prev:
        d = now[key] - prev[key]
        return f"+{d}" if d > 0 else str(d)
    return f"+{now[key]}"

def neuro_bar(count, max_c=6, width=8):
    if count == 0:
        return "░" * width
    filled = min(int((count / max_c) * width), width)
    return "█" * filled + "░" * (width - filled)

def render():
    layers = scan_brain()
    skills_n, skills_cat = scan_skills()
    know_n = scan_knowledge()
    sess_n = scan_sessions()
    prev   = get_snapshot()

    nodes = []
    for layer in LAYER_ORDER:
        items = layers.get(layer, [])
        nodes.append({
            "layer": layer,
            "name":  LAYER_NAMES.get(layer, layer),
            "short": layer.split("-")[0],
            "count": len(items),
            "items": items,
            "color": LAYER_COLORS.get(layer, ""),
        })

    total_brain = sum(n["count"] for n in nodes)
    now = {"brain": total_brain, "skills": skills_n, "knowledge": know_n, "sessions": sess_n}

    print()
    print(f"  {c('╔═══════════════════════════════════════════════════════════════════╗', DIM)}")
    print(f"  {c('║          DREWGENT BRAIN — NEUROARCHITECTURE MAP  v3            ║', W)}")
    print(f"  {c('║          Generated:', DIM)} {datetime.now().strftime('%Y-%m-%d %H:%M')}                              {c('║', DIM)}")
    print(f"  {c('╚═══════════════════════════════════════════════════════════════════╝', DIM)}")
    print()

    p6 = nodes[6]
    p6c = p6["color"]
    print(f"  {c('        ╭────────────────────────────────────────╮', DIM)}")
    print(f"  {c('     ╭──┤', DIM)}  {c('● PREFRONTAL CORTEX', p6c)}  {c('  [brain-dashboard: every session end]', DIM)}       {c('├──╮', DIM)}")
    print(f"  {c('     │  │', DIM)}  {p6c}P6-Rules:{W} {', '.join(p6['items']) if p6['items'] else '—'}     {c('│  │', DIM)}")
    print(f"  {c('     │  ╰────────────────────────────────────────╯  │', DIM)}")
    print(f"  {c('     │         ╲     ▲     ╱', DIM)}")
    print(f"  {c('     │          ╲   ╱┃╲   ╱', DIM)}")
    print(f"  {c('     │           ╲ ╱ ┃ ╲ ╱', DIM)}")
    print(f"  {c('     │            ╲╱  ┃  ╲╱', DIM)}")
    print(f"  {c('     │             ╲  ┃  ╱', DIM)}")

    p5 = nodes[5]
    p4 = nodes[4]
    p3 = nodes[3]
    print(f"  {c('   ╔════════════════╩═══════════╩═══════════════════════════╗', DIM)}")
    print(f"  {c('   ║', DIM)}  {p5['color']}P5 Temporal{W}  {p5['name']:<12} {c('[' + neuro_bar(p5['count'], 6, 6) + ']', DIM)} {p5['color']}{str(p5['count']).rjust(2)}{W}  {', '.join(p5['items']) if p5['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│  ╲                  │                  ╱  │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│   ╲   ┌──────────────────────────┐   ╱   │', DIM)}")
    print(f"  {c('   ║', DIM)}  {p4['color']}P4 Cortex{W}   {p4['name']:<12} {c('[' + neuro_bar(p4['count'], 6, 6) + ']', DIM)} {p4['color']}{str(p4['count']).rjust(2)}{W}  {', '.join(p4['items'][:3]) if p4['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│     ╲  │    DORSAL CORTEX      │  ╱     │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│      ╲ │  [SCHEMA|INDEX|MEMORY] │ ╱      │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│   ╱── ╲└──────────────────────────┘╱──╲   │', DIM)}")
    print(f"  {c('   ║', DIM)}  {p3['color']}P3 Thalamus{W} {p3['name']:<12} {c('[' + neuro_bar(p3['count'], 6, 6) + ']', DIM)} {p3['color']}{str(p3['count']).rjust(2)}{W}  {', '.join(p3['items']) if p3['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│       ╲   ┌──────────────────┐   ╱       │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│        ╲  │  LIMBIC BRIDGE   │  ╱        │', DIM)}")

    p2 = nodes[2]
    p1 = nodes[1]
    print(f"  {c('   ║', DIM)}  {p2['color']}P2 Hippo{W}    {p2['name']:<12} {c('[' + neuro_bar(p2['count'], 6, 6) + ']', DIM)} {p2['color']}{str(p2['count']).rjust(2)}{W}  {', '.join(p2['items']) if p2['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│         ╲ ┌──────────────────┐ ╱         │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│          ╲│   LIMBIC SYSTEM  │╱          │', DIM)}")
    print(f"  {c('   ║', DIM)}  {p1['color']}P1 Limbic{W}  {p1['name']:<12} {c('[' + neuro_bar(p1['count'], 6, 6) + ']', DIM)} {p1['color']}{str(p1['count']).rjust(2)}{W}  {', '.join(p1['items']) if p1['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│           ╲┌──────────────────┐╱           │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│            ╲│   ▲▲▲ BASAL     │╱            │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│             ╲│  GANGLIA ▲▲▲  │╱             │', DIM)}")

    p0 = nodes[0]
    print(f"  {c('   ╠═════════════════╩═══════════════════════════════════╣', DIM)}")
    print(f"  {c('   ║', DIM)}  {p0['color']}P0 Brainstem{W} {p0['name']:<12} {c('[' + neuro_bar(p0['count'], 6, 6) + ']', DIM)} {p0['color']}{str(p0['count']).rjust(2)}{W}  {', '.join(p0['items'][:4]) if p0['items'] else '—'}  {c('│', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│    ▲▲▲▲▲▲▲  ▲▲▲▲▲▲▲  ▲▲▲▲▲▲▲  │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│   ╔════╦═══════════════╦════╗   │', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│   ║', DIM)}  {c('SPINAL CORD', DIM)}  {c('║', DIM)}")
    print(f"  {c('   ║', DIM)}  {c('│   ╚════╩═══════════════╩════╝   │', DIM)}")
    print(f"  {c('   ╚═══════════════════════════════════════════════════╝', DIM)}")
    print()

    print(f"  {c('  ── SYNAPSE SIGNAL FLOW ─────────────────────────────────────', DIM)}")
    flow = " → ".join([nodes[i]["short"] for i in range(len(nodes))])
    print(f"  {c('  ', DIM)}[Signal]  {c(flow, DIM)}")
    print(f"  {c('  ', DIM)}{c('SENSORY → THALAMUS → LIMBIC → CORTEX → PREFRONTAL → ACTION', DIM)}")
    print()

    print(f"  {c('  ── SYSTEM STATS ─────────────────────────────────────────────', DIM)}")
    print(f"  {c('  │', DIM)}  Brain: {total_brain:>3} rules   Skills: {skills_n:>3}   Knowledge: {know_n:>4}   Sessions: {sess_n:>4}")
    print(f"  {c('  │', DIM)}  Growth: {delta_str('brain',now,prev):>6} brain  {delta_str('skills',now,prev):>6} skills  {delta_str('knowledge',now,prev):>6} know  {delta_str('sessions',now,prev):>6} sess")
    print()

    print(f"  {c('  ── LAYER DETAIL ──────────────────────────────────────────────', DIM)}")
    for n in nodes:
        items_str = ", ".join(n['items'][:6])
        if len(n['items']) > 6:
            items_str += f" (+{len(n['items'])-6})"
        print(f"  {n['color']}{n['short']}{W} {n['name']:<12} {str(n['count']).rjust(2)} {items_str}")
    print()

    save_snapshot(now)

if __name__ == "__main__":
    render()
