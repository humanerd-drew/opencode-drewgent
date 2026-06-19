#!/usr/bin/env python3
"""
agent_dashboard_push.py — Collect local agent status and push to Cloudflare dashboard.

Runs every 5 minutes via cron. Gathers:
  - System stats (uptime, load, disk, memory)
  - Launchd services (ai.drewgent.* + ai.hermes.*)
  - Kanban board
  - Cron jobs
  - Network services
  - Vault P-layer sizes
  - Recent sessions

Usage:
  python3 agent_dashboard_push.py [--dry-run] [--endpoint URL] [--secret TOKEN]
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

HOME = os.path.expanduser("~")
DREWGENT = os.path.join(HOME, ".drewgent")
HERMES = os.path.join(HOME, ".hermes")

# Ensure hermes CLI is findable when run from cron (no-agent mode)
_EXTRA_PATH = os.pathsep.join([
    os.path.join(HOME, ".local", "bin"),
    os.path.join(HOME, ".hermes", "hermes-agent", ".venv", "bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
])
_EXTRA_ENV = {"PATH": _EXTRA_PATH + os.pathsep + os.environ.get("PATH", "")}

# Defaults — override via env or CLI
ENDPOINT = os.environ.get("AGENT_DASHBOARD_URL", "https://agent-dashboard.humanerd-me.workers.dev")
PUSH_SECRET = os.environ.get("AGENT_DASHBOARD_SECRET", "")


def run(cmd, timeout=15):
    """Run a shell command, return (stdout, stderr, exit_code)."""
    try:
        env = {**_EXTRA_ENV, **os.environ}
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=True, env=env
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def collect_system():
    """Gather system-level stats."""
    out, _, _ = run("uptime")
    uptime = out.replace(",", "").strip() if out else "?"

    out, _, _ = run("sysctl -n vm.loadavg")
    load = out.strip() if out else "?"

    out, _, _ = run(r"df -h /System/Volumes/Data 2>/dev/null | tail -1")
    disk = out.split() if out else []
    disk_used = disk[2] if len(disk) > 2 else "?"
    disk_total = disk[1] if len(disk) > 1 else "?"
    disk_pct = disk[4] if len(disk) > 4 else "?"
    if disk_pct.endswith("%"):
        disk_pct = disk_pct[:-1]

    out, _, _ = run("vm_stat 2>/dev/null | head -10")
    mem_lines = out.split("\n") if out else []
    pages_active = "?"
    pages_free = "?"
    for line in mem_lines:
        if "Pages active" in line:
            pages_active = line.split(":")[-1].strip().rstrip(".")
        if "Pages free" in line:
            pages_free = line.split(":")[-1].strip().rstrip(".")

    out, _, _ = run("sw_vers -productVersion 2>/dev/null")
    os_version = out.strip() or "?"

    out, _, _ = run("uname -r")
    kernel = out.strip() or "?"

    out, _, _ = run("python3 --version 2>/dev/null")
    python = out.strip() or "?"

    out, _, _ = run(HERMES + "/hermes-agent/.venv/bin/python -c \"import hermes; print(hermes.__version__)\" 2>/dev/null || echo '?'")
    hermes_ver = out.strip() or "?"

    return {
        "uptime": uptime,
        "load": load,
        "disk_total": disk_total,
        "disk_used": disk_used,
        "disk_used_pct": disk_pct,
        "memory": f"active: {pages_active}, free: {pages_free}",
        "os_version": os_version,
        "kernel": kernel,
        "python": python,
        "hermes_version": hermes_ver,
    }


def collect_launchd():
    """Collect ai.drewgent.* and ai.hermes.* launchd services."""
    out, _, _ = run("launchctl list 2>/dev/null")
    services = []
    for line in (out.split("\n") if out else []):
        parts = line.strip().split()
        if len(parts) >= 3 and ("ai.drewgent." in parts[2] or "ai.hermes." in parts[2]):
            pid_str = parts[0]
            exit_str = parts[1]
            label = parts[2]
            try:
                pid = int(pid_str) if pid_str != "-" else -1
            except ValueError:
                pid = -1
            try:
                exit_code = int(exit_str) if exit_str != "-" else None
            except ValueError:
                exit_code = None
            services.append({
                "label": label,
                "pid": pid,
                "exit_code": exit_code,
            })
    return services


def collect_kanban():
    """Parse hermes kanban list output."""
    out, _, rc = run("hermes kanban list 2>/dev/null")
    tasks = []
    if out:
        for line in out.split("\n"):
            line = line.strip()
            if not line or "───" in line or "┌" in line or "└" in line or "│" in line or "─" in line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            # Parse status icon
            icon = parts[0]
            status_map = {"\u2298": "blocked", "\u25ef": "todo", "\u25b6": "ready",
                          "\u25cf": "running", "\u2713": "done", "\u25fc": "done"}
            status = status_map.get(icon, "?")

            if len(parts) >= 5:
                task_id = parts[1]
                assignee = parts[3]
                title = " ".join(parts[4:])
            elif len(parts) >= 4:
                task_id = parts[1]
                assignee = parts[3]
                title = ""
            elif len(parts) >= 2:
                task_id = parts[1]
                assignee = ""
                title = ""
            else:
                continue
            tasks.append({
                "id": task_id,
                "title": title,
                "status": status,
                "assignee": assignee,
            })

    blocked = sum(1 for t in tasks if t["status"] == "blocked")
    ready = sum(1 for t in tasks if t["status"] == "ready")
    todo_count = sum(1 for t in tasks if t["status"] == "todo")
    running = sum(1 for t in tasks if t["status"] == "running")

    return {
        "total": len(tasks),
        "blocked": blocked,
        "ready": ready,
        "todo": todo_count,
        "running": running,
        "tasks": tasks,
    }


def collect_cron():
    """Parse hermes cron list output — handles the box-drawing format."""
    out, _, _ = run("hermes cron list 2>/dev/null")
    active = []
    errors = []
    paused = []

    if not out:
        return {"active": [], "errors": [], "paused": []}

    lines = out.split("\n")
    current = None

    for line in lines:
        raw = line
        stripped = line.strip()

        # Skip decorative lines
        if not stripped or stripped.startswith("\u2500") or stripped.startswith("\u250c") or \
           stripped.startswith("\u2514") or stripped.startswith("\u2502"):
            continue

        # Detect job header: "  <job_id> [state]"
        if stripped.endswith("]") and "[" in stripped:
            # Save previous job
            if current:
                _cron_classify(current, active, errors, paused)

            bracket_idx = stripped.index("[")
            jid = stripped[:bracket_idx].strip()
            state = stripped[bracket_idx + 1:-1]
            current = {
                "job_id": jid,
                "state": state,
                "name": "",
                "schedule": "",
                "last_status": "",
                "last_run_at": "",
            }
            continue

        # Parse key-value pairs
        if current and ":" in stripped:
            colon_idx = stripped.index(":")
            key = stripped[:colon_idx].strip().lower().replace(" ", "_")
            val = stripped[colon_idx + 1:].strip()

            if key == "name":
                current["name"] = val
            elif key == "schedule":
                current["schedule"] = val
            elif key == "last_run":
                # "Last run" line: "2026-06-15T12:00:54.446657+09:00  ok"
                # or "2026-06-15T09:00:17.912653+09:00  error: Script exit 1"
                parts = val.split()
                if parts:
                    current["last_run_at"] = parts[0]
                if len(parts) >= 2:
                    full_status = parts[1]
                    if full_status == "ok":
                        current["last_status"] = "ok"
                    elif full_status.startswith("error"):
                        current["last_status"] = "error"
                    else:
                        current["last_status"] = full_status

    # Save last job
    if current:
        _cron_classify(current, active, errors, paused)

    return {
        "active": active,
        "errors": errors,
        "paused": paused,
    }


def _cron_classify(job, active, errors, paused):
    """Sort a parsed cron job into the right list."""
    last_status = job.get("last_status", "")
    state = job.get("state", "active")

    if last_status == "error":
        errors.append(job)
    elif state == "paused":
        paused.append(job)
    else:
        active.append(job)


def collect_network():
    """Collect listening ports for known services."""
    out, _, _ = run(
        r"lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | awk 'NR>1{print $1, $9}' | sort -u"
    )
    known_services = {
        "8642": "Hermes Gateway",
        "8765": "Kanban Dashboard",
        "11434": "Ollama",
        "8787": "Workerd (CF Workers)",
        "9229": "Workerd (Debug)",
        "3307": "SSH Tunnel (Lima DB)",
        "8080": "SSH Tunnel (Lima Web)",
        "5000": "AirPlay",
        "7000": "AirPlay",
    }
    listening = set()
    if out:
        for line in out.split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                port = parts[-1].split(":")[-1]
                listening.add(port)

    result = []
    for port, name in sorted(known_services.items()):
        result.append({
            "service": name,
            "port": port,
            "status": "listening" if port in listening else "down",
        })
    return result


def collect_git_status():
    """Check git status of the drewgent vault."""
    out, _, _ = run("cd " + DREWGENT + " && git status --porcelain 2>/dev/null | wc -l", timeout=5)
    uncommitted = out.strip()
    out, _, _ = run("cd " + DREWGENT + " && git log @{u}..HEAD 2>/dev/null | wc -l", timeout=5)
    unpushed = out.strip()
    return {
        "uncommitted_files": int(uncommitted) if uncommitted and uncommitted.isdigit() else 0,
        "unpushed_commits": int(unpushed) if unpushed and unpushed.isdigit() else 0,
    }


def collect_brew_updates():
    """Count outdated brew packages."""
    out, _, _ = run("brew outdated 2>/dev/null | wc -l", timeout=15)
    count = out.strip()
    return int(count) if count and count.isdigit() else "?"


def collect_docker():
    """List running docker containers summary."""
    out, _, rc = run("docker ps --format '{{.Names}}|{{.Status}}' 2>/dev/null", timeout=10)
    containers = []
    if out:
        for line in out.split("\n"):
            if "|" in line:
                name, status = line.split("|", 1)
                containers.append({"name": name.strip(), "status": status.strip()})
    return containers


def collect_thermal():
    """Check thermal/power state."""
    out, _, _ = run("pmset -g therm 2>/dev/null | head -5", timeout=5)
    thermal = out.strip() if out else "?"
    out2, _, _ = run("pmset -g batt 2>/dev/null | head -3", timeout=5)
    battery = out2.strip() if out2 else "?"
    return {
        "thermal": thermal,
        "battery": battery,
    }


def collect_graph():
    """Scan vault markdown files and extract wikilink graph.
    Returns {nodes: [{id, label, layer}], edges: [{source, target}]}
    Skips P2-hippocampus (too large) and binary/DB files.
    """
    import glob
    import re

    layers_to_scan = [
        ("", "root"),  # top-level .md files
        ("P0-brainstem", "P0"),
        ("P1-limbic", "P1"),
        ("P3-sensors", "P3"),
        ("P4-cortex", "P4"),
        ("P5-ego", "P5"),
        ("P6-prefrontal", "P6"),
        ("skills", "skill"),
    ]

    wiki_re = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
    frontmatter_title_re = re.compile(r'^---\s*\n.*?^title:\s*(.+)\s*$.*?\n---', re.MULTILINE | re.DOTALL)

    nodes = {}
    edges_raw = []

    MAX_NODES = 300
    MAX_FILE_SIZE = 100 * 1024  # 100KB

    for subdir, layer_tag in layers_to_scan:
        scan_dir = os.path.join(DREWGENT, subdir) if subdir else DREWGENT
        if not os.path.isdir(scan_dir):
            continue

        # Get .md files (recursive for most, but limit depth)
        if subdir == "skills":
            pattern = "**/SKILL.md"
        else:
            pattern = "**/*.md"
        md_files = glob.glob(os.path.join(scan_dir, pattern), recursive=True)

        # Limit per layer to avoid explosion
        layer_count = 0
        for fpath in md_files:
            rel = os.path.relpath(fpath, DREWGENT)
            # Skip hidden dirs, node_modules, .trash, P2
            if any(p in rel for p in ("/.", "/node_modules/", ".trash", "P2-hippocampus",
                                       "__pycache__", ".git/", "venv/", ".venv/")):
                continue

            if len(nodes) >= MAX_NODES:
                break
            if layer_count >= 60:
                break

            # Skip large files
            try:
                if os.path.getsize(fpath) > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(30000)  # read first 30KB for links
            except Exception:
                continue

            # Title from frontmatter or filename
            title_match = frontmatter_title_re.search(content)
            if title_match:
                label = title_match.group(1).strip()
            else:
                basename = os.path.basename(fpath)
                label = basename.replace(".md", "").replace("-", " ").title()

            node_id = rel.replace(".md", "").replace("/", ":")
            node = {
                "id": node_id,
                "label": label[:40],
                "layer": layer_tag,
                "links": [],
            }

            # Extract wikilinks
            links = wiki_re.findall(content)
            for link in links[:20]:  # max 20 links per file
                node["links"].append(link.strip())

            nodes[node_id] = node
            layer_count += 1

    # Build edges (resolve wikilinks to node ids)
    # Create a lookup: normalized filename -> node id
    lookup = {}
    for nid, nd in nodes.items():
        # Add by full path
        lookup[nd["label"].lower()] = nid
        # Add by filename stem
        stem = nid.split(":")[-1].lower()
        lookup[stem] = nid
        # Add by short path
        short = nid.replace(":", "/").lower()
        lookup[short] = nid

    edges = []
    seen_edges = set()
    for src_id, nd in nodes.items():
        for target_label in nd.get("links", []):
            norm = target_label.lower().strip()
            # Direct lookup
            matched = lookup.get(norm) or lookup.get(norm.replace(" ", "-")) or \
                      lookup.get(norm.replace(" ", "_"))
            if not matched:
                # Fuzzy: find any node whose label or id contains the target
                for nid2, nd2 in nodes.items():
                    if norm in nd2["label"].lower() or norm in nid2.lower():
                        matched = nid2
                        break
            if matched and matched != src_id:
                edge_key = src_id + "->" + matched if src_id < matched else matched + "->" + src_id
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({"source": src_id, "target": matched})

    # Build minimal node list (only nodes that are in edges, plus their layer info)
    connected = set()
    for e in edges:
        connected.add(e["source"])
        connected.add(e["target"])

    node_list = []
    for nid, nd in nodes.items():
        if nid in connected or len(connected) < 50:
            node_list.append({"id": nid, "label": nd["label"], "layer": nd["layer"]})

    return {
        "nodes": node_list,
        "edges": edges,
        "stats": {
            "total_files_scanned": len(nodes),
            "connected_nodes": len(node_list),
            "edges_count": len(edges),
        },
    }


def collect_recent_errors():
    """Parse last 24h of agent log for ERROR/WARNING lines.
    Returns grouped by error type with counts."""
    log_paths = [
        os.path.join(DREWGENT, "logs", "errors.log"),
        os.path.join(DREWGENT, "logs", "agent.log"),
    ]
    import re
    from collections import Counter

    error_types = Counter()
    error_samples = {}  # type -> {time, level, message}
    error_pat = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?"
        r"(ERROR|WARNING|CRITICAL).*?"
        r"(?:summary=|error=)([^\n]+)",
        re.DOTALL,
    )

    for log_path in log_paths:
        if not os.path.isfile(log_path):
            continue
        try:
            with open(log_path, "r", errors="ignore") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 200 * 1024))
                content = f.read()
        except Exception:
            continue

        for match in error_pat.finditer(content):
            ts = match.group(1)
            level = match.group(2)
            msg = match.group(3).strip()[:120]
            # Normalize for grouping: strip session IDs and timestamps
            group_key = msg[:60]
            error_types[group_key] += 1
            if group_key not in error_samples:
                error_samples[group_key] = {"time": ts, "level": level, "message": msg}

    # Return top 5 error types with counts
    result = []
    for key, count in error_types.most_common(5):
        sample = error_samples[key]
        result.append({
            "time": sample["time"],
            "level": sample["level"],
            "message": sample["message"],
            "count": count,
        })
    return result


def compute_health_status(system, services, cron_data, errors):
    """Aggregate health: returns {level, critical, warning, info, message}."""
    critical = 0
    warning = 0
    info = 0
    issues = []

    try:
        dp = int(system.get("disk_used_pct", 0) or 0)
        if dp > 85:
            critical += 1
            issues.append("disk >85%")
        elif dp > 65:
            warning += 1
            issues.append(f"disk {dp}%")
    except (ValueError, TypeError):
        pass

    if cron_data.get("errors"):
        warning += len(cron_data["errors"])
        issues.append(f"{len(cron_data['errors'])} cron errors")

    if errors:
        critical_errors = [e for e in errors if e["level"] == "CRITICAL"]
        warning_errors = [e for e in errors if e["level"] in ("ERROR", "WARNING")]
        critical += len(critical_errors)
        warning += len(warning_errors)

    if critical > 0:
        level = "critical"
    elif warning > 0:
        level = "warning"
    else:
        level = "healthy"

    return {
        "level": level,
        "critical": critical,
        "warning": warning,
        "issues": issues[:3],
    }


def collect_vault():
    """Check sizes of P-layer directories."""
    layers = [
        ("P0-brainstem", "Rules, neurons"),
        ("P1-limbic", "Persona, voice"),
        ("P2-hippocampus", "Memory, knowledge"),
        ("P3-sensors", "Tools, gateway"),
        ("P4-cortex", "Skills, growth"),
        ("P5-ego", "Self-model, config"),
        ("P6-prefrontal", "Incidents, retro"),
    ]
    result = []
    total_human = "?"
    total_bytes = 0
    for dirname, desc in layers:
        path = os.path.join(DREWGENT, dirname)
        if os.path.isdir(path):
            out, _, _ = run(f"du -sh '{path}' 2>/dev/null | cut -f1")
            size = out.strip() if out else "?"
            result.append({"name": dirname, "size": size, "desc": desc})
            # Parse size bytes
            out2, _, _ = run(f"du -s '{path}' 2>/dev/null | cut -f1")
            if out2:
                try:
                    total_bytes += int(out2.strip()) * 512
                except ValueError:
                    pass

    # Human-readable total
    if total_bytes > 0:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if total_bytes < 1024:
                total_human = f"{total_bytes:.0f}{unit}"
                break
            total_bytes /= 1024
        else:
            total_human = f"{total_bytes:.1f}TB"

    result.append({"name": "Total", "size": total_human, "desc": ""})
    return result


def collect_sessions():
    """Get recent session info from session_search equivalent."""
    out, _, _ = run("hermes sessions list --limit 3 2>/dev/null")
    sessions = []
    if out:
        for line in out.split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3:
                sessions.append({
                    "id": parts[0] if len(parts) > 0 else "",
                    "source": parts[1] if len(parts) > 1 else "",
                    "message_count": parts[2] if len(parts) > 2 else "",
                    "preview": " ".join(parts[3:]) if len(parts) > 3 else "",
                })
    return sessions


def collect_timeline(cron_data, sessions, recent_errors):
    """Build a unified activity timeline from cron runs, sessions, errors."""
    events = []

    # Cron jobs: last_run_at → event
    for j in cron_data.get("active", []) + cron_data.get("errors", []):
        ts = j.get("last_run_at", "")
        if ts and len(ts) >= 19:
            try:
                t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
                status = j.get("last_status", "")
                icon = "&#9200;"
                msg = j.get("name", "") + (" done" if status == "ok" else " error" if status == "error" else "")
                events.append({"time": int(t), "icon": icon, "msg": msg, "type": "cron"})
            except (ValueError, OSError):
                pass

    # Sessions
    for ses in sessions[:5]:
        # session objects from hermes sessions list don't have timestamps easily
        # Use time ordering from the list (most recent first)
        pass

    # Errors
    for err in recent_errors:
        try:
            t = time.mktime(time.strptime(err.get("time", "")[:19], "%Y-%m-%d %H:%M:%S"))
            events.append({"time": int(t), "icon": "&#128308;", "msg": err.get("message", "")[:60], "type": "error"})
        except (ValueError, OSError, IndexError):
            pass

    # Deduplicate and sort by time descending
    seen = set()
    deduped = []
    for e in sorted(events, key=lambda x: x["time"], reverse=True):
        key = e["msg"][:40]
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return deduped[:12]  # max 12 events


def collect_daily_usage():
    """Count activity from agent log for multiple time windows."""
    today = time.strftime("%Y-%m-%d")
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    week_ago = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7 * 86400))
    month_ago = time.strftime("%Y-%m-%d", time.localtime(time.time() - 30 * 86400))

    # grep is expensive for month; use head/tail approach
    log = os.path.join(DREWGENT, "logs", "agent.log")
    total = "?"
    try:
        out, _, _ = run("wc -l < " + log + " 2>/dev/null || echo 0", timeout=5)
        total = int(out.strip()) if out.strip().isdigit() else "?"
    except:
        pass

    def count_date(date_str):
        out, _, _ = run("grep -c '" + date_str + "' " + log + " 2>/dev/null || echo 0", timeout=5)
        return int(out.strip()) if out.strip().isdigit() else 0

    # Last 5 hours
    out5, _, _ = run(
        "awk -v d=\"$(date -v-5H '+%Y-%m-%d %H:')\" '$0 ~ d {c++} END {print c+0}' " + log + " 2>/dev/null || echo 0",
        timeout=10,
    )
    hours5 = int(out5.strip()) if out5.strip().isdigit() else 0

    today_n = count_date(today)
    yesterday_n = count_date(yesterday)
    week_n = 0
    month_n = 0

    # Week and month via iterating dates (efficient enough)
    import subprocess
    try:
        r = subprocess.run(
            "awk '{d=substr($0,1,10); if(d>=\"" + week_ago + "\") c++} END {print c+0}' " + log,
            capture_output=True, text=True, timeout=10, shell=True,
            env={**_EXTRA_ENV, **os.environ},
        )
        week_n = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except:
        week_n = today_n + yesterday_n  # fallback

    try:
        r = subprocess.run(
            "awk '{d=substr($0,1,10); if(d>=\"" + month_ago + "\") c++} END {print c+0}' " + log,
            capture_output=True, text=True, timeout=15, shell=True,
            env={**_EXTRA_ENV, **os.environ},
        )
        month_n = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except:
        month_n = week_n  # fallback

    # Daily average (over last 7 days)
    daily_avg = round(week_n / 7) if week_n else 0
    change_pct = 0
    if yesterday_n > 0 and today_n > 0:
        change_pct = round((today_n - yesterday_n) / yesterday_n * 100)

    return {
        "hours5": hours5,
        "today": today_n,
        "yesterday": yesterday_n,
        "this_week": week_n,
        "this_month": month_n,
        "daily_avg": daily_avg,
        "change_pct": change_pct,
        "total_log_lines": total,
        "provider": "opencode-go",
        "plan": "Subscription",
    }


def collect_model_usage():
    """Parse agent log for per-model usage stats."""
    log = os.path.join(DREWGENT, "logs", "agent.log")
    if not os.path.isfile(log):
        return {"models": [], "total_calls": 0}

    import re
    from collections import defaultdict

    model_counts = defaultdict(int)
    model_tokens = defaultdict(lambda: {"in": 0, "out": 0, "total": 0})
    model_providers = defaultdict(set)
    total_calls = 0

    # Read last 1MB for recent data
    try:
        with open(log, "r", errors="ignore") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 1024 * 1024))
            content = f.read()
    except Exception:
        return {"models": [], "total_calls": 0}

    # Count model appearances in API calls
    for m in re.finditer(r'model=(\S+)', content):
        model_name = m.group(1).strip()
        if model_name and '/' in model_name:
            model_name = model_name.split('/')[-1]  # strip provider prefix
        if model_name:
            model_counts[model_name] += 1
            total_calls += 1

    # Extract token data from API call lines
    for m in re.finditer(
        r'model=(\S+).*?in=(\d+)\s+out=(\d+)\s+total=(\d+)',
        content,
    ):
        model_name = m.group(1).strip()
        if '/' in model_name:
            model_name = model_name.split('/')[-1]
        try:
            model_tokens[model_name]["in"] += int(m.group(2))
            model_tokens[model_name]["out"] += int(m.group(3))
            model_tokens[model_name]["total"] += int(m.group(4))
        except ValueError:
            pass

    # Extract provider info
    for m in re.finditer(r'model=(\S+)\s+provider=(\S+)', content):
        model_name = m.group(1).strip()
        if '/' in model_name:
            model_name = model_name.split('/')[-1]
        model_providers[model_name].add(m.group(2).strip())

    models = []
    for name, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        tk = model_tokens.get(name, {"in": 0, "out": 0, "total": 0})
        providers = list(model_providers.get(name, []))
        models.append({
            "name": name,
            "calls": count,
            "tokens_in": tk["in"],
            "tokens_out": tk["out"],
            "tokens_total": tk["total"],
            "providers": providers,
        })

    return {"models": models, "total_calls": total_calls}


def collect_cpu_details():
    """Get CPU model, cores, architecture."""
    out, _, _ = run("sysctl -n machdep.cpu.brand_string 2>/dev/null || echo ?")
    brand = out.strip() or "?"
    out2, _, _ = run("sysctl -n hw.ncpu 2>/dev/null || echo 0")
    cores = out2.strip() or "0"
    out3, _, _ = run("uname -m 2>/dev/null || echo ?")
    arch = out3.strip() or "?"
    out4, _, _ = run("sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1073741824\"GB\"}' || echo ?")
    total_ram = out4.strip() or "?"
    return {"brand": brand, "cores": cores, "arch": arch, "total_ram": total_ram}


def collect_skill_categories():
    """Count skills per category (handles nested skill dirs)."""
    import glob
    cats = {}
    for fpath in glob.glob(os.path.join(DREWGENT, "skills", "**", "SKILL.md"), recursive=True):
        rel = os.path.relpath(fpath, os.path.join(DREWGENT, "skills"))
        parts = rel.split(os.sep)
        # parts = [category, skill-name, SKILL.md]  or  [skill-name, SKILL.md]
        cat = parts[0] if len(parts) >= 2 else "other"
        cats[cat] = cats.get(cat, 0) + 1

    result = [{"category": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])]
    return {"categories": result, "total": sum(cats.values())}


def collect_hourly_usage():
    """Count log lines per hour for today."""
    today = time.strftime("%Y-%m-%d")
    log = os.path.join(DREWGENT, "logs", "agent.log")
    hours = []
    for h in range(24):
        pattern = today + " " + f"{h:02d}"
        out, _, _ = run("grep -c '" + pattern + "' " + log + " 2>/dev/null || echo 0", timeout=3)
        count = int(out.strip()) if out.strip().isdigit() else 0
        hours.append({"hour": h, "count": count})
    return hours


def collect_session_details():
    """Count log lines per session from recent log."""
    log = os.path.join(DREWGENT, "logs", "agent.log")
    import re
    sessions = {}
    try:
        with open(log, "r", errors="ignore") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 500 * 1024))
            content = f.read()
    except Exception:
        return []

    for m in re.finditer(r'\[(20[0-9]{6}_[0-9]{6}_[a-f0-9]+)\]', content):
        sid = m.group(1)
        sessions[sid] = sessions.get(sid, 0) + 1

    result = [{"id": k, "lines": v} for k, v in sorted(sessions.items(), key=lambda x: -x[1])]
    return result[:10]


def collect_provider_usage():
    """Count provider distribution from log."""
    log = os.path.join(DREWGENT, "logs", "agent.log")
    import re
    providers = {}
    try:
        with open(log, "r", errors="ignore") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 500 * 1024))
            content = f.read()
    except Exception:
        return []

    for m in re.finditer(r'provider=(\S+)', content):
        p = m.group(1).strip()
        if p == 'openrouter':
            continue
        providers[p] = providers.get(p, 0) + 1
    return [{"provider": k, "count": v} for k, v in sorted(providers.items(), key=lambda x: -x[1])]


def collect_weekly_trend():
    """Log lines per day for last 7 days."""
    log = os.path.join(DREWGENT, "logs", "agent.log")
    days = []
    import subprocess
    for i in range(7):
        d = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
        out, _, _ = run("grep -c '" + d + "' " + log + " 2>/dev/null || echo 0", timeout=5)
        count = int(out.strip()) if out.strip().isdigit() else 0
        days.append({"date": d, "count": count})
    return list(reversed(days))


def collect_live_activity():
    """Tail agent.log for recent activity events, return last 20 structured events."""
    log = os.path.join(DREWGENT, "logs", "agent.log")
    if not os.path.isfile(log):
        return {"events": [], "active_session": "", "elapsed": 0}

    import re
    from collections import OrderedDict

    try:
        with open(log, "r", errors="ignore") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 150 * 1024))
            content = f.read()
    except Exception:
        return {"events": [], "active_session": "", "elapsed": 0}

    lines = content.split("\n")[-80:]  # last 80 lines
    events = []
    active_session = ""
    last_time = 0

    for line in reversed(lines):
        if not line.strip():
            continue

        # Parse timestamp
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        if not ts_match:
            continue
        ts = ts_match.group(1)
        try:
            t = int(time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S")))
        except (ValueError, OSError):
            continue
        if not last_time:
            last_time = t

        # Extract session ID
        session_match = re.search(r"\[([^\]]+)\]", line)
        session_id = session_match.group(1) if session_match else ""
        if session_id and len(session_id) > 10 and "_" in session_id:
            if not active_session:
                active_session = session_id

        # Categorize
        ev = {"time": ts[11:19], "ts_unix": t, "session": session_id}

        if "msg='" in line:
            m = line.split("msg='")[-1].rstrip("'")
            ev["icon"] = "&#128172;"
            ev["text"] = m[:80]
            ev["type"] = "msg"
        elif "Streaming failed" in line or "HTTP 400" in line:
            ev["icon"] = "&#10071;"
            ev["text"] = "API failed, falling back"
            ev["type"] = "error"
        elif "Fallback activated" in line:
            ev["icon"] = "&#128257;"
            ev["text"] = "Fallback: " + (line.split("Fallback activated:")[-1].strip() if "Fallback activated" in line else "")
            ev["type"] = "fallback"
        elif "tool_executor:" in line and "completed" in line:
            tool_match = re.search(r"tool (\S+) completed", line)
            tool_name = tool_match.group(1) if tool_match else ""
            ev["icon"] = "&#9889;"
            ev["text"] = "Tool: " + tool_name
            ev["type"] = "tool"
        elif "tool_executor:" in line and "error" in line:
            ev["icon"] = "&#10071;"
            ev["text"] = "Tool error: " + (line.split("error")[-1].strip()[:50] if "error" in line else "")
            ev["type"] = "tool_error"
        elif "API call #" in line:
            model_match = re.search(r"model=(\S+)", line)
            m_name = model_match.group(1) if model_match else ""
            dur_match = re.search(r"latency=([\d.]+)s", line)
            dur = dur_match.group(1) if dur_match else ""
            ev["icon"] = "&#129302;"
            ev["text"] = "API: " + m_name + (f" ({dur}s)" if dur else "")
            ev["type"] = "api"
        elif "terminal" in line and "environment ready" in line:
            ev["icon"] = "&#9000;"
            ev["text"] = "Terminal ready"
            ev["type"] = "terminal"
        elif "restore_primary" in line:
            ev["icon"] = "&#128259;"
            ev["text"] = "Session resumed"
            ev["type"] = "session"
        elif "pruning oldest" in line and "checkpoint" in line:
            ev["icon"] = "&#128200;"
            ev["text"] = "Checkpoint cleanup"
            ev["type"] = "sys"
        elif "Checkpoint store" in line:
            ev["icon"] = "&#128200;"
            m = re.search(r"exceeded\s+([\d.]+\s*MB)", line)
            ev["text"] = "Checkpoint: " + (m.group(1) if m else "cleanup")
            ev["type"] = "sys"
        elif "restore_primary" in line:
            ev["icon"] = "&#128259;"
            ev["text"] = "Session resumed"
            ev["type"] = "session"
        elif "conversation turn" in line:
            ev["icon"] = "&#128172;"
            ev["text"] = "Turn started"
            ev["type"] = "turn"
        elif "stream_request_complete" in line:
            ev["icon"] = "&#9989;"
            ev["text"] = "Response done"
            ev["type"] = "done"
        else:
            continue

        events.append(ev)
        if len(events) >= 15:
            break

    # Collect all unique session IDs
    sessions_list = []
    for m in re.finditer(r'\[(20[0-9]{6}_[0-9]{6}_[a-f0-9]+)\]', content):
        sid = m.group(1)
        if sid not in sessions_list:
            sessions_list.append(sid)
            if len(sessions_list) >= 8:
                break

    elapsed = 0
    if last_time > 0:
        elapsed = int(time.time() - last_time)

    return {
        "events": events,
        "active_session": active_session,
        "sessions": sessions_list,
        "elapsed": elapsed,
    }


def collect_brain_health():
    """Count brain assets: skills, neuron rules, memory entries."""
    import glob
    skills = len(glob.glob(os.path.join(DREWGENT, "skills", "**", "SKILL.md"), recursive=True))
    neurons = len(glob.glob(os.path.join(DREWGENT, "**", "*.neuron"), recursive=True))
    memories = 0
    mem_dir = os.path.join(DREWGENT, "P2-hippocampus", "memories")
    if os.path.isdir(mem_dir):
        memories = len([d for d in os.listdir(mem_dir) if os.path.isdir(os.path.join(mem_dir, d))])
    return {
        "skills": skills,
        "neurons": neurons,
        "memories": memories,
        "total": skills + neurons + memories,
    }


def collect_today_summary():
    """Count today's activity from the agent log."""
    today = time.strftime("%Y-%m-%d")
    log = os.path.join(DREWGENT, "logs", "agent.log")
    if not os.path.isfile(log):
        return {"messages": 0, "sessions": 0, "tool_calls": 0}

    # Count log lines for today
    out, _, _ = run("grep -c '" + today + "' " + log + " 2>/dev/null || echo 0", timeout=5)
    today_lines = int(out.strip()) if out.strip().isdigit() else 0

    # Count unique sessions
    out2, _, _ = run(
        "grep '" + today + "' " + log + " | grep -oP '\\[\\K[^]]+' | grep -E '^20[0-9]{8}_[0-9]{6}_[a-f0-9]+' | sort -u | wc -l 2>/dev/null || echo 0",
        timeout=10,
    )
    sessions = int(out2.strip()) if out2.strip().isdigit() else 0

    # Count tool calls
    out3, _, _ = run(
        "grep -c 'tool_call\\|Tool.*executor\\|tool=' " + log + " 2>/dev/null || echo 0",
        timeout=5,
    )
    tool_calls = int(out3.strip()) if out3.strip().isdigit() else 0

    return {
        "log_lines": today_lines,
        "sessions": sessions,
        "tool_calls": tool_calls,
    }


def collect_alerts(system, services, cron_data):
    """Generate alert items based on collected data."""
    alerts = []

    # Disk
    try:
        dp = int(system.get("disk_used_pct", 0) or 0)
        if dp > 80:
            alerts.append({"severity": "error", "message": f"Disk at {dp}% — running low on space"})
        elif dp > 65:
            alerts.append({"severity": "warn", "message": f"Disk at {dp}% — consider cleanup"})
    except (ValueError, TypeError):
        pass

    # Gateway watchdog — check the cron job, not the launchd service
    # launchd service is OnDemand (exits immediately), actual watchdog is
    # the "Drewgent launchd watchdog" cron job running every 5m
    watchdog_cron = [j for j in cron_data.get("active", [])
                     if "launchd watchdog" in j.get("name", "").lower()]
    watchdog_errors = [j for j in cron_data.get("errors", [])
                       if "launchd watchdog" in j.get("name", "").lower()]
    if watchdog_errors:
        alerts.append({
            "severity": "error",
            "message": "Gateway watchdog cron job in error state"
        })
    elif not watchdog_cron and not watchdog_errors:
        alerts.append({
            "severity": "warn",
            "message": "Gateway watchdog cron job not found"
        })

    # Error cron jobs (excluding watchdog itself to avoid double-reporting)
    other_errors = [j for j in cron_data.get("errors", [])
                    if "launchd watchdog" not in j.get("name", "").lower()]
    if other_errors:
        names = ", ".join(j.get("name", "?")[:30] for j in other_errors)
        alerts.append({
            "severity": "warn",
            "message": f"{len(other_errors)} cron job(s) in error state: {names}"
        })

    return alerts


def push(data, endpoint, secret):
    """POST JSON data to the dashboard endpoint."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        endpoint + "/api/push",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        method="POST",
    )
    if secret:
        req.add_header("Authorization", f"Bearer {secret}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    dry_run = "--dry-run" in sys.argv
    for flag in ("--endpoint", "--secret"):
        if flag in sys.argv:
            idx = sys.argv.index(flag)
            if idx + 1 < len(sys.argv):
                val = sys.argv[idx + 1]
                if flag == "--endpoint":
                    global ENDPOINT
                    ENDPOINT = val
                elif flag == "--secret":
                    global PUSH_SECRET
                    PUSH_SECRET = val

    ts = time.strftime("%Y-%m-%d %H:%M:%S KST", time.localtime())
    print(f"[{ts}] Collecting agent status...")

    system = collect_system()
    print(f"  System: OK (load={system['load']}, disk={system['disk_used_pct']}%)")

    launchd = collect_launchd()
    running = sum(1 for s in launchd if s["pid"] > 0)
    print(f"  Launchd: {len(launchd)} services ({running} running)")

    kanban = collect_kanban()
    print(f"  Kanban: {kanban['total']} tasks ({kanban['blocked']} blocked, {kanban['ready']} ready)")

    cron = collect_cron()
    print(f"  Cron: {len(cron['active'])} active, {len(cron['errors'])} errors, {len(cron['paused'])} paused")

    network = collect_network()
    listening = sum(1 for s in network if s["status"] == "listening")
    print(f"  Network: {listening}/{len(network)} services listening")

    vault = collect_vault()
    print(f"  Vault: {vault[-1]['size']} total across {len(vault)-1} P-layers")

    sessions = collect_sessions()
    print(f"  Sessions: {len(sessions)} recent")

    alerts = collect_alerts(system, launchd, cron)
    if alerts:
        print(f"  Alerts: {len(alerts)} ({', '.join(a['message'][:40] for a in alerts)})")

    git = collect_git_status()
    print(f"  Git: {git['uncommitted_files']} uncommitted, {git['unpushed_commits']} unpushed")

    brew = collect_brew_updates()
    print(f"  Brew: {brew} outdated")

    docker = collect_docker()
    print(f"  Docker: {len(docker)} containers")

    thermal = collect_thermal()
    print(f"  Thermal: {thermal['thermal'][:50] if thermal['thermal'] else '?'}")

    print("  Scanning vault wikilink graph...", end=" ", flush=True)
    graph = collect_graph()
    print(f"{graph['stats']['connected_nodes']} nodes, {graph['stats']['edges_count']} edges")

    recent_errors = collect_recent_errors()
    print(f"  Recent errors: {len(recent_errors)} found")

    usage = collect_daily_usage()
    print(f"  Usage: {usage['today']} today, {usage['yesterday']} yesterday")

    model_usage = collect_model_usage()
    models_str = ", ".join(f"{m['name']}: {m['calls']}" for m in model_usage.get("models", []))
    print(f"  Models: {models_str}")

    brain = collect_brain_health()
    print(f"  Brain: {brain['skills']} skills, {brain['neurons']} neurons, {brain['memories']} memories")

    today_summary = collect_today_summary()
    print(f"  Today: {today_summary['log_lines']} lines, {today_summary['sessions']} sessions")

    timeline = collect_timeline(cron, sessions, recent_errors)
    print(f"  Timeline: {len(timeline)} events")

    live = collect_live_activity()
    events_str = ", ".join(e["type"] for e in live.get("events", [])[:3])
    print(f"  Live: {len(live['events'])} events ({events_str}) - active: {live['active_session'][:16] or 'none'} - {live['elapsed']}s ago")

    cpu_details = collect_cpu_details()
    print(f"  CPU: {cpu_details['brand']} ({cpu_details['cores']} cores)")

    skill_cats = collect_skill_categories()
    print(f"  Skills: {skill_cats['total']} across {len(skill_cats['categories'])} categories")

    hourly = collect_hourly_usage()
    active_hours = sum(1 for h in hourly if h["count"] > 0)
    print(f"  Hourly: {active_hours} active hours today")

    sess_details = collect_session_details()
    print(f"  Sessions details: {len(sess_details)} found")

    prov_usage = collect_provider_usage()
    prov_str = ", ".join(f"{p['provider']}: {p['count']}" for p in prov_usage)
    print(f"  Providers: {prov_str}")

    weekly = collect_weekly_trend()
    active_days = sum(1 for d in weekly if d["count"] > 0)
    print(f"  Weekly: {active_days} active days")

    health = compute_health_status(system, launchd, cron, recent_errors)
    print(f"  Health: {health['level']} ({health['critical']} critical, {health['warning']} warning)")

    payload = {
        "pushed_at": ts,
        "system": system,
        "launchd": launchd,
        "kanban": kanban,
        "cron": cron,
        "network": network,
        "vault": vault,
        "sessions": sessions,
        "alerts": alerts,
        "git": git,
        "brew": brew,
        "docker": docker,
        "thermal": thermal,
        "graph": graph,
        "recent_errors": recent_errors,
        "health": health,
        "usage": usage,
        "model_usage": model_usage,
        "cpu_details": cpu_details,
        "skill_categories": skill_cats,
        "hourly": hourly,
        "session_details": sess_details,
        "provider_usage": prov_usage,
        "weekly": weekly,
        "brain": brain,
        "today": today_summary,
        "timeline": timeline,
        "live": live,
    }

    if dry_run:
        print(f"\n[Dry run] Payload ({len(json.dumps(payload))} bytes):")
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:2000])
        print("... (truncated)")
        return

    print(f"\n  Pushing to {ENDPOINT}/api/push...")
    result = push(payload, ENDPOINT, PUSH_SECRET)

    if result.get("ok"):
        print(f"  Done! pushed_at={result.get('pushed_at', '?')}")
    else:
        print(f"  FAILED: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
