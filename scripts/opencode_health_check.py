#!/usr/bin/env python3
"""
opencode_health_check.py — LLM-powered health check via opencode serve.
Replaces n8n Health Check workflow. Runs every 5min via launchd.
"""
import subprocess, json, os, sys

HOME = os.path.expanduser("~")
SERVE_URL = "http://localhost:8642"
LOG = os.path.join(HOME, ".drewgent", "logs", "health-check.log")

def run():
    prompt = (
        "Check Drewgent system health. Run: launchctl list | grep drewgent, "
        "and verify opencode serve at localhost:8642 responds. "
        "If all services running, reply 'HEALTHY'. "
        "If any service is down, reply 'UNHEALTHY: <details>'."
    )
    cmd = [
        "opencode", "run", prompt,
        "--attach", SERVE_URL,
        "--agent", "sre",
        "--dangerously-skip-permissions",
        "--dir", HOME + "/.drewgent",
        "--format", "json",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        last = ""
        for line in r.stdout.strip().split("\n"):
            try:
                d = json.loads(line)
                if d.get("type") == "text":
                    t = d.get("part", {}).get("text", "")
                    if t: last = t
            except json.JSONDecodeError:
                continue
        result = last or "[no response]"
        with open(LOG, "a") as f:
            f.write(f"{result}\n")
        if "UNHEALTHY" in result:
            print(result)
            sys.exit(1)
        print("HEALTHY")
    except Exception as e:
        with open(LOG, "a") as f:
            f.write(f"ERROR: {e}\n")
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
