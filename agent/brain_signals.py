"""Brain Signal Detection and Emission for Drewgent.

"모든 것이 신호" architecture의 핵심 component.
run_agent.py의 주요 실행 지점에서 signal을 detection하고 event bus로 emit한다.

Signal Types:
- user.prompt          : User sent a message
- agent.exploring     : Agent exploring with tool calls
- agent.modifying     : Agent modifying files/code
- tool.integration.*  : Tool integration workflow
- skill.integration.* : Skill integration workflow
- session.end         : Session ending
- context.updated     : Context changed (memory, wiki, etc.)
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal Detection Patterns
# ---------------------------------------------------------------------------

# User prompt patterns that indicate specific intents
_INTEGRATION_PATTERNS = [
    # Tool integration — order matters, more specific first
    (r"도구를\s*추가|도구\s*추가|새\s*도구|도구\s*생성", "tool.integration.start"),
    (r"도구를?\s*(?:추가|생성|통합)", "tool.integration.start"),
    (r"tool\s*add|add\s*tool|new\s*tool", "tool.integration.start"),
    (r"스킬을\s*추가|스킬\s*추가|새\s*스킬|스킬\s*생성", "skill.integration.start"),
    (r"skill\s*add|add\s*skill|new\s*skill", "skill.integration.start"),
    # Gateway platform integration
    (r"gateway.*어댑터|어댑터.*gateway|새\s*플랫폼|플랫폼\s*추가", "gateway_platform.integration.start"),
    (r"add.*gateway.*adapter|new.*platform.*adapter", "gateway_platform.integration.start"),
    (r"discord.*setup|slack.*setup|telegram.*bot.*add|whatsapp.*setup", "gateway_platform.integration.start"),
    # Slash command integration
    (r"add.*command|새\s*슬래시|슬래시\s*명령어|command.*추가", "slash_command.integration.start"),
    (r"/\w+.*command|slash.*command.*add", "slash_command.integration.start"),
    # MCP server integration
    (r"add.*mcp.*server|mcp\s*서버|mcp.*연결|new.*mcp", "mcp_server.integration.start"),
    # Cron job integration
    (r"add.*cron|cron\s*job|크론\s*작업|스케줄\s*추가|periodic", "cron_job.integration.start"),
    (r"도구\s*제거|remove\s*tool|도구\s*삭제", "tool.integration.remove"),
    # File modification
    (r"수정|modify|edit|change|update", "agent.modifying"),
    # Exploration
    (r"확인|check|look\s*at|inspect|find", "agent.exploring"),
    # Brain/Skill queries
    (r"brain|brain_query", "brain.query"),
    (r"skill|스킬", "skill.related"),
]

# Tool names that indicate specific activities
_TOOL_ACTIVITY_MAP = {
    "write_file": "agent.modifying",
    "patch": "agent.modifying",
    "terminal": "agent.exploring",
    "read_file": "agent.exploring",
    "search_files": "agent.exploring",
    "brain_query": "brain.query",
    "brain_record": "brain.record",
    "skill_manage": "skill.related",
    "skill_view": "skill.related",
}


# ---------------------------------------------------------------------------
# Signal Emitter Class
# ---------------------------------------------------------------------------

class SignalEmitter:
    """Detects and emits signals from agent execution flow.

    Usage:
        emitter = SignalEmitter()
        emitter.user_prompt(user_message)
        emitter.tool_start(tool_name, args)
        emitter.tool_complete(tool_name, result)
        emitter.session_end(summary)
    """

    def __init__(self):
        self._event_bus = None
        self._last_user_message = ""
        self._session_id = ""

    def _get_event_bus(self):
        """Lazy-load event bus to avoid circular imports."""
        if self._event_bus is None:
            try:
                from agent.event_bus import get_event_bus
                self._event_bus = get_event_bus()
            except Exception:
                return None
        return self._event_bus

    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID for correlation."""
        self._session_id = session_id or ""

    def user_prompt(self, message: str) -> None:
        """Emit signal when user sends a message."""
        bus = self._get_event_bus()
        if not bus:
            return

        self._last_user_message = message

        # Detect intent from message
        detected_signals = self._detect_signals(message)

        # Always emit base user.prompt event
        bus.emit(
            "user.prompt",
            payload={
                "message": message[:200],  # truncate for safety
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

        # Emit detected intent signals
        for signal_type, confidence in detected_signals:
            bus.emit(
                signal_type,
                payload={
                    "message": message[:200],
                    "session_id": self._session_id,
                    "confidence": confidence,
                },
                source="signal_emitter",
            )

    def agent_exploring(self, tool_calls: List[Any]) -> None:
        """Emit signal when agent is exploring with tools."""
        bus = self._get_event_bus()
        if not bus:
            return

        tool_names = []
        for tc in tool_calls:
            name = getattr(tc, "function", None)
            name = getattr(name, "name", str(tool_calls[0]) if tool_calls else "")
            tool_names.append(name)

            # Also emit tool-specific signals
            if name in _TOOL_ACTIVITY_MAP:
                bus.emit(
                    _TOOL_ACTIVITY_MAP[name],
                    payload={
                        "tool": name,
                        "session_id": self._session_id,
                    },
                    source="signal_emitter",
                )

        bus.emit(
            "agent.exploring",
            payload={
                "tools": tool_names,
                "count": len(tool_names),
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

    def tool_start(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Emit signal when a tool call starts."""
        bus = self._get_event_bus()
        if not bus:
            return

        # Map tool to activity signal
        activity_signal = _TOOL_ACTIVITY_MAP.get(tool_name)
        if activity_signal:
            bus.emit(
                activity_signal,
                payload={
                    "tool": tool_name,
                    "args_keys": list(args.keys()) if isinstance(args, dict) else [],
                    "session_id": self._session_id,
                },
                source="signal_emitter",
            )

        # Emit general tool.start
        bus.emit(
            "tool.start",
            payload={
                "tool": tool_name,
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

    def tool_complete(
        self, tool_name: str, result: str, success: bool = True
    ) -> None:
        """Emit signal when a tool call completes."""
        bus = self._get_event_bus()
        if not bus:
            return

        # Emit tool.complete
        bus.emit(
            "tool.complete",
            payload={
                "tool": tool_name,
                "success": success,
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

        # Emit integration completion signals
        if tool_name in ("write_file", "patch"):
            path = self._extract_path_from_result(result)
            if path:
                # Detect if this is a tool file being modified
                if "tools/" in path or "tool_" in path:
                    bus.emit(
                        "tool.integration.detected",
                        payload={
                            "path": path,
                            "tool_name": tool_name,
                            "session_id": self._session_id,
                        },
                        source="signal_emitter",
                    )
                # Detect if this is a skill file being modified
                if "skills/" in path or "SKILL.md" in path:
                    bus.emit(
                        "skill.integration.detected",
                        payload={
                            "path": path,
                            "tool_name": tool_name,
                            "session_id": self._session_id,
                        },
                        source="signal_emitter",
                    )

    def agent_modifying(self, operation: str, path: str, details: str = "") -> None:
        """Emit signal when agent modifies files/code."""
        bus = self._get_event_bus()
        if not bus:
            return

        bus.emit(
            "agent.modifying",
            payload={
                "operation": operation,  # write, patch, delete
                "path": path,
                "details": details,
                "session_id": self._session_id,
                "correlation_id": self._session_id,  # Use session_id for correlation
            },
            source="signal_emitter",
        )

    def session_end(
        self, summary: str = "", message_count: int = 0, tool_count: int = 0
    ) -> None:
        """Emit signal when session ends."""
        bus = self._get_event_bus()
        if not bus:
            return

        bus.emit(
            "session.end",
            payload={
                "summary": summary,
                "message_count": message_count,
                "tool_count": tool_count,
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

    def context_updated(self, context_type: str, details: str = "") -> None:
        """Emit signal when context changes (memory, wiki, etc.)."""
        bus = self._get_event_bus()
        if not bus:
            return

        bus.emit(
            "context.updated",
            payload={
                "context_type": context_type,
                "details": details,
                "session_id": self._session_id,
            },
            source="signal_emitter",
        )

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _detect_signals(self, message: str) -> List[tuple]:
        """Detect signals from user message."""
        signals = []
        msg_lower = message.lower()

        for pattern, signal_type in _INTEGRATION_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                # Confidence based on pattern specificity
                confidence = 0.7 if len(pattern) > 15 else 0.5
                signals.append((signal_type, confidence))

        return signals

    def _extract_path_from_result(self, result: str) -> Optional[str]:
        """Extract file path from tool result if present."""
        if not isinstance(result, str):
            return None
        # Simple heuristic: look for common path patterns in result
        path_patterns = [
            r'/[\w\-\.]+/[\w\-\./]+',  # absolute paths
            r'~\/[\w\-\./]+',  # home relative
        ]
        for pattern in path_patterns:
            match = re.search(pattern, result)
            if match:
                return match.group(0)
        return None


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_signal_emitter: Optional[SignalEmitter] = None


def get_signal_emitter() -> SignalEmitter:
    """Get the global SignalEmitter singleton."""
    global _signal_emitter
    if _signal_emitter is None:
        _signal_emitter = SignalEmitter()
    return _signal_emitter


# Convenience functions
def emit_user_prompt(message: str) -> None:
    get_signal_emitter().user_prompt(message)


def emit_tool_start(tool_name: str, args: Dict[str, Any]) -> None:
    get_signal_emitter().tool_start(tool_name, args)


def emit_tool_complete(tool_name: str, result: str, success: bool = True) -> None:
    get_signal_emitter().tool_complete(tool_name, result, success)


def emit_session_end(
    summary: str = "", message_count: int = 0, tool_count: int = 0
) -> None:
    get_signal_emitter().session_end(summary, message_count, tool_count)


# ----------------------------------------------------------------------
# Phase 3-1: Turn lifecycle & QA gate emitters (P0-brainstem hooks)
# ----------------------------------------------------------------------


def emit_turn_start(turn_number: int, user_message: str) -> None:
    """Emit turn.start — fires before each turn begins.

    Phase 3-1: Connects run_agent.py fusion loop → signal bus →
    signal_processor._on_turn_start().
    """
    get_signal_emitter()._get_event_bus().emit(
        "turn.start",
        payload={"turn_number": turn_number, "user_message": user_message},
        source="brain_signals",
    )


def emit_turn_end(
    turn_number: int,
    assistant_response: str = "",
    tool_calls: Optional[List[Dict]] = None,
) -> None:
    """Emit turn.end — fires after each turn completes.

    Phase 3-1: Connects run_agent.py fusion loop → signal bus →
    signal_processor._on_turn_end().
    """
    get_signal_emitter()._get_event_bus().emit(
        "turn.end",
        payload={
            "turn_number": turn_number,
            "assistant_response": assistant_response,
            "tool_calls": tool_calls or [],
        },
        source="brain_signals",
    )


def emit_qa_gate(task_id: str, phase: str, evidence_dir: str) -> None:
    """Emit qa.gate — enforce 禁task_qa_gate contract-first QA.

    Phase 3-1: Called by run_agent.py before each delivery phase
    (contract/micro/full). signal_processor._on_qa_gate() validates
    that the required evidence file exists.
    """
    get_signal_emitter()._get_event_bus().emit(
        "qa.gate",
        payload={"task_id": task_id, "phase": phase, "evidence_dir": evidence_dir},
        source="brain_signals",
    )


def emit_agent_complete(session_id: str, message_count: int) -> None:
    """Emit agent.complete — fires when agent session ends.

    Phase 3-1: Connects run_agent.py final cleanup → signal bus →
    signal_processor._on_agent_complete() for P0-brainstem final verification.
    """
    get_signal_emitter()._get_event_bus().emit(
        "agent.complete",
        payload={"session_id": session_id, "message_count": message_count},
        source="brain_signals",
    )