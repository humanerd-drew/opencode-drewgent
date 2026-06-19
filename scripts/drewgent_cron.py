#!/usr/bin/env python3
"""
drewgent_cron.py — Drewgent cron dispatcher.
Replaces n8n cron scheduling. Runs every 60s via launchd.
"""
import os, time, subprocess, json
from pathlib import Path

HOME = os.path.expanduser("~")
DREWGENT = os.path.join(HOME, ".drewgent")
NOW = time.time()
T = time.localtime(NOW)

WEEKDAY = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}

JOBS = [
    # (name, interval_sec or "HH:MM" or "dow:HH:MM", command, env)
    ("trend-evaluate", 120,
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"trend-evaluate"}),

    ("launchd-watchdog", 300,
     ["/bin/bash", f"{DREWGENT}/scripts/drewgent_launchd_watchdog.sh"], {}),

    ("dashboard-push", 300,
     ["python3", f"{DREWGENT}/scripts/agent_dashboard_push.py"], {}),

    ("gbrain-watchdog", 900,
     ["/bin/bash", f"{DREWGENT}/scripts/drewgent_gbrain_watchdog.sh"], {}),

    ("trend-collect", 21600,
     ["python3", f"{DREWGENT}/scripts/trend_harvester.py"], {}),

    ("seo-harvester", 21600,
     ["/bin/bash", f"{DREWGENT}/scripts/cron_seo_harvester.sh"], {}),

    ("log-rotate", "04:00",
     ["/bin/bash", f"{DREWGENT}/scripts/drewgent_log_rotate.sh"], {}),

    ("usage-watch", "06:00",
     ["python3", f"{DREWGENT}/scripts/trend_usage_watch.py"], {}),

    ("harmony-check", "09:00",
     ["/bin/bash", f"{DREWGENT}/scripts/drewgent_harmony_check.sh"], {}),

    ("seo-analyze", "12:00",
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"seo-analyze"}),

    ("trend-retire", "mon:10:00",
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"trend-retire"}),

    ("seo-trend-report", "mon:14:00",
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"seo-trend"}),

    ("taste-review-1", "tue:10:00",
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"taste-review"}),

    ("taste-review-2", "fri:10:00",
     ["python3", f"{DREWGENT}/scripts/n8n_trigger_runner.py"], {"N8N_TRIGGER_TYPE":"taste-review"}),
]

def due(name, sched, state):
    """Check if job should run now."""
    if isinstance(sched, (int, float)):
        return NOW - state.get(name, 0) >= sched
    if ":" in sched:
        parts = sched.split(":")
        if len(parts) == 2:
            return f"{T.tm_hour:02d}:{T.tm_min:02d}" == sched
        if len(parts) == 3:
            d, h, m = parts
            return WEEKDAY.get(d,-1) == T.tm_wday and int(h) == T.tm_hour and int(m) == T.tm_min
    return False

def run(name, cmd, env):
    env = {**os.environ, **env}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
        o = r.stdout.strip()
        if o and o != 'silent':
            print(f"[{name}] {o[:200]}")
    except subprocess.TimeoutExpired:
        print(f"[{name}] TIMEOUT")
    except Exception as e:
        print(f"[{name}] {e}")

def main():
    st = Path(f"{DREWGENT}/logs/cron_state.json")
    state = {}
    if st.exists():
        try: state = json.loads(st.read_text())
        except: pass

    any_run = False
    for name, sched, cmd, env in JOBS:
        if due(name, sched, state):
            run(name, cmd, env)
            if isinstance(sched, (int, float)):
                state[name] = NOW
            else:
                state[f"{name}_cron"] = time.strftime("%Y-%m-%d %H:%M")
            any_run = True

    if not any_run:
        print("idle")

    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps(state))

if __name__ == "__main__":
    main()
