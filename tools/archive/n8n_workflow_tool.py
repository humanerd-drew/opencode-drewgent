#!/usr/bin/env python3
"""
n8n Workflow Tool Module - Drewgent n8n REST API Integration

Provides programmatic workflow authoring, editing, and management via n8n REST API.
Tools: n8n_workflow_list, n8n_workflow_get, n8n_workflow_create,
       n8n_workflow_update, n8n_workflow_delete, n8n_workflow_execute,
       n8n_workflow_node_execute, n8n_workflow_save

Env:
    N8N_BASE_URL   — e.g. http://localhost:5678 (default: http://localhost:5678)
    N8N_API_KEY    — API key auth (or use N8N_USERNAME/N8N_PASSWORD)
    N8N_USERNAME   — optional username
    N8N_PASSWORD   — optional password
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
_API_KEY = os.environ.get("N8N_API_KEY", "")
_USERNAME = os.environ.get("N8N_USERNAME", "")
_PASSWORD = os.environ.get("N8N_PASSWORD", "")


def _headers() -> Dict[str, str]:
    """Build request headers with auth."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if _API_KEY:
        headers["X-N8N-API-KEY"] = _API_KEY
    return headers


def _auth_header() -> Optional[Dict[str, str]]:
    """Build Authorization header from username/password if no API key."""
    if not _API_KEY and _USERNAME and _PASSWORD:
        import base64
        creds = f"{_USERNAME}:{_PASSWORD}"
        return {"Authorization": f"Basic {base64.b64encode(creds.encode()).decode()}"}
    return None


def _request(
    method: str,
    path: str,
    data: Optional[Dict] = None,
    query: Optional[str] = None,
) -> Dict:
    """
    Make an HTTP request to n8n REST API.
    Returns parsed JSON dict.
    Raises on HTTP errors.
    """
    url = f"{_BASE_URL}{path}"
    if query:
        url += f"?{query}"

    headers = _headers()
    extra = _auth_header()
    if extra:
        headers.update(extra)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if raw:
                return json.loads(raw.decode("utf-8"))
            return {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8") if e.fp else ""
        raise Exception(
            f"n8n API error {e.code} on {method} {path}: {body_text[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise Exception(f"n8n connection error on {method} {path}: {e}") from e


# =============================================================================
# Tool: n8n_workflow_list
# =============================================================================
def n8n_workflow_list(
    active: Optional[bool] = None,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> str:
    """
    List all workflows in n8n.
    active: if True, only active; if False, only inactive; if None, all
    limit: max results per page (default 100)
    cursor: pagination cursor for next page
    Returns JSON string with workflows array + nextCursor.
    """
    query_parts = [f"limit={limit}"]
    if active is not None:
        query_parts.append(f"active={str(active).lower()}")
    if cursor:
        query_parts.append(f"cursor={cursor}")
    query = "&".join(query_parts)

    try:
        result = _request("GET", "/rest/workflows", query=query)
        workflows = result.get("data", result.get("workflows", []))
        # normalize to list
        if isinstance(workflows, dict):
            workflows = [workflows]
        next_cursor = result.get("nextCursor", result.get("meta", {}).get("nextCursor"))

        out = {
            "count": len(workflows),
            "workflows": [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "active": w.get("active"),
                    "nodesCount": len(w.get("nodes", [])),
                    "pinData": bool(w.get("pinData")),
                    "versionId": w.get("versionId"),
                    "updatedAt": w.get("updatedAt"),
                    "createdAt": w.get("createdAt"),
                }
                for w in workflows
            ],
        }
        if next_cursor:
            out["nextCursor"] = next_cursor
        return json.dumps(out, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_get
# =============================================================================
def n8n_workflow_get(workflow_id: str) -> str:
    """
    Get a single workflow by ID (full JSON with nodes, connections, etc.).
    workflow_id: n8n numeric or UUID workflow ID
    """
    try:
        wf = _request("GET", f"/rest/workflows/{workflow_id}")
        # return full workflow — nodes, connections, settings, etc.
        return json.dumps(wf, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_create
# =============================================================================
def n8n_workflow_create(
    name: str,
    nodes: Optional[List[Dict]] = None,
    connections: Optional[Dict] = None,
    settings: Optional[Dict] = None,
    active: bool = False,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Create a new n8n workflow.
    name: workflow name
    nodes: list of node objects (see n8n node schema)
    connections: connections dict {nodeName: {outputType: [{node, index}]}}
    settings: workflow settings dict
    active: whether to activate immediately
    tags: list of tag names (created if needed)
    """
    payload = {
        "name": name,
        "nodes": nodes or [],
        "connections": connections or {},
        "active": active,
        "settings": settings or {"executionOrder": "v1"},
    }
    if tags is not None:
        payload["tags"] = tags

    try:
        wf = _request("POST", "/rest/workflows", data=payload)
        return json.dumps(
            {"success": True, "id": wf.get("id"), "name": wf.get("name"), "active": wf.get("active")},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_update
# =============================================================================
def n8n_workflow_update(
    workflow_id: str,
    name: Optional[str] = None,
    nodes: Optional[List[Dict]] = None,
    connections: Optional[Dict] = None,
    settings: Optional[Dict] = None,
    active: Optional[bool] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Update an existing workflow (full replace).
    workflow_id: workflow ID
    name: new name (optional)
    nodes: new nodes array (optional — full replace)
    connections: new connections (optional — full replace)
    settings: new settings (optional)
    active: set active state (optional)
    tags: new tags (optional)
    """
    # Fetch current first, then patch
    try:
        current = _request("GET", f"/rest/workflows/{workflow_id}")
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch workflow: {e}"})

    if "error" in str(type(current)):
        return json.dumps({"error": f"Workflow {workflow_id} not found"})

    patch = {"name": name or current.get("name", "Untitled")}
    if nodes is not None:
        patch["nodes"] = nodes
    else:
        patch["nodes"] = current.get("nodes", [])
    if connections is not None:
        patch["connections"] = connections
    else:
        patch["connections"] = current.get("connections", {})
    if settings is not None:
        patch["settings"] = settings
    else:
        patch["settings"] = current.get("settings", {})
    if active is not None:
        patch["active"] = active
    else:
        patch["active"] = current.get("active", False)
    if tags is not None:
        patch["tags"] = tags

    try:
        updated = _request("PATCH", f"/rest/workflows/{workflow_id}", data=patch)
        return json.dumps(
            {"success": True, "id": updated.get("id"), "name": updated.get("name"), "active": updated.get("active")},
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_delete
# =============================================================================
def n8n_workflow_delete(workflow_id: str) -> str:
    """Delete a workflow by ID."""
    try:
        _request("DELETE", f"/rest/workflows/{workflow_id}")
        return json.dumps({"success": True, "deleted": workflow_id})
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_execute
# =============================================================================
def n8n_workflow_execute(workflow_id: str, data: Optional[Dict] = None) -> str:
    """
    Trigger a workflow run via webhook (POST) or manual execution.
    Uses n8n's manual execution endpoint.
    data: optional input data to pass as startNodeData
    """
    try:
        # Check if active first
        wf = _request("GET", f"/rest/workflows/{workflow_id}")
        active = wf.get("active", False)

        if not active:
            # Activate first
            _request("PATCH", f"/rest/workflows/{workflow_id}", data={"active": True})
            # Wait briefly
            import time
            time.sleep(2)

        # Trigger via webhook — find trigger node
        trigger_nodes = [n for n in wf.get("nodes", []) if n.get("type", "").startswith("n8n-nodes-base.")]
        # Use manual execution API
        exec_data = data or {}
        result = _request(
            "POST",
            f"/rest/workflows/{workflow_id}/run",
            data={"startNodes": [], "destinationNode": "", "runData": exec_data},
        )
        return json.dumps(
            {
                "success": True,
                "executionId": result.get("executionId"),
                "mode": result.get("mode"),
                "startedAt": result.get("startedAt"),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_node_execute
# =============================================================================
def n8n_workflow_node_execute(
    workflow_id: str,
    node_name: str,
    input_data: Optional[Dict] = None,
) -> str:
    """
    Execute a single node in a workflow with specific input data.
    workflow_id: workflow ID
    node_name: exact node name (case-sensitive)
    input_data: JSON data to pass to the node
    """
    try:
        payload = {
            "nodeName": node_name,
            "runData": input_data or {},
        }
        result = _request(
            "POST",
            f"/rest/workflows/{workflow_id}/run",
            data=payload,
        )
        return json.dumps(
            {
                "success": True,
                "nodeName": node_name,
                "executionId": result.get("executionId"),
                "data": result,
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_workflow_save
# =============================================================================
def n8n_workflow_save(
    workflow_id: str,
    nodes: List[Dict],
    connections: Dict,
    settings: Optional[Dict] = None,
    name: Optional[str] = None,
) -> str:
    """
    Save (replace) a workflow's nodes and connections.
    Convenience wrapper around n8n_workflow_update for node editing.
    workflow_id: workflow ID (use "new" to create fresh)
    nodes: full nodes array (from workflow_get then edited)
    connections: full connections dict
    settings: optional settings dict
    name: optional new name
    """
    if workflow_id == "new":
        return n8n_workflow_create(name=name or "Untitled", nodes=nodes, connections=connections, settings=settings)
    return n8n_workflow_update(
        workflow_id=workflow_id,
        nodes=nodes,
        connections=connections,
        settings=settings,
        name=name,
    )


# =============================================================================
# Tool: n8n_tags_list
# =============================================================================
def n8n_tags_list() -> str:
    """List all tags in n8n."""
    try:
        tags = _request("GET", "/rest/tags")
        if isinstance(tags, list):
            return json.dumps({"tags": tags}, indent=2)
        return json.dumps({"tags": tags.get("data", [])}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_tags_create
# =============================================================================
def n8n_tags_create(name: str, color: Optional[str] = None) -> str:
    """Create a new tag."""
    payload = {"name": name}
    if color:
        payload["color"] = color
    try:
        tag = _request("POST", "/rest/tags", data=payload)
        return json.dumps({"success": True, "id": tag.get("id"), "name": tag.get("name"), "color": tag.get("color")}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Tool: n8n_executions_list
# =============================================================================
def n8n_executions_list(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    List recent workflow executions.
    workflow_id: filter by specific workflow
    status: "success" | "error" | "running" | "waiting"
    limit: max results (default 20)
    """
    query_parts = [f"limit={limit}"]
    if workflow_id:
        query_parts.append(f"workflowId={workflow_id}")
    if status:
        query_parts.append(f"status={status}")
    query = "&".join(query_parts)

    try:
        result = _request("GET", "/rest/executions", query=query)
        executions = result.get("data", result.get("executions", []))
        if isinstance(executions, dict):
            executions = [executions]
        return json.dumps(
            {
                "count": len(executions),
                "executions": [
                    {
                        "id": e.get("id"),
                        "workflowId": e.get("workflowId"),
                        "status": e.get("status"),
                        "mode": e.get("mode"),
                        "startedAt": e.get("startedAt"),
                        "finishedAt": e.get("finishedAt"),
                        "duration": e.get("duration"),
                    }
                    for e in executions
                ],
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Registry
# =============================================================================
def _register_tools():
    from tools.registry import registry

    tools = [
        {
            "name": "n8n_workflow_list",
            "description": "List all n8n workflows. Returns id, name, active state, node count, tags. Use to discover existing workflows before editing.",
            "schema": {
                "type": "object",
                "properties": {
                    "active": {
                        "type": ["boolean", "null"],
                        "description": "Filter by active state: true=active only, false=inactive only, null=all",
                    },
                    "limit": {"type": "integer", "default": 100, "description": "Results per page"},
                    "cursor": {"type": "string", "description": "Pagination cursor for next page"},
                },
            },
            "handler": lambda args: n8n_workflow_list(
                active=args.get("active"),
                limit=args.get("limit", 100),
                cursor=args.get("cursor"),
            ),
        },
        {
            "name": "n8n_workflow_get",
            "description": "Get a single workflow's full JSON (nodes, connections, settings). Use this to read before editing.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "n8n workflow ID"},
                },
                "required": ["workflow_id"],
            },
            "handler": lambda args: n8n_workflow_get(args["workflow_id"]),
        },
        {
            "name": "n8n_workflow_create",
            "description": "Create a new n8n workflow. Provide name, nodes array, connections dict, optional settings. Use n8n_workflow_get to read an existing workflow as a template.",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Workflow name"},
                    "nodes": {
                        "type": "array",
                        "description": "Array of n8n node objects (type, name, parameters, position, etc.)",
                        "default": [],
                    },
                    "connections": {"type": "object", "description": "n8n connections object", "default": {}},
                    "settings": {"type": "object", "description": "Workflow settings"},
                    "active": {"type": "boolean", "default": False, "description": "Activate immediately"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tag names to assign"},
                },
                "required": ["name"],
            },
            "handler": lambda args: n8n_workflow_create(
                name=args["name"],
                nodes=args.get("nodes"),
                connections=args.get("connections"),
                settings=args.get("settings"),
                active=args.get("active", False),
                tags=args.get("tags"),
            ),
        },
        {
            "name": "n8n_workflow_update",
            "description": "Update an existing workflow. Provide workflow_id + fields to change. Fetches current first, then patches only what you provide.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "Workflow ID to update"},
                    "name": {"type": "string", "description": "New name"},
                    "nodes": {"type": "array", "description": "New nodes array (full replace)"},
                    "connections": {"type": "object", "description": "New connections dict (full replace)"},
                    "settings": {"type": "object", "description": "New settings"},
                    "active": {"type": "boolean", "description": "Set active state"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags"},
                },
                "required": ["workflow_id"],
            },
            "handler": lambda args: n8n_workflow_update(
                workflow_id=args["workflow_id"],
                name=args.get("name"),
                nodes=args.get("nodes"),
                connections=args.get("connections"),
                settings=args.get("settings"),
                active=args.get("active"),
                tags=args.get("tags"),
            ),
        },
        {
            "name": "n8n_workflow_delete",
            "description": "Delete a workflow by ID. Irreversible.",
            "schema": {
                "type": "object",
                "properties": {"workflow_id": {"type": "string", "description": "Workflow ID to delete"}},
                "required": ["workflow_id"],
            },
            "handler": lambda args: n8n_workflow_delete(args["workflow_id"]),
        },
        {
            "name": "n8n_workflow_execute",
            "description": "Trigger a workflow execution by ID. Activates if inactive, then runs.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "Workflow ID to run"},
                    "data": {"type": "object", "description": "Optional input data"},
                },
                "required": ["workflow_id"],
            },
            "handler": lambda args: n8n_workflow_execute(args["workflow_id"], args.get("data")),
        },
        {
            "name": "n8n_workflow_node_execute",
            "description": "Execute a single node within a workflow with specific input data. Useful for debugging nodes.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "Workflow ID"},
                    "node_name": {"type": "string", "description": "Exact node name (case-sensitive)"},
                    "input_data": {"type": "object", "description": "JSON data to pass to the node"},
                },
                "required": ["workflow_id", "node_name"],
            },
            "handler": lambda args: n8n_workflow_node_execute(
                args["workflow_id"], args["node_name"], args.get("input_data")
            ),
        },
        {
            "name": "n8n_workflow_save",
            "description": "Save/replace a workflow's nodes and connections. Pass workflow_id='new' to create. Use n8n_workflow_get to read an existing workflow as template, modify nodes/connections, then save.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "Workflow ID or 'new' to create"},
                    "nodes": {"type": "array", "description": "Full nodes array"},
                    "connections": {"type": "object", "description": "Full connections dict"},
                    "settings": {"type": "object"},
                    "name": {"type": "string", "description": "Workflow name (required if workflow_id='new')"},
                },
                "required": ["workflow_id", "nodes", "connections"],
            },
            "handler": lambda args: n8n_workflow_save(
                workflow_id=args["workflow_id"],
                nodes=args["nodes"],
                connections=args["connections"],
                settings=args.get("settings"),
                name=args.get("name"),
            ),
        },
        {
            "name": "n8n_tags_list",
            "description": "List all tags in n8n.",
            "schema": {"type": "object", "properties": {}},
            "handler": lambda _: n8n_tags_list(),
        },
        {
            "name": "n8n_tags_create",
            "description": "Create a tag in n8n.",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "color": {"type": "string", "description": "Hex color code e.g. '#ff0000'"},
                },
                "required": ["name"],
            },
            "handler": lambda args: n8n_tags_create(args["name"], args.get("color")),
        },
        {
            "name": "n8n_executions_list",
            "description": "List recent workflow executions for monitoring and debugging.",
            "schema": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "Filter by workflow ID"},
                    "status": {"type": "string", "description": "Filter: success, error, running, waiting"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
            "handler": lambda args: n8n_executions_list(
                workflow_id=args.get("workflow_id"),
                status=args.get("status"),
                limit=args.get("limit", 20),
            ),
        },
    ]

    for tool in tools:
        registry.register(
            name=tool["name"],
            toolset="n8n",
            schema=tool["schema"],
            handler=tool["handler"],
        )


_register_tools()