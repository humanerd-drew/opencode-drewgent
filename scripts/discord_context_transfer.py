#!/usr/bin/env python3
"""
Discord Chat Context Transfer Script for Drewgent Agent

이 스크립트는 Discord导出 채팅 로그를 읽고 Drewgent Agent가 이해할 수 있는
마크다운 형식으로 변환합니다.

사용법:
    python3 discord_context_transfer.py --input discord_export.json --output context.md

Discord 로그 내보내기:
    1. Discord 채널에서 우클릭
    2. "메시지エクスポート" 선택 (BetterDiscord 등)
    또는
    1. DiscordSettings → 개인정보 보호 및 보안
    2. "모든 개인 데이터 다운로드 요청"
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_discord_export(data: dict) -> list[dict]:
    """Discord导出 데이터 파싱"""
    messages = []

    # 다양한导出 형식対応
    if isinstance(data, dict):
        if "messages" in data:
            # Discord 내보내기 형식
            messages = data["messages"]
        elif "channel" in data:
            # BetterDiscord等形式
            messages = data.get("channel", {}).get("messages", [])
        else:
            # 단일 메시지 리스트
            messages = data if isinstance(data, list) else []
    elif isinstance(data, list):
        messages = data

    return messages


def clean_discord_content(content: str) -> str:
    """Discord 콘텐츠 정리"""
    if not content:
        return ""

    # Discord 멘션 정리
    content = re.sub(r"<@!?(\d+)>", r"@\1", content)

    # Discord 채널 멘션 정리
    content = re.sub(r"<#(\d+)>", r"#\1", content)

    # Discord 역할 멘션 정리
    content = re.sub(r"<@&(\d+)>", r"@\1", content)

    # 이모지 정리 (커스텀 이모지)
    content = re.sub(r"<a?:(\w+):(\d+)>", r":\1:", content)

    # URL 정리
    content = re.sub(r"<(.+?)>", r"\1", content)

    # 다중 빈 줄 정리
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def format_timestamp(timestamp: str) -> str:
    """타임스탬프 포맷팅"""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return timestamp


def convert_to_markdown(messages: list[dict], channel_name: str = "discord") -> str:
    """마크다운 형식으로 변환"""
    lines = []
    lines.append(f"# Discord 채팅 맥락 — {channel_name}\n")
    lines.append(f"**내보내기 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("---\n")
    lines.append("")

    current_author = None
    current_date = None

    for msg in messages:
        # 필드 추출
        author = msg.get("author", {})
        author_name = author.get("name", author.get("username", "Unknown"))
        author_id = author.get("id", "")

        content = msg.get("content", "")
        timestamp = msg.get("timestamp", msg.get("created_at", ""))

        if not content:
            # 첨부 파일이나 임베드만 있는 경우
            attachments = msg.get("attachments", [])
            embeds = msg.get("embeds", [])
            if attachments or embeds:
                content = "[메시지 있음 - 첨부파일/임베드]"
            else:
                continue

        # 날짜 구분선
        msg_date = timestamp[:10] if timestamp else None
        if msg_date and msg_date != current_date:
            current_date = msg_date
            lines.append(f"\n## {current_date}\n")

        # 작성자 변경시 구분선
        if author_name != current_author:
            current_author = author_name
            lines.append(f"\n### @{author_name}\n")

        # 메시지 형식
        clean_content = clean_discord_content(content)
        time_str = format_timestamp(timestamp)

        lines.append(f"**{time_str}**: {clean_content}")
        lines.append("")

    return "\n".join(lines)


def create_drewgent_context_file(markdown_content: str, output_path: Path) -> None:
    """Drewgent 메모리 파일로 저장"""
    header = f"""---
title: Discord 채팅 맥락
created: {datetime.now().isoformat()}
source: discord_export
---

# Discord 채팅 맥락

이 문서는 Drewgent Agent를 시작할 때 맥락 전달을 위해 사용됩니다.
아래 내용을 새 대화 시작 시 복사하여 붙여넣으세요.

---

"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(markdown_content)

    print(f"✅ 맥락 파일 생성 완료: {output_path}")


def create_session_summary(messages: list[dict]) -> str:
    """대화 요약 생성 (긴 대화용)"""
    if len(messages) <= 20:
        return ""

    # 간단한 요약
    authors = set()
    total_messages = len(messages)
    first_timestamp = None
    last_timestamp = None

    for msg in messages:
        author = msg.get("author", {})
        authors.add(author.get("name", "Unknown"))

        ts = msg.get("timestamp", msg.get("created_at", ""))
        if ts:
            if not first_timestamp:
                first_timestamp = ts
            last_timestamp = ts

    summary = f"""
## 대화 요약

| 항목 | 값 |
|------|-----|
| 총 메시지 수 | {total_messages} |
| 참여자 | {", ".join(authors)} |
| 시작 | {format_timestamp(first_timestamp) if first_timestamp else "N/A"} |
| 마지막 메시지 | {format_timestamp(last_timestamp) if last_timestamp else "N/A"} |
"""
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Discord 채팅을 Drewgent Agent 맥락 형식으로 변환"
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Discord导出 JSON 파일 경로"
    )
    parser.add_argument(
        "--output", "-o", help="출력 마크다운 파일 경로 (기본: context.md)"
    )
    parser.add_argument("--channel", default="discord", help="채널 이름 (제목용)")
    parser.add_argument(
        "--max-messages",
        "-m",
        type=int,
        default=500,
        help="최대 처리 메시지 수 (기본: 500)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="실제 파일 쓰기 없이 결과 미리보기"
    )

    args = parser.parse_args()

    # 입력 파일 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # 출력 파일 경로
    output_path = Path(args.output) if args.output else Path("context.md")

    print(f"📖 Discord 로그 읽기: {input_path}")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        sys.exit(1)

    messages = parse_discord_export(data)
    print(f"📊 총 {len(messages)}개 메시지 발견")

    # 메시지 수 제한
    if len(messages) > args.max_messages:
        print(f"⚠️ 메시지가 너무 많습니다. 최근 {args.max_messages}개만 처리합니다.")
        messages = messages[-args.max_messages :]

    # 마크다운 변환
    markdown = convert_to_markdown(messages, args.channel)

    # 요약 추가 (긴 대화용)
    summary = create_session_summary(messages)
    if summary:
        # 요약을 상단에 추가
        markdown = summary + "\n---\n\n" + markdown

    if args.dry_run:
        print("\n📝 미리보기 (첫 2000자):")
        print(markdown[:2000])
        print("\n... [생략] ...\n")
        return

    # 파일 저장
    create_drewgent_context_file(markdown, output_path)

    print(f"""
📋 사용 방법:

1. Drewgent Agent 시작
2. /new 로 새 대화 시작
3. 아래 명령어 중 하나 사용:

   방법 A: 파일 내용 복사
   - {output_path} 파일 내용을 복사
   - Drewgent에 붙여넣기

   방법 B: 컨텍스트 파일 지정
   - ~/.drewgent/context/ 디렉토리에 저장
   - Drewgent가 자동 로드
""")


if __name__ == "__main__":
    main()
