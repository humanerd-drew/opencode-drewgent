#!/usr/bin/env python3
"""
drewgent_cron.py — Drewgent cron dispatcher.
launchd 60초 틱마다 실행. jobs.json을 단일 소스로 사용.
"""
import os, time, subprocess, json, sys
from pathlib import Path

# Load .env file so Discord webhooks and other env vars are available
dotenv_path = os.path.join(os.path.expanduser("~"), ".drewgent", ".env")
if os.path.exists(dotenv_path):
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            os.environ.setdefault(key, val)

HOME = os.path.expanduser("~")
DREWGENT = os.path.join(HOME, ".drewgent")
JOBS_FILE = Path(f"{DREWGENT}/cron/jobs.json")
STATE_FILE = Path(f"{DREWGENT}/logs/cron_state.json")
SCRIPTS_DIR = Path(f"{DREWGENT}/scripts")


def parse_schedule(job):
    """jobs.json schedule을 실행 스펙 튜플로 변환."""
    sched = job.get("schedule", {})
    kind = sched.get("kind")
    if kind == "interval":
        minutes = sched.get("minutes")
        return ("interval", int(minutes) * 60) if isinstance(minutes, (int, float)) else None
    if kind == "cron":
        expr = sched.get("expr", "")
        parts = expr.split()
        if len(parts) != 5:
            return None
        m, h, dom, mon, dow = parts
        try:
            if m == "*" and h == "*" and dom == "*" and mon == "*" and dow == "*":
                return ("interval", 60)
            if m.startswith("*/") and h == "*" and dom == "*" and mon == "*" and dow == "*":
                return ("interval", int(m[2:]) * 60)
            if m == "0" and h == "*" and dom == "*" and mon == "*" and dow == "*":
                return ("interval", 3600)
            if m == "0" and h.startswith("*/") and dom == "*" and mon == "*" and dow == "*":
                return ("interval", int(h[2:]) * 3600)
            if m == "0" and h.isdigit() and dom == "*" and mon == "*" and dow == "*":
                return ("daily", int(h))
            if m == "0" and h.isdigit() and dom == "*" and mon == "*" and dow.isdigit():
                return ("weekly", int(dow), int(h))
        except ValueError:
            pass
    return None


def due(key, spec, state, now, t, now_min):
    """현재 tick에서 실행할지 판단."""
    if spec[0] == "interval":
        return now - state.get(key, 0) >= spec[1]
    if spec[0] == "daily":
        _, h = spec
        return t.tm_hour == h and t.tm_min == 0 and state.get(f"{key}_cron") != now_min
    if spec[0] == "weekly":
        _, cron_dow, h = spec
        py_wday = (cron_dow + 6) % 7  # cron 0=일 → python 6=일
        return t.tm_wday == py_wday and t.tm_hour == h and t.tm_min == 0 and state.get(f"{key}_cron") != now_min
    return False


def build_env(job):
    """스크립트에 전달할 추가 환경변수."""
    env = {}
    script = job.get("script", "")
    if "n8n_trigger_runner.py" in script:
        text = f"{job.get('id', '')} {job.get('name', '')}".lower()
        for trigger in ("trend-evaluate", "taste-review", "seo-analyze", "seo-trend", "trend-retire"):
            if trigger in text:
                env["N8N_TRIGGER_TYPE"] = trigger
                break
    return env


def resolve_script(script):
    """스크립트 경로를 안전하게 해석. scripts 디렉터리 밖이거나 없으면 None."""
    raw = Path(script)
    if raw.is_absolute():
        path = raw.resolve()
        try:
            path.relative_to(SCRIPTS_DIR.resolve())
        except ValueError:
            return None
    else:
        path = (SCRIPTS_DIR / raw).resolve()
    return path if path.is_file() else None


def _send_discord(name, deliver, content, env):
    """Best-effort Discord delivery via scripts/discord_send.py."""
    if not deliver or not deliver.startswith("discord:"):
        return
    channel = deliver.split(":", 1)[1].strip()
    if not channel:
        return
    discord_send = SCRIPTS_DIR / "discord_send.py"
    try:
        r = subprocess.run(
            [sys.executable, str(discord_send), "--channel", channel, "--title", name, "--body", content],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if r.returncode != 0:
            err = (r.stderr or "").strip()[:200]
            print(f"[{name}] discord_send error: {err}")
        else:
            print(f"[{name}] delivered to discord:{channel}")
    except Exception as e:
        print(f"[{name}] discord delivery failed: {e}")


def run(name, path, extra_env, deliver=None):
    """스크립트 실행 후 출력 표시."""
    env = {**os.environ, **extra_env}
    interpreter = "/bin/bash" if path.suffix == ".sh" else sys.executable
    try:
        r = subprocess.run([interpreter, str(path)], capture_output=True, text=True, timeout=300, env=env)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode == 0:
            if out and out != "silent":
                print(f"[{name}] {out[:200]}")
                if deliver:
                    _send_discord(name, deliver, out, env)
        else:
            msg = err or out or f"exit {r.returncode}"
            print(f"[{name}] {msg[:200]}")
    except subprocess.TimeoutExpired:
        print(f"[{name}] TIMEOUT")
    except Exception as e:
        print(f"[{name}] {e}")


def load_jobs():
    """jobs.json에서 실행 대상만 필터링."""
    try:
        data = json.loads(JOBS_FILE.read_text())
    except Exception as e:
        print(f"[cron] jobs.json 로드 실패: {e}")
        return []
    jobs = []
    for job in data.get("jobs", []):
        if not job.get("script") or job.get("no_agent") is not True:
            continue
        if job.get("enabled") is not True or job.get("state") == "paused":
            continue
        spec = parse_schedule(job)
        if spec:
            job["_spec"] = spec
            jobs.append(job)
    return jobs


def main():
    now = time.time()
    t = time.localtime(now)
    now_min = time.strftime("%Y-%m-%d %H:%M", t)
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    any_run = False
    for job in load_jobs():
        job_id = job.get("id", job.get("name", "unknown"))
        name = job.get("name", job_id)
        spec = job["_spec"]
        if not due(job_id, spec, state, now, t, now_min):
            continue
        path = resolve_script(job["script"])
        if path is None:
            print(f"[{name}] 스크립트 없음: {job['script']}")
            continue
        run(name, path, build_env(job), job.get("deliver"))
        if spec[0] == "interval":
            state[job_id] = now
        else:
            state[f"{job_id}_cron"] = now_min
        any_run = True
    if not any_run:
        print("idle")
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))


if __name__ == "__main__":
    print("[cron] daemon started")
    while True:
        main()
        time.sleep(60)
