#!/usr/bin/env python3
"""
Drewgent Brain — HTML Dashboard Generator
생성된 HTML을 ~/.drewgent/brain_dashboard.html로 저장
브라우저에서 열면 실시간 뇌 모니터링 대시보드 확인 가능
"""

from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json

DREWGENT_HOME = Path.home() / ".drewgent"
BRAIN_DIR  = DREWGENT_HOME / "brain" / "Drewgent-brain"
SKILLS_DIR = DREWGENT_HOME / "skills"
DATA_DIR   = DREWGENT_HOME
STATE_FILE = DATA_DIR / "brain_rule_state.json"
OUT_HTML   = DATA_DIR / "brain_dashboard.html"
SNAPSHOT   = DATA_DIR / "brain_snapshot.json"

LAYER_ORDER = [
    ("P0-brainstem",  "Brainstem",  "#e53935"),
    ("P1-limbic",     "Limbic",     "#ab47bc"),
    ("P2-hippocampus","Hippocampus","#00acc1"),
    ("P3-sensors",    "Thalamus",   "#fdd835"),
    ("P4-cortex",     "Cortex",     "#43a047"),
    ("P5-ego",        "Temporal",   "#1e88e5"),
    ("P6-prefrontal", "Prefrontal", "#eceff1"),
]

LAYER_NAMES = {k: v for k, v, _ in LAYER_ORDER}
LAYER_COLS  = {k: c for k, _, c in LAYER_ORDER}

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
    count, cats = 0, []
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

def load_rule_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def neuro_bar(count, max_c=6, width=12):
    if count == 0:
        return "░" * width
    filled = min(int((count / max_c) * width), width)
    return "█" * filled + "░" * (width - filled)

def generate():
    layers = scan_brain()
    skills_n, skills_cat = scan_skills()
    know_n  = scan_knowledge()
    sess_n  = scan_sessions()
    snap    = get_snapshot()
    rule_state = load_rule_state()

    prev_total = rule_state.get("total", 0)
    total_brain = sum(len(v) for v in layers.values())
    growth = total_brain - prev_total

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    layer_data = []
    for layer_id, name, color in LAYER_ORDER:
        items = layers.get(layer_id, [])
        layer_data.append({
            "id": layer_id,
            "short": layer_id.split("-")[0],
            "name": name,
            "color": color,
            "count": len(items),
            "items": items,
            "bar": neuro_bar(len(items), 6, 12),
        })

    svg_nodes = []
    y_base = 380
    y_step = 52
    for i, ld in enumerate(layer_data):
        y = y_base - i * y_step
        x = 280
        svg_nodes.append({**ld, "x": x, "y": y})

    svg_connections = []
    for i in range(len(svg_nodes) - 1):
        n1 = svg_nodes[i]
        n2 = svg_nodes[i + 1]
        svg_connections.append({
            "x1": n1["x"], "y1": n1["y"],
            "x2": n2["x"], "y2": n2["y"],
            "color": n2["color"],
        })

    skill_rows = ""
    cols = 4
    row = []
    for i, cat in enumerate(skills_cat):
        row.append(f'<span class="skill-tag">{cat}</span>')
        if len(row) == cols or i == len(skills_cat) - 1:
            skill_rows += '<div class="skill-row">' + "".join(row) + "</div>"
            row = []

    svg_node_elements = ""
    for nd in svg_nodes:
        items_list = "<br>".join(nd["items"][:5])
        if len(nd["items"]) > 5:
            items_list += f"<br>+{len(nd['items'])-5} more"

        svg_node_elements += f"""
        <g class="brain-node" data-layer="{nd['short']}" opacity="0">
          <defs>
            <filter id="glow-{nd['short']}" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur"/>
              <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <rect x="{nd['x']-120}" y="{nd['y']-28}" width="240" height="56"
                rx="10" fill="#0d1117" stroke="{nd['color']}" stroke-width="2"
                filter="url(#glow-{nd['short']})"/>
          <circle cx="{nd['x']-95}" cy="{nd['y']}" r="18"
                  fill="{nd['color']}" opacity="0.9"/>
          <text x="{nd['x']-95}" y="{nd['y']+5}"
                text-anchor="middle" fill="white" font-size="11" font-weight="bold">
            {nd['short']}
          </text>
          <text x="{nd['x']-65}" y="{nd['y']-5}"
                fill="{nd['color']}" font-size="13" font-weight="bold"
                font-family="monospace">
            {nd['name']}
          </text>
          <text x="{nd['x']-65}" y="{nd['y']+12}"
                fill="#8b949e" font-size="11" font-family="monospace">
            {nd['count']} rules
          </text>
          <text x="{nd['x']+55}" y="{nd['y']+4}"
                fill="#c9d1d9" font-size="10" font-family="monospace">
            {nd['items'][0] if nd['items'] else '—'}
          </text>
        </g>
        """

    svg_conn_elements = ""
    for conn in svg_connections:
        svg_conn_elements += f"""
        <line x1="{conn['x1']}" y1="{conn['y1']-28}"
              x2="{conn['x2']}" y2="{conn['y2']+28}"
              stroke="{conn['color']}" stroke-width="2"
              stroke-dasharray="4,4" opacity="0.5"/>
        <circle cx="{(conn['x1']+conn['x2'])//2}"
                cy="{(conn['y1']+conn['y2'])//2}"
                r="3" fill="{conn['color']}" opacity="0.6">
          <animate attributeName="opacity" values="0.3;1;0.3" dur="2s" repeatCount="indefinite"/>
        </circle>
        """

    spine_svg = f"""
    <rect x="260" y="400" width="40" height="60" rx="5"
          fill="#0d1117" stroke="#e53935" stroke-width="2"/>
    <text x="280" y="435" text-anchor="middle" fill="#e53935"
          font-size="9" font-family="monospace">SPINAL</text>
    <circle r="4" fill="#43a047" opacity="0">
      <animateMotion dur="3s" repeatCount="indefinite" begin="0s"
        path="M280,80 L280,380"/>
      <animate attributeName="opacity" values="0;1;0" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle r="4" fill="#1e88e5" opacity="0">
      <animateMotion dur="3s" repeatCount="indefinite" begin="1s"
        path="M280,80 L280,380"/>
      <animate attributeName="opacity" values="0;1;0" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle r="4" fill="#fdd835" opacity="0">
      <animateMotion dur="3s" repeatCount="indefinite" begin="2s"
        path="M280,80 L280,380"/>
      <animate attributeName="opacity" values="0;1;0" dur="3s" repeatCount="indefinite"/>
    </circle>
    """

    def stat_card(icon, label, value, delta, color):
        delta_str = f'<span class="delta delta-pos">+{delta}</span>' if delta > 0 else (
            f'<span class="delta delta-neg">{delta}</span>' if delta < 0 else
            '<span class="delta delta-zero">—</span>')
        return f"""
        <div class="stat-card" style="border-top: 3px solid {color}">
          <div class="stat-icon">{icon}</div>
          <div class="stat-body">
            <div class="stat-label">{label}</div>
            <div class="stat-value" style="color:{color}">{value}</div>
            <div class="stat-delta">vs prev {delta_str}</div>
          </div>
        </div>
        """

    g_brain   = total_brain - snap.get("brain", 0)
    g_skills  = skills_n    - snap.get("skills", 0)
    g_know    = know_n      - snap.get("knowledge", 0)
    g_sessions= sess_n      - snap.get("sessions", 0)

    stats_html = stat_card("🧠", "Brain Rules", total_brain, g_brain, "#43a047")
    stats_html += stat_card("⚡", "Skills", skills_n, g_skills, "#1e88e5")
    stats_html += stat_card("💡", "Knowledge", know_n, g_know, "#00acc1")
    stats_html += stat_card("🔄", "Sessions", sess_n, g_sessions, "#ab47bc")

    layer_rows = ""
    for ld in layer_data:
        items_str = ", ".join(ld["items"][:6])
        if len(ld["items"]) > 6:
            items_str += f" (+{len(ld['items'])-6})"
        layer_rows += f"""
        <tr>
          <td><span class="layer-badge" style="background:{ld['color']}20;color:{ld['color']}">{ld['short']}</span></td>
          <td>{ld['name']}</td>
          <td><span class="bar-display">{ld['bar']}</span></td>
          <td>{ld['count']}</td>
          <td class="items-col">{items_str}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Drewgent Brain Dashboard — {now_str}</title>
<style>
  :root {{
    --bg: #0d1117;
    --bg2: #161b22;
    --bg3: #21262d;
    --border: #30363d;
    --text: #c9d1d9;
    --text-dim: #8b949e;
    --accent: #43a047;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --mono: 'SF Mono', 'Fira Code', monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; overflow-x: hidden; }}
  .header {{ background: linear-gradient(135deg, #0d1117 0%, #1a2332 100%); border-bottom: 1px solid var(--border); padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 20px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }}
  .header h1 span {{ color: var(--accent); }}
  .header-right {{ display: flex; align-items: center; gap: 16px; }}
  .refresh-btn {{ background: var(--bg3); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
  .refresh-btn:hover {{ background: var(--accent); border-color: var(--accent); }}
  .updated-at {{ color: var(--text-dim); font-size: 12px; font-family: var(--mono); }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px 32px; }}
  .stat-card {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; gap: 12px; align-items: center; transition: transform 0.2s; }}
  .stat-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
  .stat-icon {{ font-size: 28px; }}
  .stat-body {{ flex: 1; }}
  .stat-label {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-value {{ font-size: 28px; font-weight: 700; font-family: var(--mono); margin: 2px 0; }}
  .stat-delta {{ font-size: 11px; color: var(--text-dim); }}
  .delta-pos {{ color: #3fb950; }}
  .delta-neg {{ color: #f85149; }}
  .delta-zero {{ color: var(--text-dim); }}
  .brain-section {{ padding: 0 32px 24px; }}
  .section-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  .brain-container {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 20px; overflow-x: auto; }}
  .brain-svg {{ width: 100%; height: 460px; }}
  .table-section {{ padding: 0 32px 24px; }}
  .data-table {{ width: 100%; border-collapse: collapse; background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
  .data-table th {{ background: var(--bg3); color: var(--text-dim); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }}
  .data-table td {{ padding: 10px 16px; font-size: 13px; border-bottom: 1px solid #21262d; vertical-align: middle; }}
  .data-table tr:last-child td {{ border-bottom: none; }}
  .data-table tr:hover td {{ background: #161b22; }}
  .layer-badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; font-family: var(--mono); }}
  .bar-display {{ font-family: var(--mono); font-size: 12px; letter-spacing: -1px; color: var(--text-dim); }}
  .items-col {{ color: var(--text-dim); font-size: 12px; font-family: var(--mono); }}
  .skills-section {{ padding: 0 32px 32px; }}
  .skill-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }}
  .skill-tag {{ background: var(--bg3); border: 1px solid var(--border); color: var(--text-dim); padding: 4px 10px; border-radius: 20px; font-size: 11px; font-family: var(--mono); transition: all 0.2s; }}
  .skill-tag:hover {{ border-color: var(--accent); color: var(--accent); }}
  .flow-section {{ padding: 0 32px 32px; }}
  .synapse-flow {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 20px; text-align: center; }}
  .flow-chain {{ display: flex; align-items: center; justify-content: center; gap: 8px; font-family: var(--mono); font-size: 14px; flex-wrap: wrap; }}
  .flow-node {{ background: var(--bg3); border: 1px solid var(--border); padding: 6px 14px; border-radius: 8px; font-weight: 600; }}
  .flow-arrow {{ color: var(--text-dim); font-size: 18px; }}
  .footer {{ padding: 16px 32px; border-top: 1px solid var(--border); color: var(--text-dim); font-size: 11px; display: flex; justify-content: space-between; font-family: var(--mono); }}
  @keyframes fadeInDown {{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes pulse {{ 0%, 100% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} }}
  .brain-node {{ animation: fadeInDown 0.5s ease forwards; }}
  .stat-card {{ animation: fadeInDown 0.4s ease forwards; }}
  .live-dot {{ animation: pulse 1.5s ease infinite; }}
  @media (max-width: 768px) {{ .stats-grid {{ grid-template-columns: repeat(2, 1fr); }} .header {{ flex-direction: column; gap: 12px; align-items: flex-start; }} }}
</style>
</head>
<body>

<div class="header">
  <h1>🧠 Drewgent <span>Brain Dashboard</span></h1>
  <div class="header-right">
    <span class="updated-at">Updated: {now_str}</span>
    <button class="refresh-btn" onclick="location.reload()">⟳ Refresh</button>
    <span class="live-dot" style="color:#3fb950;font-size:12px;">● LIVE</span>
  </div>
</div>

<div class="stats-grid">
  {stats_html}
</div>

<div class="brain-section">
  <div class="section-title">Neuroarchitecture — Real-time Brain State</div>
  <div class="brain-container">
    <svg class="brain-svg" viewBox="0 0 560 460" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#21262d" stroke-width="0.5"/>
        </pattern>
        <radialGradient id="brainGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#43a047" stop-opacity="0.1"/>
          <stop offset="100%" stop-color="#43a047" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="560" height="460" fill="url(#grid)"/>
      <ellipse cx="280" cy="230" rx="200" ry="180" fill="url(#brainGlow)" opacity="0.3"/>
      {svg_conn_elements}
      {svg_node_elements}
      {spine_svg}
      <text x="280" y="30" text-anchor="middle" fill="#8b949e" font-size="11" font-family="monospace">
        P6 ────────────────────────────────────────────── P0
      </text>
    </svg>
  </div>
</div>

<div class="flow-section">
  <div class="section-title">Synapse Signal Flow</div>
  <div class="synapse-flow">
    <div class="flow-chain">
      <span class="flow-node" style="color:#fdd835">SENSORY</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#fdd835">P3 Thalamus</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#ab47bc">P1 Limbic</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#00acc1">P2 Hippo</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#43a047">P4 Cortex</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#1e88e5">P5 Temporal</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#eceff1">P6 Prefrontal</span>
      <span class="flow-arrow">→</span>
      <span class="flow-node" style="color:#3fb950">ACTION</span>
    </div>
    <div style="margin-top:10px;font-size:12px;color:#8b949e;font-family:monospace">
      P0 Brainstem: {len(layers.get("P0-brainstem", []))} rules (safety overrides all)
    </div>
  </div>
</div>

<div class="table-section">
  <div class="section-title">Layer Detail — All Neuron Rules</div>
  <table class="data-table">
    <thead>
      <tr><th>ID</th><th>Layer</th><th>Activity</th><th>Rules</th><th>Neuron Rules</th></tr>
    </thead>
    <tbody>
      {layer_rows}
    </tbody>
  </table>
</div>

<div class="skills-section">
  <div class="section-title">Skills Library — {skills_n} categories</div>
  <div class="skill-rows">
    {skill_rows}
  </div>
</div>

<div class="footer">
  <span>Drewgent Brain Dashboard v3 — Generated: {now_str}</span>
  <span>Auto-refresh: 5min · Brain Rules: {total_brain} · Growth: {f'+{growth}' if growth >= 0 else growth}</span>
</div>

<script>
  document.querySelectorAll('.stat-card').forEach((el, i) => {{ el.style.animationDelay = `${{i * 0.1}}s`; }});
  document.querySelectorAll('.brain-node').forEach((el, i) => {{ el.style.animationDelay = `${{i * 0.15}}s`; el.setAttribute('opacity', '1'); }});
  setTimeout(() => {{ location.reload(); }}, 5 * 60 * 1000);
</script>

</body>
</html>"""

    with open(OUT_HTML, "w") as f:
        f.write(html)

    print(f"✅ Brain Dashboard HTML generated: {OUT_HTML}")
    print(f"   Total: {total_brain} rules · {skills_n} skills · {know_n} knowledge · {sess_n} sessions")
    return str(OUT_HTML)

if __name__ == "__main__":
    generate()
