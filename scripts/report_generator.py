#!/usr/bin/env python3
"""
Drewgent 상태 보고서 생성기
  python report_generator.py daily|weekly|monthly|quarterly|semi|annual

각 보고서는 stderr에 요약을 출력하고 stdout에 Discord 메시지를 출력.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ─── 경로 설정 ────────────────────────────────────────────
DREW_HOME = Path.home() / ".drewgent"
MEMORIES  = DREW_HOME / "memories"
SESSIONS  = DREW_HOME / "sessions.db"
SKILLS_DIR= DREW_HOME / "skills"
CRON_DIR  = DREW_HOME / "cron"
CONFIG    = DREW_HOME / "config.yaml"

# ─── 시간 유틸 ────────────────────────────────────────────
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

def now():
    return datetime.now(KST)

def kst_now():
    # KST = UTC+9 (명시적 Asia/Seoul timezone)
    return datetime.now(KST).replace(microsecond=0)

def parse_date(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ─── 기간 정의 ────────────────────────────────────────────
def get_range(report_type):
    """각 보고서 타입의 기간(start, end, label)을 반환."""
    now_dt = kst_now()
    if report_type == "daily":
        start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"📅 {now_dt.strftime('%Y-%m-%d')} 일일 보고서"
    elif report_type == "weekly":
        # 월요일 시작
        days_since_monday = now_dt.weekday()
        start = (now_dt - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"📊 {now_dt.strftime('%Y-%m-%d')} 주간 보고서"
    elif report_type == "monthly":
        start = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = f"📆 {now_dt.strftime('%Y년 %m월')} 월간 보고서"
    elif report_type == "quarterly":
        q = (now_dt.month - 1) // 3
        start = datetime(now_dt.year, q * 3 + 1, 1, tzinfo=now_dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"📐 {now_dt.strftime('%Y년')} Q{q+1} 분기 보고서"
    elif report_type == "semi":
        m = 1 if now_dt.month <= 6 else 7
        start = datetime(now_dt.year, m, 1, tzinfo=now_dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"🗓️ {now_dt.year}년 {'상' if m == 1 else '하'}반기 보고서"
    elif report_type == "annual":
        start = now_dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        label = f"🏆 {now_dt.year}년 연간 보고서"
    else:
        start = now_dt - timedelta(days=1)
        label = f"보고서 ({report_type})"
    end = now_dt
    return start, end, label

# ─── 수집 함수 ────────────────────────────────────────────
def collect_session_stats(start, end):
    """세션 통계를 수집한다."""
    stats = {
        "total_sessions": 0,
        "total_messages": 0,
        "platforms": defaultdict(int),
        "active_sessions": [],
    }
    try:
        conn = sqlite3.connect(str(SESSIONS))
        cur = conn.cursor()
        cur.execute(
            "SELECT id, platform, created_at, message_count FROM sessions WHERE created_at >= ? AND created_at < ?",
            (start.isoformat(), end.isoformat())
        )
        rows = cur.fetchall()
        conn.close()
        stats["total_sessions"] = len(rows)
        for row in rows:
            sid, platform, created, mcount = row
            stats["platforms"][platform or "cli"] += 1
            stats["total_messages"] += mcount or 0
            if mcount:
                stats["active_sessions"].append({
                    "id": sid[:12],
                    "platform": platform or "cli",
                    "messages": mcount or 0
                })
    except Exception:
        pass
    return stats

def collect_brain_stats(start, end):
    """Brain/지식베이스 통계를 수집한다."""
    stats = {
        "total_entries": 0,
        "user_entries": 0,
        "memory_entries": 0,
        "concept_entries": 0,
        "new_this_period": 0,
        "access_counts": [],
        "gaps_detected": [],
    }

    try:
        # entities/에서 파일 수 카운트
        entities_dir = MEMORIES / "entities"
        if entities_dir.exists():
            all_files = list(entities_dir.rglob("*.md"))
            stats["total_entries"] = len(all_files)

            for f in all_files:
                content = f.read_text()
                # 태그 파싱
                in_frontmatter = False
                tags = []
                for line in content.split("\n"):
                    if line.strip() == "---":
                        in_frontmatter = not in_frontmatter
                        continue
                    if in_frontmatter and line.startswith("tags:"):
                        import re
                        tag_match = re.findall(r'\[([^\]]+)\]', line)
                        if tag_match:
                            tags = [t.strip() for t in tag_match[0].split(",")]

                if "user" in tags:
                    stats["user_entries"] += 1
                elif "memory" in tags or "concept" in tags:
                    stats["memory_entries"] += 1
                    stats["concept_entries"] += 1

                # 새 항목 체크 (created 날짜 기준)
                updated = None
                for line in content.split("\n"):
                    if line.strip().startswith("updated:"):
                        import re
                        m = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                        if m:
                            try:
                                d = datetime.fromisoformat(m.group(1))
                                if start <= d <= end:
                                    stats["new_this_period"] += 1
                            except Exception:
                                pass
                        break
    except Exception:
        pass

    # vector DB에서 access_count 수집
    try:
        vector_db = MEMORIES / "vectors.db"
        if vector_db.exists():
            conn = sqlite3.connect(str(vector_db))
            cur = conn.cursor()
            cur.execute("SELECT access_count FROM entries WHERE access_count > 0")
            stats["access_counts"] = [r[0] for r in cur.fetchall()]
            conn.close()
    except Exception:
        pass

    # gaps 디텍션 (지식 베이스에 없는 주제)
    known_topics = {"preferences", "communication-style", "environment", "corrections", "user-profile"}
    topics_with_coverage = set()
    try:
        entities_dir = MEMORIES / "entities"
        if entities_dir.exists():
            for f in entities_dir.rglob("*.md"):
                content = f.read_text()
                for topic in known_topics:
                    if topic.replace("-", " ") in content.lower() or topic in content.lower():
                        topics_with_coverage.add(topic)
    except Exception:
        pass

    stats["gaps_detected"] = sorted(known_topics - topics_with_coverage)
    return stats

def collect_todo_stats():
    """현재 진행중인 할일 목록을 가져온다."""
    todos = []
    try:
        from pathlib import Path
        import json
        todo_file = DREW_HOME / ".todo.json"
        if todo_file.exists():
            with open(todo_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    todos = [t for t in data if t.get("status") != "completed" and t.get("status") != "cancelled"]
                elif isinstance(data, dict) and "todos" in data:
                    todos = [t for t in data.get("todos", []) if t.get("status") != "completed" and t.get("status") != "cancelled"]
    except Exception:
        pass
    return todos

def collect_cron_stats():
    """예약된 cron 작업 상태를 가져온다."""
    jobs = []
    try:
        jobs_file = CRON_DIR / "jobs.json"
        if jobs_file.exists():
            with open(jobs_file) as f:
                jobs = json.load(f)
    except Exception:
        pass
    return jobs

def collect_skills_stats():
    """활성화된 스킬 목록을 가져온다."""
    skills = []
    try:
        if SKILLS_DIR.exists():
            for d in SKILLS_DIR.iterdir():
                if d.is_dir() and d.name not in ("__pycache__", ".cache"):
                    # SKILL.md가 있는지 확인
                    skill_md = d / "SKILL.md"
                    desc = ""
                    if skill_md.exists():
                        import re
                        m = re.search(r'description:\s*(.+)', skill_md.read_text()[:500])
                        if m:
                            desc = m.group(1).strip()
                    skills.append({"name": d.name, "description": desc})
    except Exception:
        pass
    return skills

def collect_tools_status():
    """활성화된 주요 도구 상태를 반환한다."""
    tools = []
    try:
        config_file = DREW_HOME / "config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                content = f.read()
                import re
                # enabled_toolsets 찾기
                ts = re.findall(r'enabled_toolsets:\s*\[(.*?)\]', content, re.DOTALL)
                if ts:
                    toolsets = [t.strip().strip('"\'') for t in ts[0].split(",") if t.strip()]
                    return toolsets
    except Exception:
        pass
    return []

# ─── 리포트 생성 ────────────────────────────────────────────
def build_report(report_type: str) -> str:
    start, end, label = get_range(report_type)
    session_stats = collect_session_stats(start, end)
    brain_stats   = collect_brain_stats(start, end)
    todos         = collect_todo_stats()
    cron_jobs     = collect_cron_stats()
    skills        = collect_skills_stats()
    toolsets      = collect_tools_status()

    # ── Embed ──
    lines = [f"## {label}", ""]

    # 1. 세션 요약
    if session_stats["total_sessions"] > 0:
        lines.append("### 💬 세션")
        lines.append(f"- 총 세션: **{session_stats['total_sessions']}개**")
        lines.append(f"- 총 메시지: **{session_stats['total_messages']}개**")
        if session_stats["platforms"]:
            plat = ", ".join(f"**{k}**: {v}" for k, v in session_stats["platforms"].items())
            lines.append(f"- 플랫폼: {plat}")
        lines.append("")

    # 2. Brain / 지식 베이스
    lines.append("### 🧠 Brain")
    lines.append(f"- 총 항목: **{brain_stats['total_entries']}개** (user: {brain_stats['user_entries']}, memory/concept: {brain_stats['concept_entries']})")
    if brain_stats["new_this_period"] > 0:
        lines.append(f"- 이번 기간新增: **{brain_stats['new_this_period']}개**")
    if brain_stats["access_counts"]:
        avg = sum(brain_stats["access_counts"]) / len(brain_stats["access_counts"])
        lines.append(f"- 평균 접근: **{avg:.1f}회** (이번 기간)")
    if brain_stats["gaps_detected"]:
        gaps = ", ".join(brain_stats["gaps_detected"])
        lines.append(f"- ⚠️ 지식 빈칸: `{gaps}`")
    lines.append("")

    # 3. 진행 중인 할일
    if todos:
        lines.append("### 📋 진행중인 할일")
        for t in todos[:10]:
            status_emoji = {"in_progress": "🔄", "pending": "⏳"}.get(t.get("status", "pending"), "📌")
            lines.append(f"{status_emoji} {t.get('content', 'Untitled')}")
        if len(todos) > 10:
            lines.append(f"_...외 {len(todos) - 10}개_")
        lines.append("")

    # 4. Cron 작업
    if cron_jobs and isinstance(cron_jobs, list):
        active = [j for j in cron_jobs if isinstance(j, dict) and j.get("enabled", True)]
        lines.append(f"### ⏰ 예약 작업 ({len(active)}개 활성화)")
        for j in active[:6]:
            n = j.get("name") or j.get("id", "?")[:8]
            sched = j.get("schedule_display") or (j.get("schedule") or {}).get("display") if isinstance(j.get("schedule"), dict) else "?"
            lines.append(f"- `{sched}` — {n}")
        lines.append("")

    # 5. 스킬 & 도구
    if skills or toolsets:
        lines.append("### 🛠️ 스킬 & 도구")
        if skills:
            skill_names = ", ".join(f"**{s['name']}**" for s in skills[:8])
            lines.append(f"- 스킬: {skill_names}")
        if toolsets:
            lines.append(f"- 도구셋: `{'`, `'.join(toolsets)}`")
        lines.append("")

    # 6. 기간 설정
    lines.append(f"📆 기간: {start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)

# ─── 메인 ────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: report_generator.py <daily|weekly|monthly|quarterly|semi|annual>", file=sys.stderr)
        sys.exit(1)

    report_type = sys.argv[1].lower()
    valid_types = ["daily", "weekly", "monthly", "quarterly", "semi", "annual"]
    if report_type not in valid_types:
        print(f"Invalid type: {report_type}. Choose from: {', '.join(valid_types)}", file=sys.stderr)
        sys.exit(1)

    report = build_report(report_type)
    print(report)