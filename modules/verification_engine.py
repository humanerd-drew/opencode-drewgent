"""
VerificationEngine - Drewgent's Quality Gate

Multi-stage validation of AIAgent outputs before user delivery.
Supports P0 blocking rules and weighted scoring for P1/P5 rules.

Architecture:
    Sub-Agent Result
        ↓
    VerificationEngine.verify()
        ├─ HallucinationChecker (P0) — BLOCK if violated
        ├─ SafetyChecker (P0) — BLOCK if violated
        ├─ FactualAccuracyChecker — score 0.0-1.0
        ├─ CompletenessChecker — score 0.0-1.0
        ├─ SourceCitationChecker (P5-2) — score 0.0-1.0
        └─ KoreanFirstChecker (P5-1) — score 0.0-1.0
        ↓
    Weighted Score = Σ(score × weight) / Σ(weight)
        ↓
    Status: APPROVED / REVISION / REJECTED
        ↓
    (REVISION) → revise() → Loop (max 3x)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Verification result status."""

    APPROVED = "approved"
    REVISION = "revision"
    REJECTED = "rejected"


@dataclass
class ValidationScore:
    """Score from a single validation rule."""

    name: str
    score: float  # 0.0 to 1.0
    passed: bool
    threshold: float
    details: str = ""
    weight: float = 1.0
    priority: str = "P1"  # P0, P1, P5
    required: bool = False


@dataclass
class VerificationResult:
    """Complete verification result."""

    status: VerificationStatus
    overall_score: float  # 0.0 to 1.0
    rule_scores: list[ValidationScore] = field(default_factory=list)
    revision_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ValidationRule:
    """Base class for validation rules."""

    def __init__(
        self,
        name: str,
        description: str,
        weight: float = 1.0,
        threshold: float = 0.8,
        required: bool = False,
        priority: str = "P1",  # P0, P1, P5
    ):
        self.name = name
        self.description = description
        self.weight = weight
        self.threshold = threshold
        self.required = required
        self.priority = priority

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        """Evaluate output and return score."""
        raise NotImplementedError

    def _make_score(
        self,
        score: float,
        passed: bool,
        details: str,
    ) -> ValidationScore:
        """Helper to create ValidationScore with rule attributes."""
        return ValidationScore(
            name=self.name,
            score=score,
            passed=passed,
            threshold=self.threshold,
            details=details,
            weight=self.weight,
            priority=self.priority,
            required=self.required,
        )


class HallucinationChecker(ValidationRule):
    """P0: Detect source-free claims and invented statistics."""

    HALLUCINATION_PATTERNS = [
        r"研究表明",
        r"据.*报道",
        r"专家表示",
        r"调查显示",
        r"^研究表明",
        r"研究表明.*$",
        r"すべての.*이라고$",
        r"모두.*하다$",
        r"必ず.*です",
        r"確実です",
        r" 이는.*이다$",  # Korean: 이것은 확실히...
    ]

    def __init__(self):
        super().__init__(
            name="no_hallucination",
            description="Source-free claims and invented statistics",
            weight=2.0,
            threshold=1.0,  # P0 must pass completely
            required=True,
            priority="P0",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        for pattern in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, output):
                return self._make_score(
                    score=0.0,
                    passed=False,
                    details=f"Detected hallucination pattern: {pattern}",
                )

        return self._make_score(
            score=1.0,
            passed=True,
            details="No hallucination patterns detected",
        )


class SafetyChecker(ValidationRule):
    """P0: Detect API keys, passwords, PII exposure."""

    SAFETY_PATTERNS = [
        (r"API[_-]?KEY\s*[:=]\s*[\w\-]{20,}", "API key detected"),
        (r"sk\-[a-zA-Z0-9]{20,}", "Secret API key detected"),
        (r"password\s*[:=]\s*\S+", "Password detected"),
        (r"PASSWORD\s*[:=]\s*\S+", "Password detected"),
        (r"secret\s*[:=]\s*\S+", "Secret detected"),
        (r"token\s*[:=]\s*[\w\-]{20,}", "Token detected"),
        (r"Bearer\s+[\w\-]{20,}", "Bearer token detected"),
        (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key detected"),
    ]

    def __init__(self):
        super().__init__(
            name="safety_score",
            description="API keys, passwords, PII exposure",
            weight=2.0,
            threshold=1.0,  # P0 must pass completely
            required=True,
            priority="P0",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        for pattern, reason in self.SAFETY_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                return self._make_score(
                    score=0.0,
                    passed=False,
                    details=reason,
                )

        return self._make_score(
            score=1.0,
            passed=True,
            details="No safety violations detected",
        )


class FactualAccuracyChecker(ValidationRule):
    """P1: Verify factual accuracy of claims."""

    UNCERTAINTY_PATTERNS = [
        r"不确定",
        r"불확실",
        r"일 것이다",
        r"것으로 보인다",
        r"확실히 않다",
        r"TBD",
        r"待定",
    ]

    def __init__(self):
        super().__init__(
            name="factual_accuracy",
            description="Dates, numbers, names match reality",
            weight=1.5,
            threshold=0.8,
            required=True,
            priority="P1",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        uncertainty_count = 0
        for pattern in self.UNCERTAINTY_PATTERNS:
            uncertainty_count += len(re.findall(pattern, output))

        # More uncertainty = lower score
        if uncertainty_count == 0:
            score = 1.0
            details = "No uncertainty markers detected"
        elif uncertainty_count <= 2:
            score = 0.8
            details = f"Minor uncertainty detected ({uncertainty_count} markers)"
        else:
            score = 0.5
            details = f"Significant uncertainty detected ({uncertainty_count} markers)"

        return self._make_score(
            score=score,
            passed=score >= self.threshold,
            details=details,
        )


class CompletenessChecker(ValidationRule):
    """P1: Verify all required actions are completed."""

    INCOMPLETE_MARKERS = [
        r"TBD",
        r"待定",
        r"미완료",
        r"아직",
        r"to be determined",
        r"\[\s*\]",  # [ ]
        r"_\s*$",  # trailing underscore as placeholder
    ]

    def __init__(self):
        super().__init__(
            name="completeness",
            description="All required actions done, no TBD",
            weight=1.0,
            threshold=0.9,
            required=True,
            priority="P1",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        incomplete_count = 0
        for pattern in self.INCOMPLETE_MARKERS:
            incomplete_count += len(re.findall(pattern, output, re.IGNORECASE))

        if incomplete_count == 0:
            score = 1.0
            details = "All content complete"
        elif incomplete_count == 1:
            score = 0.85
            details = f"Incomplete marker detected ({incomplete_count})"
        else:
            score = 0.6
            details = f"Multiple incomplete markers ({incomplete_count})"

        return self._make_score(
            score=score,
            passed=score >= self.threshold,
            details=details,
        )


class SourceCitationChecker(ValidationRule):
    """P5: Verify research tasks cite sources."""

    CITATION_PATTERNS = [
        r"https?://",
        r"according to",
        r"source:",
        r"출처:",
        r"참고:",
    ]

    def __init__(self):
        super().__init__(
            name="source_cited",
            description="Research tasks cite sources",
            weight=1.0,
            threshold=0.5,
            required=False,
            priority="P5",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        # Check if this is a research task
        is_research = any(
            keyword in task.lower()
            for keyword in ["조사", "research", "trends", "분석", "analysis"]
        )

        if not is_research:
            # Not a research task, skip this check
            return self._make_score(
                score=1.0,
                passed=True,
                details="Not a research task, skipping citation check",
            )

        # Check for citations
        citation_count = 0
        for pattern in self.CITATION_PATTERNS:
            citation_count += len(re.findall(pattern, output, re.IGNORECASE))

        if citation_count > 0:
            score = min(1.0, 0.5 + (citation_count * 0.25))
            details = f"Found {citation_count} citation(s)"
        else:
            score = 0.3
            details = "No sources cited"

        return self._make_score(
            score=score,
            passed=score >= self.threshold,
            details=details,
        )


class KoreanFirstChecker(ValidationRule):
    """P5: Korean users should get Korean responses."""

    def __init__(self):
        super().__init__(
            name="korean_first",
            description="Korean users get Korean responses",
            weight=0.5,
            threshold=0.5,
            required=False,
            priority="P5",
        )

    def evaluate(self, task: str, output: str, context: dict) -> ValidationScore:
        # Check if user is Korean-speaking
        user_language = context.get("language", "ko")  # default to Korean

        if user_language != "ko":
            # Not a Korean user, skip
            return self._make_score(
                score=1.0,
                passed=True,
                details="Not a Korean user, skipping",
            )

        # Count Korean characters
        korean_chars = len(re.findall(r"[가-힣]", output))
        total_chars = len(re.findall(r"[\w]", output))

        if total_chars == 0:
            return self._make_score(
                score=1.0,
                passed=True,
                details="No text to evaluate",
            )

        korean_ratio = korean_chars / total_chars

        if korean_ratio >= 0.3:
            score = 1.0
            details = f"Korean ratio {korean_ratio:.0%}"
        elif korean_ratio >= 0.1:
            score = 0.6
            details = f"Korean ratio {korean_ratio:.0%} (low)"
        else:
            score = 0.2
            details = f"Non-Korean response to Korean user ({korean_ratio:.0%})"

        return self._make_score(
            score=score,
            passed=score >= self.threshold,
            details=details,
        )


class VerificationEngine:
    """
    Drewgent's quality gate for AIAgent outputs.

    Validates outputs against P0 (critical), P1 (required), and P5 (ego) rules.
    """

    def __init__(self):
        self.rules: list[ValidationRule] = [
            HallucinationChecker(),
            SafetyChecker(),
            FactualAccuracyChecker(),
            CompletenessChecker(),
            SourceCitationChecker(),
            KoreanFirstChecker(),
        ]

    def verify(
        self,
        task: str,
        output: str,
        context: dict = None,
    ) -> VerificationResult:
        """
        Verify output against all rules.

        Args:
            task: The original task description
            output: The AIAgent's output to verify
            context: Additional context (language, task_type, etc.)

        Returns:
            VerificationResult with status and scores
        """
        context = context or {}
        rule_scores: list[ValidationScore] = []

        # Query Knowledge Bus for relevant prior knowledge (informational)
        prior_knowledge = self._query_prior_knowledge(task, output, context)
        if prior_knowledge:
            context["_prior_knowledge"] = prior_knowledge

        # Evaluate all rules
        for rule in self.rules:
            score = rule.evaluate(task, output, context)
            rule_scores.append(score)

        # Check P0 rules first (immediate block/reject)
        p0_failed = [s for s in rule_scores if s.priority == "P0" and not s.passed]

        if p0_failed:
            # P0 failure = immediate REJECTED
            result = VerificationResult(
                status=VerificationStatus.REJECTED,
                overall_score=0.0,
                rule_scores=rule_scores,
                rejection_reason=f"P0 violation: {p0_failed[0].name} - {p0_failed[0].details}",
            )
            # Store in Knowledge Bus
            self._store_verification_knowledge(task, result, context)
            return result

        # Calculate weighted score
        total_weight = sum(s.weight for s in rule_scores)
        weighted_sum = sum(s.score * s.weight for s in rule_scores)
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Check if any required rule failed
        required_failed = [s for s in rule_scores if s.required and not s.passed]

        # Determine status
        if overall_score < 0.8 or required_failed:
            revision_notes = self._format_revision_notes(rule_scores, required_failed)
            result = VerificationResult(
                status=VerificationStatus.REVISION,
                overall_score=overall_score,
                rule_scores=rule_scores,
                revision_notes=revision_notes,
            )
            # Store in Knowledge Bus
            self._store_verification_knowledge(task, result, context)
            return result

        # All passed
        result = VerificationResult(
            status=VerificationStatus.APPROVED,
            overall_score=overall_score,
            rule_scores=rule_scores,
        )
        # Store in Knowledge Bus
        self._store_verification_knowledge(task, result, context)
        return result

    def _store_verification_knowledge(
        self,
        task: str,
        result: VerificationResult,
        context: dict,
    ) -> None:
        """Store verification results in Knowledge Bus."""
        try:
            from .knowledge_bus import KnowledgeBus, Knowledge

            kb = KnowledgeBus.get_instance()

            # Store failure patterns
            for score in result.rule_scores:
                if not score.passed:
                    kb.store(
                        Knowledge(
                            source="verification_engine",
                            type="check_failure",
                            content=f"{score.name} failed for task: {task[:50]}... - {score.details}",
                            confidence=result.overall_score,
                            tags=[score.name, score.priority, "verification_failure"],
                        )
                    )

            # Store overall result
            kb.store(
                Knowledge(
                    source="verification_engine",
                    type="verification_result",
                    content=f"Task '{task}' -> {result.status.value} (score: {result.overall_score:.0%})",
                    confidence=result.overall_score,
                    tags=[result.status.value, "verification"],
                )
            )

        except Exception as e:
            logger.warning("[VerificationEngine] Failed to store knowledge: %s", e)

    def _query_prior_knowledge(
        self,
        task: str,
        output: str,
        context: dict,
    ) -> list:
        """Query Knowledge Bus for relevant prior knowledge."""
        try:
            from .knowledge_bus import KnowledgeBus

            kb = KnowledgeBus.get_instance()

            # Extract keywords from task
            keywords = self._extract_task_keywords(task)

            # Query for relevant knowledge
            prior = kb.query(
                tags=["verification"] + keywords,
                min_confidence=0.5,
                limit=10,
            )

            return prior

        except Exception as e:
            logger.warning("[VerificationEngine] Failed to query knowledge: %s", e)
            return []

    def _extract_task_keywords(self, task: str) -> list:
        """Extract keywords from task for knowledge query."""
        keywords = []
        task_lower = task.lower()

        if any(w in task_lower for w in ["조사", "research", "trends"]):
            keywords.append("research")
        if any(w in task_lower for w in ["코드", "code", "python"]):
            keywords.append("coding")
        if any(w in task_lower for w in ["작성", "write", "글"]):
            keywords.append("writing")
        if any(w in task_lower for w in ["번역", "translate"]):
            keywords.append("translation")

        return keywords if keywords else ["general"]

    def _format_revision_notes(
        self,
        rule_scores: list[ValidationScore],
        failed_rules: list[ValidationScore],
    ) -> str:
        """Format revision notes for failed rules."""
        notes = ["## 📝 수정 요청\n\n검증 결과, 다음과 같은 수정이 필요합니다:\n"]

        for score in rule_scores:
            if not score.passed:
                status_icon = "❌" if score.priority == "P0" else "⚠️"
                notes.append(f"### {status_icon} {score.name}:")
                notes.append(f"- 현재: {score.details}")
                notes.append(
                    f"- 점수: {score.score:.0%} (임계값: {score.threshold:.0%})"
                )
                notes.append("")

        return "\n".join(notes)


# Convenience function for drewgent_hooks
def get_verification_engine():
    """Get or initialize VerificationEngine instance."""
    try:
        return VerificationEngine()
    except Exception as e:
        print(f"[Drewgent] VerificationEngine init error: {e}")
        return None
