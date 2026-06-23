"""Brain Processor — the organic runtime brain engine for Drewgent.

This module implements the "living brain" concept: a per-turn brain loop
that classifies the current task, applies P0-P6 layer weights, and surfaces
relevant rules to guide the agent's reasoning — not just passive injection.

Usage:
    processor = BrainProcessor()
    decision = processor.decide(task_type, context, tools)
    if decision.rules_to_fire:
        system_prompt_extra = processor.render_rules(decision.rules_to_fire)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from drewgent_constants import get_drewgent_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task Type Classification
# ---------------------------------------------------------------------------

# Task type detection patterns — ordered by priority
_TASK_TYPE_PATTERNS = [
    # High-priority (P0 fires strongly)
    (r"(삭제|remove|delete|rm\s)", "DANGEROUS_OPERATION", 0.95),
    (r"(格式化|format\s|init\s|reset\s)", "DANGEROUS_OPERATION", 0.95),
    (r"(rm\s+-\s*rf|rm\s+-rf)", "DANGEROUS_OPERATION", 0.99),
    (r"(write_file|patch).*production|production.*(write_file|patch)", "PRODUCTION_EDIT", 0.90),
    (r"(도구\s*추가|tool\s*add|새\s*도구|new\s*tool)", "TOOL_INTEGRATION", 0.95),
    (r"(스킬\s*추가|skill\s*add|새\s*스킬|new\s*skill)", "SKILL_INTEGRATION", 0.95),
    (r"(gateway.*플랫폼|플랫폼.*gateway|새\s*플랫폼)", "GATEWAY_INTEGRATION", 0.90),
    # Coding tasks (karpathy principles apply)
    (r"코드|code|implement|build|create\s+\w+", "CODING", 0.85),
    (r"(함수|function|class|method|module)", "CODING", 0.80),
    (r"(수정|modify|edit|change|update)", "CODING", 0.75),
    (r"(버그|bug|fix|error|패치)", "CODING", 0.80),
    (r"(테스트|test|spec|validate)", "CODING", 0.75),
    # Research / info
    (r"(검색|search|lookup|find|확인)", "RESEARCH", 0.70),
    (r"(질문|question|what|why|how)", "RESEARCH", 0.60),
    (r"(리서치|research|조사|분석)", "RESEARCH", 0.75),
    # Creative
    (r"(생성|create|generate|write\s+\w+)", "CREATIVE", 0.70),
    (r"(문서|document|report|文章)", "CREATIVE", 0.65),
    # P1-P6 dedicated task types (Phase 4-2)
    (r"(기억|memory|세션\s*검색|past\s*session|session_search|이전\s*대화)", "MEMORY_QUERY", 0.80),
    (r"(전략|strategy|계획|planning|다음\s*단계|roadmap|long[- ]term)", "STRATEGY", 0.80),
    (r"(자가\s*개선|self[- ]?improv|성장|growth|학습|learn\s+from)", "SELF_IMPROVEMENT", 0.85),
    (r"(자기\s*인식|자아|P5|P5-?ego|who\s+am\s+I|what\s+is\s+my)", "SELF_IMPROVEMENT", 0.80),
]

# Layer priority per task type
# Phase 4-1: All 7 layers represented — P0 (always first if applicable),
#            P1-P6 (in order of subsumption hierarchy when relevant)
_TASK_TYPE_LAYER_PRIORITY = {
    # P0 always first for dangerous/high-risk
    "DANGEROUS_OPERATION":  ["P0-brainstem"],
    "PRODUCTION_EDIT":      ["P0-brainstem", "P1-limbic", "P4-cortex"],
    "TOOL_INTEGRATION":     ["P0-brainstem", "P4-cortex", "P1-limbic", "P2-hippocampus"],
    "SKILL_INTEGRATION":    ["P0-brainstem", "P4-cortex", "P1-limbic", "P2-hippocampus"],
    "GATEWAY_INTEGRATION":  ["P0-brainstem", "P4-cortex", "P1-limbic", "P3-sensors"],
    "CODING":               ["P0-brainstem", "P4-cortex", "P1-limbic", "P2-hippocampus", "P5-ego", "P6-prefrontal"],
    # P1-P6 tasks
    "RESEARCH":             ["P1-limbic", "P2-hippocampus", "P3-sensors", "P4-cortex"],
    "CREATIVE":             ["P1-limbic", "P4-cortex", "P5-ego"],
    "MEMORY_QUERY":         ["P2-hippocampus"],
    "STRATEGY":             ["P6-prefrontal", "P4-cortex", "P1-limbic"],
    "SELF_IMPROVEMENT":      ["P5-ego", "P4-cortex", "P0-brainstem"],
    "GENERAL":              ["P1-limbic", "P2-hippocampus", "P3-sensors", "P4-cortex"],
}


# ---------------------------------------------------------------------------
# Decision Result
# ---------------------------------------------------------------------------

@dataclass
class BrainDecision:
    """Result of a brain decision cycle."""
    task_type: str
    confidence: float
    layers_to_consult: List[str]
    rules_to_fire: List[Dict[str, Any]]
    hints: List[str]  # actionable guidance
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Brain Processor
# ---------------------------------------------------------------------------

class BrainProcessor:
    """Organic brain runtime — classifies task, applies layer weights, fires rules.

    This is NOT a one-shot injection. It runs every turn and produces
    contextual, task-specific brain guidance.
    """

    _instance: Optional["BrainProcessor"] = None

    def __init__(self):
        self._brain_rules: List[Dict[str, Any]] = []
        self._layer_neurons: Dict[str, List[Dict[str, Any]]] = {}
        self._last_classification: Optional[str] = None
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "BrainProcessor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Loading ────────────────────────────────────────────────────────────

    def load_brain(self) -> None:
        """Load brain rules from active brain's P-folder structure."""
        if self._loaded:
            return

        try:
            from drewgent_cli.brain_manager import get_active_brain_name, scan_brain

            active = get_active_brain_name()
            if not active:
                logger.debug("No active brain for BrainProcessor")
                return

            brain = scan_brain(active)
            if not brain:
                return

            # Build layer → neurons map
            self._layer_neurons = {}
            for layer in brain.layers:
                self._layer_neurons[layer.name] = []
                for neuron in layer.neurons:
                    self._layer_neurons[layer.name].append({
                        "name": neuron.name,
                        "content": neuron.content or "",
                        "weight": neuron.weight,
                    })
                # Include sublayer neurons
                for sublayer in layer.sublayers:
                    for neuron in sublayer.neurons:
                        self._layer_neurons[layer.name].append({
                            "name": neuron.name,
                            "content": neuron.content or "",
                            "weight": neuron.weight,
                        })

            # Flatten into brain rules list for fast lookup
            self._brain_rules = []
            for layer_name, neurons in self._layer_neurons.items():
                for neuron in neurons:
                    self._brain_rules.append({
                        "layer": layer_name,
                        "name": neuron["name"],
                        "content": neuron["content"],
                        "weight": neuron["weight"],
                    })

            self._loaded = True
            logger.debug("BrainProcessor loaded: %d rules across %d layers",
                        len(self._brain_rules), len(self._layer_neurons))
        except Exception as e:
            logger.debug("BrainProcessor load failed: %s", e)

    def reload(self) -> None:
        """Force reload of brain rules."""
        self._loaded = False
        self._brain_rules = []
        self._layer_neurons = {}
        self._last_classification = None
        self.load_brain()

    # ── Core Decision Loop ────────────────────────────────────────────────

    def decide(
        self,
        user_message: str = "",
        assistant_message: str = "",
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None,
    ) -> BrainDecision:
        """Run one brain decision cycle.

        Classifies the task type, determines which layers to consult,
        and returns rules that should fire for this turn.

        Args:
            user_message: The user's message (for task classification)
            assistant_message: The assistant's response so far
            tool_calls: List of tool calls the assistant wants to make
            tool_results: List of tool results received

        Returns:
            BrainDecision with task_type, rules_to_fire, and hints
        """
        self.load_brain()

        # 1. Classify task type
        task_type, confidence = self._classify_task(
            user_message, assistant_message, tool_calls
        )
        self._last_classification = task_type

        # 2. Determine which layers to consult
        layers = _TASK_TYPE_LAYER_PRIORITY.get(
            task_type,
            ["P1-limbic", "P2-hippocampus", "P3-sensors", "P4-cortex"]
        )

        # 3. Find rules to fire from those layers
        rules = self._get_rules_for_layers(layers, task_type)

        # 4. Generate actionable hints
        hints = self._generate_hints(task_type, rules, tool_calls)

        return BrainDecision(
            task_type=task_type,
            confidence=confidence,
            layers_to_consult=layers,
            rules_to_fire=rules,
            hints=hints,
        )

    def decide_for_message(self, message: str, tool_calls: Optional[List[Dict]] = None) -> BrainDecision:
        """Convenience method — single user message → brain decision."""
        return self.decide(user_message=message, tool_calls=tool_calls)

    # ── Task Classification ──────────────────────────────────────────────

    def _classify_task(
        self,
        user_message: str,
        assistant_message: str,
        tool_calls: Optional[List[Dict]],
    ) -> tuple[str, float]:
        """Classify the current task type from message content and tool calls."""
        combined = f"{user_message} {assistant_message}".lower()

        # Check tool calls for stronger signals
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("function", {}).get("name", "") or str(tc)
                if "write" in name or "patch" in name:
                    combined += " write_file modify"
                if "terminal" in name:
                    combined += " command execution"

        # Match against patterns — first match wins (priority order)
        for pattern, task_type, confidence in _TASK_TYPE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return task_type, confidence

        # Default
        return "GENERAL", 0.5

    # ── Rule Selection ───────────────────────────────────────────────────

    def _get_rules_for_layers(
        self,
        layers: List[str],
        task_type: str,
    ) -> List[Dict[str, Any]]:
        """Get rules that should fire for the given layers and task type.

        Phase 4-3: All P1-P6 neurons are loaded into self._brain_rules
        by load_brain(). This method filters by layer name only — the
        layer priority is already encoded in _TASK_TYPE_LAYER_PRIORITY.
        """
        if not self._brain_rules:
            return self._get_fallback_rules(task_type)

        active_rules = []
        for rule in self._brain_rules:
            if rule["layer"] in layers:
                # Phase 4-3: Task-type relevance filter — skip rules
                # whose name/content have no connection to the task type
                name_lower = rule["name"].lower()
                content_lower = rule["content"].lower()

                # P0 rules fire regardless of task type
                if rule["layer"] == "P0-brainstem":
                    active_rules.append(rule)
                    continue

                # P4-cortex: filter by semantic relevance
                if rule["layer"] == "P4-cortex":
                    # Only include if rule name matches task type keyword
                    task_keywords = {
                        "MEMORY_QUERY": ["memory", "session", "hippocampus", "recall"],
                        "STRATEGY": ["strategy", "prefrontal", "planning", "roadmap"],
                        "SELF_IMPROVEMENT": ["self", "improv", "ego", "growth", "learn"],
                        "RESEARCH": ["semble", "research", "search", "find"],
                        "CREATIVE": ["creative", "limbic", "tone", "persona"],
                        "CODING": ["karpathy", "coding", "skill", "tool"],
                    }
                    relevant = task_keywords.get(task_type, [])
                    if any(kw in name_lower or kw in content_lower for kw in relevant):
                        active_rules.append(rule)
                    continue

                # P1-limbic: tone rules fire for all interactive tasks
                if rule["layer"] == "P1-limbic":
                    if task_type in ("GENERAL", "CREATIVE", "RESEARCH", "CODING",
                                     "MEMORY_QUERY", "STRATEGY", "SELF_IMPROVEMENT"):
                        active_rules.append(rule)
                    continue

                # P2-hippocampus: memory rules fire for recall tasks
                if rule["layer"] == "P2-hippocampus":
                    if task_type in ("MEMORY_QUERY", "SELF_IMPROVEMENT", "GENERAL"):
                        active_rules.append(rule)
                    continue

                # P3-sensors: tool/gateway rules fire for integration tasks
                if rule["layer"] == "P3-sensors":
                    if task_type in ("TOOL_INTEGRATION", "SKILL_INTEGRATION", "GATEWAY_INTEGRATION"):
                        active_rules.append(rule)
                    continue

                # P5-ego and P6-prefrontal: always include when in layer list
                if rule["layer"] in ("P5-ego", "P6-prefrontal"):
                    active_rules.append(rule)
                    continue

        return active_rules

    def _get_fallback_rules(self, task_type: str) -> List[Dict[str, Any]]:
        """Hardcoded fallback rules when brain is not loaded.

        Phase 4-4: All P0-P6 layers have fallback rules.
        When brain is not loaded, these ensure P1-P6 guidance still fires.
        """
        rules: List[Dict[str, Any]] = []

        # ── P0-brainstem: always included ──────────────────────────────────
        p0_rules = [
            {
                "layer": "P0-brainstem",
                "name": "禁rm_rf_root",
                "content": "FORBIDDEN: rm -rf on root or system paths. REASON: Catastrophic data loss.",
                "weight": 1.0,
            },
            {
                "layer": "P0-brainstem",
                "name": "禁blind_write",
                "content": "FORBIDDEN: write_file without reading existing file first.",
                "weight": 1.0,
            },
            {
                "layer": "P0-brainstem",
                "name": "禁secrets_in_code",
                "content": "FORBIDDEN: Hardcoded secrets in code. Use environment variables.",
                "weight": 1.0,
            },
        ]

        # Karpathy principles for coding tasks
        if task_type == "CODING":
            p0_rules.append({
                "layer": "P0-brainstem",
                "name": "禁karpathy_coding_principles",
                "content": "FOLLOW: Think Before Coding | Simplicity First | Surgical Changes | Goal-Driven Execution",
                "weight": 0.95,
            })

        # Integration rules for integration tasks
        if task_type in ("TOOL_INTEGRATION", "SKILL_INTEGRATION", "GATEWAY_INTEGRATION"):
            p0_rules.append({
                "layer": "P0-brainstem",
                "name": "禁tool_integration_3file",
                "content": "MUST: Complete all 3 integration files before declaring completion.",
                "weight": 0.95,
            })

        rules.extend(p0_rules)

        # ── P1-limbic: tone/style ─────────────────────────────────────────
        if task_type in ("GENERAL", "CREATIVE", "RESEARCH", "CODING",
                         "MEMORY_QUERY", "STRATEGY", "SELF_IMPROVEMENT"):
            rules.append({
                "layer": "P1-limbic",
                "name": "limbic-tone-direct",
                "content": "Be direct. Say what is true, even when inconvenient. Admit uncertainty explicitly.",
                "weight": 0.8,
            })
            rules.append({
                "layer": "P1-limbic",
                "name": "limbic-tone-korean",
                "content": "For Korean-speaking users, respond in Korean with appropriate respect level.",
                "weight": 0.8,
            })

        # ── P2-hippocampus: memory/recall ─────────────────────────────────
        if task_type in ("MEMORY_QUERY", "SELF_IMPROVEMENT", "GENERAL"):
            rules.append({
                "layer": "P2-hippocampus",
                "name": "hippocampus-session-search-first",
                "content": "Search past sessions before asking the user to repeat themselves.",
                "weight": 0.75,
            })

        # ── P3-sensors: tool routing hints ────────────────────────────────
        if task_type in ("TOOL_INTEGRATION", "SKILL_INTEGRATION", "GATEWAY_INTEGRATION"):
            rules.append({
                "layer": "P3-sensors",
                "name": "sensors-tool-routing",
                "content": "Use skill_view() to load skills. Use search() for code exploration. Use read_file() over terminal cat.",
                "weight": 0.7,
            })

        # ── P4-cortex: growth patterns ────────────────────────────────────
        if task_type in ("CODING", "RESEARCH", "SELF_IMPROVEMENT"):
            rules.append({
                "layer": "P4-cortex",
                "name": "cortex-semble-first",
                "content": "For code exploration, use sembe_search before grep. For unfamiliar code, ask 'where is X' not 'grep X'.",
                "weight": 0.7,
            })
            rules.append({
                "layer": "P4-cortex",
                "name": "cortex-skill-save",
                "content": "After difficult tasks, offer to save as a skill. After correcting approach, patch the skill.",
                "weight": 0.7,
            })

        # ── P5-ego: self-model — fire for all cognitive tasks ─────────────────
        # Phase 4-4 fix: CODING also needs P5-ego (identity + self-reflection)
        if task_type in ("SELF_IMPROVEMENT", "GENERAL", "CODING"):
            rules.append({
                "layer": "P5-ego",
                "name": "ego-identity-p5",
                "content": "I am Drewgent — Claude Code with NeuronFS-style brain. P0 overrides everything. Think before code.",
                "weight": 0.65,
            })

        # ── P6-prefrontal: strategy ──────────────────────────────────────
        if task_type in ("STRATEGY", "SELF_IMPROVEMENT", "CODING"):
            rules.append({
                "layer": "P6-prefrontal",
                "name": "prefrontal-plan-before",
                "content": "For multi-step tasks, state a brief plan before executing. Define success criteria.",
                "weight": 0.65,
            })

        return rules

    # ── Hint Generation ───────────────────────────────────────────────────

    def _generate_hints(
        self,
        task_type: str,
        rules: List[Dict[str, Any]],
        tool_calls: Optional[List[Dict]],
    ) -> List[str]:
        """Generate actionable hints based on task type and active rules."""
        hints = []

        # Add hint from highest-priority active rule
        if rules:
            top_rule = rules[0]
            name = top_rule.get("name", "")
            if "karpathy" in name.lower():
                hints.append("Think Before Coding: state assumptions, present tradeoffs, stop when confused.")
            elif "rm_rf" in name.lower():
                hints.append("DANGEROUS: Verify target path is not root or system directory.")
            elif "blind_write" in name.lower():
                hints.append("Read existing file before writing to it.")

        # Task-specific hints
        if task_type == "TOOL_INTEGRATION":
            hints.append("Check: tools/<name>_tool.py, model_tools.py (_discover_tools), toolsets.py")
        elif task_type == "SKILL_INTEGRATION":
            hints.append("Check: skills/<name>/SKILL.md, agent/skill_commands.py")
        elif task_type == "CODING":
            hints.append("Simplicity First: if 200 lines could be 50, rewrite.")
            hints.append("Surgical Changes: touch only what you must.")
            hints.append("Goal-Driven: define success criteria, verify each step.")
        elif task_type == "DANGEROUS_OPERATION":
            hints.append("P0-brainstem ACTIVE: verify each step before proceeding. Ask if uncertain.")
        # P1-P6 dedicated hints (Phase 4-2)
        elif task_type == "MEMORY_QUERY":
            hints.append("P2-hippocampus: search past sessions before asking the user.")
        elif task_type == "STRATEGY":
            hints.append("P6-prefrontal: present multiple approaches, state tradeoffs clearly.")
        elif task_type == "SELF_IMPROVEMENT":
            hints.append("P5-ego: reflect on identity and growth. Apply patterns from past errors.")

        # Tool-call specific hints
        if tool_calls:
            for tc in tool_calls:
                name = tc.get("function", {}).get("name", "") or str(tc)
                if name == "write_file" and task_type == "CODING":
                    hints.append("禁blind_write: read existing file before write_file.")
                if name == "patch":
                    hints.append("Verify patch target file exists and is what you expect.")

        return hints[:5]  # cap at 5 hints

    # ── Rendering ─────────────────────────────────────────────────────────

    def render_decision(self, decision: BrainDecision) -> str:
        """Render a BrainDecision as a system-prompt block."""
        if not decision.rules_to_fire and not decision.hints:
            return ""

        lines = [
            "## 🧠 Brain Decision (This Turn)",
            f"Task: **{decision.task_type}** | Confidence: {decision.confidence:.0%}",
            "",
        ]

        if decision.hints:
            lines.append("### Action Hints")
            for hint in decision.hints:
                lines.append(f"- {hint}")
            lines.append("")

        if decision.rules_to_fire:
            lines.append("### Active Rules")
            shown_layers = set()
            for rule in decision.rules_to_fire[:8]:  # cap at 8 rules shown
                layer = rule.get("layer", "?")
                if layer not in shown_layers:
                    lines.append(f"**[{layer}]**")
                    shown_layers.add(layer)
                name = rule.get("name", "?")
                content = rule.get("content", "")[:150]
                lines.append(f"  `{name}`: {content}...")
                lines.append("")

        return "\n".join(lines)

    def render_for_system_prompt(self, message: str, tool_calls: Optional[List[Dict]] = None) -> str:
        """One-shot: classify message, run decision, return prompt block."""
        decision = self.decide_for_message(message, tool_calls)
        return self.render_decision(decision)

    # ── Self-Modification (brain learns from results) ────────────────────

    def observe_result(
        self,
        tool_name: str,
        success: bool,
        result_preview: str = "",
    ) -> None:
        """Record observation about a tool execution for self-improvement.

        This feeds into the brain's self-modifying loop — when patterns
        are observed repeatedly, the agent can update brain rules.
        """
        if not success and tool_name in ("write_file", "patch"):
            # Pattern: write/patch failure — could indicate missing read step
            logger.info(
                "BrainProcessor observe: %s failed (%s). "
                "Consider: was the file read before writing?",
                tool_name,
                result_preview[:100] if result_preview else "no preview",
            )
            # This could trigger a brain_record in a future iteration
            # Currently logged — could be enhanced with pattern storage

    def get_active_task_type(self) -> Optional[str]:
        """Return the last classified task type."""
        return self._last_classification


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_processor: Optional[BrainProcessor] = None


def get_brain_processor() -> BrainProcessor:
    """Get the global BrainProcessor instance."""
    global _processor
    if _processor is None:
        _processor = BrainProcessor()
        _processor.load_brain()
    return _processor