"""Brain tools — bidirectional brain access for agent.

Two tools:
- brain_query: agent queries wiki for contextually relevant knowledge
- brain_record: agent intentionally saves knowledge to wiki

These tools give the agent active, bidirectional access to its own brain,
not just passive context injection.
"""

import json
import os
from pathlib import Path

from tools.registry import registry


# --------------------------------------------------------------------------,
#brain_record
# --------------------------------------------------------------------------


def brain_record(
    itype: str,
    content: str,
    target: str = "user",
    context: str = "",
    task_id: str = None,
) -> str:
    """Record a learning to the agent's brain (wiki).

    This gives the agent intentional, explicit control over what gets
    saved to its knowledge base. Unlike auto_learn which extracts patterns
    passively from conversation, brain_record lets the agent decide
    "this is worth remembering."

    Args:
        itype: Insight type — preference, correction, style_concise, tool, etc.
        content: What to remember
        target: Who this applies to — "user" (for user preferences) or "memory" (agent knowledge)
        context: Optional context about when/why this was recorded
        task_id: Current task context

    Returns:
        JSON result with success status and what was saved
    """
    try:
        from agent.auto_learn import AutoLearner, Insight, INSIGHT_CATEGORIES
        from drewgent_constants import get_drewgent_home

        # Validate itype against known categories
        valid_itypes = list(INSIGHT_CATEGORIES.keys())
        if not itype or itype.strip() not in valid_itypes:
            # Default to "general" for unknown/empty itype to avoid ugly wiki entries
            itype = "general"

        wiki_path = Path(os.getenv("HERMES_HOME", str(get_drewgent_home()))) / "memories"
        learner = AutoLearner(wiki_path=wiki_path, enabled=True)
        learner.enable(wiki_path)

        insight = Insight(
            target=target,
            itype=itype,
            content=content.strip(),
            context=context.strip() if context else "",
        )

        saved = learner.save_insight(insight)

        if saved:
            return json.dumps({
                "success": True,
                "saved": True,
                "itype": itype,
                "target": target,
                "preview": content.strip()[:100],
            })
        else:
            return json.dumps({
                "success": True,
                "saved": False,
                "reason": "insight already exists or write failed",
                "itype": itype,
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


# --------------------------------------------------------------------------
# brain_query
# --------------------------------------------------------------------------


def brain_query(
    query: str,
    context: str = "",
    max_results: int = 5,
    max_chars: int = 2000,
    task_id: str = None,
) -> str:
    """Query the agent's brain for relevant knowledge.

    This gives the agent active, real-time access to its knowledge base
    during reasoning. Instead of relying solely on static system-prompt
    injection, the agent can ask "what do I know about X?" and get
    contextually relevant responses.

    Args:
        query: What to search for (topic, tool name, preference question)
        context: Current task context for relevance ranking
        max_results: Maximum number of entries to return
        max_chars: Maximum total characters in response

    Returns:
        JSON result with relevant wiki entries formatted for reasoning
    """
    try:
        from agent.auto_learn import AutoLearner
        from drewgent_constants import get_drewgent_home

        wiki_path = Path(os.getenv("HERMES_HOME", str(get_drewgent_home()))) / "memories"
        learner = AutoLearner(wiki_path=wiki_path, enabled=True)
        learner.enable(wiki_path)

        result = learner.query_wiki(
            query=query.strip(),
            context=context.strip() if context else "",
            max_results=max_results,
            max_chars=max_chars,
        )

        return json.dumps({
            "success": True,
            "query": query,
            "results": result,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


def check_requirements() -> bool:
    """Brain tools require HERMES_HOME set (or default ~/.drewgent available)."""
    return True  # get_drewgent_home() always returns a valid path


registry.register(
    name="brain_query",
    toolset="brain",
    schema={
        "name": "brain_query",
        "description": """Query the agent's brain (knowledge base) for relevant information.

Use this when you need to know:
- What preferences has the user expressed?
- What tools or patterns has the user used before?
- What insights were learned from previous sessions?
- What context exists about a topic the user is asking about?

This is active querying — you formulate the question and get back relevant knowledge,
not just passive context injection from the system prompt.

Args:
  query: What to search for — be specific (e.g., "n8n workflow", "user preference concise", "docker error handling")
  context: Current task or conversation context to help rank results (optional)
  max_results: Maximum entries to return (default 5)
  max_chars: Maximum response size (default 2000)""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in the knowledge base. Be specific — topic names, tool names, preference keywords.",
                },
                "context": {
                    "type": "string",
                    "description": "Current task or conversation context to improve relevance ranking (optional).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 5).",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum total characters in response (default 2000).",
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: brain_query(
        query=args.get("query", ""),
        context=args.get("context", ""),
        max_results=args.get("max_results", 5),
        max_chars=args.get("max_chars", 2000),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=[],
)


registry.register(
    name="brain_record",
    toolset="brain",
    schema={
        "name": "brain_record",
        "description": """Record a learning to the agent's brain (knowledge base).

Use this when you have learned something worth remembering:
- The user expressed a preference ("I prefer concise answers")
- A correction was made ("don't use that approach, use this instead")
- A pattern was observed ("every time I ask about X, Y happens")
- A tool or technique worked well for a specific task
- Context about a project or technology the user is working on

This is intentional, explicit recording — unlike auto_learn which extracts
patterns passively, this is the agent deciding "this is worth saving."

Args:
  itype: Insight type — preference, correction, style_concise, tool, project, etc.
  content: What to remember (specific, actionable)
  target: Who this applies to — "user" (for user preferences) or "memory" (general agent knowledge)
  context: Optional context about when/why this was recorded""",
        "parameters": {
            "type": "object",
            "properties": {
                "itype": {
                    "type": "string",
                    "description": """Insight type — one of:
  preference: User preference or liking
  correction: Correction or negative preference
  style_concise: User prefers brief answers
  style_detailed: User prefers thorough answers
  style_command: User uses short command-style input
  style_cautious: User prefers careful/accurate responses
  tool: Tool or command pattern observed
  project: Project-specific context
  os: Operating system or environment fact""",
                },
                "content": {
                    "type": "string",
                    "description": "What to remember — be specific and actionable.",
                },
                "target": {
                    "type": "string",
                    "description": "Who this applies to — 'user' (user preferences) or 'memory' (agent knowledge). Default: user.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context about when/why this was recorded (optional).",
                },
            },
            "required": ["itype", "content"],
        },
    },
    handler=lambda args, **kw: brain_record(
        itype=args.get("itype", ""),
        content=args.get("content", ""),
        target=args.get("target", "user"),
        context=args.get("context", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=[],
)
