from __future__ import annotations
import json, os, re, subprocess
from typing import Optional
from core.models import Post

WP = ["docker", "exec", "humanerd-wp", "wp", "--allow-root", "--format=json"]
CACHE = os.path.expanduser("~/.drewgent/P4-cortex/content/wp-cache.json")


def _wp(*args, timeout=15):
    r = subprocess.run([*WP, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"WP-CLI error: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def get_categories() -> dict[int, str]:
    raw = _wp("term", "list", "category")
    cats = {}
    for t in json.loads(raw):
        cats[int(t["term_id"])] = t["name"]
    return cats


def get_tags() -> dict[int, str]:
    raw = _wp("term", "list", "post_tag")
    tags = {}
    for t in json.loads(raw):
        tags[int(t["term_id"])] = t["name"]
    return tags


def get_posts(status="publish", limit=100) -> list[Post]:
    raw = _wp("post", "list", f"--posts_per_page={limit}", f"--post_status={status}")
    posts = []
    for p in json.loads(raw):
        pid = str(p["ID"])
        try:
            cats_raw = _wp("post", "term", "list", pid, "category")
            cats = json.loads(cats_raw) if cats_raw else []
        except RuntimeError:
            cats = []
        try:
            tags_raw = _wp("post", "term", "list", pid, "post_tag")
            tags = json.loads(tags_raw) if tags_raw else []
        except RuntimeError:
            tags = []
        content = _wp("post", "get", pid, "--field=post_content")
        excerpt = _wp("post", "get", pid, "--field=post_excerpt")
        posts.append(Post(
            id=int(p["ID"]),
            title=p.get("post_title", ""),
            content=content or "",
            excerpt=excerpt or "",
            slug=p.get("post_name", ""),
            status=p.get("post_status", "publish"),
            categories=[int(c["term_id"]) for c in cats],
            tags=[int(t["term_id"]) for t in tags],
            permalink=p.get("guid", ""),
        ))
    return posts


def update_post(post_id: int, content: str) -> bool:
    container = "humanerd-wp"
    tmp_host = "/tmp/cge-content.html"
    tmp_ctn = "/tmp/cge-content.html"
    with open(tmp_host, "w") as f:
        f.write(content)
    try:
        subprocess.run(["docker", "cp", tmp_host, f"{container}:{tmp_ctn}"],
                       capture_output=True, timeout=30, check=True)
        result = subprocess.run(
            ["docker", "exec", "-i", container, "wp", "--allow-root",
             "post", "update", str(post_id), "--post_content=-"],
            input=content.encode(), capture_output=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Update failed: {result.stderr.decode()[:200]}")
        subprocess.run(["docker", "exec", container, "rm", tmp_ctn],
                       capture_output=True, timeout=15)
        return True
    finally:
        try: os.unlink(tmp_host)
        except FileNotFoundError: pass


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
