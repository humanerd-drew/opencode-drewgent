#!/usr/bin/env python3
"""
GBrain Tool Module - Knowledge Graph Brain Integration

Provides Drewgent agent with access to the gbrain knowledge graph.
gbrain is a hybrid search brain with:
  - Vector + keyword + RRF fusion search
  - Self-wiring typed links
  - Timeline tracking

This tool allows Drewgent to query gbrain for:
  - People, companies, projects
  - Relationships and connections
  - Historical context
  - Domain knowledge

Usage:
    brain_query(question: str, limit: int = 5) -> str
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

# gbrain configuration
GBRAIN_CWD = os.environ.get("GBRAIN_PATH", "/root/gbrain")
GBRAIN_BUN = os.environ.get("GBRAIN_BUN", "bun")


def _check_gbrain_available() -> bool:
    """Check if gbrain CLI is available."""
    try:
        result = subprocess.run(
            [GBRAIN_BUN, "--version"],
            cwd=GBRAIN_CWD,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_gbrain_query(question: str, limit: int = 5) -> Dict[str, Any]:
    """Run a gbrain query and return structured results."""
    try:
        result = subprocess.run(
            [
                GBRAIN_BUN, "run", "src/cli.ts", "query",
                question,
                "--limit", str(limit),
            ],
            cwd=GBRAIN_CWD,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"gbrain query failed: {result.stderr}")
            return {"error": result.stderr, "results": []}

        # Parse output - gbrain outputs markdown-style results
        output = result.stdout.strip()
        return {"results": output, "raw": output}

    except subprocess.TimeoutExpired:
        return {"error": "gbrain query timed out", "results": []}
    except Exception as e:
        logger.error(f"gbrain query error: {e}")
        return {"error": str(e), "results": []}


def _run_gbrain_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Run a gbrain keyword search."""
    try:
        result = subprocess.run(
            [
                GBRAIN_BUN, "run", "src/cli.ts", "search",
                query,
                "--limit", str(limit),
            ],
            cwd=GBRAIN_CWD,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"error": result.stderr, "results": []}

        return {"results": result.stdout.strip(), "raw": result.stdout}

    except Exception as e:
        logger.error(f"gbrain search error: {e}")
        return {"error": str(e), "results": []}


def _run_gbrain_stats() -> Dict[str, Any]:
    """Get gbrain brain statistics."""
    try:
        result = subprocess.run(
            [GBRAIN_BUN, "run", "src/cli.ts", "stats"],
            cwd=GBRAIN_CWD,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"stats": result.stdout.strip()}

    except Exception as e:
        logger.error(f"gbrain stats error: {e}")
        return {"error": str(e)}


def brain_query(question: str, limit: int = 5) -> str:
    """
    Query the gbrain knowledge graph using hybrid search.

    Args:
        question: The question to search for
        limit: Maximum number of results (default: 5)

    Returns:
        JSON string with search results
    """
    result = _run_gbrain_query(question, limit)
    return json.dumps(result, ensure_ascii=False)


def brain_search(query: str, limit: int = 5) -> str:
    """
    Keyword search in gbrain knowledge graph.

    Args:
        query: Keywords to search for
        limit: Maximum number of results (default: 5)

    Returns:
        JSON string with search results
    """
    result = _run_gbrain_search(query, limit)
    return json.dumps(result, ensure_ascii=False)


def brain_stats() -> str:
    """
    Get gbrain brain statistics.

    Returns:
        JSON string with brain stats
    """
    result = _run_gbrain_stats()
    return json.dumps(result, ensure_ascii=False)


# Register as Drewgent tool
registry.register(
    name="brain_query",
    toolset="brain",
    schema={
        "name": "brain_query",
        "description": "Query the gbrain knowledge graph for facts, people, companies, and relationships. Use this when the user asks about something that might be in the knowledge base - things like 'who works at X', 'tell me about Y', 'what do we know about Z'. Returns hybrid search results with relevance scores.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to search for in the knowledge graph",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["question"],
        },
    },
    handler=lambda args, **kw: brain_query(
        question=args.get("question", ""),
        limit=args.get("limit", 5),
    ),
    check_fn=_check_gbrain_available,
    requires_env=[],
)

registry.register(
    name="brain_search",
    toolset="brain",
    schema={
        "name": "brain_search",
        "description": "Keyword search in gbrain knowledge graph. Use for exact keyword matching when brain_query returns too broad results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search for",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: brain_search(
        query=args.get("query", ""),
        limit=args.get("limit", 5),
    ),
    check_fn=_check_gbrain_available,
    requires_env=[],
)

registry.register(
    name="brain_stats",
    toolset="brain",
    schema={
        "name": "brain_stats",
        "description": "Get statistics about the gbrain knowledge graph - number of pages, chunks, embeddings, links, and tags.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    handler=lambda args, **kw: brain_stats(),
    check_fn=_check_gbrain_available,
    requires_env=[],
)
