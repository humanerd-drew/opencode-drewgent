"""SelfBranchDecider — Autonomous branching decision for Drewgent.

Phase 1 of self-replicating agent TDD-PDCA.
Parent agent scores conversation complexity and decides whether to branch.

Usage:
    decider = SelfBranchDecider(agent)
    if decider.should_branch(messages):
        branches = decider.plan_branches(goal, context)
        results = _run_branches_parallel(branches, agent)
        response = decider.integrate_results(results)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
COMPLEXITY_THRESHOLD = 0.30        # score >= this → consider branching
COMPLEXITY_HIGH = 0.50           # score >= this → strongly recommend branching
MAX_CONCURRENT_CHILDREN = 3        # matches delegate_tool.MAX_CONCURRENT_CHILDREN
MAX_BRANCH_DEPTH = 1              # parent=0, child=1 (no further recursion)

# Scoring weights (must sum to 1.0 for normalization)
_WEIGHT_TOOL_DIVERSITY = 0.30
_WEIGHT_TURN_COUNT = 0.20
_WEIGHT_TOOL_CALL_COUNT = 0.30
_WEIGHT_REASONING_RATIO = 0.10
_WEIGHT_CONTEXT_COMPRESSION = 0.10


@dataclass
class BranchTask:
    """A single branch of work to delegate."""
    goal: str
    context: str
    branch_id: int


class ComplexityScore:
    """Components of a complexity score — useful for debugging."""

    def __init__(
        self,
        tool_diversity: float = 0.0,
        turn_count: float = 0.0,
        tool_call_count: float = 0.0,
        reasoning_ratio: float = 0.0,
        context_compression: float = 0.0,
    ):
        self.tool_diversity = tool_diversity
        self.turn_count = turn_count
        self.tool_call_count = tool_call_count
        self.reasoning_ratio = reasoning_ratio
        self.context_compression = context_compression

    @property
    def total(self) -> float:
        return (
            self.tool_diversity * _WEIGHT_TOOL_DIVERSITY
            + self.turn_count * _WEIGHT_TURN_COUNT
            + self.tool_call_count * _WEIGHT_TOOL_CALL_COUNT
            + self.reasoning_ratio * _WEIGHT_REASONING_RATIO
            + self.context_compression * _WEIGHT_CONTEXT_COMPRESSION
        )

    def __repr__(self) -> str:
        return (
            f"ComplexityScore(total={self.total:.2f}, "
            f"tool_div={self.tool_diversity:.2f}, "
            f"turns={self.turn_count:.2f}, "
            f"tool_calls={self.tool_call_count:.2f}, "
            f"reasoning={self.reasoning_ratio:.2f}, "
            f"compression={self.context_compression:.2f})"
        )


class SelfBranchDecider:
    """Decides when and how to branch the parent agent.

    The decider monitors conversation complexity via score_complexity(),
    and provides should_branch(), plan_branches(), and integrate_results()
    to orchestrate autonomous branching.
    """

    def __init__(self, agent):
        self.agent = agent
        self._branching_happened = False  # per-run flag

    # -------------------------------------------------------------------------
    # Complexity scoring
    # -------------------------------------------------------------------------

    def score_complexity(self, messages: List[Dict[str, Any]]) -> float:
        """Calculate 0.0–1.0 complexity score for a message list.

        Components:
          - tool_diversity: fraction of unique tool types vs total tool calls
          - turn_count: ratio of assistant turns to max_expected (8)
          - tool_call_count: ratio of tool calls to max_expected (15)
          - reasoning_ratio: presence of reasoning/thinking blocks (bonus)
          - context_compression: whether compression has fired (bonus)
        """
        if not messages:
            return 0.0

        components = self._score_components(messages)
        return min(1.0, components.total)

    def _score_components(self, messages: List[Dict[str, Any]]) -> ComplexityScore:
        """Compute individual scoring components."""
        # 1. Tool diversity — extract from BOTH assistant.tool_calls (OpenAI format)
        # AND tool role messages (Drewgent format uses this for results).
        # This matches how Drewgent actually stores tool call information.
        tool_names: List[str] = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    if name := fn.get("name"):
                        tool_names.append(name)
            elif msg.get("role") == "tool" and msg.get("tool_name"):
                # Drewgent stores tool name in tool role message
                if name := msg.get("tool_name"):
                    tool_names.append(name)

        tool_diversity = 0.0
        if tool_names:
            unique = len(set(tool_names))
            total = len(tool_names)
            tool_diversity = min(1.0, unique / max(total, 1))

        # 2. Turn count (normalized to ~8 turns for "complex")
        assistant_turns = sum(
            1 for m in messages if m.get("role") == "assistant" and not m.get("tool_calls")
        )
        turn_count = min(1.0, assistant_turns / 8.0)

        # 3. Tool call count (normalized to ~15 for "complex")
        tool_call_count_score = min(1.0, len(tool_names) / 15.0)

        # 4. Reasoning ratio — check for thinking/reasoning blocks
        reasoning_ratio = self._detect_reasoning_ratio(messages)

        # 5. Context compression — bonus if conversation is long enough to compress
        context_compression = 0.0
        if len(messages) > 30:  # rough proxy for compression having fired
            context_compression = 0.5

        return ComplexityScore(
            tool_diversity=tool_diversity,
            turn_count=turn_count,
            tool_call_count=tool_call_count_score,
            reasoning_ratio=reasoning_ratio,
            context_compression=context_compression,
        )

    def _detect_reasoning_ratio(self, messages: List[Dict[str, Any]]) -> float:
        """Detect if conversation involves heavy reasoning.

        Looks for:
        - thinking blocks in assistant messages
        - keywords suggesting analysis/investigation
        """
        reasoning_indicators = 0
        total_assistant = 0

        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            total_assistant += 1

            content = msg.get("content") or ""
            # Check for reasoning/thinking blocks (various formats)
            has_thinking = (
                "<thinking>" in content
                or "<reasoning>" in content
                or ("analyz" in content.lower())
                or ("investigate" in content.lower())
                or ("debugg" in content.lower())
                or ("trace" in content.lower())
            )
            if has_thinking:
                reasoning_indicators += 1

        if total_assistant == 0:
            return 0.0
        return min(1.0, reasoning_indicators / max(total_assistant, 1))

    # -------------------------------------------------------------------------
    # Branching decision
    # -------------------------------------------------------------------------

    def should_branch(self, messages: List[Dict[str, Any]]) -> bool:
        """Return True if the conversation is complex enough to branch.

        Respects:
        - Complexity score threshold
        - already_branching flag (prevent double-branch)
        - max depth (parent=0 → child=1, no further)
        """
        # No branching during child agent runs
        if getattr(self.agent, "_delegate_depth", 0) > 0:
            return False

        # Don't re-branch if already branched in this run
        if self._branching_happened:
            return False

        score = self.score_complexity(messages)
        if score < COMPLEXITY_THRESHOLD:
            return False

        logger.info(
            "SelfBranchDecider: complexity score=%.2f (threshold=%.2f) — branching recommended",
            score,
            COMPLEXITY_THRESHOLD,
        )
        return True

    def get_complexity_score_debug(self, messages: List[Dict[str, Any]]) -> ComplexityScore:
        """Return full complexity breakdown for debugging."""
        return self._score_components(messages)

    # -------------------------------------------------------------------------
    # Branch planning
    # -------------------------------------------------------------------------

    def plan_branches(
        self,
        goal: str,
        context: str,
        max_branches: int = MAX_CONCURRENT_CHILDREN,
    ) -> List[BranchTask]:
        """Split a goal into branch tasks.

        Strategy:
        1. If goal contains "and" / "also" / parallel keywords → split by conjunctions
        2. If goal is single task → return single branch
        3. Cap at max_branches

        Each branch gets:
        - goal: the sub-task
        - context: shared context from parent
        - branch_id: unique index for result tracking
        """
        # Heuristic: split by common parallel indicators
        split_indicators = [" and also ", " and ", " + ", "此同时", "그리고", "且", "並且"]
        parts = [goal]
        for sep in split_indicators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            if len(new_parts) > len(parts):
                parts = new_parts
                break

        # Deduplicate and clean
        seen = set()
        cleaned = []
        for p in parts:
            p = p.strip()
            if p and p not in seen and len(p) > 10:
                seen.add(p)
                cleaned.append(p)

        # Cap at max_branches
        if len(cleaned) > max_branches:
            cleaned = cleaned[:max_branches]

        branches = [
            BranchTask(goal=part, context=context, branch_id=i)
            for i, part in enumerate(cleaned)
        ]

        logger.info(
            "SelfBranchDecider: planned %d branches for goal: %s",
            len(branches),
            goal[:60],
        )
        return branches

    # -------------------------------------------------------------------------
    # Result integration
    # -------------------------------------------------------------------------

    def integrate_results(self, results: List[Dict[str, Any]]) -> str:
        """Aggregate branch results into a coherent parent response.

        Strategy:
        1. Filter to completed/failed results
        2. Sort by branch_id to maintain order
        3. Concatenate summaries with clear section headers
        4. If any branch failed, append a warning note
        """
        completed = [r for r in results if r.get("status") in ("completed",)]
        failed = [r for r in results if r.get("status") not in ("completed",)]

        if not completed:
            if failed:
                errors = "; ".join(r.get("error", str(r)) for r in failed[:3])
                return f"[Branch integration failed: {errors}]"
            return "[No branch results to integrate]"

        # Sort by branch_id to keep original order
        completed.sort(key=lambda r: r.get("task_index", 0))

        sections = []
        for r in completed:
            summary = r.get("summary", "")
            if summary:
                sections.append(f"## Branch {r.get('task_index', '?')+1}\n{summary}")

        response = "\n\n".join(sections)

        if failed:
            response += (
                f"\n\n⚠️  Note: {len(failed)} branch(es) failed and were skipped."
            )

        return response

    # -------------------------------------------------------------------------
    # Full branching workflow
    # -------------------------------------------------------------------------

    def execute_branching(
        self,
        goal: str,
        context: str,
        messages: List[Dict[str, Any]],
        parent_agent,
    ) -> str:
        """Run the full autonomous branching workflow.

        Called by the agent loop when should_branch() fires.
        Returns the integrated response from all branches.
        """
        self._branching_happened = True

        branches = self.plan_branches(goal, context)
        if not branches:
            return ""  # nothing to branch

        # Build tasks array for delegate_task
        tasks = [
            {"goal": b.goal, "context": b.context}
            for b in branches
        ]

        # Import here to avoid circular dependency
        from tools.delegate_tool import delegate_task

        result_json = delegate_task(
            tasks=tasks,
            parent_agent=parent_agent,
            max_iterations=getattr(parent_agent, "max_iterations", 50) // 2,
        )

        try:
            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
        except Exception:
            logger.warning("SelfBranchDecider: failed to parse delegate result: %s", result_json)
            return f"[Branch results unavailable: {result_json}]"

        results = parsed.get("results", [])
        return self.integrate_results(results)


# ---------------------------------------------------------------------------
# Module-level helpers (for testing)
# ---------------------------------------------------------------------------

import json