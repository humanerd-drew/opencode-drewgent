"""
Cron job scheduler - executes due jobs.

Provides tick() which checks for due jobs and runs them. The gateway
calls this every 60 seconds from a background thread.

Uses a file-based lock (~/.drewgent/cron/.tick.lock) so only one tick
runs at a time if multiple processes overlap.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import subprocess
import sys

# fcntl is Unix-only; on Windows use msvcrt for file locking
try:
    import fcntl
except ImportError:
    fcntl = None
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
import time
from pathlib import Path
from typing import Optional

# Determine the Python interpreter to use when dispatching cron jobs.
# The gateway may run under a different Python than the venv where openai
# is installed (e.g. system/homebrew Python vs .venv Python).  We always
# use sys.executable so we inherit whatever the gateway already uses —
# but if that Python lacks openai, run_job() will dispatch to cron_runner.py
# via subprocess.run([sys.executable, ...]) and cron_runner.py will in turn
# use the venv python to guarantee openai is importable.
_venv_python = str(Path(__file__).parent.parent / "source" / "drewgent-agent" / ".venv" / "bin" / "python")

# Add parent directory to path for imports BEFORE repo-level imports.
# Without this, standalone invocations (e.g. after `drewgent update` reloads
# the module) fail with ModuleNotFoundError for drewgent_time et al.
sys.path.insert(0, str(Path(__file__).parent.parent))

from drewgent_constants import get_drewgent_home
from drewgent_cli.config import load_config
from drewgent_time import now as _drewgent_now

logger = logging.getLogger(__name__)

# Valid delivery platforms — used to validate user-supplied platform names
# in cron delivery targets, preventing env var enumeration via crafted names.
_KNOWN_DELIVERY_PLATFORMS = frozenset({
    "telegram", "discord", "slack", "whatsapp", "signal",
    "matrix", "mattermost", "homeassistant", "dingtalk", "feishu",
    "wecom", "sms", "email", "webhook",
})

from cron.jobs import get_due_jobs, mark_job_run, save_job_output, advance_next_run, OUTPUT_DIR

# Path to the drewgent-agent source root (parent of cron/)
_AGENT_ROOT = Path(__file__).parent.parent.resolve()

# Sentinel: when a cron agent has nothing new to report, it can start its
# response with this marker to suppress delivery.  Output is still saved
# locally for audit.
SILENT_MARKER = "[SILENT]"

# Resolve Drewgent home directory (respects DREW_HOME override)
_drewgent_home = get_drewgent_home()

# File-based lock prevents concurrent ticks from gateway + daemon + systemd timer
_LOCK_DIR = _drewgent_home / "cron"
_LOCK_FILE = _LOCK_DIR / ".tick.lock"


def _resolve_origin(job: dict) -> Optional[dict]:
    """Extract origin info from a job, preserving any extra routing metadata."""
    origin = job.get("origin")
    if not origin:
        return None
    platform = origin.get("platform")
    chat_id = origin.get("chat_id")
    if platform and chat_id:
        return origin
    return None


def _resolve_delivery_target(job: dict) -> Optional[dict]:
    """Resolve the concrete auto-delivery target for a cron job, if any."""
    deliver = job.get("deliver", "local")
    origin = _resolve_origin(job)

    if deliver == "local":
        return None

    if deliver == "origin":
        if origin:
            return {
                "platform": origin["platform"],
                "chat_id": str(origin["chat_id"]),
                "thread_id": origin.get("thread_id"),
            }
        # Origin missing (e.g. job created via API/script) — try each
        # platform's home channel as a fallback instead of silently dropping.
        for platform_name in ("matrix", "telegram", "discord", "slack"):
            chat_id = os.getenv(f"{platform_name.upper()}_HOME_CHANNEL", "")
            if chat_id:
                logger.info(
                    "Job '%s' has deliver=origin but no origin; falling back to %s home channel",
                    job.get("name", job.get("id", "?")),
                    platform_name,
                )
                return {
                    "platform": platform_name,
                    "chat_id": chat_id,
                    "thread_id": None,
                }
        return None

    if ":" in deliver:
        platform_name, rest = deliver.split(":", 1)
        platform_key = platform_name.lower()

        from tools.send_message_tool import _parse_target_ref

        parsed_chat_id, parsed_thread_id, is_explicit = _parse_target_ref(platform_key, rest)
        if is_explicit:
            chat_id, thread_id = parsed_chat_id, parsed_thread_id
        else:
            chat_id, thread_id = rest, None

        # Resolve human-friendly labels like "Alice (dm)" to real IDs.
        try:
            from gateway.channel_directory import resolve_channel_name
            resolved = resolve_channel_name(platform_key, chat_id)
            if resolved:
                parsed_chat_id, parsed_thread_id, resolved_is_explicit = _parse_target_ref(platform_key, resolved)
                if resolved_is_explicit:
                    chat_id, thread_id = parsed_chat_id, parsed_thread_id
                else:
                    chat_id = resolved
        except Exception:
            pass

        return {
            "platform": platform_name,
            "chat_id": chat_id,
            "thread_id": thread_id,
        }

    platform_name = deliver
    if origin and origin.get("platform") == platform_name:
        return {
            "platform": platform_name,
            "chat_id": str(origin["chat_id"]),
            "thread_id": origin.get("thread_id"),
        }

    if platform_name.lower() not in _KNOWN_DELIVERY_PLATFORMS:
        return None
    chat_id = os.getenv(f"{platform_name.upper()}_HOME_CHANNEL", "")
    if not chat_id:
        return None

    return {
        "platform": platform_name,
        "chat_id": chat_id,
        "thread_id": None,
    }


def _deliver_result(job: dict, content: str, adapters=None, loop=None) -> None:
    """
    Deliver job output to the configured target (origin chat, specific platform, etc.).

    When ``adapters`` and ``loop`` are provided (gateway is running), tries to
    use the live adapter first — this supports E2EE rooms (e.g. Matrix) where
    the standalone HTTP path cannot encrypt.  Falls back to standalone send if
    the adapter path fails or is unavailable.
    """
    target = _resolve_delivery_target(job)
    if not target:
        if job.get("deliver", "local") != "local":
            logger.warning(
                "Job '%s' deliver=%s but no concrete delivery target could be resolved",
                job["id"],
                job.get("deliver", "local"),
            )
        return

    platform_name = target["platform"]
    chat_id = target["chat_id"]
    thread_id = target.get("thread_id")

    from tools.send_message_tool import _send_to_platform
    from gateway.config import load_gateway_config, Platform

    platform_map = {
        "telegram": Platform.TELEGRAM,
        "discord": Platform.DISCORD,
        "slack": Platform.SLACK,
        "whatsapp": Platform.WHATSAPP,
        "signal": Platform.SIGNAL,
        "matrix": Platform.MATRIX,
        "mattermost": Platform.MATTERMOST,
        "homeassistant": Platform.HOMEASSISTANT,
        "dingtalk": Platform.DINGTALK,
        "feishu": Platform.FEISHU,
        "wecom": Platform.WECOM,
        "email": Platform.EMAIL,
        "sms": Platform.SMS,
    }
    platform = platform_map.get(platform_name.lower())
    if not platform:
        logger.warning("Job '%s': unknown platform '%s' for delivery", job["id"], platform_name)
        return

    try:
        config = load_gateway_config()
    except Exception as e:
        logger.error("Job '%s': failed to load gateway config for delivery: %s", job["id"], e)
        return

    pconfig = config.platforms.get(platform)
    if not pconfig or not pconfig.enabled:
        logger.warning("Job '%s': platform '%s' not configured/enabled", job["id"], platform_name)
        return

    # Optionally wrap the content with a header/footer so the user knows this
    # is a cron delivery.  Wrapping is on by default; set cron.wrap_response: false
    # in config.yaml for clean output.
    wrap_response = True
    try:
        user_cfg = load_config()
        wrap_response = user_cfg.get("cron", {}).get("wrap_response", True)
    except Exception:
        pass

    if wrap_response:
        task_name = job.get("name", job["id"])
        delivery_content = (
            f"Cronjob Response: {task_name}\n"
            f"-------------\n\n"
            f"{content}\n\n"
            f"Note: The agent cannot see this message, and therefore cannot respond to it."
        )
    else:
        delivery_content = content

    # Extract MEDIA: tags so attachments are forwarded as files, not raw text
    from gateway.platforms.base import BasePlatformAdapter
    media_files, cleaned_delivery_content = BasePlatformAdapter.extract_media(delivery_content)

    # Prefer the live adapter when the gateway is running — this supports E2EE
    # rooms (e.g. Matrix) where the standalone HTTP path cannot encrypt.
    runtime_adapter = (adapters or {}).get(platform)
    if runtime_adapter is not None and loop is not None and getattr(loop, "is_running", lambda: False)():
        send_metadata = {"thread_id": thread_id} if thread_id else None
        try:
            future = asyncio.run_coroutine_threadsafe(
                runtime_adapter.send(chat_id, delivery_content, metadata=send_metadata),
                loop,
            )
            send_result = future.result(timeout=60)
            if send_result and not getattr(send_result, "success", True):
                err = getattr(send_result, "error", "unknown")
                logger.warning(
                    "Job '%s': live adapter send to %s:%s failed (%s), falling back to standalone",
                    job["id"], platform_name, chat_id, err,
                )
            else:
                logger.info("Job '%s': delivered to %s:%s via live adapter", job["id"], platform_name, chat_id)
                return
        except Exception as e:
            logger.warning(
                "Job '%s': live adapter delivery to %s:%s failed (%s), falling back to standalone",
                job["id"], platform_name, chat_id, e,
            )

    # Standalone path: run the async send in a fresh event loop (safe from any thread)
    coro = _send_to_platform(platform, pconfig, chat_id, cleaned_delivery_content, thread_id=thread_id, media_files=media_files)
    try:
        result = asyncio.run(coro)
    except RuntimeError:
        # asyncio.run() checks for a running loop before awaiting the coroutine;
        # when it raises, the original coro was never started — close it to
        # prevent "coroutine was never awaited" RuntimeWarning, then retry in a
        # fresh thread that has no running loop.
        coro.close()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _send_to_platform(platform, pconfig, chat_id, cleaned_delivery_content, thread_id=thread_id, media_files=media_files))
            result = future.result(timeout=30)
    except Exception as e:
        logger.error("Job '%s': delivery to %s:%s failed: %s", job["id"], platform_name, chat_id, e)
        return

    if result and result.get("error"):
        logger.error("Job '%s': delivery error: %s", job["id"], result["error"])
    else:
        logger.info("Job '%s': delivered to %s:%s", job["id"], platform_name, chat_id)


_SCRIPT_TIMEOUT = 120  # seconds


def _run_job_script(script_path: str) -> tuple[bool, str]:
    """Execute a cron job's data-collection script and capture its output.

    Scripts must reside within DREW_HOME/scripts/.  Both relative and
    absolute paths are resolved and validated against this directory to
    prevent arbitrary script execution via path traversal or absolute
    path injection.

    Args:
        script_path: Path to a Python script.  Relative paths are resolved
            against DREW_HOME/scripts/.  Absolute and ~-prefixed paths
            are also validated to ensure they stay within the scripts dir.

    Returns:
        (success, output) — on failure *output* contains the error message so the
        LLM can report the problem to the user.
    """
    from drewgent_constants import get_drewgent_home

    scripts_dir = get_drewgent_home() / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir_resolved = scripts_dir.resolve()

    raw = Path(script_path).expanduser()
    if raw.is_absolute():
        path = raw.resolve()
    else:
        path = (scripts_dir / raw).resolve()

    # Guard against path traversal, absolute path injection, and symlink
    # escape — scripts MUST reside within DREW_HOME/scripts/.
    try:
        path.relative_to(scripts_dir_resolved)
    except ValueError:
        return False, (
            f"Blocked: script path resolves outside the scripts directory "
            f"({scripts_dir_resolved}): {script_path!r}"
        )

    if not path.exists():
        return False, f"Script not found: {path}"
    if not path.is_file():
        return False, f"Script path is not a file: {path}"

    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=_SCRIPT_TIMEOUT,
            cwd=str(path.parent),
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            parts = [f"Script exited with code {result.returncode}"]
            if stderr:
                parts.append(f"stderr:\n{stderr}")
            if stdout:
                parts.append(f"stdout:\n{stdout}")
            return False, "\n".join(parts)

        # Redact any secrets that may appear in script output before
        # they are injected into the LLM prompt context.
        try:
            from agent.redact import redact_sensitive_text
            stdout = redact_sensitive_text(stdout)
        except Exception:
            pass
        return True, stdout

    except subprocess.TimeoutExpired:
        return False, f"Script timed out after {_SCRIPT_TIMEOUT}s: {path}"
    except Exception as exc:
        return False, f"Script execution failed: {exc}"


def _build_job_prompt(job: dict) -> str:
    """Build the effective prompt for a cron job, optionally loading one or more skills first."""
    prompt = job.get("prompt", "")
    skills = job.get("skills")

    # Run data-collection script if configured, inject output as context.
    script_path = job.get("script")
    if script_path:
        success, script_output = _run_job_script(script_path)
        if success:
            if script_output:
                prompt = (
                    "## Script Output\n"
                    "The following data was collected by a pre-run script. "
                    "Use it as context for your analysis.\n\n"
                    f"```\n{script_output}\n```\n\n"
                    f"{prompt}"
                )
            else:
                prompt = (
                    "[Script ran successfully but produced no output.]\n\n"
                    f"{prompt}"
                )
        else:
            prompt = (
                "## Script Error\n"
                "The data-collection script failed. Report this to the user.\n\n"
                f"```\n{script_output}\n```\n\n"
                f"{prompt}"
            )

    # Always prepend cron execution guidance so the agent knows how
    # delivery works and can suppress delivery when appropriate.
    cron_hint = (
        "[SYSTEM: You are running as a scheduled cron job. "
        "DELIVERY: Your final response will be automatically delivered "
        "to the user — do NOT use send_message or try to deliver "
        "the output yourself. Just produce your report/output as your "
        "final response and the system handles the rest. "
        "SILENT: If there is genuinely nothing new to report, respond "
        "with exactly \"[SILENT]\" (nothing else) to suppress delivery. "
        "Never combine [SILENT] with content — either report your "
        "findings normally, or say [SILENT] and nothing more.]\n\n"
    )
    prompt = cron_hint + prompt
    if skills is None:
        legacy = job.get("skill")
        skills = [legacy] if legacy else []

    skill_names = [str(name).strip() for name in skills if str(name).strip()]
    if not skill_names:
        return prompt

    from tools.skills_tool import skill_view

    parts = []
    skipped: list[str] = []
    for skill_name in skill_names:
        loaded = json.loads(skill_view(skill_name))
        if not loaded.get("success"):
            error = loaded.get("error") or f"Failed to load skill '{skill_name}'"
            logger.warning("Cron job '%s': skill not found, skipping — %s", job.get("name", job.get("id")), error)
            skipped.append(skill_name)
            continue

        content = str(loaded.get("content") or "").strip()
        if parts:
            parts.append("")
        parts.extend(
            [
                f'[SYSTEM: The user has invoked the "{skill_name}" skill, indicating they want you to follow its instructions. The full skill content is loaded below.]',
                "",
                content,
            ]
        )

    if skipped:
        notice = (
            f"[SYSTEM: The following skill(s) were listed for this job but could not be found "
            f"and were skipped: {', '.join(skipped)}. "
            f"Start your response with a brief notice so the user is aware, e.g.: "
            f"'⚠️ Skill(s) not found and skipped: {', '.join(skipped)}']"
        )
        parts.insert(0, notice)

    if prompt:
        parts.extend(["", f"The user has provided the following instruction alongside the skill invocation: {prompt}"])
    return "\n".join(parts)


def _serialize_env_for_subprocess(job, prompt, model, runtime_kwargs, turn_route,
                                   max_iterations, reasoning_config, prefill_messages,
                                   providers_allowed, providers_ignored, providers_order,
                                   provider_sort, origin, delivery_target, _cron_session_id):
    """Serialize cron job context to a temp JSON file for the subprocess runner."""
    import tempfile
    payload = {
        "job": job,
        "prompt": prompt,
        "model": model,
        "runtime_kwargs": runtime_kwargs,
        "turn_route": turn_route,
        "max_iterations": max_iterations,
        "reasoning_config": reasoning_config,
        "prefill_messages": prefill_messages,
        "providers_allowed": providers_allowed,
        "providers_ignored": providers_ignored,
        "providers_order": providers_order,
        "provider_sort": provider_sort,
        "origin": origin,
        "delivery_target": delivery_target,
        "session_id": _cron_session_id,
    }
    fd, path = tempfile.mkstemp(suffix=".json", prefix="cron_runner_env_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def _extract_final_response_from_output(output_file: Path) -> str:
    """Parse the saved output file and return the final_response text."""
    try:
        content = output_file.read_text(encoding="utf-8")
        # Output format: ## Response\n{logged_response}\n--- or ## Error\n{error}
        marker = "## Response\n"
        idx = content.find(marker)
        if idx < 0:
            return ""
        start = idx + len(marker)
        end = content.find("\n---", start)
        if end < 0:
            end = len(content)
        return content[start:end].strip()
    except Exception:
        return ""


def run_job(job: dict) -> tuple[bool, str, str, Optional[str]]:
    """
    Execute a single cron job by dispatching to a subprocess.

    Uses sys.executable (the venv python that has openai) to run the agent,
    avoiding 'No module named openai' failures when the gateway process uses
    a different Python interpreter.

    Returns:
        Tuple of (success, full_output_doc, final_response, error_message)
    """
    _session_db = None
    try:
        from drewgent_state import SessionDB
        _session_db = SessionDB()
    except Exception as e:
        logger.debug("Job '%s': SQLite session store not available: %s", job.get("id", "?"), e)

    job_id = job["id"]
    job_name = job["name"]
    prompt = _build_job_prompt(job)
    origin = _resolve_origin(job)
    _cron_session_id = f"cron_{job_id}_{_drewgent_now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("Running job '%s' (ID: %s) via subprocess", job_name, job_id)
    logger.info("Prompt: %s", prompt[:100])

    try:
        if origin:
            os.environ["DREW_SESSION_PLATFORM"] = origin["platform"]
            os.environ["DREW_SESSION_CHAT_ID"] = str(origin["chat_id"])
            if origin.get("chat_name"):
                os.environ["DREW_SESSION_CHAT_NAME"] = origin["chat_name"]
        from dotenv import load_dotenv
        try:
            load_dotenv(str(_drewgent_home / ".env"), override=True, encoding="utf-8")
        except UnicodeDecodeError:
            load_dotenv(str(_drewgent_home / ".env"), override=True, encoding="latin-1")

        delivery_target = _resolve_delivery_target(job)
        if delivery_target:
            os.environ["DREW_CRON_AUTO_DELIVER_PLATFORM"] = delivery_target["platform"]
            os.environ["DREW_CRON_AUTO_DELIVER_CHAT_ID"] = str(delivery_target["chat_id"])
            if delivery_target.get("thread_id") is not None:
                os.environ["DREW_CRON_AUTO_DELIVER_THREAD_ID"] = str(delivery_target["thread_id"])

        model = job.get("model") or os.getenv("DREW_MODEL") or ""

        _cfg = {}
        try:
            import yaml
            _cfg_path = str(_drewgent_home / "config.yaml")
            if os.path.exists(_cfg_path):
                with open(_cfg_path) as _f:
                    _cfg = yaml.safe_load(_f) or {}
                _model_cfg = _cfg.get("model", {})
                if not job.get("model"):
                    if isinstance(_model_cfg, str):
                        model = _model_cfg
                    elif isinstance(_model_cfg, dict):
                        model = _model_cfg.get("default", model)
        except Exception as e:
            logger.warning("Job '%s': failed to load config.yaml, using defaults: %s", job_id, e)

        # Cron-specific model config (overrides global model for scheduled jobs)
        _cron_model_cfg = {}
        if isinstance(_cfg.get("cron"), dict):
            _cron_model_cfg = _cfg["cron"].get("model", {}) or {}
        if _cron_model_cfg.get("model") and not job.get("model"):
            model = _cron_model_cfg["model"]

        from drewgent_constants import parse_reasoning_effort
        effort = os.getenv("DREW_REASONING_EFFORT", "")
        if not effort:
            effort = str(_cfg.get("agent", {}).get("reasoning_effort", "")).strip()
        reasoning_config = parse_reasoning_effort(effort)

        prefill_messages = None
        prefill_file = os.getenv("HERMES_PREFILL_MESSAGES_FILE", "") or _cfg.get("prefill_messages_file", "")
        if prefill_file:
            import json as _json
            pfpath = Path(prefill_file).expanduser()
            if not pfpath.is_absolute():
                pfpath = _drewgent_home / pfpath
            if pfpath.exists():
                try:
                    with open(pfpath, "r", encoding="utf-8") as _pf:
                        prefill_messages = _json.load(_pf)
                    if not isinstance(prefill_messages, list):
                        prefill_messages = None
                except Exception as e:
                    logger.warning("Job '%s': failed to parse prefill messages file '%s': %s", job_id, pfpath, e)
                    prefill_messages = None

        max_iterations = _cfg.get("agent", {}).get("max_turns") or _cfg.get("max_turns") or 90

        pr = _cfg.get("provider_routing", {})
        smart_routing = _cfg.get("smart_model_routing", {}) or {}

        from drewgent_cli.runtime_provider import (
            resolve_runtime_provider,
            format_runtime_provider_error,
        )
        try:
            runtime_kwargs = {
                "requested": job.get("provider") or os.getenv("HERMES_INFERENCE_PROVIDER") or _cron_model_cfg.get("provider"),
            }
            if job.get("base_url"):
                runtime_kwargs["explicit_base_url"] = job.get("base_url")
            runtime = resolve_runtime_provider(**runtime_kwargs)
            # Fix api_mode: runtime provider uses global model config (minimax-m3)
            # for api_mode resolution, but cron jobs may use a different model.
            if runtime.get("provider") in ("opencode-go", "opencode-zen") and model:
                from drewgent_cli.models import opencode_model_api_mode
                corrected = opencode_model_api_mode(runtime["provider"], model)
                if corrected:
                    runtime["api_mode"] = corrected
        except Exception as exc:
            message = format_runtime_provider_error(exc)
            raise RuntimeError(message) from exc

        from agent.smart_model_routing import resolve_turn_route
        turn_route = resolve_turn_route(
            prompt,
            smart_routing,
            {
                "model": model,
                "api_key": runtime.get("api_key"),
                "base_url": runtime.get("base_url"),
                "provider": runtime.get("provider"),
                "api_mode": runtime.get("api_mode"),
                "command": runtime.get("command"),
                "args": list(runtime.get("args") or []),
            },
        )

        # Serialize context and dispatch to subprocess
        env_json_path = _serialize_env_for_subprocess(
            job, prompt, model, runtime_kwargs, turn_route,
            max_iterations, reasoning_config, prefill_messages,
            providers_allowed=pr.get("only"),
            providers_ignored=pr.get("ignore"),
            providers_order=pr.get("order"),
            provider_sort=pr.get("sort"),
            origin=origin,
            delivery_target=delivery_target,
            _cron_session_id=_cron_session_id,
        )

        try:
            # Use the venv python (which has openai) to run cron_runner.py.
            # sys.executable may be the gateway's Python (homebrew/system) which
            # lacks openai in site-packages — cron_runner.py is built to handle
            # this by also using the venv python, but we call it directly here
            # to guarantee openai is available on the first try.
            runner_path = str(_AGENT_ROOT / "cron_runner.py")
            result = subprocess.run(
                [_venv_python, runner_path, env_json_path],
                capture_output=True,
                text=True,
                timeout=None,  # Timeout is handled by cron_runner.py internally
            )
            # Read output file written by cron_runner.py
            # Output dir: ~/.drewgent/cron/output/{job_id}/
            output_dir = _OUTPUT_DIR / job_id
            if output_dir.exists():
                # Get most recent output file
                output_files = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                if output_files:
                    output_file = output_files[0]
                    with open(output_file, "r", encoding="utf-8") as f:
                        output = f.read()
                    final_response = _extract_final_response_from_output(output_file)
                else:
                    output = ""
                    final_response = ""
            else:
                output = ""
                final_response = ""

            if result.returncode == 0:
                logger.info("Job '%s' completed successfully", job_name)
                return True, output, final_response, None
            else:
                error_msg = result.stderr.strip() or "Subprocess failed with non-zero exit"
                # Try to extract error from output file
                if output and "## Error" in output:
                    err_start = output.find("## Error\n") + len("## Error\n")
                    err_end = output.find("\n##", err_start)
                    error_msg = output[err_start:err_end].strip()
                logger.error("Job '%s' failed: %s", job_name, error_msg)
                return False, output, "", error_msg

        finally:
            # Clean up temp JSON
            try:
                os.unlink(env_json_path)
            except Exception:
                pass

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.exception("Job '%s' failed: %s", job_name, error_msg)
        output = f"""# Cron Job: {job_name} (FAILED)

**Job ID:** {job_id}
**Run Time:** {_drewgent_now().strftime('%Y-%m-%d %H:%M:%S')}
**Schedule:** {job.get('schedule_display', 'N/A')}

## Prompt

{prompt}

## Error

```
{error_msg}
```
"""
        return False, output, "", error_msg

    finally:
        for key in (
            "DREW_SESSION_PLATFORM",
            "DREW_SESSION_CHAT_ID",
            "DREW_SESSION_CHAT_NAME",
            "DREW_CRON_AUTO_DELIVER_PLATFORM",
            "DREW_CRON_AUTO_DELIVER_CHAT_ID",
            "DREW_CRON_AUTO_DELIVER_THREAD_ID",
        ):
            os.environ.pop(key, None)
        if _session_db:
            try:
                _session_db.end_session(_cron_session_id, "cron_complete")
            except Exception as e:
                logger.debug("Job '%s': failed to end session: %s", job_id, e)
            try:
                _session_db.close()
            except Exception as e:
                logger.debug("Job '%s': failed to close SQLite session store: %s", job_id, e)


def _execute_script_only_job(job: dict) -> tuple[bool, str, str, Optional[str]]:
    """Execute a script-only cron job — no AI agent involved.

    The script is resolved via _run_job_script().  If the script outputs
    ``[SILENT]`` (or empty), delivery is suppressed.  Otherwise the raw
    script output becomes both the stored output and the delivery content.

    Returns:
        Tuple of (success, full_output_doc, final_response, error_message)
    """
    job_id = job["id"]
    job_name = job.get("name", job_id)
    script_path = job.get("script")
    now = _drewgent_now()

    if not script_path:
        error_msg = "script_only job has no script path"
        output = (
            f"# Cron Job: {job_name} (FAILED)\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## Error\n\n```\n{error_msg}\n```\n"
        )
        return False, output, "", error_msg

    # Load .env so scripts have access to API keys / credentials
    try:
        from dotenv import load_dotenv
        try:
            load_dotenv(str(_drewgent_home / ".env"), override=True, encoding="utf-8")
        except UnicodeDecodeError:
            load_dotenv(str(_drewgent_home / ".env"), override=True, encoding="latin-1")
    except Exception:
        pass

    success, script_output = _run_job_script(script_path)
    now_iso = now.strftime('%Y-%m-%d %H:%M:%S')

    if not success:
        output = (
            f"# Cron Job: {job_name} (FAILED)\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now_iso}\n"
            f"**Schedule:** {job.get('schedule_display', 'N/A')}\n\n"
            f"## Error\n\n```\n{script_output}\n```\n"
        )
        return False, output, "", script_output

    stripped = script_output.strip()
    if not stripped or stripped.upper() == "[SILENT]":
        logger.info("Job '%s': script returned [SILENT] — skipping delivery", job_name)
        output = (
            f"# Cron Job: {job_name}\n\n"
            f"**Job ID:** {job_id}\n"
            f"**Run Time:** {now_iso}\n"
            f"**Schedule:** {job.get('schedule_display', 'N/A')}\n\n"
            f"## Output\n\n{stripped if stripped else '(empty — suppressed)'}\n"
        )
        return True, output, "[SILENT]", None

    output = (
        f"# Cron Job: {job_name}\n\n"
        f"**Job ID:** {job_id}\n"
        f"**Run Time:** {now_iso}\n"
        f"**Schedule:** {job.get('schedule_display', 'N/A')}\n\n"
        f"## Output\n\n{script_output}\n"
    )
    return True, output, script_output, None


def _execute_one_job(job: dict, adapters=None, loop=None) -> bool:
    """Run a single cron job: advance schedule, execute, save, deliver.

    Designed to be submitted to a ThreadPoolExecutor for concurrent execution.

    Returns:
        True if the job succeeded, False otherwise.
    """
    try:
        advance_next_run(job["id"])
        if job.get("script_only"):
            success, output, final_response, error = _execute_script_only_job(job)
        else:
            success, output, final_response, error = run_job(job)
        output_file = save_job_output(job["id"], output)
        logger.info("Output saved to: %s", output_file)
        deliver_content = final_response if success else f"⚠️ Cron job '{job.get('name', job['id'])}' failed:\n{error}"
        should_deliver = bool(deliver_content)
        if should_deliver and success and SILENT_MARKER in deliver_content.strip().upper():
            logger.info("Job '%s': agent returned %s — skipping delivery", job["id"], SILENT_MARKER)
            should_deliver = False
        if should_deliver:
            try:
                _deliver_result(job, deliver_content, adapters=adapters, loop=loop)
            except Exception as de:
                logger.error("Delivery failed for job %s: %s", job["id"], de)
        mark_job_run(job["id"], success, error)
        return success
    except Exception as e:
        logger.error("Error processing job %s: %s", job['id'], e)
        mark_job_run(job["id"], False, str(e))
        return False


def tick(verbose: bool = True, adapters=None, loop=None) -> int:
    """
    Check and run all due jobs (concurrently via ThreadPoolExecutor).

    Uses a file lock so only one tick runs at a time, even if the gateway's
    in-process ticker and a standalone daemon or manual tick overlap.

    Args:
        verbose: Whether to print status messages
        adapters: Optional dict mapping Platform → live adapter (from gateway)
        loop: Optional asyncio event loop (from gateway) for live adapter sends

    Returns:
        Number of jobs executed (0 if another tick is already running)
    """
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)

    # Cross-platform file locking: fcntl on Unix, msvcrt on Windows
    lock_fd = None
    try:
        lock_fd = open(_LOCK_FILE, "w")
        if fcntl:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif msvcrt:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        logger.debug("Tick skipped — another instance holds the lock")
        if lock_fd is not None:
            lock_fd.close()
        return 0

    try:
        due_jobs = get_due_jobs()

        if verbose and not due_jobs:
            logger.info("%s - No jobs due", _drewgent_now().strftime('%H:%M:%S'))
            return 0

        if verbose:
            logger.info("%s - %s job(s) due (running concurrently)", _drewgent_now().strftime('%H:%M:%S'), len(due_jobs))

        if len(due_jobs) <= 1:
            for job in due_jobs:
                _execute_one_job(job, adapters=adapters, loop=loop)
            return len(due_jobs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(due_jobs), 8)) as pool:
            futures = [pool.submit(_execute_one_job, job, adapters, loop) for job in due_jobs]
            concurrent.futures.wait(futures)

        return len(due_jobs)
    finally:
        if fcntl:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        elif msvcrt:
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
        lock_fd.close()


if __name__ == "__main__":
    tick(verbose=True)
