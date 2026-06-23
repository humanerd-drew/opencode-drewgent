#!/usr/bin/env python3
"""
Drewgent Auto-Update Checker
============================
Checks for Drewgent updates from GitHub and optionally:
- Writes update status to a file (for Obsidian/polling)
- Sends notification via Discord
- Auto-pulls updates

Usage:
    python3 check_drewgent_update.py                    # Check only
    python3 check_drewgent_update.py --notify           # Notify via Discord
    python3 check_drewgent_update.py --autopull       # Auto-pull if behind

Cron setup (every 6 hours):
    drewgent cron add "every 6h" "Check Drewgent updates" --script check_drewgent_update.py --skill drewgent
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add drewgent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from drewgent_cli.banner import check_for_updates
    from drewgent_constants import get_drewgent_home
except ImportError:
    # Fallback if not in drewgent env
    check_for_updates = None
    get_drewgent_home = lambda: Path.home() / ".drewgent"


# ============================================================================
# Configuration
# ============================================================================

UPDATE_STATUS_FILE = Path(__file__).parent / "update_status.json"
DISCORD_WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"


# ============================================================================
# Update Checking
# ============================================================================


def get_update_status() -> dict:
    """Get current update status."""
    now = datetime.now().isoformat()

    if check_for_updates is None:
        return {
            "timestamp": now,
            "status": "error",
            "behind": None,
            "message": "check_for_updates not available",
        }

    behind = check_for_updates()

    if behind is None:
        return {
            "timestamp": now,
            "status": "unknown",
            "behind": None,
            "message": "Could not check for updates",
        }
    elif behind == 0:
        return {
            "timestamp": now,
            "status": "up_to_date",
            "behind": 0,
            "message": "Drewgent is up to date!",
        }
    else:
        return {
            "timestamp": now,
            "status": "update_available",
            "behind": behind,
            "message": f"Drewgent is {behind} commit(s) behind. Consider updating!",
        }


# ============================================================================
# Notification
# ============================================================================


def send_discord_notification(status: dict) -> bool:
    """Send update notification to Discord webhook."""
    webhook_url = os.getenv(DISCORD_WEBHOOK_ENV)
    if not webhook_url:
        return False

    import urllib.request

    # Color codes (decimal)
    colors = {
        "up_to_date": 3066993,  # Green
        "update_available": 15105570,  # Orange
        "error": 10038562,  # Red
        "unknown": 9807270,  # Yellow
    }

    color = colors.get(status["status"], 9807270)

    # Build embed
    embed = {
        "title": "🔄 Drewgent Update Check",
        "color": color,
        "fields": [
            {
                "name": "Status",
                "value": status["message"],
                "inline": True,
            },
            {
                "name": "Commits Behind",
                "value": str(status["behind"])
                if status["behind"] is not None
                else "N/A",
                "inline": True,
            },
        ],
        "footer": {
            "text": f"Checked at {status['timestamp']}",
        },
    }

    # Add update command hint if available
    if status["status"] == "update_available":
        embed["fields"].append(
            {
                "name": "How to Update",
                "value": "```cd ~/.drewgent/drewgent-agent && git pull origin main```",
                "inline": False,
            }
        )

    payload = json.dumps({"embeds": [embed]}).encode("utf-8")

    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200 or resp.status == 204
    except Exception as e:
        print(f"Discord notification failed: {e}", file=sys.stderr)
        return False


def write_status_file(status: dict) -> None:
    """Write status to a JSON file for Obsidian/polling."""
    try:
        UPDATE_STATUS_FILE.write_text(json.dumps(status, indent=2))
    except Exception as e:
        print(f"Failed to write status file: {e}", file=sys.stderr)


# ============================================================================
# Auto-Pull
# ============================================================================


def auto_pull_update() -> dict:
    """Attempt to pull latest Drewgent updates."""
    result = {
        "success": False,
        "output": "",
        "error": None,
    }

    drewgent_home = get_drewgent_home()
    repo_dir = drewgent_home / "drewgent-agent"

    if not (repo_dir / ".git").exists():
        repo_dir = Path(__file__).parent.parent.resolve()

    if not (repo_dir / ".git").exists():
        result["error"] = "Not a git repository"
        return result

    try:
        # Stash any local changes first
        subprocess.run(
            ["git", "stash"],
            capture_output=True,
            cwd=str(repo_dir),
        )

        # Pull latest
        proc = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            cwd=str(repo_dir),
        )

        result["output"] = proc.stdout + proc.stderr
        result["success"] = proc.returncode == 0

        if proc.returncode != 0:
            result["error"] = f"Git pull failed with code {proc.returncode}"

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Drewgent Auto-Update Checker")
    parser.add_argument(
        "--notify", action="store_true", help="Send Discord notification"
    )
    parser.add_argument(
        "--autopull", action="store_true", help="Auto-pull if updates available"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current status and exit"
    )
    args = parser.parse_args()

    # Get update status
    status = get_update_status()

    # Show status
    print(f"📦 Drewgent Update Status")
    print(f"   Status: {status['message']}")
    print(f"   Behind: {status['behind'] if status['behind'] is not None else 'N/A'}")
    print(f"   Checked: {status['timestamp']}")

    # Write to status file
    write_status_file(status)

    # Send Discord notification if requested
    if args.notify and status["status"] != "up_to_date":
        if send_discord_notification(status):
            print("✅ Discord notification sent")
        else:
            print("⚠️ Discord notification failed (no webhook configured?)")

    # Auto-pull if requested and updates available
    if args.autopull and status["status"] == "update_available":
        print("\n🔄 Auto-pulling updates...")
        pull_result = auto_pull_update()
        if pull_result["success"]:
            print("✅ Update pulled successfully!")
            print(pull_result["output"])
        else:
            print(f"❌ Auto-pull failed: {pull_result['error']}")

    # Exit with appropriate code
    if status["status"] == "up_to_date":
        sys.exit(0)
    elif status["status"] == "update_available":
        sys.exit(10)  # Special code for "updates available"
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
