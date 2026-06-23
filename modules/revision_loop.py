"""
RevisionLoop - Drewgent's Response Revision System

Provides automatic revision of LLM responses that fail verification.
Enables a feedback loop where verification failures trigger revision attempts.

Architecture:
    Verification Result (REVISION)
        ↓
    RevisionLoop.revise()
        ↓
    LLM Revision Request (with revision_notes)
        ↓
    Revised Response
        ↓
    Re-verification
        ↓
    (if still fails) → Loop (max attempts)

Usage:
    from revision_loop import RevisionLoop

    revision_loop = RevisionLoop(max_attempts=1)
    result = await revision_loop.revise(
        original_task="user message",
        original_response="llm response",
        revision_notes="needs more detail",
        context={"session_id": "123"},
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RevisionResult:
    """Result from a revision attempt."""

    success: bool
    revised_response: Optional[str] = None
    attempt_number: int = 0
    error: Optional[str] = None


class RevisionLoop:
    """
    RevisionLoop handles automatic revision of LLM responses.

    When verification fails, RevisionLoop attempts to revise the response
    by sending it back to the LLM with revision instructions.
    """

    def __init__(self, max_attempts: int = 1):
        """
        Initialize RevisionLoop.

        Args:
            max_attempts: Maximum number of revision attempts (default: 1)
        """
        self.max_attempts = max_attempts

    async def revise(
        self,
        original_task: str,
        original_response: str,
        revision_notes: str,
        context: dict = None,
    ) -> RevisionResult:
        """
        Attempt to revise a response based on revision notes.

        Args:
            original_task: The original user task/message
            original_response: The LLM response that needs revision
            revision_notes: Notes on what needs to be revised
            context: Additional context (session_id, user_id, etc.)

        Returns:
            RevisionResult with success status, revised response, attempt count
        """
        context = context or {}
        session_id = context.get("session_id", "unknown")

        logger.info(
            "[RevisionLoop] Starting revision for session %s (max_attempts=%d)",
            session_id,
            self.max_attempts,
        )

        for attempt in range(1, self.max_attempts + 1):
            try:
                revised = await self._attempt_revision(
                    original_task=original_task,
                    original_response=original_response,
                    revision_notes=revision_notes,
                    attempt_number=attempt,
                    context=context,
                )

                if revised:
                    logger.info(
                        "[RevisionLoop] Revision successful (attempt %d/%d)",
                        attempt,
                        self.max_attempts,
                    )
                    return RevisionResult(
                        success=True,
                        revised_response=revised,
                        attempt_number=attempt,
                    )

            except Exception as e:
                logger.error(
                    "[RevisionLoop] Revision attempt %d failed: %s",
                    attempt,
                    str(e),
                )
                if attempt == self.max_attempts:
                    return RevisionResult(
                        success=False,
                        revised_response=None,
                        attempt_number=attempt,
                        error=str(e),
                    )

        logger.warning(
            "[RevisionLoop] All %d revision attempts failed",
            self.max_attempts,
        )
        return RevisionResult(
            success=False,
            revised_response=None,
            attempt_number=self.max_attempts,
            error="All revision attempts failed",
        )

    async def _attempt_revision(
        self,
        original_task: str,
        original_response: str,
        revision_notes: str,
        attempt_number: int,
        context: dict,
    ) -> Optional[str]:
        """
        Single revision attempt - calls LLM to revise response.

        Uses auxiliary_client.async_call_llm for the revision request.
        """
        # Import here to avoid circular imports at module load time
        try:
            from agent.auxiliary_client import async_call_llm, extract_content_or_reasoning
        except ImportError as e:
            logger.error(
                "[RevisionLoop] Could not import auxiliary_client: %s",
                str(e),
            )
            return None

        revision_prompt = f"""You are helping revise an LLM response that did not pass verification.

ORIGINAL TASK:
{original_task}

ORIGINAL RESPONSE (that needs revision):
{original_response}

VERIFICATION FAILURE NOTES:
{revision_notes}

Please provide an improved response that addresses the issues noted above.
Your revised response should:
1. Fix any errors or inaccuracies
2. Address any missing information or incomplete answers
3. Be clear, concise, and helpful

Respond ONLY with your revised response (no explanation of what you changed)."""

        messages = [{"role": "user", "content": revision_prompt}]

        try:
            response = await async_call_llm(
                task="revision",
                messages=messages,
                max_tokens=4000,
                timeout=60.0,
            )

            revised = extract_content_or_reasoning(response)

            if revised:
                logger.info(
                    "[RevisionLoop] LLM returned revised response (%d chars)",
                    len(revised),
                )
                return revised
            else:
                logger.warning(
                    "[RevisionLoop] LLM returned empty response",
                )
                return None

        except Exception as e:
            logger.error(
                "[RevisionLoop] LLM call failed: %s",
                str(e),
            )
            return None


# =============================================================================
# Standalone async interface
# =============================================================================


async def revise_with_revision_loop(
    original_task: str,
    original_response: str,
    revision_notes: str,
    context: dict = None,
    max_attempts: int = 1,
) -> RevisionResult:
    """
    Convenience function for one-off revision.

    Args:
        original_task: Original user task
        original_response: Response to revise
        revision_notes: What needs to be revised
        context: Additional context
        max_attempts: Max revision attempts

    Returns:
        RevisionResult
    """
    loop = RevisionLoop(max_attempts=max_attempts)
    return await loop.revise(
        original_task=original_task,
        original_response=original_response,
        revision_notes=revision_notes,
        context=context,
    )
