"""
Drewgent Hooks - Gateway Integration Module

This module provides integration between Drewgent Gateway and Drewgent modules:
- NeuronFS (brain governance)
- VerificationEngine (quality gate)
- GrowthEngine (pattern detection)
- Knowledge Bus (central knowledge store)
- RevisionLoop (response revision)

This module is loaded by gateway/run.py to provide Drewgent-specific functionality.

NOTE: This module relies on gateway/run.py having added the project root to
sys.path BEFORE importing this module. This is done via:
    sys.path.insert(0, str(Path(__file__).parent.parent))
"""

import os
from pathlib import Path

# =============================================================================
# IMPORTS - with graceful degradation
# =============================================================================

# Verification Engine
try:
    from modules.verification_engine import (
        VerificationEngine,
        VerificationStatus,
    )
    VERIFICATION_ENGINE_OK = True
except ImportError as e:
    VERIFICATION_ENGINE_OK = False
    # Stub classes for when module is not available
    class VerificationStatus:
        APPROVED = "approved"
        REVISION = "revision"
        REJECTED = "rejected"

    class VerificationEngine:
        def __init__(self, *args, **kwargs):
            pass
        def verify(self, *args, **kwargs):
            return None
    import sys
    sys.stderr.write(f"[Drewgent] VerificationEngine import failed: {e}\n")

# Growth Engine
try:
    from modules.growth_engine import (
        GrowthEngine,
        run_growth_analysis,
    )
    GROWTH_ENGINE_OK = True
except ImportError:
    GROWTH_ENGINE_OK = False
    GrowthEngine = None
    def run_growth_analysis(*args, **kwargs):
        return {}

# Revision Loop
try:
    from modules.revision_loop import (
        RevisionLoop,
        RevisionResult,
        revise_with_revision_loop,
    )
    REVISION_LOOP_OK = True
except ImportError:
    REVISION_LOOP_OK = False
    RevisionLoop = None
    RevisionResult = None
    def revise_with_revision_loop(*args, **kwargs):
        return None

# Knowledge Bus
try:
    from modules.knowledge_bus import (
        KnowledgeBus,
        Knowledge,
        get_knowledge_bus,
    )
    KNOWLEDGE_BUS_OK = True
except ImportError:
    KNOWLEDGE_BUS_OK = False
    class KnowledgeBus:
        @staticmethod
        def get_instance():
            return None
    class Knowledge:
        def __init__(self, **kwargs):
            pass
    def get_knowledge_bus():
        return None

# Logging V2
try:
    from modules.logging_v2 import (
        get_log_db_connection,
        get_recent_errors,
        get_task_stats,
        get_tool_stats,
        get_active_patterns,
        detect_and_record_pattern,
        record_knowledge_update,
        find_similar_tasks,
        search_logs,
        audit_log,
    )
    LOGGING_V2_OK = True
except ImportError:
    LOGGING_V2_OK = False
    # Stub functions
    def get_log_db_connection():
        return None
    def get_recent_errors(*args, **kwargs):
        return []
    def get_task_stats(*args, **kwargs):
        return {}
    def get_tool_stats(*args, **kwargs):
        return {}
    def get_active_patterns(*args, **kwargs):
        return []
    def detect_and_record_pattern(*args, **kwargs):
        pass
    def record_knowledge_update(*args, **kwargs):
        pass
    def find_similar_tasks(*args, **kwargs):
        return []
    def search_logs(*args, **kwargs):
        return []
    def audit_log(*args, **kwargs):
        pass

# =============================================================================
# METRICS
# =============================================================================

class DrewgentMetrics:
    """
    Metrics collection for Drewgent analytics with Knowledge Bus persistence.

    Thread-safe singleton - use get_instance() to get the singleton.
    """

    _instance = None

    def __init__(self):
        self._metrics = {
            "verifications": 0,
            "approved": 0,
            "revision": 0,
            "rejected": 0,
            "blocks": 0,
        }
        self._kb = get_knowledge_bus() if KNOWLEDGE_BUS_OK else None

    @classmethod
    def get_instance(cls):
        """Get or create the metrics singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _persist_metric(
        self,
        metric_type: str,
        content: str,
        tags: list,
        confidence: float = 0.9,
    ):
        """Persist a metric event to Knowledge Bus."""
        if self._kb is None:
            return
        try:
            self._kb.store_from_module(
                module="drewgent_metrics",
                content=content,
                knowledge_type=metric_type,
                confidence=confidence,
                tags=tags,
            )
        except Exception as e:
            print(f"[DrewgentMetrics] Failed to persist: {e}")

    def record_verification(self, status: str, score: float, revision_count: int = 0):
        """Record a verification result."""
        self._metrics["verifications"] += 1
        if status == "approved":
            self._metrics["approved"] += 1
        elif status == "revision":
            self._metrics["revision"] += 1
        elif status == "rejected":
            self._metrics["rejected"] += 1

        # Persist to Knowledge Bus
        self._persist_metric(
            metric_type="verification_result",
            content=f"Verification: status={status}, score={score}, revision_count={revision_count}",
            tags=["verification", status],
            confidence=0.95,
        )

    def record_p0_block(self, block_type: str, reason: str):
        """Record a P0 block event."""
        self._metrics["blocks"] += 1

        # Persist to Knowledge Bus
        self._persist_metric(
            metric_type="p0_block",
            content=f"P0 Block: type={block_type}, reason={reason}",
            tags=["p0", "block", block_type],
            confidence=1.0,
        )

    def record_task(self, task_type: str, duration: float, success: bool):
        """Record task execution."""
        # Persist to Knowledge Bus
        self._persist_metric(
            metric_type="task_execution",
            content=f"Task: type={task_type}, duration={duration:.2f}s, success={success}",
            tags=["task", task_type, "success" if success else "failure"],
            confidence=0.9,
        )

    def get_summary(self) -> dict:
        """Get metrics summary."""
        return dict(self._metrics)


def get_drewgent_metrics() -> DrewgentMetrics:
    """Get or create the metrics singleton."""
    return DrewgentMetrics.get_instance()


# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

_verification_engine_instance = None


def _get_verification_engine():
    """Get or create the VerificationEngine singleton."""
    global _verification_engine_instance
    if _verification_engine_instance is None and VERIFICATION_ENGINE_OK:
        try:
            _verification_engine_instance = VerificationEngine()
        except Exception as e:
            print(f"[Drewgent] VerificationEngine init error: {e}")
            _verification_engine_instance = False
    return _verification_engine_instance if _verification_engine_instance else None


def verify_and_process_response(
    user_message: str,
    response: str,
    context: dict = None,
) -> dict | None:
    """
    Verify an LLM response and process the result.

    This is the main integration point for Drewgent verification.
    Called by gateway/run.py after agent completes processing.

    Args:
        user_message: The original user message
        response: The LLM's response to verify
        context: Additional context (platform, session_id, user_id, etc.)

    Returns:
        dict with verification result or None if verification unavailable
    """
    if not response:
        return None

    context = context or {}

    engine = _get_verification_engine()
    if not engine:
        return None

    try:
        verification = engine.verify(
            task=user_message,
            output=response,
            context=context,
        )

        if verification is None:
            return None

        result = {
            "drewgent_verified": True,
            "status": verification.status.value if hasattr(verification.status, 'value') else verification.status,
            "score": verification.overall_score,
            "response": response,
            "revision_notes": getattr(verification, 'revision_notes', None),
            "rejection_reason": getattr(verification, 'rejection_reason', None),
            "revision_count": 0,
        }

        return result

    except Exception as e:
        print(f"[Drewgent] verify_and_process_response error: {e}")
        return None


# =============================================================================
# NOTIFICATION FUNCTIONS
# =============================================================================

# Discord webhook URL from environment
_DREW_DISCORD_WEBHOOK = os.environ.get("DREW_DISCORD_WEBHOOK", "")


def _send_discord_webhook(message: str, title: str = None) -> bool:
    """
    Send a message to Discord webhook.

    Args:
        message: The message content to send
        title: Optional title for the embed

    Returns:
        True if sent successfully, False otherwise
    """
    if not _DREW_DISCORD_WEBHOOK:
        return False

    try:
        import urllib.request
        import json

        payload = {
            "content": message,
            "username": "Drewgent",
        }
        if title:
            payload["embeds"] = [{
                "title": title,
                "description": message,
                "color": 0x00FF00,  # Green
            }]

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _DREW_DISCORD_WEBHOOK,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200 or resp.status == 204
    except Exception as e:
        print(f"[Drewgent] Discord webhook error: {e}")
        return False


def notify_blocked(reason: str, context: dict = None):
    """Send notification when response is blocked by P0 rules."""
    context = context or {}
    session_id = context.get("session_id", "unknown") if context else "unknown"
    message = f"🛑 **BLOCKED** | Session: `{session_id}`\n```\n{reason}\n```"

    sent = _send_discord_webhook(message, "P0 Block")
    if not sent:
        print(f"[Drewgent] BLOCKED: {reason}")


def notify_rejected(score: float, rejection_reason: str, context: dict = None):
    """Send notification when response is rejected."""
    context = context or {}
    session_id = context.get("session_id", "unknown") if context else "unknown"
    message = f"❌ **REJECTED** | Session: `{session_id}`\nScore: `{score:.0%}`\nReason: {rejection_reason}"

    sent = _send_discord_webhook(message, "Response Rejected")
    if not sent:
        print(f"[Drewgent] REJECTED: score={score:.0%}, reason={rejection_reason}")


def notify_revision(score: float, revision_notes: str, context: dict = None):
    """Send notification when response needs revision."""
    context = context or {}
    session_id = context.get("session_id", "unknown") if context else "unknown"
    truncated = revision_notes[:500] + "..." if len(revision_notes) > 500 else revision_notes
    message = f"🔧 **REVISION NEEDED** | Session: `{session_id}`\nScore: `{score:.0%}`\nNotes: {truncated}"

    sent = _send_discord_webhook(message, "Response Needs Revision")
    if not sent:
        print(f"[Drewgent] REVISION NEEDED: score={score:.0%}, notes={revision_notes[:50]}...")


def notify_approved(score: float, context: dict = None):
    """Send notification when response is approved."""
    context = context or {}
    session_id = context.get("session_id", "unknown") if context else "unknown"
    message = f"✅ **APPROVED** | Session: `{session_id}`\nScore: `{score:.0%}`"

    sent = _send_discord_webhook(message, "Response Approved")
    if not sent:
        print(f"[Drewgent] APPROVED: score={score:.0%}")


def notify_metrics(context: dict = None):
    """Send metrics summary notification."""
    metrics = get_drewgent_metrics()
    summary = metrics.get_summary()

    verifications = summary.get("verifications", 0)
    approved = summary.get("approved", 0)
    revision = summary.get("revision", 0)
    rejected = summary.get("rejected", 0)
    blocks = summary.get("blocks", 0)

    message = (
        f"📊 **Drewgent Metrics**\n"
        f"Verifications: `{verifications}`\n"
        f"✅ Approved: `{approved}` | "
        f"🔧 Revision: `{revision}` | "
        f"❌ Rejected: `{rejected}` | "
        f"🛑 Blocks: `{blocks}`"
    )

    sent = _send_discord_webhook(message, "Metrics Summary")
    if not sent:
        print(f"[Drewgent] Metrics: {summary}")


# =============================================================================
# KNOWLEDGE FUNCTIONS
# =============================================================================

def record_verification_knowledge(task: str, result, context: dict = None):
    """Record verification result as knowledge."""
    if not KNOWLEDGE_BUS_OK:
        return

    kb = get_knowledge_bus()
    if not kb:
        return

    try:
        # Record verification result as knowledge
        if hasattr(result, 'status') and hasattr(result, 'overall_score'):
            kb.store(Knowledge(
                source="verification_engine",
                type="verification_result",
                content=f"Task '{task}' -> {result.status.value if hasattr(result.status, 'value') else result.status} (score: {result.overall_score:.0%})",
                confidence=result.overall_score,
                tags=[result.status.value if hasattr(result.status, 'value') else result.status, "verification"],
            ))
    except Exception as e:
        print(f"[Drewgent] Failed to record verification knowledge: {e}")


def query_knowledge_for_verification(task: str, context: dict = None) -> list:
    """Query knowledge to inform verification."""
    if not KNOWLEDGE_BUS_OK:
        return []

    kb = get_knowledge_bus()
    if not kb:
        return []

    try:
        return kb.query(tags=["verification"], min_confidence=0.6, limit=5)
    except Exception as e:
        print(f"[Drewgent] Failed to query knowledge: {e}")
        return []


# =============================================================================
# GROWTH ENGINE INTEGRATION
# =============================================================================

_growth_last_run = None
_GROWTH_INTERVAL_MINUTES = 60  # Run analysis every hour


def run_periodic_growth_analysis(force: bool = False) -> dict:
    """
    Run GrowthEngine analysis if enough time has passed.

    This function is designed to be called periodically by the gateway
    scheduler. It respects the internal interval to avoid excessive analysis.

    Args:
        force: If True, skip the interval check and run immediately

    Returns:
        dict with analysis results or skip reason
    """
    global _growth_last_run

    if not GROWTH_ENGINE_OK:
        return {"status": "skipped", "reason": "GrowthEngine not available"}

    from datetime import datetime, timedelta

    if not force and _growth_last_run is not None:
        elapsed = datetime.now() - _growth_last_run
        if elapsed.total_seconds() / 60 < _GROWTH_INTERVAL_MINUTES:
            return {
                "status": "skipped",
                "reason": f"Only {elapsed.total_seconds() / 60:.1f} minutes since last run",
            }

    try:
        results = run_growth_analysis(force=force)
        _growth_last_run = datetime.now()

        # Log results
        patterns = results.get("patterns_detected", [])
        suggestions = results.get("suggestions", [])
        if patterns or suggestions:
            print(f"[Drewgent] Growth analysis: {len(patterns)} patterns, {len(suggestions)} suggestions")

        return results
    except Exception as e:
        print(f"[Drewgent] Growth analysis error: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# INITIALIZATION CHECK
# =============================================================================

def check_initialization():
    """Check and log initialization status."""
    status = {
        "verification_engine": VERIFICATION_ENGINE_OK,
        "growth_engine": GROWTH_ENGINE_OK,
        "revision_loop": REVISION_LOOP_OK,
        "knowledge_bus": KNOWLEDGE_BUS_OK,
        "logging_v2": LOGGING_V2_OK,
    }
    print(f"[Drewgent] Hooks initialized: {status}")
    return status
