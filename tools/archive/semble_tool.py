#!/usr/bin/env python3
"""
Semble Tool Module

Semble is a semantic code search tool that indexes codebases and enables
natural-language queries. It provides much faster and more relevant results
than grep for exploratory questions about code.

Semble is invoked via: uvx --from "semble[mcp]" semble search <query> <path>

Semble indexes are stored at ~/.semble/ and persist across sessions.

Available tools:
- semble_search: Search code using natural language queries
- semble_find_related: Find code similar to a specific location

Usage:
    from tools.semble_tool import semble_search

    result = semble_search(query="authentication flow", path="/repo", top_k=5)
"""

import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEMBLE_CMD_BASE = ["uvx", "--from", "semble[mcp]", "semble"]


def check_semble_requirements() -> bool:
    """Check if uvx is available (required to run Semble)."""
    return shutil.which("uvx") is not None


def semble_search(
    query: str,
    path: str = ".",
    top_k: int = 5,
    task_id: str = None,
) -> str:
    """
    Search a codebase using Semble's semantic search.

    Args:
        query: Natural language query describing what to find
        path: Directory to search (default: current directory)
        top_k: Number of results to return (default: 5)
        task_id: Optional task identifier (ignored, for API compatibility)

    Returns:
        JSON string with search results
    """
    cmd = SEMBLE_CMD_BASE + [
        "search",
        query,
        path,
        "--top-k", str(top_k),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.abspath(os.path.expanduser(path)) if path != "." else None,
        )

        if result.returncode != 0:
            # Try to provide useful error message
            stderr = result.stderr.strip()
            if "no such option" in stderr.lower():
                return json.dumps({
                    "success": False,
                    "error": "Semble argument error",
                    "details": stderr,
                    "hint": "Check seems search query syntax"
                })
            return json.dumps({
                "success": False,
                "error": f"Semble exited with code {result.returncode}",
                "stderr": stderr[:500] if stderr else "",
            })

        # Parse output - Semble returns markdown-formatted results
        output = result.stdout.strip()

        return json.dumps({
            "success": True,
            "results": _parse_semble_output(output),
            "raw_output": output[:3000] if len(output) > 3000 else output,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Semble search timed out after 120 seconds",
        })
    except FileNotFoundError:
        return json.dumps({
            "success": False,
            "error": "uvx not found - please install uvx",
        })
    except Exception as e:
        logger.exception("Semble search failed")
        return json.dumps({
            "success": False,
            "error": str(e),
        })


def semble_find_related(
    file_path: str,
    line: int,
    path: str = ".",
    top_k: int = 5,
    task_id: str = None,
) -> str:
    """
    Find code similar to a specific location using Semble.

    Args:
        file_path: Path to the reference file
        line: Line number in the reference file
        path: Directory containing the codebase (default: current directory)
        top_k: Number of results to return (default: 5)
        task_id: Optional task identifier (ignored)

    Returns:
        JSON string with related code results
    """
    cmd = SEMBLE_CMD_BASE + [
        "find-related",
        file_path,
        str(line),
        path,
        "--top-k", str(top_k),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "error": f"Semble exited with code {result.returncode}",
                "stderr": result.stderr.strip()[:500] if result.stderr else "",
            })

        output = result.stdout.strip()

        return json.dumps({
            "success": True,
            "results": _parse_semble_output(output),
            "raw_output": output[:3000] if len(output) > 3000 else output,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Semble find-related timed out after 120 seconds",
        })
    except Exception as e:
        logger.exception("Semble find-related failed")
        return json.dumps({
            "success": False,
            "error": str(e),
        })


def _parse_semble_output(output: str) -> List[Dict[str, Any]]:
    """
    Parse Semble's markdown output into structured results.

    Expected format:
    ## 1. path/to/file:123-145  [score=0.025]
    ```
    code snippet...
    ```
    """
    results = []
    current_result: Optional[Dict[str, Any]] = None
    in_code_block = False

    for line in output.split("\n"):
        stripped = line.strip()

        if stripped.startswith("## "):
            # New result starts
            if current_result and current_result.get("code"):
                results.append(current_result)

            # Parse header: "## 1. path/to/file:123-145  [score=0.025]"
            header = stripped[3:].strip()  # Remove "## "
            parts = header.split("\t")

            location = parts[0] if parts else ""
            score = None

            # Extract score from [score=X]
            if "[" in location and "score=" in location:
                score_start = location.find("[score=") + 7
                score_end = location.find("]", score_start)
                if score_end > score_start:
                    try:
                        score = float(location[score_start:score_end])
                    except ValueError:
                        pass
                location = location[: location.find("[")].strip()

            # Parse file:line range
            file_path = location
            line_start = None
            line_end = None

            if ":" in location:
                file_part, range_part = location.rsplit(":", 1)
                if "-" in range_part:
                    try:
                        parts = range_part.split("-")
                        line_start = int(parts[0])
                        line_end = int(parts[1])
                    except ValueError:
                        pass
                    file_path = file_part
                else:
                    try:
                        line_start = int(range_part)
                        line_end = line_start
                    except ValueError:
                        pass
                    file_path = location

            current_result = {
                "file": file_path,
                "line_start": line_start,
                "line_end": line_end,
                "score": score,
                "code": "",
            }

        elif stripped.startswith("```"):
            in_code_block = not in_code_block

        elif current_result and in_code_block:
            current_result["code"] += line + "\n"

    if current_result and current_result.get("code"):
        results.append(current_result)

    return results


def _handle_semble_search(args: Dict[str, Any], **kwargs) -> str:
    """Handler for the semble_search tool."""
    return semble_search(
        query=args.get("query", ""),
        path=args.get("path", "."),
        top_k=args.get("top_k", 5),
        task_id=kwargs.get("task_id"),
    )


def _handle_semble_find_related(args: Dict[str, Any], **kwargs) -> str:
    """Handler for the semble_find_related tool."""
    return semble_find_related(
        file_path=args.get("file_path", ""),
        line=args.get("line", 1),
        path=args.get("path", "."),
        top_k=args.get("top_k", 5),
        task_id=kwargs.get("task_id"),
    )


SEARCH_SCHEMA = {
    "name": "semble_search",
    "description": "Search code using natural language queries via Semble semantic search. Use this instead of grep when exploring code by intent (e.g., 'how does authentication work', 'where is the cache invalidation'). Returns ranked results with file locations and code snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing what to find in the codebase",
            },
            "path": {
                "type": "string",
                "description": "Directory to search (default: current directory)",
                "default": ".",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5, max: 20)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

FIND_RELATED_SCHEMA = {
    "name": "semble_find_related",
    "description": "Find code similar to a specific location. Pass a file path and line number from a prior search result to discover related implementations. Use after initial sembe_search to explore related code.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the reference file",
            },
            "line": {
                "type": "integer",
                "description": "Line number in the reference file",
            },
            "path": {
                "type": "string",
                "description": "Directory containing the codebase (default: current directory)",
                "default": ".",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["file_path", "line"],
    },
}


from tools.registry import registry

registry.register(
    name="semble_search",
    toolset="research",
    schema=SEARCH_SCHEMA,
    handler=_handle_semble_search,
    check_fn=check_semble_requirements,
)

registry.register(
    name="semble_find_related",
    toolset="research",
    schema=FIND_RELATED_SCHEMA,
    handler=_handle_semble_find_related,
    check_fn=check_semble_requirements,
)
