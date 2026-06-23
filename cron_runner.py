#!/usr/bin/env python3
"""
Standalone cron job runner.

Always runs with the correct Drewgent venv Python. The gateway process may run
under a different Python (system, homebrew, etc.) which lacks openai installed
in site-packages, causing 'No module named openai' when run_job() tries to
import run_agent inline.

This script is invoked by scheduler.run_job() via subprocess.run() with
sys.executable pointing to the venv Python — guaranteeing openai is importable.

Usage:
    python cron_runner.py <path_to_cron_env_json>
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime

from drewgent_constants import get_drewgent_home

# Load .env before anything else so API keys/credentials are available
_drew_home = get_drewgent_home()
_env_path = _drew_home / ".env"
if _env_path.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(str(_env_path), override=True, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            from dotenv import load_dotenv
            load_dotenv(str(_env_path), override=True, encoding="latin-1")
        except Exception as e:
            logger.warning("Failed to load .env with latin-1 fallback: %s", e)

# Resolve the drewgent-agent source root.
# When invoked as a subprocess from scheduler.run_job(), __file__ is
# <drewgent-home>/cron_runner.py, so parent is <drewgent-home>.
_AGENT_ROOT = Path(__file__).parent.resolve()
_SOURCE_ROOT = _AGENT_ROOT / "source" / "drewgent-agent"
sys.path.insert(0, str(_SOURCE_ROOT))

from drewgent_time import now as _drewgent_now
from cron.jobs import save_job_output, mark_job_run
from drewgent_state import SessionDB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cron_runner")


def main() -> int:
    if len(sys.argv) < 2:
        logger.error("Usage: python cron_runner.py <path_to_cron_env_json>")
        return 1

    env_path = Path(sys.argv[1])
    if not env_path.exists():
        logger.error("Cron env JSON not found: %s", env_path)
        return 1

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        logger.error("Failed to read cron env JSON: %s", e)
        return 1

    job = payload["job"]
    job_id = job["id"]
    job_name = job["name"]
    prompt = payload["prompt"]
    model = payload.get("model", "")
    turn_route = payload.get("turn_route", {})
    max_iterations = payload.get("max_iterations", 90)
    reasoning_config = payload.get("reasoning_config", {})
    prefill_messages = payload.get("prefill_messages")
    providers_allowed = payload.get("providers_allowed")
    providers_ignored = payload.get("providers_ignored")
    providers_order = payload.get("providers_order")
    provider_sort = payload.get("provider_sort")
    origin = payload.get("origin")
    delivery_target = payload.get("delivery_target")
    _cron_session_id = payload.get("session_id", f"cron_{job_id}_{_drewgent_now().strftime('%Y%m%d_%H%M%S')}")

    logger.info("Running job '%s' (ID: %s)", job_name, job_id)

    # Inject origin/delivery context
    if origin:
        os.environ["DREW_SESSION_PLATFORM"] = origin.get("platform", "")
        os.environ["DREW_SESSION_CHAT_ID"] = str(origin.get("chat_id", ""))
        if origin.get("chat_name"):
            os.environ["DREW_SESSION_CHAT_NAME"] = origin["chat_name"]

    if delivery_target:
        os.environ["DREW_CRON_AUTO_DELIVER_PLATFORM"] = delivery_target.get("platform", "")
        os.environ["DREW_CRON_AUTO_DELIVER_CHAT_ID"] = str(delivery_target.get("chat_id", ""))
        if delivery_target.get("thread_id") is not None:
            os.environ["DREW_CRON_AUTO_DELIVER_THREAD_ID"] = str(delivery_target["thread_id"])

    # SQLite session store
    _session_db = None
    try:
        _session_db = SessionDB()
    except Exception as e:
        logger.debug("Job '%s': SQLite session store not available: %s", job_id, e)

    try:
        import importlib.util
        _cron_agent_path = _AGENT_ROOT / "cron" / "cron_agent.py"
        _spec = importlib.util.spec_from_file_location("cron.cron_agent", _cron_agent_path)
        _cron_agent_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_cron_agent_mod)
        create_cron_agent = _cron_agent_mod.create_cron_agent

        agent = create_cron_agent(
            model=turn_route.get("model", model),
            api_key=turn_route.get("runtime", {}).get("api_key"),
            base_url=turn_route.get("runtime", {}).get("base_url"),
            provider=turn_route.get("runtime", {}).get("provider"),
            api_mode=turn_route.get("runtime", {}).get("api_mode"),
            acp_command=turn_route.get("runtime", {}).get("command"),
            acp_args=turn_route.get("runtime", {}).get("args"),
            max_iterations=max_iterations,
            reasoning_config=reasoning_config,
            prefill_messages=prefill_messages,
            providers_allowed=providers_allowed,
            providers_ignored=providers_ignored,
            providers_order=providers_order,
            provider_sort=provider_sort,
            session_id=_cron_session_id,
            session_db=_session_db,
        )

        # Inactivity-based timeout (same as scheduler.run_job)
        _cron_timeout = float(os.environ.get("DREW_CRON_TIMEOUT", 600))
        _cron_inactivity_limit = _cron_timeout if _cron_timeout > 0 else None
        _POLL_INTERVAL = 5.0
        _cf = __import__("concurrent.futures")
        _cron_pool = _cf.ThreadPoolExecutor(max_workers=1)
        _cron_future = _cron_pool.submit(agent.run_conversation, prompt)
        _inactivity_timeout = False

        try:
            if _cron_inactivity_limit is None:
                result = _cron_future.result()
            else:
                result = None
                while True:
                    done, _ = _cf.wait({_cron_future}, timeout=_POLL_INTERVAL)
                    if done:
                        result = _cron_future.result()
                        break
                    _idle_secs = 0.0
                    if hasattr(agent, "get_activity_summary"):
                        try:
                            _act = agent.get_activity_summary()
                            _idle_secs = _act.get("seconds_since_activity", 0.0)
                        except Exception as e:
                            logger.debug("Activity summary failed: %s", e)
                    if _idle_secs >= _cron_inactivity_limit:
                        _inactivity_timeout = True
                        break
        finally:
            _cron_pool.shutdown(wait=False)

        if _inactivity_timeout:
            _activity = {}
            if hasattr(agent, "get_activity_summary"):
                try:
                    _activity = agent.get_activity_summary()
                except Exception as e:
                    logger.debug("Activity summary on timeout failed: %s", e)
            _last_desc = _activity.get("last_activity_desc", "unknown")
            _secs_ago = _activity.get("seconds_since_activity", 0)
            _cur_tool = _activity.get("current_tool")
            _iter_n = _activity.get("api_call_count", 0)
            _iter_max = _activity.get("max_iterations", 0)

            logger.error(
                "Job '%s' idle for %.0fs (inactivity limit %.0fs) "
                "| last_activity=%s | iteration=%s/%s | tool=%s",
                job_name, _secs_ago, _cron_inactivity_limit,
                _last_desc, _iter_n, _iter_max,
                _cur_tool or "none",
            )
            if hasattr(agent, "interrupt"):
                agent.interrupt("Cron job timed out (inactivity)")
            raise TimeoutError(
                f"Cron job '{job_name}' idle for "
                f"{int(_secs_ago)}s (limit {int(_cron_inactivity_limit)}s) "
                f"— last activity: {_last_desc}"
            )

        final_response = result.get("final_response", "") or ""
        logged_response = final_response if final_response else "(No response generated)"

        output = f"""# Cron Job: {job_name}

**Job ID:** {job_id}
**Run Time:** {_drewgent_now().strftime('%Y-%m-%d %H:%M:%S')}
**Schedule:** {job.get('schedule_display', 'N/A')}

## Prompt

{prompt}

## Response

{logged_response}
"""

        logger.info("Job '%s' completed successfully", job_name)

        # Save output
        output_file = save_job_output(job_id, output)
        logger.info("Output saved to: %s", output_file)

        # Mark success
        mark_job_run(job_id, True, None)

        return 0

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
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

## Traceback

```
{tb_str}
```
"""

        output_file = save_job_output(job_id, output)
        logger.info("Output saved to: %s", output_file)

        mark_job_run(job_id, False, error_msg)

        return 1

    finally:
        # Clean up injected env vars
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


if __name__ == "__main__":
    sys.exit(main())