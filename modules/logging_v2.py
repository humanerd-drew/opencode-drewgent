"""
===============================================================================
Drewgent Logging v2 + Self-Evolution Foundation
===============================================================================
Location: modules/logging_v2.py
Version: 2.0 (Integrated Growth Model)

Purpose:
    1. Structured logging with correlation IDs
    2. Database storage for analysis
    3. Foundation for self-evolution

Key Principles:
    - Observe: Log everything important
    - Analyze: Patterns detected via queries
    - Learn: Knowledge base updates (via separate module)
    - Reflect: Self-questioning (via separate module)

Safety Constraints:
    - NO self-modifying code
    - NO direct deployment
    - Knowledge updates go to MEMORY/ markdown only
===============================================================================
"""

import json
import uuid
import sqlite3
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from contextvars import ContextVar
from typing import Optional, Any
from functools import wraps
import threading
import logging
from logging.handlers import RotatingFileHandler

# =============================================================================
# CONTEXT VARIABLES (Correlation IDs)
# =============================================================================

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


def get_request_id() -> str:
    """Get current request ID or generate new one"""
    return request_id_var.get() or str(uuid.uuid4())


def get_session_id() -> str:
    """Get current session ID"""
    return session_id_var.get() or ""


def set_request_id(req_id: Optional[str] = None) -> str:
    """Set request ID for current context"""
    req_id = req_id or str(uuid.uuid4())
    request_id_var.set(req_id)
    return req_id


def set_session_id(sess_id: str) -> None:
    """Set session ID for current context"""
    session_id_var.set(sess_id)


# =============================================================================
# DATABASE SETUP
# =============================================================================

LOG_DB_PATH = Path.home() / ".drewgent" / "logging_v2.db"
LOG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_log_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory and optimized settings"""
    conn = sqlite3.connect(str(LOG_DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def init_log_database():
    """Initialize logging_v2 database with full schema"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # audit_log - Main audit trail
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            session_id TEXT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
            logger TEXT NOT NULL,
            message TEXT NOT NULL,
            context_json TEXT,
            stack_trace TEXT,
            source_file TEXT,
            source_line INTEGER,
            reflection_question TEXT,
            reflection_answer TEXT,
            pattern_tag TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # task_history - Task execution history
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id TEXT PRIMARY KEY,
            request_id TEXT,
            session_id TEXT,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
            priority INTEGER DEFAULT 0,
            loop_count INTEGER DEFAULT 0,
            input_tokens INTEGER,
            output_tokens INTEGER,
            duration_ms INTEGER,
            error_message TEXT,
            result_summary TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            similar_task_ids TEXT,
            advice_given TEXT,
            lessons_learned TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # tool_call_registry - Tool invocation tracking
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_call_registry (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            session_id TEXT,
            task_id TEXT,
            tool_name TEXT NOT NULL,
            parameters_json TEXT,
            result_summary TEXT,
            duration_ms INTEGER,
            success INTEGER NOT NULL DEFAULT 1,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            retry_count INTEGER DEFAULT 0,
            pattern_tag TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # pattern_detections - Detected patterns for self-evolution
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_detections (
            id TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'alert', 'critical')),
            description TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            occurrence_count INTEGER DEFAULT 1,
            affected_items_json TEXT,
            recommendation TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # -------------------------------------------------------------------------
    # knowledge_updates - Knowledge base update history
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_updates (
            id TEXT PRIMARY KEY,
            update_type TEXT NOT NULL,
            target_file TEXT NOT NULL,
            summary TEXT NOT NULL,
            content_before TEXT,
            content_after TEXT,
            trigger_log_id TEXT,
            auto_generated INTEGER DEFAULT 0,
            approved_by_drew INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # -------------------------------------------------------------------------
    # INDEXES
    # -------------------------------------------------------------------------
    indexes = [
        ("idx_audit_request", "audit_log", "request_id"),
        ("idx_audit_session", "audit_log", "session_id"),
        ("idx_audit_timestamp", "audit_log", "timestamp"),
        ("idx_audit_level", "audit_log", "level"),
        ("idx_audit_logger", "audit_log", "logger"),
        ("idx_audit_pattern_tag", "audit_log", "pattern_tag"),
        ("idx_task_request", "task_history", "request_id"),
        ("idx_task_session", "task_history", "session_id"),
        ("idx_task_status", "task_history", "status"),
        ("idx_task_created", "task_history", "created_at"),
        ("idx_tool_request", "tool_call_registry", "request_id"),
        ("idx_tool_session", "tool_call_registry", "session_id"),
        ("idx_tool_name", "tool_call_registry", "tool_name"),
        ("idx_tool_success", "tool_call_registry", "success"),
        ("idx_pattern_type", "pattern_detections", "pattern_type"),
        ("idx_pattern_status", "pattern_detections", "status"),
        ("idx_pattern_severity", "pattern_detections", "severity"),
    ]

    for idx_name, table, column in indexes:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")

    # -------------------------------------------------------------------------
    # FTS5 VIRTUAL TABLE for full-text search
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS audit_fts USING fts5(
            message,
            context_json,
            content='audit_log',
            content_rowid='rowid'
        )
    """)

    # FTS triggers
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS audit_ai AFTER INSERT ON audit_log BEGIN
            INSERT INTO audit_fts(rowid, message, context_json) 
            VALUES (new.rowid, new.message, new.context_json);
        END
    """)

    conn.commit()
    conn.close()
    print(f"[logging_v2] Database initialized: {LOG_DB_PATH}")


# =============================================================================
# AUDIT LOG FUNCTIONS
# =============================================================================


def audit_log(
    level: str,
    logger_name: str,
    message: str,
    context: Optional[dict] = None,
    stack_trace: Optional[str] = None,
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
    pattern_tag: Optional[str] = None,
) -> str:
    """
    Write to audit log.

    Args:
        level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        logger_name: __name__ of the logger
        message: Log message
        context: Additional context dict
        stack_trace: Exception stack trace if applicable
        source_file: Source file name
        source_line: Source line number
        pattern_tag: Optional tag for pattern detection (e.g., 'error_timeout')

    Returns:
        Generated audit log ID (UUID)
    """
    conn = get_log_db_connection()
    cursor = conn.cursor()

    log_id = str(uuid.uuid4())
    req_id = get_request_id()
    sess_id = get_session_id()
    timestamp = datetime.now().isoformat()

    context_json = json.dumps(context) if context else None

    cursor.execute(
        """
        INSERT INTO audit_log (
            id, request_id, session_id, timestamp, level, logger, 
            message, context_json, stack_trace, source_file, source_line, pattern_tag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            log_id,
            req_id,
            sess_id,
            timestamp,
            level,
            logger_name,
            message,
            context_json,
            stack_trace,
            source_file,
            source_line,
            pattern_tag,
        ),
    )

    conn.commit()
    conn.close()

    return log_id


# =============================================================================
# TASK LOGGING FUNCTIONS
# =============================================================================


def log_task_start(task_id: str, task_type: str, priority: int = 0, **kwargs) -> str:
    """Log task start with context"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    req_id = get_request_id()
    created_at = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO task_history (
            id, request_id, task_type, status, priority, created_at
        ) VALUES (?, ?, ?, 'pending', ?, ?)
    """,
        (task_id, req_id, task_type, priority, created_at),
    )

    conn.commit()
    conn.close()

    audit_log(
        level="INFO",
        logger_name="task_manager",
        message=f"Task started: {task_type}",
        context={"task_id": task_id, "task_type": task_type, **kwargs},
    )

    return task_id


def log_task_complete(
    task_id: str,
    status: str = "completed",
    result_summary: str = None,
    lessons_learned: str = None,
    **kwargs,
) -> None:
    """Log task completion"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    completed_at = datetime.now().isoformat()

    cursor.execute(
        """
        UPDATE task_history 
        SET status = ?, result_summary = ?, completed_at = ?, lessons_learned = ?
        WHERE id = ?
    """,
        (status, result_summary, completed_at, lessons_learned, task_id),
    )

    conn.commit()
    conn.close()

    audit_log(
        level="INFO" if status == "completed" else "ERROR",
        logger_name="task_manager",
        message=f"Task {status}: {result_summary or ''}",
        context={"task_id": task_id, "status": status, **kwargs},
    )


def log_task_update(
    task_id: str,
    status: str = None,
    loop_count: int = None,
    duration_ms: int = None,
    error_message: str = None,
    **kwargs,
) -> None:
    """Update task fields"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if status:
        updates.append("status = ?")
        params.append(status)
    if loop_count is not None:
        updates.append("loop_count = ?")
        params.append(loop_count)
    if duration_ms is not None:
        updates.append("duration_ms = ?")
        params.append(duration_ms)
    if error_message:
        updates.append("error_message = ?")
        params.append(error_message)

    if updates:
        params.append(task_id)
        cursor.execute(
            f"UPDATE task_history SET {', '.join(updates)} WHERE id = ?", params
        )
        conn.commit()
    conn.close()


# =============================================================================
# TOOL CALL TRACKING
# =============================================================================


def log_tool_call(
    tool_name: str,
    parameters: dict,
    result_summary: str = None,
    duration_ms: int = None,
    success: bool = True,
    error: str = None,
    retry_count: int = 0,
    pattern_tag: str = None,
) -> str:
    """Log tool invocation"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    tool_id = str(uuid.uuid4())
    req_id = get_request_id()
    sess_id = get_session_id()

    cursor.execute(
        """
        INSERT INTO tool_call_registry (
            id, request_id, session_id, tool_name, parameters_json,
            result_summary, duration_ms, success, error_message, retry_count, pattern_tag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            tool_id,
            req_id,
            sess_id,
            tool_name,
            json.dumps(_sanitize_parameters(parameters)),
            result_summary,
            duration_ms,
            1 if success else 0,
            error,
            retry_count,
            pattern_tag,
        ),
    )

    conn.commit()
    conn.close()

    return tool_id


def _sanitize_parameters(params: dict, sensitive_keys: list = None) -> dict:
    """
    Remove sensitive information from parameters.

    Strategy:
    1. If vault reference (vault_xxx) - keep as is (already a ref)
    2. If sensitive key detected - try to register in vault, get ref
    3. If vault unavailable - fallback to REDACTED
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password",
            "token",
            "api_key",
            "apikey",
            "secret",
            "auth",
            "credential",
            "authorization",
            "access_token",
            "refresh_token",
            "session_token",
            "private_key",
            "client_secret",
            "bearer",
        ]

    sanitized = {}

    # Try to use vault for sensitive values
    try:
        from secrets_vault import vault as secure_vault

        vault_available = True
    except ImportError:
        vault_available = False

    for key, value in params.items():
        key_lower = key.lower()

        if isinstance(value, str) and value.startswith("vault_"):
            # Already a vault reference - keep as is
            sanitized[key] = value

        elif any(s in key_lower for s in sensitive_keys):
            # Sensitive key detected
            if vault_available and isinstance(value, str) and len(value) > 0:
                # Try to register in vault and get reference
                try:
                    ref = secure_vault.register(
                        name=f"param_{key}",
                        value=value,
                        category="parameter",
                        description=f"Auto-registered from log_tool_call: {key}",
                    )
                    sanitized[key] = ref
                except Exception:
                    # Vault failed - use fallback
                    sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = "***REDACTED***"

        elif isinstance(value, dict):
            sanitized[key] = _sanitize_parameters(value, sensitive_keys)
        else:
            sanitized[key] = value

    return sanitized


# =============================================================================
# QUERY FUNCTIONS (FOR ANALYSIS)
# =============================================================================


def search_logs(
    query: str = None,
    level: str = None,
    logger_name: str = None,
    from_time: str = None,
    to_time: str = None,
    limit: int = 100,
    pattern_tag: str = None,
) -> list[dict]:
    """Search audit logs with filters"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM audit_log WHERE 1=1"
    params = []

    if query:
        sql = """
            SELECT audit_log.* FROM audit_log 
            JOIN audit_fts ON audit_log.rowid = audit_fts.rowid
            WHERE audit_fts MATCH ?
        """
        params.append(query)

    if level:
        sql += " AND level = ?"
        params.append(level)

    if logger_name:
        sql += " AND logger = ?"
        params.append(logger_name)

    if from_time:
        sql += " AND timestamp >= ?"
        params.append(from_time)

    if to_time:
        sql += " AND timestamp <= ?"
        params.append(to_time)

    if pattern_tag:
        sql += " AND pattern_tag = ?"
        params.append(pattern_tag)

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_recent_errors(hours: int = 24, limit: int = 50) -> list[dict]:
    """Get recent errors"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM audit_log 
        WHERE level IN ('ERROR', 'CRITICAL')
        AND timestamp >= datetime('now', ?)
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (f"-{hours} hours", limit),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_task_stats(from_time: str = None) -> dict:
    """Get task statistics"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    where = "WHERE 1=1"
    params = []

    if from_time:
        where += " AND created_at >= ?"
        params.append(from_time)

    cursor.execute(
        f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            AVG(duration_ms) as avg_duration_ms,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens
        FROM task_history
        {where}
    """,
        params,
    )

    result = dict(cursor.fetchone())
    conn.close()

    return result


def get_tool_stats(tool_name: str = None, hours: int = 24) -> dict:
    """Get tool call statistics"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    where = "WHERE created_at >= datetime('now', ?)"
    params = [f"-{hours} hours"]

    if tool_name:
        where += " AND tool_name = ?"
        params.append(tool_name)

    cursor.execute(
        f"""
        SELECT 
            COUNT(*) as total_calls,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
            AVG(duration_ms) as avg_duration_ms,
            SUM(retry_count) as total_retries
        FROM tool_call_registry
        {where}
    """,
        params,
    )

    row = cursor.fetchone()
    result = dict(row) if row else {}
    if result and result.get("total_calls", 0) > 0:
        result["success_rate"] = result["successes"] / result["total_calls"]
    conn.close()

    return result


def get_error_rate(hours: int = 1) -> float:
    """Calculate error rate"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            CAST(SUM(CASE WHEN level IN ('ERROR', 'CRITICAL') THEN 1 ELSE 0 END) AS FLOAT) /
            CAST(COUNT(*) AS FLOAT) as error_rate
        FROM audit_log
        WHERE timestamp >= datetime('now', ?)
    """,
        (f"-{hours} hours",),
    )

    result = cursor.fetchone()
    conn.close()

    return result["error_rate"] if result and result["error_rate"] else 0.0


def find_similar_tasks(task_type: str, limit: int = 5) -> list[dict]:
    """Find similar past tasks for contextual advice"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, task_type, status, duration_ms, error_message, created_at
        FROM task_history
        WHERE task_type = ?
        ORDER BY created_at DESC
        LIMIT ?
    """,
        (task_type, limit),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# =============================================================================
# PATTERN DETECTION FUNCTIONS
# =============================================================================


def detect_and_record_pattern(
    pattern_type: str,
    severity: str,
    description: str,
    affected_items: list,
    recommendation: str = None,
) -> str:
    """
    Detect and record a pattern.
    Called by the pattern analyzer periodically.
    """
    conn = get_log_db_connection()
    cursor = conn.cursor()

    # Check if pattern already exists
    cursor.execute(
        """
        SELECT id, occurrence_count FROM pattern_detections
        WHERE pattern_type = ? AND description = ? AND status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
    """,
        (pattern_type, description),
    )

    existing = cursor.fetchone()
    now = datetime.now().isoformat()

    if existing:
        # Update existing pattern
        pattern_id = existing["id"]
        cursor.execute(
            """
            UPDATE pattern_detections
            SET last_seen = ?, occurrence_count = occurrence_count + 1
            WHERE id = ?
        """,
            (now, pattern_id),
        )
    else:
        # Create new pattern
        pattern_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO pattern_detections (
                id, pattern_type, severity, description, 
                first_seen, last_seen, affected_items_json, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                pattern_id,
                pattern_type,
                severity,
                description,
                now,
                now,
                json.dumps(affected_items),
                recommendation,
            ),
        )

    conn.commit()
    conn.close()

    audit_log(
        level="WARNING" if severity in ("warning", "alert") else "INFO",
        logger_name="pattern_detector",
        message=f"Pattern detected: {pattern_type}",
        context={
            "pattern_id": pattern_id,
            "severity": severity,
            "description": description,
            "recommendation": recommendation,
        },
        pattern_tag=f"pattern_{pattern_type}",
    )

    return pattern_id


def get_active_patterns(severity: str = None) -> list[dict]:
    """Get all active patterns, optionally filtered by severity"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    where = "WHERE status = 'active'"
    params = []

    if severity:
        where += " AND severity = ?"
        params.append(severity)

    cursor.execute(
        f"""
        SELECT * FROM pattern_detections
        {where}
        ORDER BY 
            CASE severity 
                WHEN 'critical' THEN 1 
                WHEN 'alert' THEN 2 
                WHEN 'warning' THEN 3 
                ELSE 4 
            END,
            last_seen DESC
    """,
        params,
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def acknowledge_pattern(pattern_id: str, action: str = "acknowledged") -> None:
    """Mark a pattern as acknowledged/resolved/ignored"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE pattern_detections
        SET status = ?
        WHERE id = ?
    """,
        (action, pattern_id),
    )

    conn.commit()
    conn.close()


# =============================================================================
# KNOWLEDGE UPDATE FUNCTIONS
# =============================================================================


def record_knowledge_update(
    update_type: str,
    target_file: str,
    summary: str,
    content_before: str = None,
    content_after: str = None,
    trigger_log_id: str = None,
    auto_generated: bool = False,
) -> str:
    """
    Record a knowledge base update.
    Does NOT modify the actual file - that requires separate action.
    """
    conn = get_log_db_connection()
    cursor = conn.cursor()

    update_id = str(uuid.uuid4())

    cursor.execute(
        """
        INSERT INTO knowledge_updates (
            id, update_type, target_file, summary,
            content_before, content_after, trigger_log_id, auto_generated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            update_id,
            update_type,
            target_file,
            summary,
            content_before[:500] if content_before else None,
            content_after[:500] if content_after else None,
            trigger_log_id,
            1 if auto_generated else 0,
        ),
    )

    conn.commit()
    conn.close()

    audit_log(
        level="INFO",
        logger_name="knowledge_manager",
        message=f"Knowledge update recorded: {update_type}",
        context={
            "update_id": update_id,
            "target_file": target_file,
            "summary": summary,
            "auto_generated": auto_generated,
        },
    )

    return update_id


def get_pending_knowledge_updates() -> list[dict]:
    """Get knowledge updates pending Drew approval"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM knowledge_updates
        WHERE approved_by_drew = 0
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def approve_knowledge_update(update_id: str) -> bool:
    """Mark a knowledge update as approved by Drew"""
    conn = get_log_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE knowledge_updates
        SET approved_by_drew = 1
        WHERE id = ?
    """,
        (update_id,),
    )

    affected = cursor.rowcount
    conn.commit()
    conn.close()

    return affected > 0


# =============================================================================
# PYTHON LOGGING INTEGRATION
# =============================================================================


class LoggingV2Handler(logging.Handler):
    """Custom handler that writes to logging_v2 database"""

    def emit(self, record: logging.LogRecord):
        try:
            level_map = {
                logging.DEBUG: "DEBUG",
                logging.INFO: "INFO",
                logging.WARNING: "WARNING",
                logging.ERROR: "ERROR",
                logging.CRITICAL: "CRITICAL",
            }

            context = {}
            if hasattr(record, "__dict__"):
                for key in ["task_id", "agent", "user_id", "session_id"]:
                    if hasattr(record, key):
                        context[key] = getattr(record, key)

            audit_log(
                level=level_map.get(record.levelno, "INFO"),
                logger_name=record.name,
                message=record.getMessage(),
                context=context if context else None,
                stack_trace=record.exc_text,
                source_file=record.filename,
                source_line=record.lineno,
            )
        except Exception:
            pass  # Prevent handler errors


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a Python logger configured for logging_v2"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not any(isinstance(h, LoggingV2Handler) for h in logger.handlers):
        logger.addHandler(LoggingV2Handler())

    return logger


logger = get_logger(__name__)

# =============================================================================
# INITIALIZATION
# =============================================================================

init_log_database()
