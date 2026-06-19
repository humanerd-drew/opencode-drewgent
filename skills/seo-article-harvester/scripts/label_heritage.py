#!/usr/bin/env python3
"""
SEO Article Heritage Labeler
============================
기존 article에 heritage 태그 추가 + 연도 폴더 분류

Usage:
    python3 label_heritage.py              # 전체 실행
    python3 label_heritage.py --dry-run   # 확인만
    python3 label_heritage.py --limit 100 # 일부만
"""

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

DREW_HOME = Path(os.environ.get("DREW_HOME", os.path.expanduser("~/.drewgent")))
sys.path.insert(0, str(DREW_HOME))

from agent.obsidian_graph import ensure_backlink, ensure_related_section, wiki_link

SEO_DIR = DREW_HOME / "P2-hippocampus" / "knowledge" / "seo-articles"
ARCHIVE_DIR = SEO_DIR / "_archive" / "heritage-labeled"

def ensure_seo_index() -> Path:
    index_file = SEO_DIR / "index-by-topic.md"
    if not index_file.exists():
        SEO_DIR.mkdir(parents=True, exist_ok=True)
        index_file.write_text(
            "\n".join(
                [
                    "---",
                    "title: SEO Articles Index By Topic",
                    "tags: [seo, articles, P2, hippocampus]",
                    "links:",
                    f'  - "{wiki_link("P2-hippocampus/memories/index")}"',
                    f'  - "{wiki_link("skills/seo-article-harvester/SKILL")}"',
                    "---",
                    "",
                    "# SEO Articles Index By Topic",
                    "",
                    "Cron-collected SEO and AI search articles.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return index_file

def connect_article(filepath: Path) -> None:
    index_file = ensure_seo_index()
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    updated = ensure_related_section(
        content,
        [
            wiki_link("P2-hippocampus/knowledge/seo-articles/index-by-topic"),
            wiki_link("skills/seo-article-harvester/SKILL"),
        ],
    )
    if updated != content:
        filepath.write_text(updated, encoding="utf-8")
    index_content = index_file.read_text(encoding="utf-8", errors="ignore")
    index_updated = ensure_related_section(index_content, [wiki_link(filepath, DREW_HOME)])
    if index_updated != index_content:
        index_file.write_text(index_updated, encoding="utf-8")

def extract_year_from_filename(filename: str) -> str:
    """파일명에서 연도 추출"""
    # 2025, 2024, 2023, 2026等形式 (정규화) — _2025_에서도 잡히도록
    m = re.search(r"(20[12][0-9]|2030)", filename)
    if m:
        return m.group(1)
    return ""

def extract_year_from_content(content: str) -> Optional[str]:
    """본문에서 연도 추출 (published, date, 2025等形式)"""
    patterns = [
        r"(?:published|date|created)[:\s]*(\d{4}-\d{2}-\d{2})",
        r"(202[3-9]|2030)",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return m.group(1)[:4]
    return None

def get_year_from_frontmatter(content: str) -> Optional[str]:
    """frontmatter에서 수집 연도 추출"""
    patterns = [
        r"(?:collected_date|collected|year)[:\s]*(\d{4})",
        r"created[:\s]*(\d{4})-",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return m.group(1)
    return None

def add_heritage_tags(content: str, year: str) -> str:
    """frontmatter에 heritage 태그 추가 (기존 heritage/heritage_year line 제거 후 삽입)"""
    if re.search(r"^heritage:\s*true\s*$", content, re.MULTILINE):
        # 이미 heritage: true면 스킵
        return content, False
    
    # 기존 heritage: / heritage_year: line 제거 (중복 frontmatter 방지)
    content = re.sub(r"^heritage(?:_year)?:\s*\S+\s*\n?", "", content, flags=re.MULTILINE)
    
    lines = content.split("\n")
    new_lines = []
    inserted = False
    
    for line in lines:
        new_lines.append(line)
        if not inserted and line.startswith("---") and len(line) == 3:
            # 2번째 --- 뒤에 heritage 태그 추가
            new_lines.append(f"heritage: true")
            new_lines.append(f"heritage_year: {year}")
            inserted = True
    
    return "\n".join(new_lines), inserted

def move_to_year_folder(filepath: Path, year: str) -> Path:
    """파일을 연도 폴더로 이동"""
    year_dir = SEO_DIR / year
    year_dir.mkdir(parents=True, exist_ok=True)
    
    dest = year_dir / filepath.name
    
    if dest.exists() and dest.stat().st_size >= filepath.stat().st_size:
        # 이미 같은 파일이 있으면 archive로
        archive_name = f"{filepath.stem}_heritage-{datetime.now().strftime('%Y%m%d%H%M')}{filepath.suffix}"
        dest = ARCHIVE_DIR / archive_name
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(filepath), str(dest))
    return dest

def process_file(filepath: Path, dry_run: bool = False) -> tuple[bool, str, str]:
    """单个 파일 처리 — (수정됨, 새 경로, 연도)"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, "", ""
    
    # frontmatter에서 이미 heritage인지 확인
    if re.search(r"^heritage:\s*true\s*$", content, re.MULTILINE):
        return False, "", ""
    
    # 연도 결정 (priority: filename > frontmatter > content)
    year = extract_year_from_filename(filepath.name)
    if not year:
        year = get_year_from_frontmatter(content)
    if not year:
        year = extract_year_from_content(content)
    if not year:
        year = "unknown"
    
    # heritage 태그 추가
    new_content, inserted = add_heritage_tags(content, year)
    
    if dry_run:
        return inserted, str(filepath), year
    
    if inserted:
        filepath.write_text(new_content, encoding="utf-8")
    
    # 연도 폴더로 이동
    if inserted:
        dest = move_to_year_folder(filepath, year)
        connect_article(dest)
        return True, str(dest), year
    
    return False, "", ""

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    
    print(f"📦 SEO Heritage Labeler — {datetime.now().isoformat()}")
    print(f"   SEO dir: {SEO_DIR}")
    print()
    
    # 대상 파일 목록 (root만, _new/_archive 제외)
    files = []
    for f in SEO_DIR.iterdir():
        if f.is_file() and f.suffix == ".md" and not f.name.startswith("_"):
            files.append(f)
    
    # _new 폴더도 포함
    new_dir = SEO_DIR / "_new"
    if new_dir.exists():
        for f in new_dir.glob("*.md"):
            files.append(f)
    
    print(f"   총 파일: {len(files)}개")
    
    if args.limit > 0:
        files = files[:args.limit]
        print(f"   제한: {args.limit}개")
    
    print()
    
    modified = 0
    skipped = 0
    years: dict = {}
    
    for i, filepath in enumerate(files, 1):
        changed, new_path, year = process_file(filepath, dry_run=args.dry_run)
        
        if changed:
            modified += 1
            years[year] = years.get(year, 0) + 1
            if modified <= 10:
                print(f"[{i}] ✅ {filepath.name} → {year}/")
        elif new_path:
            skipped += 1
        else:
            skipped += 1
        
        if i % 200 == 0:
            print(f"   진행중... {i}/{len(files)}")
    
    print()
    print(f"📊 결과:")
    print(f"   수정됨: {modified}개")
    print(f"   스킵 (이미 heritage or 오류): {skipped}개")
    
    if years:
        print(f"   연도별:")
        for y, c in sorted(years.items()):
            print(f"     {y}: {c}개")
    
    if args.dry_run:
        print()
        print("🟡 DRY-RUN — 실제 변경 없음")

if __name__ == "__main__":
    main()
