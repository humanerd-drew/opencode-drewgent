#!/usr/bin/env python3
"""Send message to Discord webhook, auto-splitting into chunks if needed.

Supports either a legacy positional webhook URL or --channel/--title/--body
flags. When --channel is given, the webhook URL is read from an environment
variable named DISCORD_WEBHOOK_<CHANNEL_ID>, falling back to DISCORD_WEBHOOK.
"""
import argparse
import json
import os
import subprocess
import sys


def send(url, message, max_len=1900):
    if not url or not message:
        return
    message = str(message).strip()
    if not message:
        return
    chunks = [message[i:i+max_len] for i in range(0, len(message), max_len)]
    for chunk in chunks:
        payload = json.dumps({'content': chunk})
        subprocess.run(
            ['curl', '-s', '-X', 'POST', url, '-H', 'Content-Type: application/json', '-d', payload],
            timeout=5,
            capture_output=True,
        )


def _webhook_url_for_channel(channel):
    """Resolve a webhook URL for a channel ID, best-effort."""
    if channel:
        url = os.environ.get(f'DISCORD_WEBHOOK_{channel}')
        if url:
            return url
    return os.environ.get('DISCORD_WEBHOOK', '')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send a message to a Discord webhook')
    parser.add_argument('url', nargs='?', help='Webhook URL (legacy positional argument)')
    parser.add_argument('--channel', help='Discord channel ID')
    parser.add_argument('--title', help='Message title/header')
    parser.add_argument('--body', help='Message body (if omitted, read from stdin)')
    args = parser.parse_args()

    url = args.url or _webhook_url_for_channel(args.channel)
    if not url:
        sys.exit(0)

    body = args.body if args.body is not None else sys.stdin.read()
    if args.title and body:
        message = f'{args.title}\n\n{body}'
    else:
        message = args.title or body
    send(url, message)
