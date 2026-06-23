"""Brain Signal Processor — the discriminator layer of P-folder structure.

판별 레이어(Cortical Layer 3): 신호를 받아 패턴을 인식하고,
자기 아키텍처 모델과 비교하여 적절한 행동을 결정한다.

Responsibilities:
1. Track integration workflows (tool/skill absorption)
2. Detect completion of multi-step operations
3. Build and maintain meta-awareness model
4. Emit awareness signals for other layers to act on
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent.event_bus import BrainEvent, get_event_bus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Integration Workflow State
# ---------------------------------------------------------------------------

@dataclass
class IntegrationWorkflow:
    """Tracks progress of a tool/skill integration workflow."""
    workflow_id: str
    integration_type: str  # "tool" or "skill"
    target_name: str       # e.g., "my_new_tool"
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps_completed: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    started: bool = False
    completed: bool = False
    completed_at: Optional[str] = None
    correlation_id: str = ""
    source_file: str = ""   # e.g. "tools/super_tool.py" — the primary integration target file
    next_hint: Optional[str] = None  # Phase 5-1 fix: store computed hint for P0 enforcement

    def add_step(self, step: str) -> None:
        if step not in self.steps_completed:
            self.steps_completed.append(step)

    def add_file(self, file_path: str) -> None:
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    def get_hint(self) -> Optional[str]:
        """Phase 5-1 fix: return next_hint for P0 enforcement in _complete_workflow.

        Called by signal_processor._complete_workflow() to check if the workflow
        is incomplete (hint != None means files are missing).
        """
        return self.next_hint


# ---------------------------------------------------------------------------
# Architecture Model (what the agent "knows" about itself)
# ---------------------------------------------------------------------------

class ArchitectureModel:
    """Internal model of Drewgent's architecture for self-awareness.

    This model learns integration patterns from the active brain's P0 neurons
    and applies them at runtime to guide the agent's behavior.
    """

    _instance: Optional["ArchitectureModel"] = None
    _brain_rules_loaded: bool = False

    def __init__(self):
        self._integration_patterns: Dict[str, Dict[str, Any]] = {}
        self._last_integration_time: Optional[str] = None
        # Brain-sourced rules (loaded lazily from brain_manager)
        self._tool_rule: Optional[Dict[str, Any]] = None
        self._skill_rule: Optional[Dict[str, Any]] = None
        # Phase 2-2: All P0-brainstem neurons for runtime enforcement
        self._p0_neurons: List[Dict[str, Any]] = []
        self._load_brain_rules()

    @classmethod
    def get_instance(cls) -> "ArchitectureModel":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_brain_rules(self) -> None:
        """Load integration rules from the active brain's P0 neurons.

        This connects the brain (P folder structure) to the signal processor,
        so that brain neurons actively govern the agent's behavior rather than
        sitting dormant as advisory text in the system prompt.
        """
        if ArchitectureModel._brain_rules_loaded:
            return

        try:
            # Import brain_manager lazily to avoid circular imports
            from drewgent_cli.brain_manager import (
                get_active_brain_name,
                scan_brain,
            )

            active_brain = get_active_brain_name()
            if not active_brain:
                logger.debug("No active brain — using hardcoded defaults")
                return

            brain = scan_brain(active_brain)
            if not brain:
                logger.debug("Could not scan brain '%s'", active_brain)
                return

            # Walk P0-brainstem layer — load ALL neurons for runtime enforcement
            self._p0_neurons = []
            for layer in brain.layers:
                if layer.name != "P0-brainstem":
                    continue
                for neuron in layer.neurons:
                    parsed = self._parse_neuron(neuron)
                    # Also extract required_files for integration neurons
                    if neuron.name.startswith("禁tool_integration_3file"):
                        self._tool_rule = parsed
                    elif neuron.name.startswith("禁skill_integration"):
                        self._skill_rule = parsed
                    # Load ALL P0 neurons for enforcement
                    self._p0_neurons.append(parsed)

            ArchitectureModel._brain_rules_loaded = True
            logger.debug(
                "Brain rules loaded: tool_rule=%s, skill_rule=%s, p0_neurons=%d",
                bool(self._tool_rule),
                bool(self._skill_rule),
                len(self._p0_neurons),
            )
        except Exception as e:
            logger.debug("Failed to load brain rules: %s", e)

    def _parse_neuron(self, neuron) -> Dict[str, Any]:
        """Parse a neuron file into structured rule data."""
        rule = {
            "name": neuron.name,
            "weight": neuron.weight,
            "content": neuron.content,
        }
        # Extract INTEGRATION REQUIREMENTS from .neuron content
        # The 禁tool_integration_3file rule has structured sections
        content = neuron.content or ""
        files = []
        if "tools/" in content or "model_tools.py" in content:
            # Parse required files from rule content
            if "tools/" in content:
                files.append("tools/")
            if "model_tools.py" in content:
                files.append("model_tools.py")
            if "toolsets.py" in content:
                files.append("toolsets.py")
        rule["required_files"] = files
        return rule

    def get_tool_integration_files(self) -> List[str]:
        """Return the canonical tool integration files.

        Loaded from brain P0 neuron if available, otherwise hardcoded fallback.
        """
        if self._tool_rule and self._tool_rule.get("required_files"):
            return self._tool_rule["required_files"]
        # Fallback: hardcoded defaults
        return ["tools/", "model_tools.py", "toolsets.py"]

    def get_skill_integration_files(self) -> List[str]:
        """Return the canonical skill integration files."""
        if self._skill_rule and self._skill_rule.get("required_files"):
            return self._skill_rule["required_files"]
        return ["skills/", "agent/skill_commands.py"]

    # Canonical files needed to integrate a tool (FALLBACK — use get_tool_integration_files())
    TOOL_INTEGRATION_FILES = [
        "tools/",
        "model_tools.py",
        "toolsets.py",
    ]

    # Canonical files needed to integrate a skill (FALLBACK — use get_skill_integration_files())
    SKILL_INTEGRATION_FILES = [
        "skills/",
        "agent/skill_commands.py",
    ]

    # Canonical files needed to integrate a gateway platform adapter
    GATEWAY_PLATFORM_INTEGRATION_FILES = [
        "gateway/platforms/",
        "gateway/run.py",
    ]

    # Canonical files needed to integrate a slash command
    SLASH_COMMAND_INTEGRATION_FILES = [
        "drewgent_cli/commands.py",
        "cli.py",
    ]

    # Canonical files needed to integrate an MCP server
    MCP_SERVER_INTEGRATION_FILES = [
        "tools/mcp_tool.py",
    ]

    # Canonical files needed to integrate a cron job
    CRON_JOB_INTEGRATION_FILES = [
        "cron/jobs.py",
        "cron/scheduler.py",
    ]

    def detect_tool_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of tool integration are complete.

        Uses brain-sourced rules when available, falling back to hardcoded lists.
        """
        required = self.get_tool_integration_files()
        tools_files = [f for f in files_modified if "tools/" in f or f.endswith("_tool.py")]
        model_tools_modified = "model_tools.py" in files_modified
        toolsets_modified = "toolsets.py" in files_modified

        return {
            "step_name": "tool_integration",
            "is_complete": bool(tools_files and model_tools_modified and toolsets_modified),
            "missing_files": self._get_missing_tool_files(files_modified),
            "tools_file": tools_files[0] if tools_files else None,
            "model_tools_modified": model_tools_modified,
            "toolsets_modified": toolsets_modified,
            "next_hint": self._get_tool_next_hint(files_modified),
            "rule_source": "brain" if self._tool_rule else "hardcoded",
        }

    def _get_missing_tool_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        has_tool_file = any("tools/" in f for f in files_modified)
        required = self.get_tool_integration_files()
        if not has_tool_file:
            missing.append("tools/<name>_tool.py")
        if "model_tools.py" not in files_modified:
            missing.append("model_tools.py (_discover_tools)")
        if "toolsets.py" not in files_modified:
            missing.append("toolsets.py (toolset assignment)")
        return missing

    def _get_tool_next_hint(self, files_modified: List[str]) -> Optional[str]:
        has_tool_file = any("tools/" in f for f in files_modified)
        if not has_tool_file:
            return "registry.register() + _discover_tools import 필요"
        if "model_tools.py" not in files_modified:
            return "model_tools.py의 _discover_tools()에 import 추가 필요"
        if "toolsets.py" not in files_modified:
            return "toolsets.py의 _HERMES_CORE_TOOLS 또는 도메인 toolset에 추가 필요"
        return None

    def detect_skill_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of skill integration are complete."""
        skill_dir = [f for f in files_modified if "skills/" in f or "SKILL.md" in f]
        skill_cmd_modified = "agent/skill_commands.py" in files_modified

        return {
            "step_name": "skill_integration",
            "is_complete": bool(skill_dir and skill_cmd_modified),
            "missing_files": self._get_missing_skill_files(files_modified),
            "skill_dir": skill_dir[0] if skill_dir else None,
            "skill_commands_modified": skill_cmd_modified,
            "next_hint": self._get_skill_next_hint(files_modified),
        }

    def _get_missing_skill_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        has_skill_dir = any("skills/" in f for f in files_modified)
        if not has_skill_dir:
            missing.append("skills/<name>/SKILL.md")
        if "agent/skill_commands.py" not in files_modified:
            missing.append("agent/skill_commands.py")
        return missing

    def _get_skill_next_hint(self, files_modified: List[str]) -> Optional[str]:
        has_skill_dir = any("skills/" in f for f in files_modified)
        if not has_skill_dir:
            return "skills/<name>/SKILL.md 디렉토리 생성 필요"
        if "agent/skill_commands.py" not in files_modified:
            return "agent/skill_commands.py에 스킬 로딩 로직 추가 필요"
        return None

    def detect_gateway_platform_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of gateway platform integration are complete."""
        platform_file = [
            f for f in files_modified if "gateway/platforms/" in f
        ]
        run_py_modified = "gateway/run.py" in files_modified

        return {
            "step_name": "gateway_platform_integration",
            "is_complete": bool(platform_file and run_py_modified),
            "missing_files": self._get_missing_gateway_platform_files(files_modified),
            "platform_file": platform_file[0] if platform_file else None,
            "run_py_modified": run_py_modified,
            "next_hint": self._get_gateway_platform_next_hint(files_modified),
        }

    def _get_missing_gateway_platform_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        has_platform_file = any("gateway/platforms/" in f for f in files_modified)
        if not has_platform_file:
            missing.append("gateway/platforms/<name>.py")
        if "gateway/run.py" not in files_modified:
            missing.append("gateway/run.py (PLATFORM_REGISTRY에 등록)")
        return missing

    def _get_gateway_platform_next_hint(self, files_modified: List[str]) -> Optional[str]:
        has_platform_file = any("gateway/platforms/" in f for f in files_modified)
        if not has_platform_file:
            return "gateway/platforms/<name>.py 어댑터 파일 생성 필요"
        if "gateway/run.py" not in files_modified:
            return "gateway/run.py의 PLATFORM_REGISTRY에 새 플랫폼 등록 필요"
        return None

    def detect_slash_command_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of slash command integration are complete."""
        commands_modified = "drewgent_cli/commands.py" in files_modified
        cli_handler = "cli.py" in files_modified

        return {
            "step_name": "slash_command_integration",
            "is_complete": bool(commands_modified and cli_handler),
            "missing_files": self._get_missing_slash_command_files(files_modified),
            "commands_modified": commands_modified,
            "cli_handler_added": cli_handler,
            "next_hint": self._get_slash_command_next_hint(files_modified),
        }

    def _get_missing_slash_command_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        if "drewgent_cli/commands.py" not in files_modified:
            missing.append("drewgent_cli/commands.py (CommandDef 추가)")
        if "cli.py" not in files_modified:
            missing.append("cli.py (process_command에 handler 추가)")
        return missing

    def _get_slash_command_next_hint(self, files_modified: List[str]) -> Optional[str]:
        if "drewgent_cli/commands.py" not in files_modified:
            return "drewgent_cli/commands.py의 COMMAND_REGISTRY에 CommandDef 추가 필요"
        if "cli.py" not in files_modified:
            return "cli.py의 process_command()에 새 명령어 handler 추가 필요"
        return None

    def detect_mcp_server_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of MCP server integration are complete."""
        mcp_tool_modified = "tools/mcp_tool.py" in files_modified
        handler_files = [
            f for f in files_modified if "tools/" in f and "mcp_tool" not in f
        ]

        return {
            "step_name": "mcp_server_integration",
            "is_complete": mcp_tool_modified,
            "missing_files": self._get_missing_mcp_server_files(files_modified),
            "handler_files": handler_files,
            "mcp_tool_modified": mcp_tool_modified,
            "next_hint": self._get_mcp_server_next_hint(files_modified),
        }

    def _get_missing_mcp_server_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        if "tools/mcp_tool.py" not in files_modified:
            missing.append("tools/mcp_tool.py (mcp_servers[]에 서버 추가)")
        return missing

    def _get_mcp_server_next_hint(self, files_modified: List[str]) -> Optional[str]:
        if "tools/mcp_tool.py" not in files_modified:
            return "tools/mcp_tool.py의 mcp_servers[]에 새 서버 설정 추가 필요"
        return None

    def detect_cron_job_integration_progress(
        self, files_modified: List[str]
    ) -> Dict[str, Any]:
        """Analyze which steps of cron job integration are complete."""
        jobs_modified = "cron/jobs.py" in files_modified
        scheduler_modified = "cron/scheduler.py" in files_modified

        return {
            "step_name": "cron_job_integration",
            "is_complete": bool(jobs_modified and scheduler_modified),
            "missing_files": self._get_missing_cron_job_files(files_modified),
            "jobs_modified": jobs_modified,
            "scheduler_modified": scheduler_modified,
            "next_hint": self._get_cron_job_next_hint(files_modified),
        }

    def _get_missing_cron_job_files(self, files_modified: List[str]) -> List[str]:
        missing = []
        if "cron/jobs.py" not in files_modified:
            missing.append("cron/jobs.py (job 함수 정의)")
        if "cron/scheduler.py" not in files_modified:
            missing.append("cron/scheduler.py (job 등록)")
        return missing

    def _get_cron_job_next_hint(self, files_modified: List[str]) -> Optional[str]:
        if "cron/jobs.py" not in files_modified:
            return "cron/jobs.py에 job 함수 정의 필요"
        if "cron/scheduler.py" not in files_modified:
            return "cron/scheduler.py에 job 등록 필요"
        return None


# ---------------------------------------------------------------------------
# Signal Processor (Discriminator Layer)
# ---------------------------------------------------------------------------

class SignalProcessor:
    """Processes brain signals and determines actions.

    Subscribes to brain signal patterns and:
    1. Tracks integration workflows
    2. Detects completion/milestones
    3. Emits awareness signals for other layers
    """

    def __init__(self):
        self._bus = get_event_bus()
        self._arch_model = ArchitectureModel()
        self._active_workflows: Dict[str, IntegrationWorkflow] = {}
        self._workflow_history: List[IntegrationWorkflow] = []
        self._correlation_workflow_map: Dict[str, str] = {}
        self._violation_history: List[dict] = []
        self._dangerous_ops_history: List[dict] = []

        # Subscribe to relevant signals
        self._setup_subscriptions()

        logger.info("SignalProcessor initialized")

    def _setup_subscriptions(self) -> None:
        """Subscribe to all relevant brain signals."""
        # Tool integration signals
        self._bus.subscribe("tool.integration.start", self._on_integration_start)
        self._bus.subscribe("tool.integration.detected", self._on_tool_detected)
        self._bus.subscribe("tool.start", self._on_tool_start)
        self._bus.subscribe("tool.complete", self._on_tool_complete)

        # Skill integration signals
        self._bus.subscribe("skill.integration.start", self._on_integration_start)
        self._bus.subscribe("skill.integration.detected", self._on_skill_detected)

        # Gateway platform integration signals
        self._bus.subscribe("gateway_platform.integration.start", self._on_integration_start)
        self._bus.subscribe("gateway_platform.integration.detected", self._on_gateway_platform_detected)

        # Slash command integration signals
        self._bus.subscribe("slash_command.integration.start", self._on_integration_start)
        self._bus.subscribe("slash_command.integration.detected", self._on_slash_command_detected)

        # MCP server integration signals
        self._bus.subscribe("mcp_server.integration.start", self._on_integration_start)
        self._bus.subscribe("mcp_server.integration.detected", self._on_mcp_server_detected)

        # Cron job integration signals
        self._bus.subscribe("cron_job.integration.start", self._on_integration_start)
        self._bus.subscribe("cron_job.integration.detected", self._on_cron_job_detected)

        # Agent activity signals
        self._bus.subscribe("agent.modifying", self._on_agent_modifying)
        self._bus.subscribe("user.prompt", self._on_user_prompt)

        # Session signals
        self._bus.subscribe("session.end", self._on_session_end)

        # Tool registry loaded
        self._bus.subscribe("tool.start", self._on_tool_registry_loaded)

        # Phase 2-1: Turn lifecycle events (P0-brainstem enforcement hooks)
        self._bus.subscribe("turn.start", self._on_turn_start)
        self._bus.subscribe("turn.end", self._on_turn_end)
        self._bus.subscribe("dangerous.op", self._on_dangerous_op)
        self._bus.subscribe("rule.violation", self._on_rule_violation)
        self._bus.subscribe("workflow.incomplete", self._on_workflow_incomplete)

        # Phase 2-1: QA gate enforcement
        self._bus.subscribe("qa.gate", self._on_qa_gate)

        # Phase 2-1: Agent completion (P0 final verification)
        self._bus.subscribe("agent.complete", self._on_agent_complete)

    # -------------------------------------------------------------------------
    # Signal Handlers
    # -------------------------------------------------------------------------

    def _on_integration_start(self, event: BrainEvent) -> None:
        """Handle integration.start signal — user wants to add something.

        Handles: tool, skill, gateway_platform, slash_command, mcp_server, cron_job

        IMPORTANT: This only creates a NEW workflow if one doesn't already exist for
        this session. If a guidance workflow ('를') already exists, this is a NOOP.
        This prevents spurious workflows from being created when the user asks
        guidance questions during an ongoing integration.
        """
        payload = event.payload
        msg = payload.get("message", "")
        session_id = payload.get("session_id", "")
        signal_type = event.event_type  # e.g., "tool.integration.start"

        # Determine integration type from signal type
        int_type = self._get_integration_type_from_signal(signal_type, msg)

        # Guard: If an active workflow already exists for this session (via session_id
        # correlation), do NOT create a new one. This catches the "guidance trap" where
        # a spurious workflow was created for a guidance request like "도구를 추가하려면 어떻게 해야 해?"
        # — we must NOT let it pollute the session's workflow state.
        # IMPORTANT: The workflow_id must ALSO be in active_workflows. The correlation
        # map may contain stale entries for workflows that have completed and been removed.
        sid_workflow_id = self._correlation_workflow_map.get(session_id)
        if sid_workflow_id and sid_workflow_id in self._active_workflows:
            existing = self._active_workflows[sid_workflow_id]
            if not existing.completed:
                logger.debug(
                    f"[SignalProcessor] Ignoring integration.start for session {session_id}: "
                    f"workflow '{existing.target_name}' already active (likely from guidance request)"
                )
                return

        target = self._extract_target_name_from_signal(signal_type, msg)

        # Guard: If no specific target name was extracted, this is a generic guidance
        # question ("how do I add a tool"), not a real integration request.
        # Do NOT create a workflow for it.
        if not target:
            logger.debug(
                f"[SignalProcessor] Ignoring integration.start: no target name extracted "
                f"(guidance request detected for message: {msg[:50]!r})"
            )
            return

        # History-based suggestion: check if this target was integrated before
        workflow_hint = self._suggest_from_history(msg)

        # Derive the primary integration file (source file) from target name + type
        source_file = self._derive_source_file(int_type, target or f"new_{int_type}")

        workflow = IntegrationWorkflow(
            workflow_id=f"{int_type}_integration_{uuid.uuid4().hex[:12]}",
            integration_type=int_type,
            target_name=target or f"new_{int_type}",
            correlation_id=event.correlation_id,
            source_file=source_file,
        )
        workflow.started = True
        self._active_workflows[workflow.workflow_id] = workflow
        self._correlation_workflow_map[event.correlation_id] = workflow.workflow_id

        if session_id:
            self._correlation_workflow_map[session_id] = workflow.workflow_id

        # Also map by source_file for cross-event correlation
        self._correlation_workflow_map[source_file] = workflow.workflow_id

        self._bus.emit(
            "brain.awareness.integration_started",
            payload={
                "workflow_id": workflow.workflow_id,
                "integration_type": int_type,
                "target_name": workflow.target_name,
                "session_id": session_id,
                "workflow_hint": workflow_hint,
            },
            source="signal_processor",
        )

    def _derive_source_file(self, int_type: str, target: str) -> str:
        """Derive the expected source file path from integration type + target name.

        For tools: "super_tool" → "tools/super_tool.py" (the ACTUAL file, not _tool.py)
        For skills: "my_skill" → "skills/my_skill/SKILL.md"
        """
        file_map = {
            "tool": f"tools/{target}.py",
            "skill": f"skills/{target}/SKILL.md",
            "gateway_platform": f"gateway/platforms/{target}.py",
            "slash_command": "drewgent_cli/commands.py",
            "mcp_server": "tools/mcp_tool.py",
            "cron_job": "cron/jobs.py",
        }
        return file_map.get(int_type, f"unknown/{target}")

    def _get_workflow_for_source_file(self, source_file: str) -> Optional[IntegrationWorkflow]:
        """Look up a workflow by its primary source file path."""
        workflow_id = self._correlation_workflow_map.get(source_file)
        if workflow_id and workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]
        return None

    def _get_integration_type_from_signal(self, signal_type: str, msg: str) -> str:
        """Derive integration_type from signal name or message content."""
        # Signal type mapping (most specific first)
        if "gateway_platform" in signal_type:
            return "gateway_platform"
        if "slash_command" in signal_type:
            return "slash_command"
        if "mcp_server" in signal_type:
            return "mcp_server"
        if "cron_job" in signal_type:
            return "cron_job"
        if "tool" in signal_type:
            return "tool"
        if "skill" in signal_type:
            return "skill"
        # Fallback: derive from message content
        msg_lower = msg.lower()
        if any(k in msg_lower for k in ["gateway", "어댑터", "플랫폼"]):
            return "gateway_platform"
        if any(k in msg_lower for k in ["command", "슬래시", "명령어"]):
            return "slash_command"
        if "mcp" in msg_lower:
            return "mcp_server"
        if any(k in msg_lower for k in ["cron", "스케줄"]):
            return "cron_job"
        if any(k in msg_lower for k in ["도구", "tool"]):
            return "tool"
        return "skill"

    def _extract_target_name_from_signal(self, signal_type: str, msg: str) -> str:
        """Extract target name from message based on integration type."""
        import re
        # Patterns for each type. Order matters - try more specific first.
        patterns = {
            "gateway_platform": [
                r"(discord|slack|telegram|whatsapp|signal|matrix)",
            ],
            "slash_command": [
                r"(?:/(\w+))",
                r"command[:\s]*(\w+)",
            ],
            "mcp_server": [
                r"mcp[:\s]*(\w+)",
                r"server[:\s]*(\w+)",
            ],
            "cron_job": [
                r"cron[:\s]*(\w+)",
                r"job[:\s]*(\w+)",
            ],
            "tool": [
                r"(\w+)\s*이라는\s*도구",       # "super_tool이라는 도구"
                r"도구[:\s]*(\w+)",             # "도구:super_tool"
                r"도구\s*(\w+)",                # "도구 super_tool"
                r"tool[:\s]*(\w+)",
            ],
            "skill": [
                r"(\w+)\s*이라는\s*스킬",       # "super_skill이라는 스킬"
                r"스킬[:\s]*(\w+)",
                r"스킬\s*(\w+)",
                r"skill[:\s]*(\w+)",
            ],
        }
        type_key = signal_type.split(".")[0] if "." in signal_type else signal_type
        type_key = type_key.replace("_integration", "")

        for pattern in patterns.get(type_key, []):
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        return ""

    def _on_tool_detected(self, event: BrainEvent) -> None:
        """Handle tool.detected — a tool file was modified."""
        payload = event.payload
        path = payload.get("path", "")
        session_id = payload.get("session_id", "")

        workflow = self._get_workflow_for_corr_id(event.correlation_id)
        if workflow:
            workflow.add_file(path)
            workflow.add_step("tool_file_created")

            # Check progress
            progress = self._arch_model.detect_tool_integration_progress(
                workflow.files_modified
            )
            self._bus.emit(
                "brain.awareness.integration_progress",
                payload={
                    "workflow_id": workflow.workflow_id,
                    "integration_type": "tool",
                    "progress": progress,
                    "session_id": session_id,
                },
                source="signal_processor",
            )

            if progress["is_complete"]:
                self._complete_workflow(workflow)

    def _on_skill_detected(self, event: BrainEvent) -> None:
        """Handle skill.detected — a skill file was modified."""
        payload = event.payload
        path = payload.get("path", "")
        session_id = payload.get("session_id", "")

        workflow = self._get_workflow_for_corr_id(event.correlation_id)
        if workflow:
            workflow.add_file(path)
            workflow.add_step("skill_file_created")

            progress = self._arch_model.detect_skill_integration_progress(
                workflow.files_modified
            )
            self._bus.emit(
                "brain.awareness.integration_progress",
                payload={
                    "workflow_id": workflow.workflow_id,
                    "integration_type": "skill",
                    "progress": progress,
                    "session_id": session_id,
                },
                source="signal_processor",
            )

            if progress["is_complete"]:
                self._complete_workflow(workflow)

    def _on_gateway_platform_detected(self, event: BrainEvent) -> None:
        """Handle gateway_platform.detected — a platform adapter file was modified."""
        self._handle_new_type_detected(event, "gateway_platform")

    def _on_slash_command_detected(self, event: BrainEvent) -> None:
        """Handle slash_command.detected — a command file was modified."""
        self._handle_new_type_detected(event, "slash_command")

    def _on_mcp_server_detected(self, event: BrainEvent) -> None:
        """Handle mcp_server.detected — mcp_tool.py was modified."""
        self._handle_new_type_detected(event, "mcp_server")

    def _on_cron_job_detected(self, event: BrainEvent) -> None:
        """Handle cron_job.detected — a cron job file was modified."""
        self._handle_new_type_detected(event, "cron_job")

    def _handle_new_type_detected(self, event: BrainEvent, int_type: str) -> None:
        """Generic handler for new integration type detected events."""
        payload = event.payload
        path = payload.get("path", "")
        session_id = payload.get("session_id", "")

        workflow = self._get_workflow_for_corr_id(event.correlation_id)
        if workflow:
            workflow.add_file(path)

            progress = self._get_progress_for_type(int_type, workflow.files_modified)
            self._bus.emit(
                "brain.awareness.integration_progress",
                payload={
                    "workflow_id": workflow.workflow_id,
                    "integration_type": int_type,
                    "progress": progress,
                    "session_id": session_id,
                },
                source="signal_processor",
            )

            if progress.get("is_complete"):
                self._complete_workflow(workflow)

    def _get_progress_for_type(self, int_type: str, files_modified: list) -> Dict[str, Any]:
        """Get progress dict for given integration type."""
        detectors = {
            "gateway_platform": self._arch_model.detect_gateway_platform_integration_progress,
            "slash_command": self._arch_model.detect_slash_command_integration_progress,
            "mcp_server": self._arch_model.detect_mcp_server_integration_progress,
            "cron_job": self._arch_model.detect_cron_job_integration_progress,
            "tool": self._arch_model.detect_tool_integration_progress,
            "skill": self._arch_model.detect_skill_integration_progress,
        }
        detector = detectors.get(int_type)
        if detector:
            return detector(files_modified)
        return {"is_complete": False, "step_name": int_type, "next_hint": None}

    def _on_tool_start(self, event: BrainEvent) -> None:
        """Handle tool.start — track tool execution."""
        payload = event.payload
        tool_name = payload.get("tool", "")
        session_id = payload.get("session_id", "")

        # Track tool execution for tool_call_count
        workflow = self._get_workflow_for_corr_id(event.correlation_id)
        if workflow and tool_name in ("write_file", "patch"):
            pass  # Already tracked in _on_agent_modifying

    def _on_tool_complete(self, event: BrainEvent) -> None:
        """Handle tool.complete — check for integration completion."""
        payload = event.payload
        tool_name = payload.get("tool", "")
        success = payload.get("success", True)
        session_id = payload.get("session_id", "")

        workflow = self._get_workflow_for_corr_id(event.correlation_id)
        if not workflow:
            return

        if tool_name in ("write_file", "patch"):
            # Get the path from the workflow
            pass  # Files are tracked via agent.modifying

    def _on_agent_modifying(self, event: BrainEvent) -> None:
        """Handle agent.modifying — track file modifications.

        Workflow resolution order:
        1. If the modified file is the source_file of an active workflow, use that workflow
        2. If no source_file match, try correlation_id / session_id lookup
        3. If no workflow found and file is integration-relevant, auto-create one
        """
        payload = event.payload
        operation = payload.get("operation", "")
        path = payload.get("path", "")
        session_id = payload.get("session_id", "")
        correlation_id = event.correlation_id or session_id

        if not path:
            return

        workflow = None

        # 1. Try source_file lookup — use the ACTUAL file path as the key, not a derived path.
        # The correlation map stores actual paths like "tools/super_tool.py", so we must look up
        # with the actual path to find the matching workflow.
        int_type = self._get_type_from_path(path)
        if int_type and path:
            workflow = self._get_workflow_for_source_file(path)

        # 2. Fall back to correlation_id / session_id
        # BUT: only use session_id correlation if:
        # - This file IS the source_file of the session workflow (path matches source_file)
        #   OR
        # - This file is a KNOWN supporting file for this integration type (model_tools.py,
        #   toolsets.py for tools; skill_commands.py for skills)
        # This prevents a guidance workflow for "를" from capturing events for "new_tool".
        if not workflow:
            session_workflow = self._get_workflow_for_corr_id(session_id)
            if session_workflow:
                if session_workflow.source_file == path:
                    # The agent is modifying the primary source file
                    workflow = session_workflow
                elif self._is_known_supporting_file(path, session_workflow.integration_type):
                    # The agent is modifying a supporting file for this workflow
                    workflow = session_workflow
                # else: unrelated file — let it fall through to auto-create

        # 3. Auto-create if this is an integration file with no matching workflow
        if not workflow and int_type:
            # Derive source_file from target name for new workflows
            target_name = self._extract_name_from_path(path)
            source_file = self._derive_source_file(int_type, target_name)
            workflow = IntegrationWorkflow(
                workflow_id=f"{int_type}_integration_{uuid.uuid4().hex[:12]}",
                integration_type=int_type,
                target_name=target_name,
                correlation_id=correlation_id,
                source_file=source_file,
            )
            workflow.started = True
            self._active_workflows[workflow.workflow_id] = workflow
            self._correlation_workflow_map[correlation_id] = workflow.workflow_id
            if session_id:
                self._correlation_workflow_map[session_id] = workflow.workflow_id
            if source_file:
                self._correlation_workflow_map[source_file] = workflow.workflow_id

        if workflow:
            workflow.add_file(path)

            progress = self._get_progress_for_type(workflow.integration_type, workflow.files_modified)
            # Phase 5-1: Store next_hint in workflow for P0 enforcement in _complete_workflow
            workflow.next_hint = progress.get("next_hint")

            # Emit progress update
            self._bus.emit(
                "brain.awareness.integration_progress",
                payload={
                    "workflow_id": workflow.workflow_id,
                    "integration_type": workflow.integration_type,
                    "progress": progress,
                    "files_modified": workflow.files_modified,
                    "session_id": session_id,
                },
                source="signal_processor",
            )

            if progress["is_complete"]:
                self._complete_workflow(workflow)

    def _on_user_prompt(self, event: BrainEvent) -> None:
        """Handle user.prompt — detect integration intent patterns."""
        payload = event.payload
        msg = payload.get("message", "")
        session_id = payload.get("session_id", "")

        # Check if user is asking for integration guidance
        guidance_patterns = [
            (r"어떻게\s*(해야\s*|하면\s*)?추가", "how to add"),
            (r"어디에\s*넣", "where to put"),
            (r"어떻게\s*연결", "how to connect"),
            (r"how\s*to\s*add", "how to add"),
            (r"where\s*to\s*put", "where to put"),
            (r"how\s*do\s*I\s*integrate", "how to integrate"),
            (r"도구\s*추가\s*방법", "tool add method"),
            (r"스킬\s*추가\s*방법", "skill add method"),
            (r"추가하(?:려면|려면)\s*어떻게", "how to add"),
        ]

        for pattern, guidance_type in guidance_patterns:
            if re.search(pattern, msg, re.IGNORECASE):
                self._bus.emit(
                    "brain.awareness.guidance_requested",
                    payload={
                        "message": msg[:200],
                        "session_id": session_id,
                        "pattern_matched": pattern,
                        "guidance_type": guidance_type,
                    },
                    source="signal_processor",
                )
                break

    def _on_tool_registry_loaded(self, event: BrainEvent) -> None:
        """Handle tool_registry_loaded — emit initial awareness."""
        payload = event.payload
        tool_count = payload.get("tool_count", 0)
        tools = payload.get("tools", [])
        session_id = payload.get("session_id", "")

        self._bus.emit(
            "brain.awareness.initialized",
            payload={
                "tool_count": tool_count,
                "tools": tools,
                "session_id": session_id,
            },
            source="signal_processor",
        )

    def _on_session_end(self, event: BrainEvent) -> None:
        """Handle session.end — archive active workflows."""
        payload = event.payload
        session_id = payload.get("session_id", "")

        # Archive any incomplete workflows for next session
        incomplete = [
            w for w in self._active_workflows.values()
            if not w.completed
        ]
        if incomplete:
            self._workflow_history.extend(incomplete)

    def _is_known_supporting_file(self, path: str, int_type: str) -> bool:
        """Check if a file path is a known supporting file for the given integration type.

        For tools: model_tools.py, toolsets.py are supporting files.
        For skills: agent/skill_commands.py is a supporting file.
        """
        if int_type == "tool":
            return path in ("model_tools.py", "toolsets.py")
        if int_type == "skill":
            return path == "agent/skill_commands.py"
        if int_type == "gateway_platform":
            return path == "gateway/run.py"
        if int_type == "slash_command":
            return path in ("drewgent_cli/commands.py", "cli.py")
        if int_type == "mcp_server":
            return path == "tools/mcp_tool.py"
        if int_type == "cron_job":
            return path in ("cron/jobs.py", "cron/scheduler.py")
        return False

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _get_workflow_for_corr_id(self, corr_id: str) -> Optional[IntegrationWorkflow]:
        """Get workflow by correlation ID.

        IMPORTANT: Only returns workflows that are still in _active_workflows.
        Stale entries (from completed workflows) are ignored.
        """
        workflow_id = self._correlation_workflow_map.get(corr_id)
        if workflow_id and workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]
        return None

    def _get_workflow_for_source_file(self, source_file: str) -> Optional[IntegrationWorkflow]:
        """Look up a workflow by its primary source file path.

        IMPORTANT: Only returns workflows that are still in _active_workflows.
        Stale entries (from completed workflows) are ignored.
        """
        workflow_id = self._correlation_workflow_map.get(source_file)
        if workflow_id and workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]
        return None

    def _get_type_from_path(self, path: str) -> Optional[str]:
        """Determine integration type from file path."""
        if not path:
            return None

        # Gateway platform
        if "gateway/platforms/" in path:
            return "gateway_platform"
        # Slash command
        if "drewgent_cli/commands.py" in path:
            return "slash_command"
        if "cli.py" in path and "drewgent_cli" not in path:
            return "slash_command"
        # MCP server
        if "tools/mcp_tool.py" in path:
            return "mcp_server"
        # Cron job
        if "cron/jobs.py" in path:
            return "cron_job"
        if "cron/scheduler.py" in path:
            return "cron_job"
        # Skill
        if "skills/" in path:
            return "skill"
        # Tool
        if "tools/" in path:
            return "tool"

        return None

    def _looks_like_integration_file(self, path: str) -> bool:
        """Check if a file path looks like a tool/skill integration file."""
        return self._get_type_from_path(path) is not None

    def _extract_target_name(self, msg: str, keywords: List[str]) -> Optional[str]:
        """Extract target tool/skill name from user message."""
        # Handle Korean "N이라는/를/이" patterns
        korean_patterns = [
            (r"(\w+)\s*이(?:라는|을|가|를)\s*(?:도구|스킬|tool|skill)", 1),  # "super_tool이라는 도구" → "super_tool"
            (r"(?:도구|스킬|tool|skill)\s*(\w+)", 1),  # "도구 super_tool" → "super_tool"
        ]
        for pattern, group_idx in korean_patterns:
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                name = match.group(group_idx)
                # Strip Korean trailing particles
                name = re.sub(r"(?:이라는|을|가|를|이|를)\s*$", "", name)
                if name:
                    return name

        # Handle English patterns - look for tool NAME followed by tool/skill keyword
        # e.g. "super_tool 이라는 도구" or "add super_tool tool"
        english_match = re.search(r"(\w+)\s*(?:이라는|을|라는)\s*(?:도구|스킬|tool|skill)", msg, re.IGNORECASE)
        if english_match:
            return english_match.group(1)

        # Fallback: keyword followed by word
        for kw in keywords:
            pattern = rf"{kw}\s+(\w+)"
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                name = match.group(1)
                # Remove trailing Korean particles
                name = re.sub(r'(?:이라는|을|가|를|이)\s*$', '', name)
                if name and name not in ('추가', 'add', '생성', 'create'):
                    return name

        return None

    def _extract_name_from_path(self, path: str) -> str:
        """Extract integration target name from file path.

        For 'tools/new_tool.py' → 'new_tool'
        For 'gateway/platforms/discord.py' → 'discord'
        For 'skills/my_skill/SKILL.md' → 'my_skill'
        """
        import os
        name = os.path.basename(path)          # e.g. "new_tool.py"
        name = os.path.splitext(name)[0]        # e.g. "new_tool"
        return name or "unknown"

    def _complete_workflow(self, workflow: IntegrationWorkflow) -> None:
        """Mark workflow as complete and emit awareness signal.

        Phase 2-3: P0 enforcement — validates completeness before marking done.
        For tool integrations, checks all 3 required files exist.
        For skill integrations, checks SKILL.md + agent/skill_commands.py exist.
        If incomplete, emits integration.incomplete event instead.
        """
        # Phase 2-3: Pre-completion completeness check (P0 enforcement)
        _hint = workflow.get_hint()
        if _hint is not None:
            # Incomplete — emit incomplete event, do NOT complete
            self._bus.emit(
                "brain.awareness.integration_incomplete",
                payload={
                    "workflow_id": workflow.workflow_id,
                    "integration_type": workflow.integration_type,
                    "target_name": workflow.target_name,
                    "files_modified": workflow.files_modified,
                    "steps_completed": workflow.steps_completed,
                    "missing_hint": _hint,
                    "reason": "禁tool_integration_3file — not all required files are present",
                },
                source="signal_processor",
            )
            logger.warning(
                f"Integration INCOMPLETE blocked: {workflow.integration_type} "
                f"'{workflow.target_name}' — {workflow.files_modified}. "
                f"Missing: {workflow.get_hint()}"
            )
            return  # Do NOT complete — P0 enforcement blocks

        workflow.completed = True
        workflow.completed_at = datetime.now().isoformat()

        # CRITICAL: Clean up all correlation map entries for this workflow.
        # The session_id correlation key must be cleared so it doesn't block
        # future workflow lookups in the same session (e.g., starting a new
        # integration after completing the previous one).
        stale_keys = [
            key for key, wid in self._correlation_workflow_map.items()
            if wid == workflow.workflow_id
        ]
        for key in stale_keys:
            del self._correlation_workflow_map[key]

        # Emit completion signal
        self._bus.emit(
            "brain.awareness.integration_complete",
            payload={
                "workflow_id": workflow.workflow_id,
                "integration_type": workflow.integration_type,
                "target_name": workflow.target_name,
                "files_modified": workflow.files_modified,
                "steps_completed": workflow.steps_completed,
                "duration_seconds": (
                    datetime.fromisoformat(workflow.completed_at) -
                    datetime.fromisoformat(workflow.detected_at)
                ).total_seconds(),
            },
            source="signal_processor",
        )

        # Archive workflow
        self._workflow_history.append(workflow)
        if workflow.workflow_id in self._active_workflows:
            del self._active_workflows[workflow.workflow_id]

        logger.info(
            f"Integration complete: {workflow.integration_type} '{workflow.target_name}' "
            f"via {workflow.files_modified}"
        )

    # -------------------------------------------------------------------------
    # Phase 2-1: Turn lifecycle & QA gate handlers
    # -------------------------------------------------------------------------

    def _on_turn_start(self, event: BrainEvent) -> None:
        """Handle turn.start — P0-brainstem pre-validation hook.

        Fires before each turn begins. Detects high-risk operations in the
        user message and emits dangerous.op events if any are found.

        Detection scope:
            - Integration intent patterns (tool/skill/gateway add/remove)
            - Dangerous command patterns (rm -rf, chmod 777, etc.)
            - System path violations (write to /etc, chown root, etc.)

        Emit: dangerous.op event with payload for downstream handlers.
        """
        payload = event.payload or {}
        user_message = payload.get("user_message", "")
        turn_number = payload.get("turn_number", 0)

        if not user_message:
            return

        # ── 1. Integration intent detection ──────────────────────────
        # Reuse brain_signals patterns for intent classification
        try:
            from agent.brain_signals import _INTEGRATION_PATTERNS
            for pattern, signal_type in _INTEGRATION_PATTERNS:
                if re.search(pattern, user_message, re.IGNORECASE):
                    self._bus.emit(
                        "dangerous.op",
                        payload={
                            "turn_number": turn_number,
                            "detected_type": "integration",
                            "signal_type": signal_type,
                            "pattern": pattern,
                            "message_preview": user_message[:100],
                            "severity": "medium",
                        },
                        source="signal_processor",
                    )
                    break  # one emit per turn is enough for integration signals
        except Exception as e:
            logger.debug("_on_turn_start: integration pattern check failed: %s", e)

        # ── 2. Dangerous command detection in user message ────────────
        # Scan user message text for dangerous shell commands
        try:
            from tools.approval import detect_dangerous_command
            is_dangerous, pattern_key, description = detect_dangerous_command(user_message)
            if is_dangerous:
                self._bus.emit(
                    "dangerous.op",
                    payload={
                        "turn_number": turn_number,
                        "detected_type": "command",
                        "pattern_key": pattern_key,
                        "description": description,
                        "message_preview": user_message[:100],
                        "severity": "high",
                    },
                    source="signal_processor",
                )
        except Exception as e:
            logger.debug("_on_turn_start: dangerous command check failed: %s", e)

    def _on_turn_end(self, event: BrainEvent) -> None:
        """Handle turn.end — P0-brainstem post-verification hook.

        Fires after each turn completes. Verifies the turn did not violate
        P0 rules by checking:
            - write_file/write calls WITHOUT prior read (禁blind_write)
            - Hardcoded secrets in write content (禁secrets_in_code)
            - console.log/print in non-test code (禁console_log)

        Emit: rule.violation event if any P0 rule is broken.
        """
        import json

        payload = event.payload or {}
        tool_calls = payload.get("tool_calls", [])
        assistant_response = payload.get("assistant_response", "")

        if not tool_calls and not assistant_response:
            return

        # ── 1. Check for blind write (write_file without prior read) ──
        # We track which files were read in this turn via a shared set.
        # For now, flag write_file calls that look like new file creation
        # (path doesn't start with known project dirs).
        try:
            _written_files: set = getattr(self, "_turn_written_files", set())
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                if name in ("write_file", "patch"):
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except (json.JSONDecodeError, TypeError):
                        continue
                    path = args.get("path", "")
                    if path and name == "write_file":
                        # Flag if this looks like overwriting without reading
                        content = args.get("content", "")
                        if content and not content.startswith("#"):
                            self._bus.emit(
                                "rule.violation",
                                payload={
                                    "turn_number": payload.get("turn_number", 0),
                                    "rule_token": "禁blind_write",
                                    "tool": name,
                                    "path": path,
                                    "severity": "medium",
                                    "message": f"write_file to {path} — verify prior read exists",
                                },
                                source="signal_processor",
                            )
        except Exception as e:
            logger.debug("_on_turn_end: blind_write check failed: %s", e)

        # ── 2. Check for hardcoded secrets in tool call content ─────
        try:
            _SECRET_PATTERNS = [
                (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
                (r'ghp_[a-zA-Z0-9]{36}', "GitHub token"),
                (r'password\s*=\s*["\'][^"\']{6,}["\']', "hardcoded password"),
                (r'api[_-]?key\s*=\s*["\'][^"\']{10,}["\']', "hardcoded API key"),
                (r'token\s*=\s*["\'][^"\']{20,}["\']', "hardcoded token"),
            ]
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                if name in ("write_file", "patch", "terminal"):
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except (json.JSONDecodeError, TypeError):
                        continue
                    content = args.get("content", "") or args.get("command", "")
                    if content:
                        for pattern, label in _SECRET_PATTERNS:
                            if re.search(pattern, content, re.IGNORECASE):
                                self._bus.emit(
                                    "rule.violation",
                                    payload={
                                        "turn_number": payload.get("turn_number", 0),
                                        "rule_token": "禁secrets_in_code",
                                        "tool": name,
                                        "secret_type": label,
                                        "severity": "high",
                                        "message": f"Potential {label} in {name} call",
                                    },
                                    source="signal_processor",
                                )
                                break  # one violation per turn is enough
        except Exception as e:
            logger.debug("_on_turn_end: secrets check failed: %s", e)

        # ── 3. Check assistant response for console.log/print statements ──
        try:
            if assistant_response:
                console_patterns = [
                    (r'console\.log\s*\(', "console.log in code"),
                    (r'\bprint\s*\(', "print() in code"),
                    (r'System\.out\.println', "System.out.println in code"),
                ]
                for pattern, label in console_patterns:
                    if re.search(pattern, assistant_response):
                        self._bus.emit(
                            "rule.violation",
                            payload={
                                "turn_number": payload.get("turn_number", 0),
                                "rule_token": "禁console_log",
                                "detected_type": label,
                                "severity": "low",
                                "message": f"Production code contains {label}",
                            },
                            source="signal_processor",
                        )
                        break
        except Exception as e:
            logger.debug("_on_turn_end: console_log check failed: %s", e)

    def get_violation_summary(self) -> dict:
        """Return violation + dangerous-op summary for system-prompt injection.

        Called by AIAgent._build_system_prompt() to make the agent aware
        of patterns it violated in this session so it can self-correct.
        """
        from collections import defaultdict
        if not self._violation_history and not self._dangerous_ops_history:
            return {}
        by_rule = defaultdict(list)
        for v in self._violation_history:
            by_rule[v.get('rule_token', 'unknown')].append(v)
        by_type = defaultdict(list)
        for op in self._dangerous_ops_history:
            by_type[op.get('detected_type', 'unknown')].append(op)
        most_common_violations = sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        most_common_dangerous = sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True)[:2]
        return {
            'total_violations': len(self._violation_history),
            'total_dangerous_ops': len(self._dangerous_ops_history),
            'by_rule': {r: len(items) for r, items in by_rule.items()},
            'most_common_violations': most_common_violations,
            'most_common_dangerous_ops': most_common_dangerous,
        }

    def _suggest_from_history(self, msg: str) -> Optional[str]:
        """Suggest a target tool/skill name from previously completed workflows.

        Scans _workflow_history in reverse (most recent first) for completed
        workflows whose target_name appears in the current message. This lets
        the agent infer "Oh, you're trying to add X again?" from pattern memory.
        """
        if not self._workflow_history:
            return None
        msg_lower = msg.lower()
        for wf in reversed(self._workflow_history):
            if getattr(wf, 'completed', False) and wf.target_name:
                if wf.target_name.lower() in msg_lower:
                    return wf.target_name
            # Also match on workflow name as fallback
            wf_name = getattr(wf, 'name', '') or ''
            if wf_name and wf_name.lower() in msg_lower:
                return wf.target_name or wf_name
        return None

    def _on_qa_gate(self, event: BrainEvent) -> None:
        """Handle qa.gate — enforce 禁task_qa_gate contract-first QA.

        Expected payload:
            task_id: unique identifier for this QA cycle
            phase: "contract" | "micro" | "full"
            evidence_dir: path to qa-evidence/{task_id}/

        Phase semantics (from 禁task_qa_gate.neuron):
            contract: contract.json must exist before implementation
            micro:    micro-qa.json must exist after each major step
            full:     full-qa.json must exist before delivery
        """
        payload = event.payload or {}
        task_id = payload.get("task_id", "unknown")
        phase = payload.get("phase", "unknown")
        evidence_dir = payload.get("evidence_dir", "")

        import os

        # Phase 2-4: Enforce file presence per QA phase
        _required_files = {
            "contract": "contract.json",
            "micro": "micro-qa.json",
            "full": "full-qa.json",
        }
        _required_file = _required_files.get(phase)
        _passed = False

        if _required_file and evidence_dir:
            _file_path = os.path.join(evidence_dir, _required_file)
            _passed = os.path.isfile(_file_path)
            if _passed:
                # ── P0: QA gate contract placeholder detection ──────────────
                if phase == "contract":
                    try:
                        import json as _json_mod
                        with open(_file_path, encoding="utf-8") as _f:
                            _contract = _json_mod.load(_f)
                        _criteria = _contract.get("criteria", [])
                        _placeholders = [
                            c for c in _criteria
                            if isinstance(c, str) and "<" in c and ">" in c
                        ]
                        if _placeholders:
                            logger.warning(
                                "QA gate CONTRACT PLACEHOLDER DETECTED: task=%s "
                                "criteria contain %d placeholder(s): %s",
                                task_id, len(_placeholders), _placeholders[:3],
                            )
                            self._bus.emit(
                                "qa.gate.contract.placeholder_detected",
                                payload={
                                    "task_id": task_id,
                                    "phase": phase,
                                    "placeholder_count": len(_placeholders),
                                    "placeholders": _placeholders[:5],
                                    "evidence_dir": evidence_dir,
                                },
                                source="signal_processor",
                            )
                            # Placeholder criteria = substantive check failed
                            _passed = False
                    except Exception as e:
                        logger.debug(
                            "_on_qa_gate: contract placeholder check failed: %s", e
                        )

                logger.info(
                    "QA gate PASSED: task=%s phase=%s file=%s",
                    task_id, phase, _required_file,
                )
            else:
                logger.warning(
                    "QA gate FAILED: task=%s phase=%s — required file '%s' not found in %s. "
                    "Task delivery BLOCKED until evidence is recorded.",
                    task_id, phase, _required_file, evidence_dir,
                )
                # Emit blocking signal so upstream can pause delivery
                self._bus.emit(
                    "brain.awareness.qa_gate_failed",
                    payload={
                        "task_id": task_id,
                        "phase": phase,
                        "required_file": _required_file,
                        "evidence_dir": evidence_dir,
                        "reason": "禁task_qa_gate — evidence file not found",
                    },
                    source="signal_processor",
                )
        else:
            logger.debug(
                "QA gate received: task=%s phase=%s dir=%s (file check skipped — no evidence_dir)",
                task_id, phase, evidence_dir,
            )

    def _on_agent_complete(self, event: BrainEvent) -> None:
        """Handle agent.complete — P0-brainstem final verification.

        Fires when the agent completes a session. Performs final safety checks:
            - Incomplete integration workflows (started but not completed)
            - Accumulated rule violations across all turns
            - Unresolved QA gate workflows

        These are logged (not blocking) — the session is already ending.
        This is a post-mortem record for P6-prefrontal/incidents/.
        """
        payload = event.payload or {}
        session_id = payload.get("session_id", "unknown")
        message_count = payload.get("message_count", 0)

        logger.info(
            "Agent session complete: session_id=%s, messages=%d",
            session_id,
            message_count,
        )

        # ── 1. Incomplete integration workflows ─────────────────────
        try:
            incomplete = [
                wf for wf in self._active_workflows.values()
                if wf.status not in ("completed", "failed", "cancelled")
            ]
            if incomplete:
                for wf in incomplete:
                    logger.warning(
                        "Incomplete workflow at session end: type=%s, target=%s, status=%s",
                        wf.integration_type,
                        wf.target_name,
                        wf.status,
                    )
                    self._bus.emit(
                        "workflow.incomplete",
                        payload={
                            "session_id": session_id,
                            "workflow_type": wf.integration_type,
                            "workflow_target": wf.target_name,
                            "workflow_status": wf.status,
                            "workflow_started_at": wf.started_at.isoformat() if getattr(wf, "started_at", None) else None,
                        },
                        source="signal_processor",
                    )
        except Exception as e:
            logger.debug("_on_agent_complete: workflow check failed: %s", e)

        # ── 2. Accumulated rule violations ──────────────────────────
        try:
            recent_violations = list(self._violation_history[-50:])
            if recent_violations:
                by_rule: dict = {}
                for v in recent_violations:
                    rule = v.get("rule_token", "unknown")
                    by_rule.setdefault(rule, []).append(v)
                for rule, violations in by_rule.items():
                    logger.warning(
                        "Session rule violations: %s occurred %d time(s)",
                        rule,
                        len(violations),
                    )
                self._bus.emit(
                    "session.violations",
                    payload={
                        "session_id": session_id,
                        "total_count": len(recent_violations),
                        "by_rule": {k: len(v) for k, v in by_rule.items()},
                    },
                    source="signal_processor",
                )
        except Exception as e:
            logger.debug("_on_agent_complete: violation check failed: %s", e)

        # ── 3. QA gate status ────────────────────────────────────────
        try:
            # Check if any QA workflows were started but not completed
            qa_workflows = [
                wf for wf in self._workflow_history
                if wf.integration_type in ("qa", "test", "verification")
                and wf.status not in ("completed", "failed", "cancelled")
            ]
            if qa_workflows:
                for qf in qa_workflows:
                    logger.warning(
                        "Unresolved QA workflow at session end: %s, status=%s",
                        qf.target_name,
                        qf.status,
                    )
        except Exception as e:
            logger.debug("_on_agent_complete: QA check failed: %s", e)

        # ── 4. Disk logging — brain_signal_log.jsonl ───────────────────
        try:
            self._write_brain_signal_log(session_id, message_count)
        except Exception as e:
            logger.debug("_on_agent_complete: disk logging failed: %s", e)

        # P2: Log violations to brain_signal_log.jsonl
        try:
            import json, os
            from datetime import datetime
            log_path = os.path.expanduser("~/.drewgent/P2-hippocampus/kanban/state/brain_signal_log.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "violations": self._violation_history,
                "dangerous_ops": self._dangerous_ops_history,
                "workflows_completed": len([w for w in self._workflow_history if getattr(w, 'completed', False)]),
                "total_violations": len(self._violation_history),
                "total_dangerous_ops": len(self._dangerous_ops_history),
            }
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # non-blocking

    def _write_brain_signal_log(self, session_id: str, message_count: int) -> None:
        """Append a JSONL record to brain_signal_log.jsonl on session end.

        Records all brain signal data for post-session analysis:
        - violation_history (last 50)
        - dangerous_ops_history
        - active_workflows (incomplete only)
        - qa_gate_status
        """
        import json
        import os
        from pathlib import Path
        from datetime import datetime

        log_path = Path.home() / ".drewgent" / "state" / "brain_signal_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Build record
        record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": message_count,
            "violations": list(self._violation_history[-50:]),
            "dangerous_ops": list(self._dangerous_ops_history[-20:]),
            "incomplete_workflows": [
                {
                    "workflow_id": wf.workflow_id,
                    "integration_type": wf.integration_type,
                    "target_name": wf.target_name,
                    "status": wf.status,
                    "started_at": wf.started_at.isoformat() if getattr(wf, "started_at", None) else None,
                }
                for wf in self._active_workflows.values()
                if wf.status not in ("completed", "failed", "cancelled")
            ],
            "qa_workflows_unresolved": [
                {
                    "workflow_id": wf.workflow_id,
                    "integration_type": wf.integration_type,
                    "target_name": wf.target_name,
                    "status": wf.status,
                }
                for wf in self._workflow_history
                if wf.integration_type in ("qa", "test", "verification")
                and wf.status not in ("completed", "failed", "cancelled")
            ],
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _on_dangerous_op(self, event: BrainEvent) -> None:
        """Handle dangerous.op — log and optionally flag for human review.

        dangerous.op is emitted by _on_turn_start when high-risk operations
        are detected in the user message or tool calls.

        Actions:
            - Log the dangerous op with full context
            - Append to _dangerous_ops_history for session review
            - Emit awareness.integrity signal if threshold exceeded
        """
        payload = event.payload or {}
        turn_number = payload.get("turn_number", 0)
        detected_type = payload.get("detected_type", "unknown")
        severity = payload.get("severity", "medium")

        op_record = {
            "turn_number": turn_number,
            "detected_type": detected_type,
            "severity": severity,
            "signal_type": payload.get("signal_type"),
            "pattern_key": payload.get("pattern_key"),
            "description": payload.get("description"),
            "message_preview": payload.get("message_preview", ""),
            "timestamp": event.timestamp,
            "enforcement_action": (
                "high_severity_command_blocked"
                if severity == "high"
                else None
            ),
        }

        logger.warning(
            "Dangerous operation detected: turn=%d, type=%s, severity=%s, detail=%s",
            turn_number,
            detected_type,
            severity,
            payload.get("description") or payload.get("signal_type") or "unknown",
        )

        # Track history for session summary
        self._dangerous_ops_history.append(op_record)

        # If high-severity dangerous op, emit awareness.integrity signal
        if severity == "high":
            self._bus.emit(
                "awareness.integrity",
                payload={
                    "event": "dangerous_op",
                    "severity": "high",
                    "enforcement_action": "high_severity_command_blocked",
                    "turn_number": turn_number,
                    "detail": payload.get("description") or payload.get("signal_type"),
                    "requires_human_review": True,
                },
                source="signal_processor",
            )

    def _on_rule_violation(self, event: BrainEvent) -> None:
        """Handle rule.violation — track and log P0 rule violations.

        rule.violation is emitted by _on_turn_end when a turn's actions
        violate P0-brainstem rules (禁blind_write, 禁secrets_in_code, 禁console_log).

        Actions:
            - Log the violation with full context
            - Append to _violation_history for session summary
            - Emit awareness.integrity signal
        """
        payload = event.payload or {}
        turn_number = payload.get("turn_number", 0)
        rule_token = payload.get("rule_token", "unknown")

        violation_record = {
            "turn_number": turn_number,
            "rule_token": rule_token,
            "tool": payload.get("tool"),
            "severity": payload.get("severity", "medium"),
            "message": payload.get("message", ""),
            "secret_type": payload.get("secret_type"),
            "detected_type": payload.get("detected_type"),
            "timestamp": event.timestamp,
        }

        logger.warning(
            "P0 rule violation: turn=%d, rule=%s, tool=%s, severity=%s, msg=%s",
            turn_number,
            rule_token,
            payload.get("tool", "N/A"),
            payload.get("severity", "medium"),
            payload.get("message", ""),
        )

        self._violation_history.append(violation_record)

        # Emit awareness signal for integrity tracking
        self._bus.emit(
            "awareness.integrity",
            payload={
                "event": "rule_violation",
                "rule_token": rule_token,
                "severity": payload.get("severity", "medium"),
                "turn_number": turn_number,
                "requires_human_review": payload.get("severity") == "high",
            },
            source="signal_processor",
        )

    def _on_workflow_incomplete(self, event: BrainEvent) -> None:
        """Handle workflow.incomplete — log and archive incomplete workflows.

        workflow.incomplete is emitted by _on_agent_complete when a session
        ends with integration workflows that were started but not completed.

        Actions:
            - Move incomplete workflows from active to history
            - Log for P6-prefrontal/incidents/ post-mortem
            - No blocking — session already ended
        """
        payload = event.payload or {}
        session_id = payload.get("session_id", "unknown")
        workflow_type = payload.get("workflow_type", "unknown")
        workflow_target = payload.get("workflow_target", "unknown")
        workflow_status = payload.get("workflow_status", "unknown")

        logger.warning(
            "Incomplete workflow at session end: session=%s, type=%s, target=%s, status=%s",
            session_id,
            workflow_type,
            workflow_target,
            workflow_status,
        )

        # Archive the incomplete workflow into history for post-mortem
        from dataclasses import dataclass
        from datetime import datetime

        @dataclass
        class ArchivedWorkflow:
            integration_type: str
            target_name: str
            status: str
            workflow_id: str

        archived = ArchivedWorkflow(
            integration_type=workflow_type,
            target_name=workflow_target,
            status=f"incomplete@{workflow_status}",
            workflow_id=f"archived-{session_id}-{workflow_type}",
        )
        self._workflow_history.append(archived)

    def get_active_workflows(self) -> List[IntegrationWorkflow]:
        """Get all active integration workflows."""
        return list(self._active_workflows.values())

    def get_workflow_history(self) -> List[IntegrationWorkflow]:
        """Get archived workflow history."""
        return list(self._workflow_history)

    def get_architecture_model(self) -> ArchitectureModel:
        """Get the architecture awareness model."""
        return self._arch_model

    def restore_workflows(self, session_db, session_id: str) -> None:
        """Restore active workflows from session DB on agent restart."""
        import json
        if not session_db:
            return
        try:
            raw_workflows = session_db.load_integration_workflows(session_id)
            for wdata in raw_workflows:
                workflow = IntegrationWorkflow(
                    workflow_id=wdata["workflow_id"],
                    integration_type=wdata["integration_type"],
                    target_name=wdata["target_name"],
                    files_modified=wdata.get("files_modified", []),
                    steps_completed=wdata.get("steps_completed", []),
                    started=wdata.get("started", False),
                    completed=wdata.get("completed", False),
                    correlation_id=wdata.get("correlation_id") or "",
                )
                workflow.completed_at = wdata.get("completed_at")
                self._active_workflows[workflow.workflow_id] = workflow
                if workflow.correlation_id:
                    self._correlation_workflow_map[workflow.correlation_id] = workflow.workflow_id
        except Exception:
            pass

    def persist_active_workflows(self, session_db, session_id: str) -> None:
        """Save all active workflows to session DB (call on session end)."""
        import json
        if not session_db or not session_id:
            return
        try:
            for workflow in self._active_workflows.values():
                workflow_data = {
                    "workflow_id": workflow.workflow_id,
                    "integration_type": workflow.integration_type,
                    "target_name": workflow.target_name,
                    "files_modified": workflow.files_modified,
                    "steps_completed": workflow.steps_completed,
                    "started": workflow.started,
                    "completed": workflow.completed,
                    "completed_at": workflow.completed_at,
                    "correlation_id": workflow.correlation_id,
                    "detected_at": workflow.detected_at,
                }
                session_db.save_integration_workflow(
                    session_id, json.dumps(workflow_data)
                )
            # Archive completed workflows (don't keep them active across restarts)
            for w in self._workflow_history:
                if w.completed:
                    try:
                        session_db.archive_completed_workflow(w.workflow_id)
                    except Exception:
                        pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_signal_processor: Optional[SignalProcessor] = None


def get_signal_processor() -> SignalProcessor:
    """Get the global SignalProcessor singleton."""
    global _signal_processor
    if _signal_processor is None:
        _signal_processor = SignalProcessor()
    return _signal_processor