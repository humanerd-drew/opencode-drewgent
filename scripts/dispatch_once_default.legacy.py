#!/usr/bin/env python3
"""
dispatch_once for default board kanban tasks.
Reclaims stale tasks, claims ready tasks, spawns workers.
"""
import os, sqlite3, subprocess, datetime, signal, json
from pathlib import Path

DREW_HOME = Path(os.environ.get('DREW_HOME', str(Path.home() / '.drewgent')))
DB = DREW_HOME / 'P2-hippocampus' / 'kanban' / 'state' / 'drewgent_tasks.db'

result = {'reclaimed': 0, 'watchdog_reclaimed': 0, 'claimed': 0, 'spawned': 0, 'skipped': 0}
reclaimed_details = []
watchdog_details = []
claimed_details = []
spawned_details = []
skipped_details = []

conn = sqlite3.connect(str(DB))
now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ── Adaptive MAX_CLAIM ──
# ready task 수에 따라 한 번에 claim하는 태스크 수를 조절
ready_count = conn.execute('''
    SELECT COUNT(*) FROM tasks
    WHERE status = "ready" AND board = "default"
''').fetchone()[0] or 0

running_count = conn.execute('''
    SELECT COUNT(*) FROM tasks
    WHERE status = "in_progress" AND board = "default"
''').fetchone()[0] or 0

if ready_count >= 100:
    MAX_CLAIM = 10
elif ready_count >= 50:
    MAX_CLAIM = 5
else:
    MAX_CLAIM = 3

# Half the ready tasks at most (don't drain entire queue in one tick)
MAX_CLAIM = max(1, min(MAX_CLAIM, max(1, ready_count // 2)))

# Phase 0: watchdog — dead worker (worker_pid set but process gone) 즉시 reclaim
# TTL 만료 전이라도 worker가 죽었으면 queue에 stuck 되지 않도록
in_progress = conn.execute('''
    SELECT id, title, worker_pid, last_heartbeat_at FROM tasks
    WHERE status = "in_progress" AND worker_pid IS NOT NULL AND board = "default"
''').fetchall()

now_dt = datetime.datetime.now(datetime.timezone.utc)
heartbeat_timeout = datetime.timedelta(minutes=5)

for task_id, title, wpid, last_hb in in_progress:
    worker_dead = False
    reason = ""

    # 1) PID existence check
    try:
        os.kill(int(wpid), 0)
    except (ProcessLookupError, OSError):
        worker_dead = True
        reason = f"pid={wpid} DEAD"

    # 2) Heartbeat check (PID alive but no heartbeat for 5+ min → hung)
    if not worker_dead and last_hb:
        try:
            hb_time = datetime.datetime.fromisoformat(last_hb)
            if (now_dt - hb_time) > heartbeat_timeout:
                # Worker process exists but hasn't reported progress
                try:
                    os.kill(int(wpid), signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    pass
                worker_dead = True
                reason = f"pid={wpid} HUNG (no heartbeat since {last_hb[:19]})"
        except (ValueError, TypeError):
            pass

    if worker_dead:
        conn.execute('UPDATE tasks SET status="ready", worker_pid=NULL, claim_expires=NULL WHERE id=?', (task_id,))
        result['watchdog_reclaimed'] += 1
        watchdog_details.append(f"{task_id}: {reason} | {str(title)[:60]}")

if result['watchdog_reclaimed'] > 0:
    conn.commit()

# ── Phase 1.5: Worker affinity & cooldown ──
# skills 필드 기반으로 실패 이력이 많은 태스크 타입은 후순위
AFFINITY_FILE = DREW_HOME / "P2-hippocampus" / "kanban" / "state" / "worker_affinity.json"
cooldown_skills = set()
try:
    if AFFINITY_FILE.exists():
        affinity = json.loads(AFFINITY_FILE.read_text())
        now_unix = datetime.datetime.now(datetime.timezone.utc).timestamp()
        for skill, entry in affinity.items():
            cooldown_until = entry.get("cooldown_until", 0)
            consecutive_fails = entry.get("consecutive_failures", 0)
            if consecutive_fails >= 3 and now_unix < cooldown_until:
                cooldown_skills.add(skill)
except Exception:
    pass

# Phase 1: reclaim stale in_progress (TTL-based)
stale = conn.execute('''
    SELECT id, title, worker_pid, claim_expires FROM tasks
    WHERE status = "in_progress"
      AND claim_expires IS NOT NULL
      AND claim_expires < ?
      AND board = "default"
    ORDER BY claim_expires ASC
''', (now_ts,)).fetchall()

for task_id, title, wpid, expires in stale:
    # Liveness check: if worker is still alive, DO NOT reclaim — let it finish.
    # Phase 0 watchdog already handled dead workers. Phase 1 is the safety net for
    # workers that died AFTER Phase 0 (e.g., between ticks) but with stale TTL.
    worker_alive = False
    if wpid:
        try:
            os.kill(int(wpid), 0)
            worker_alive = True
        except (ProcessLookupError, OSError):
            worker_alive = False
    if worker_alive:
        # Worker alive — skip reclaim; trust the worker
        result['skipped'] += 1
        skipped_details.append(f"{task_id}: pid={wpid} ALIVE (TTL expired but worker still working) | {str(title)[:60]}")
        continue
    conn.execute('UPDATE tasks SET status="ready", worker_pid=NULL, claim_expires=NULL WHERE id=?', (task_id,))
    result['reclaimed'] += 1
    reclaimed_details.append(f"{task_id}: pid={wpid} DEAD + TTL expired | {str(title)[:60]}")

conn.commit()

# Phase 2: claim ready tasks (adaptive max)
# - consecutive_failures >= max_retries 인 태스크는 제외
# - cooldown_skills 에 포함된 skills 의 태스크는 후순위
now_utc = datetime.datetime.now(datetime.timezone.utc)
claim_expires = (now_utc + datetime.timedelta(hours=1)).isoformat()

if cooldown_skills:
    # Cooldown skills 먼저 (제외하고 카운트), 나머지 우선 할당
    normal_ready = conn.execute('''
        SELECT id, title, consecutive_failures, max_retries, skills FROM tasks
        WHERE board = "default"
          AND status = "ready"
          AND (consecutive_failures IS NULL OR consecutive_failures < COALESCE(max_retries, 3))
          AND (skills IS NULL OR skills NOT IN ({}))
        ORDER BY priority DESC, consecutive_failures ASC NULLS FIRST, created_at ASC
        LIMIT ?
    '''.format(','.join('?' for _ in cooldown_skills)),
        list(cooldown_skills) + [MAX_CLAIM]
    ).fetchall()
    remaining = MAX_CLAIM - len(normal_ready)
    if remaining > 0:
        cooldown_ready = conn.execute('''
            SELECT id, title, consecutive_failures, max_retries, skills FROM tasks
            WHERE board = "default"
              AND status = "ready"
              AND (consecutive_failures IS NULL OR consecutive_failures < COALESCE(max_retries, 3))
              AND skills IN ({})
            ORDER BY consecutive_failures ASC NULLS FIRST, created_at ASC
            LIMIT ?
        '''.format(','.join('?' for _ in cooldown_skills)),
            list(cooldown_skills) + [remaining]
        ).fetchall()
        ready = normal_ready + cooldown_ready
    else:
        ready = normal_ready
else:
    ready = conn.execute('''
        SELECT id, title, consecutive_failures, max_retries, skills FROM tasks
        WHERE board = "default"
          AND status = "ready"
          AND (consecutive_failures IS NULL OR consecutive_failures < COALESCE(max_retries, 3))
        ORDER BY priority DESC, consecutive_failures ASC NULLS FIRST, created_at ASC
        LIMIT ?
    ''', (MAX_CLAIM,)).fetchall()

# Report exhausted tasks (consecutive_failures >= max_retries, no more retries)
exhausted = conn.execute('''
    SELECT id, title, consecutive_failures, max_retries, last_failure_error FROM tasks
    WHERE board = "default"
      AND status = "ready"
      AND consecutive_failures >= COALESCE(max_retries, 3)
''').fetchall()

for task_id, title, *_ in ready:
    updated = conn.execute(
        'UPDATE tasks SET status="in_progress", worker_pid=?, claim_expires=?, last_heartbeat_at=? WHERE id=? AND status="ready"',
        (os.getpid(), claim_expires, now_utc.isoformat(), task_id)
    ).rowcount
    if updated:
        result['claimed'] += 1
        claimed_details.append(f"{task_id}: {str(title)[:60]}")

conn.commit()

# Phase 3: spawn workers for just-claimed tasks
venv_python = str(DREW_HOME / 'source' / 'drewgent-agent' / '.venv' / 'bin' / 'python')
src_agent = str(DREW_HOME / 'source' / 'drewgent-agent')

spawned_tasks = conn.execute('''
    SELECT id, title, body, workspace_kind, workspace_path FROM tasks
    WHERE status = "in_progress" AND worker_pid = ?
''', (os.getpid(),)).fetchall()

conn.close()

for task_id, title, body, ws_kind, ws_path in spawned_tasks:
        env = os.environ.copy()
        env.update({
            'KANBAN_TASK_ID': task_id,
            'KANBAN_WORKER_PID': str(os.getpid()),
            'KANBAN_BOARD': 'default',
            'DREW_HOME': str(DREW_HOME),
            'KANBAN_WORKER_MODE': '1',
        })
        ws_dir = str(DREW_HOME) if not ws_path or ws_path == 'None' else ws_path

        worker_script = str(DREW_HOME / 'scripts' / 'run_kanban_worker.py')

        try:
            log_dir = DREW_HOME / 'P4-cortex' / 'scripts' / 'kanban' / 'logs' / 'workers'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f'{task_id}.log'
            logf = open(log_path, 'ab')
            proc = subprocess.Popen(
                [venv_python, worker_script],
                stdout=logf, stderr=subprocess.STDOUT,
                env=env, cwd=ws_dir, start_new_session=True
            )
            logf.close()  # Popen이 fd 상속 — parent close 안전
            # Fix: store WORKER's PID (proc.pid) — dispatcher PID dies in 0.05s and confuses watchdog
            _pid_conn = sqlite3.connect(str(DB), timeout=10)
            _pid_conn.execute('UPDATE tasks SET worker_pid=? WHERE id=?', (proc.pid, task_id))
            _pid_conn.commit()
            _pid_conn.close()
            result['spawned'] += 1
            spawned_details.append(f"{task_id}: {str(title)[:60]} | pid={proc.pid} | log={log_path.name}")
        except Exception as e:
            # Spawn failed — rollback: status=ready, worker_pid=NULL so next tick can retry
            try:
                _rb = sqlite3.connect(str(DB), timeout=10)
                _rb.execute('UPDATE tasks SET status="ready", worker_pid=NULL, claim_expires=NULL WHERE id=?', (task_id,))
                _rb.commit()
                _rb.close()
            except Exception:
                pass
            spawned_details.append(f"{task_id}: SPAWN FAILED — {e}")

# Output — script-only cron jobs read this raw; [SILENT] suppresses delivery
total = result['watchdog_reclaimed'] + result['reclaimed'] + result['claimed'] + result['spawned']
if total == 0 and not exhausted:
    print("[SILENT]")
else:
    print(f"queue={ready_count} running={running_count} max_claim={MAX_CLAIM} | "
          f"watchdog_reclaimed={result['watchdog_reclaimed']} | "
          f"ttl_reclaimed={result['reclaimed']} | "
          f"claimed={result['claimed']} | "
          f"spawned={result['spawned']} | "
          f"skipped={result['skipped']}"
          + (f" | cooldown={','.join(sorted(cooldown_skills))}" if cooldown_skills else "")
          + ")")
    if exhausted:
        print(f"\n⚠️ Exhausted tasks (max retries reached, won't retry):")
        for tid, ttl, cf, mr, lfe in exhausted:
            err = (lfe or "unknown")[:60]
            print(f"  - {tid}: {str(ttl)[:60]} (failures={cf}/{mr}, last: {err})")
    if result['watchdog_reclaimed'] > 0:
        print("\nWatchdog reclaimed (dead workers):")
        for d in watchdog_details:
            print(f"  - {d}")
    if result['reclaimed'] > 0:
        print("\nTTL reclaimed (dead + TTL expired):")
        for d in reclaimed_details:
            print(f"  - {d}")
    if result['skipped'] > 0:
        print("\nSkipped (worker alive, TTL expired but trusting worker):")
        for d in skipped_details:
            print(f"  - {d}")
    if result['claimed'] > 0:
        print("\nClaimed tasks:")
        for d in claimed_details:
            print(f"  - {d}")
    if result['spawned'] > 0:
        print("\nSpawned workers:")
        for d in spawned_details:
            print(f"  - {d}")
