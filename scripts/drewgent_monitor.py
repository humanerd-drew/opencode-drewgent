#!/usr/bin/env python3
"""
Drewgent Local Monitor
- 1시간마다 디스코드로 알림 (새벽 12시~오전 8시 제외)
- 아침 8시에 밤 사이 전체 요약 전송
- 모든 모니터링 데이터 포함
"""

import requests
import time
import json
import os
from datetime import datetime, time as dtime
from typing import Dict, Any, List, Optional

# Configuration
DISCORD_WEBHOOK_URL = os.environ.get("DREW_DISCORD_WEBHOOK", "")
GATEWAY_URL = "http://localhost:8642"
CHECK_INTERVAL = 3600  # 1 hour

# Night exclusion (midnight to 8 AM)
NIGHT_START = dtime(0, 0)
NIGHT_END = dtime(8, 0)

# History storage
STATE_FILE = "/tmp/drewgent_monitor_state.json"


def is_night_time() -> bool:
    now = datetime.now().time()
    return NIGHT_START <= now < NIGHT_END


def is_8am() -> bool:
    return datetime.now().hour == 8 and datetime.now().minute < 10


def load_state() -> Dict[str, Any]:
    """Load previous state for night summary"""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"last_summary": None, "night_data": []}


def save_state(state: Dict[str, Any]) -> None:
    """Save current state"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_gateway(endpoint: str) -> Optional[Dict[str, Any]]:
    """Fetch data from gateway endpoint"""
    try:
        resp = requests.get(f"{GATEWAY_URL}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None


def check_health() -> Dict[str, Any]:
    """Check gateway health"""
    health = get_gateway("/health")
    if health:
        return {"status": "healthy", "data": health}

    metrics = get_gateway("/v1/metrics")
    if metrics:
        return {"status": "degraded", "data": metrics}

    return {"status": "down", "data": None}


def format_health_report(health: Dict[str, Any]) -> str:
    """Format health check for Discord"""
    status = health.get("status", "unknown")
    data = health.get("data", {})

    status_emoji = {"healthy": "✅", "degraded": "⚠️", "down": "❌"}.get(status, "❓")

    lines = [
        f"{status_emoji} **Gateway Health:** {status.upper()}",
    ]

    if data:
        if "platform" in data:
            lines.append(f"   Platform: {data.get('platform', 'N/A')}")
        if "status" in data:
            lines.append(f"   Status: {data.get('status', 'N/A')}")

    return "\n".join(lines)


def format_metrics_report(metrics: Dict[str, Any]) -> str:
    """Format all metrics for Discord"""
    if not metrics or "metrics" not in metrics:
        return "📊 **Metrics:** No data available"

    m = metrics.get("metrics", {})
    ver = m.get("verification", {})
    scores = m.get("scores", {})
    p0 = m.get("p0_blocks", {})

    # Calculate pass rate
    total = ver.get("total", 0)
    approved = ver.get("approved", 0)
    pass_rate = (approved / total * 100) if total > 0 else 0

    lines = [
        "📊 **Drewgent Metrics**",
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "**검증 결과:**",
        f"  전체: {total} | 통과: {approved} | 수정: {ver.get('revision', 0)} | 거부: {ver.get('rejected', 0)}",
        f"  통과율: {pass_rate:.1f}%",
        "",
        f"**평균 점수:** {scores.get('avg', 0):.3f} (min: {scores.get('min', 0):.3f} / max: {scores.get('max', 0):.3f})",
        "",
        "**P0 차단:**",
        f"  환각(hallucination): {p0.get('hallucination', 0)}",
        f"  안전(safety): {p0.get('safety', 0)}",
    ]

    # Recent blocks
    recent = m.get("recent_blocks", [])
    if recent:
        lines.append("")
        lines.append("**최근 차단 내역 (최근 5건):**")
        for block in recent[-5:]:
            ts = block.get("timestamp", "")[:19].replace("T", " ")
            btype = block.get("block_type", "unknown")
            reason = block.get("reason", "N/A")[:50]
            lines.append(f"  [{ts}] {btype}: {reason}")

    return "\n".join(lines)


def format_knowledge_report(knowledge: Dict[str, Any]) -> str:
    """Format knowledge bus for Discord"""
    if not knowledge or "knowledge" not in knowledge:
        return "🧠 **Knowledge Bus:** No data available"

    k = knowledge.get("knowledge", {})
    total = k.get("total_knowledge", 0)
    by_source = k.get("by_source", {})
    by_type = k.get("by_type", {})
    avg_conf = k.get("avg_confidence", 0)

    lines = [
        "🧠 **Knowledge Bus**",
        f"  총 패턴: {total}개",
        f"  평균 신뢰도: {avg_conf:.1%}",
        "",
        "**소스별:**",
    ]

    for source, count in by_source.items():
        lines.append(f"  • {source}: {count}")

    lines.append("")
    lines.append("**유형별:**")
    for typ, count in by_type.items():
        lines.append(f"  • {typ}: {count}")

    # Recent patterns
    recent = knowledge.get("recent", [])
    if recent:
        lines.append("")
        lines.append("**최근 학습된 패턴 (최근 3건):**")
        for item in recent[-3:]:
            content = item.get("content", "")[:60]
            tags = item.get("tags", [])[:3]
            lines.append(f"  • [{', '.join(tags)}] {content}...")

    return "\n".join(lines)


def format_night_summary(night_data: List[Dict[str, Any]]) -> str:
    """Format night summary for 8 AM notification"""
    if not night_data:
        return "🌙 **밤 사이 데이터 없음**"

    lines = [
        "🌅 **Drewgent 아침 요약**",
        f"📅 {datetime.now().strftime('%Y-%m-%d')}",
        f"⏰ 새벽 {NIGHT_START.strftime('%H:%M')} ~ 아침 {NIGHT_END.strftime('%H:%M')} 동안",
        "",
    ]

    # Aggregate data
    total_verifications = 0
    total_approved = 0
    total_revision = 0
    total_rejected = 0
    total_hallucination = 0
    total_safety = 0

    for data in night_data:
        metrics = data.get("metrics", {}).get("metrics", {})
        ver = metrics.get("verification", {})
        p0 = metrics.get("p0_blocks", {})

        total_verifications += ver.get("total", 0)
        total_approved += ver.get("approved", 0)
        total_revision += ver.get("revision", 0)
        total_rejected += ver.get("rejected", 0)
        total_hallucination += p0.get("hallucination", 0)
        total_safety += p0.get("safety", 0)

    pass_rate = (
        (total_approved / total_verifications * 100) if total_verifications > 0 else 0
    )

    lines.extend(
        [
            "**밤 사이 검증 결과:**",
            f"  전체: {total_verifications} | 통과: {total_approved} | 수정: {total_revision} | 거부: {total_rejected}",
            f"  통과율: {pass_rate:.1f}%",
            "",
            "**P0 차단:**",
            f"  환각: {total_hallucination} | 안전: {total_safety}",
        ]
    )

    return "\n".join(lines)


def send_discord(message: str) -> bool:
    """Send message to Discord webhook"""
    if not DISCORD_WEBHOOK_URL:
        print("No Discord webhook configured, skipping")
        print(message)
        return False

    try:
        payload = {"content": message, "username": "Drewgent Monitor"}
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Discord: {e}")
        return False


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Drewgent Monitor started")
    print(f"Gateway: {GATEWAY_URL}")
    print(f"Discord: {'Configured' if DISCORD_WEBHOOK_URL else 'NOT SET'}")

    last_summary_date = None

    while True:
        now = datetime.now()
        night = is_night_time()
        morning = is_8am()

        # Health check
        health = check_health()
        print(f"[{now.strftime('%H:%M:%S')}] Status: {health['status']}")

        if night:
            # During night, just collect data
            if health["status"] != "down":
                state = load_state()
                state["night_data"].append(
                    {
                        "timestamp": now.isoformat(),
                        "metrics": get_gateway("/v1/metrics"),
                        "knowledge": get_gateway("/v1/knowledge"),
                    }
                )
                save_state(state)

            print("  Night time - collecting data only")
            time.sleep(300)  # Check every 5 minutes during night
            continue

        # Day time
        state = load_state()

        # Send morning summary at 8 AM
        if morning and last_summary_date != now.date():
            print("  Sending morning summary...")
            night_summary = format_night_summary(state.get("night_data", []))
            send_discord(night_summary)

            # Reset night data
            state["night_data"] = []
            state["last_summary"] = now.isoformat()
            save_state(state)
            last_summary_date = now.date()

        # Get all data
        metrics = get_gateway("/v1/metrics")
        knowledge = get_gateway("/v1/knowledge")
        models = get_gateway("/v1/models")

        # Build comprehensive message
        lines = [
            f"⏰ **{now.strftime('%Y-%m-%d %H:%M')} Drewgent 상태 보고**",
            "",
        ]

        lines.append(format_health_report(health))
        lines.append("")
        lines.append(
            format_metrics_report(metrics)
            if metrics
            else "📊 **Metrics:** Gateway unreachable"
        )
        lines.append("")
        lines.append(
            format_knowledge_report(knowledge)
            if knowledge
            else "🧠 **Knowledge:** Gateway unreachable"
        )

        # Model info
        if models and "data" in models:
            model_list = [m.get("id", "unknown") for m in models.get("data", [])]
            lines.append("")
            lines.append(f"🤖 **Models:** {', '.join(model_list)}")

        message = "\n".join(lines)
        send_discord(message)
        print("  Notification sent")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
