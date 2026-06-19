#!/usr/bin/env python3
"""Send message to Discord webhook, auto-splitting into chunks if needed."""
import json, sys, subprocess, os

def send(url, message, max_len=1900):
    if not message: return
    message = str(message).strip()
    if not message: return
    chunks = [message[i:i+max_len] for i in range(0, len(message), max_len)]
    for i, chunk in enumerate(chunks):
        payload = json.dumps({'content': chunk})
        subprocess.run(['curl', '-s', '-X', 'POST', url, '-H', 'Content-Type: application/json', '-d', payload], timeout=5, capture_output=True)

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISCORD_WEBHOOK', '')
    msg = sys.stdin.read()
    send(url, msg)
