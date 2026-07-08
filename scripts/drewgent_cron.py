#!/usr/bin/env python3
"""
drewgent_cron.py — Drewgent cron dispatcher.
launchd 60초 틱마다 실행. jobs.json을 단일 소스로 사용.
"""
import os, time, subprocess, json, sys, threading
from pathlib import Path

_RUNNING_AGENTS = {}
_RUNNING_LOCK = threading.Lock()

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
            if m == "0" and "," in h and all(p.isdigit() for p in h.split(",")) and dom == "*" and mon == "*" and dow == "*":
                return ("daily_multi", [int(p) for p in h.split(",")])
            if m == "0" and h.isdigit() and dom == "*" and mon == "*" and dow.isdigit():
                return ("weekly", int(dow), int(h))
        except ValueError:
            pass
    return None


def due(key, spec, state, now, t, now_min):
    """현재 tick에서 실행할지 판단.
    daily/weekly: 날짜 기반 (분 정확도가 아닌 일 정확도) — blocking agent job으로 인해 1분 윈도우를 놓치는 걸 방지.
    """
    if spec[0] == "interval":
        return now - state.get(key, 0) >= spec[1]
    if spec[0] == "daily":
        _, h = spec
        today = time.strftime("%Y-%m-%d", t)
        return t.tm_hour == h and state.get(f"{key}_day") != today
    if spec[0] == "daily_multi":
        _, hours = spec
        today = time.strftime("%Y-%m-%d", t)
        return t.tm_hour in hours and state.get(f"{key}_day") != today
    if spec[0] == "weekly":
        _, cron_dow, h = spec
        py_wday = (cron_dow + 6) % 7  # cron 0=일 → python 6=일
        today = time.strftime("%Y-%m-%d", t)
        return t.tm_wday == py_wday and t.tm_hour == h and state.get(f"{key}_day") != today
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
                print(f"[{name}] {out[:2000]}")
                if deliver:
                    _send_discord(name, deliver, out, env)
        else:
            msg = err or out or f"exit {r.returncode}"
            print(f"[{name}] {msg[:2000]}")
    except subprocess.TimeoutExpired:
        print(f"[{name}] TIMEOUT")
    except Exception as e:
        print(f"[{name}] {e}")


def load_jobs():
    """jobs.json에서 실행 대상만 필터링. script + agent job 모두 처리."""
    try:
        data = json.loads(JOBS_FILE.read_text())
    except Exception as e:
        print(f"[cron] jobs.json 로드 실패: {e}")
        return []
    jobs = []
    for job in data.get("jobs", []):
        if job.get("enabled") is not True or job.get("state") == "paused":
            continue
        spec = parse_schedule(job)
        if not spec:
            continue
        is_agent = job.get("prompt") and job.get("no_agent") is not True
        is_script = job.get("script") and job.get("no_agent") is True
        if not is_script and not is_agent:
            continue
        job["_spec"] = spec
        job["_kind"] = "agent" if is_agent else "script"
        jobs.append(job)
    return jobs


def run_agent_sync(name, job, deliver):
    """Agent 기반 job을 동기 실행. 분리된 스레드에서 호출됨."""
    import shutil
    opencode = shutil.which("opencode")
    if not opencode:
        print(f"[{name}] opencode not found in PATH")
        return

    profile = job.get("profile")
    model = job.get("model", "")
    provider = job.get("provider", "")
    prompt = job.get("prompt", "")

    if not prompt:
        print(f"[{name}] no prompt, skipping")
        return

    cmd = [opencode, "run", "--dangerously-skip-permissions"]
    if profile:
        cmd.extend(["--agent", profile])
    if model:
        full = f"{provider}/{model}" if provider else model
        cmd.extend(["--model", full])
    opencode_attach = os.getenv("OPENCODE_ATTACH", "http://localhost:8642")
    cmd.extend(["--attach", opencode_attach])
    cmd.append(prompt)

    print(f"[{name}] launching agent job")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, env=os.environ)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        combined = (out + "\n" + err).strip()
        if r.returncode == 0:
            if combined and "SILENT" not in combined.upper()[:100]:
                msg = combined[:500]
                print(f"[{name}] {msg[:200]}")
                if deliver:
                    _send_discord(name, deliver, msg, os.environ)
        else:
            msg = err or out or f"exit {r.returncode}"
            print(f"[{name}] {msg[:200]}")
    except subprocess.TimeoutExpired:
        print(f"[{name}] TIMEOUT (2h)")
    except Exception as e:
        print(f"[{name}] {e}")


def dispatch_agent(job_id, job, deliver):
    """에이전트 job을 별도 스레드로 발송. 중복 실행 방지."""
    with _RUNNING_LOCK:
        if job_id in _RUNNING_AGENTS:
            print(f"[{job_id}] already running, skip")
            return False
        _RUNNING_AGENTS[job_id] = True

    name = job.get("name", job_id)

    def _run():
        try:
            run_agent_sync(name, job, deliver)
        finally:
            with _RUNNING_LOCK:
                _RUNNING_AGENTS.pop(job_id, None)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return True


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
        if job["_kind"] == "script":
            path = resolve_script(job["script"])
            if path is None:
                print(f"[{name}] 스크립트 없음: {job['script']}")
                continue
            run(name, path, build_env(job), job.get("deliver"))
        elif not dispatch_agent(job_id, job, job.get("deliver")):
            continue  # 이미 실행 중인 agent job — state 업데이트 안 함
        if spec[0] == "interval":
            state[job_id] = now
        else:
            today = time.strftime("%Y-%m-%d", t)
            state[f"{job_id}_day"] = today
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
