#!/usr/bin/env python3
"""Drewgent Agent Release Script

Generates changelogs and creates GitHub releases with CalVer tags.

Usage:
    # Preview changelog (dry run)
    python scripts/release.py

    # Preview with semver bump
    python scripts/release.py --bump minor

    # Create the release
    python scripts/release.py --bump minor --publish

    # First release (no previous tag)
    python scripts/release.py --bump minor --publish --first-release

    # Override CalVer date (e.g. for a belated release)
    python scripts/release.py --bump minor --publish --date 2026.3.15
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "drewgent_cli" / "__init__.py"
PYPROJECT_FILE = REPO_ROOT / "pyproject.toml"

# ──────────────────────────────────────────────────────────────────────
# Git email → GitHub username mapping
# ──────────────────────────────────────────────────────────────────────

# Auto-extracted from noreply emails + manual overrides
AUTHOR_MAP = {
    # teknium (multiple emails)
    "teknium1@gmail.com": "teknium1",
    "teknium@nousresearch.com": "teknium1",
    "127238744+teknium1@users.noreply.github.com": "teknium1",
    "128259593+Gutslabs@users.noreply.github.com": "Gutslabs",
    "50326054+nocturnum91@users.noreply.github.com": "nocturnum91",
    "223003280+Abd0r@users.noreply.github.com": "Abd0r",
    "abdielv@proton.me": "AJV20",
    "mason@growagainorchids.com": "masonjames",
    "ytchen0719@gmail.com": "liquidchen",
    "am@studio1.tailb672fe.ts.net": "subtract0",
    "axmaiqiu@gmail.com": "qWaitCrypto",
    "159539633+MottledShadow@users.noreply.github.com": "MottledShadow",
    "aludwin+gh@gmail.com": "adamludwin",
    "ngusev@astralinux.ru": "NikolayGusev-astra",
    "liuguangyong201@hellobike.com": "liuguangyong93",
    "2093036+exiao@users.noreply.github.com": "exiao",
    "thunderggnn@gmail.com": "ggnnggez",
    "haozhe4547@gmail.com": "ehz0ah",
    "kevyan1998@gmail.com": "kyan12",
    "rylen.anil@gmail.com": "rylena",
    "godnanijatin@gmail.com": "jatingodnani",
    "252811164+adybag14-cyber@users.noreply.github.com": "adybag14-cyber",
    "14046872+tmimmanuel@users.noreply.github.com": "tmimmanuel",
    "112875006+donramon77@users.noreply.github.com": "donramon77",
    "657290301@qq.com": "IMHaoyan",
    "revar@users.noreply.github.com": "revaraver",
    "dengtaoyuan@dengtaoyuandeMac-mini.local": "dengtaoyuan450-a11y",
    "ysfalweshcan@gmail.com": "Junass1",
    "bartokmagic@proton.me": "Bartok9",
    "25840394+Bongulielmi@users.noreply.github.com": "Bongulielmi",
    "jonathan.troyer@overmatch.com": "JTroyerOvermatch",
    "harryykyle1@gmail.com": "hharry11",
    "wysie@users.noreply.github.com": "wysie",
    "jkausel@gmail.com": "jkausel-ai",
    "e.silacandmr@gmail.com": "Es1la",
    "51599529+stephen0110@users.noreply.github.com": "stephen0110",
    "265632032+sonic-netizen@users.noreply.github.com": "sonic-netizen",
    "82531659+mwnickerson@users.noreply.github.com": "mwnickerson",
    "sandrohub013@gmail.com": "SandroHub013",
    "maciekczech@users.noreply.github.com": "maciekczech",
    "154585401+LeonSGP43@users.noreply.github.com": "LeonSGP43",
    "zjtan1@gmail.com": "zeejaytan",
    "asslaenn5@gmail.com": "Aslaaen",
    "trae.anderson17@icloud.com": "Tkander1715",
    "beardthelion@users.noreply.github.com": "beardthelion",
    "tangyuanjc@JCdeAIfenshendeMac-mini.local": "tangyuanjc",
    "leon@agentlinker.ai": "agentlinker",
    "santoshhumagain1887@gmail.com": "npmisantosh",
    "novax635@gmail.com": "novax635",
    "krionex1@gmail.com": "Krionex",
    "rxdxxxx@users.noreply.github.com": "rxdxxxx",
    "ma.haohao2@xydigit.com": "MaHaoHao-ch",
    "29756950+revaraver@users.noreply.github.com": "revaraver",
    "nexus@eptic.me": "TheEpTic",
    "74554762+wmagev@users.noreply.github.com": "wmagev",
    "ashermorse@icloud.com": "ashermorse",
    "happy5318@users.noreply.github.com": "happy5318",
    "anatoliygranichenko@gmail.com": "wabrent",
    "cash.williams@acquia.com": "CashWilliams",
    "chengoak@users.noreply.github.com": "chengoak",
    "mrhanoi@outlook.com": "qxxaa",
    "guillaume.meyer@outlook.com": "guillaumemeyer",
    "emelyanenko.kirill@gmail.com": "EmelyanenkoK",
    "lazycat.manatee@gmail.com": "manateelazycat",
    "bzarnitz13@gmail.com": "Beandon13",
    "tony@tonysimons.dev": "asimons81",
    "jetha@google.com": "jethac",
    "jani@0xhoneyjar.xyz": "deep-name",
    "xiangyong@zspace.cn": "CES4751",
    "harish.kukreja@gmail.com": "counterposition",
    "35294173+Fearvox@users.noreply.github.com": "Fearvox",
    "hypnus.yuan@gmail.com": "Hypnus-Yuan",
    "15558128926@qq.com": "xsfX20",
    "binhnt.ht.92@gmail.com": "binhnt92",
    "johnny@Jons-MBA-M4.local": "acesjohnny",
    "1581133593@qq.com": "liu-collab",
    "haidaoe@proton.me": "haidao1919",
    "50561768+zhanggttry@users.noreply.github.com": "zhanggttry",
    "formulahendry@gmail.com": "formulahendry",
    "93757150+bogerman1@users.noreply.github.com": "bogerman1",
    "132852777+rob-maron@users.noreply.github.com": "rob-maron",
    # Matrix parity salvage batch (April 2026)
    "sr@samirusani": "samrusani",
    "angelclaw@AngelMacBook.local": "angel12",
    "charles@cryptoassetrecovery.com": "charles-brooks",
    # DeepSeek v4 + Kimi thinking-mode reasoning_content salvage (April 2026)
    "luwinyang@deepseek.com": "lsdsjy",
    "season.saw@gmail.com": "season179",
    "heathley@Heathley-MacBook-Air.local": "heathley",
    "vlad19@gmail.com": "dandaka",
    "adamrummer@gmail.com": "cyclingwithelephants",
    # Temporary tool-progress cleanup salvage (May 2026)
    "Mrcharlesiv@gmail.com": "mrcharlesiv",
    "nbot@liizfq.top": "liizfq",
    "274096618+hermes-agent-dhabibi@users.noreply.github.com": "dhabibi",
    "dejie.guo@gmail.com": "JayGwod",
    "133716830+0xKingBack@users.noreply.github.com": "0xKingBack",
    "daixin1204@gmail.com": "SimbaKingjoe",
    "maxence@groine.fr": "MaxyMoos",
    "61830395+leprincep35700@users.noreply.github.com": "leprincep35700",
    # OpenViking viking_read salvage (April 2026)
    "hitesh@gmail.com": "htsh",
    "pty819@outlook.com": "pty819",
    "pty819@users.noreply.github.com": "pty819",
    "517024110@qq.com": "chennest",
    # Curator fixes (Apr 30 2026)
    "yuxiangl490@gmail.com": "y0shua1ee",
    "manmit0x@gmail.com": "0xDevNinja",
    "stevekelly622@gmail.com": "steezkelly",
    "momowind@gmail.com": "momowind",
    "clockwork-codex@users.noreply.github.com": "misery-hl",
    "207811921+misery-hl@users.noreply.github.com": "misery-hl",
    "suncokret@protonmail.com": "suncokret12",
    "mio.imoto.ai@gmail.com": "mioimotoai-lgtm",
    "aamirjawaid@microsoft.com": "heyitsaamir",
    "johnnncenaaa77@gmail.com": "johnncenae",
    "thomasjhon6666@gmail.com": "ThomassJonax",
    "focusflow.app.help@gmail.com": "yes999zc",
    "rob@atlas.lan": "rmoen",
    # Slack ephemeral slash-ack salvage (May 2026)
    "probepark@users.noreply.github.com": "probepark",
    # Slack batch salvage (May 2026)
    "280484231+prive-fe-bot@users.noreply.github.com": "priveperfumes",
    "amr@ghanem.sa": "amroessam",
    "paperlantern.agent@gmail.com": "Hinotoi-agent",
    "valda@underscore.jp": "valda",
    "162235745+0z1-ghb@users.noreply.github.com": "0z1-ghb",
    "yes999zc@163.com": "yes999zc",
    "343873859@qq.com": "DrStrangerUJN",
    "252818347@qq.com": "hejuntt1014",
    "uzmpsk.dilekakbas@gmail.com": "dlkakbs",
    "beliefanx@gmail.com": "BeliefanX",
    "changchun989@proton.me": "changchun989",
    "jefferson@heimdallstrategy.com": "Mind-Dragon",
    "44753291+Nanako0129@users.noreply.github.com": "Nanako0129",
    "steve.westerhouse@origami-analytics.com": "westers",
    "yeyitech@users.noreply.github.com": "yeyitech",
    "260878550+beenherebefore@users.noreply.github.com": "beenherebefore",
    "79389617+txbxxx@users.noreply.github.com": "txbxxx",
    "liuhao03@bilibili.com": "liuhao1024",
    "130918800+devorun@users.noreply.github.com": "devorun",
    "surat.s@itm.kmutnb.ac.th": "beesrsj2500",
    "beesr@bee.localdomain": "beesrsj2500",
    "mind-dragon@nous.research": "Mind-Dragon",
    "juntingpublic@gmail.com": "JustinUssuri",
    "mtf201013@gmail.com": "ma-pony",
    "sonoyuncudmr@gmail.com": "Sonoyunchu",
    "43525405+yatesjalex@users.noreply.github.com": "yatesjalex",
    "maks.mir@yahoo.com": "say8hi",
    "27719690+Mirac1eSky@users.noreply.github.com": "Mirac1eSky",
    "web3blind@users.noreply.github.com": "web3blind",
    "julia@alexland.us": "alexg0bot",
    "christian@scheid.tech": "scheidti",
    # Moonshot schema anyOf+enum salvage (May 2026)
    "git@local.invalid": "hendrixfreire",
    "1060770+benjaminsehl@users.noreply.github.com": "benjaminsehl",
    "nerijusn76@gmail.com": "Nerijusas",
    # Compaction salvage batch (May 2026)
    "MacroAnarchy@users.noreply.github.com": "MacroAnarchy",
    "itonov@proton.me": "Ito-69",
    "glesstech@gmail.com": "georgeglessner",
    "maxim.smetanin@gmail.com": "maxims-oss",
    "nazirulhafiy@gmail.com": "nazirulhafiy",
    "CREWorx@users.noreply.github.com": "BadTechBandit",
    "yoimexex@gmail.com": "Yoimex",
    "6548898+romanornr@users.noreply.github.com": "romanornr",
    "foxion37@gmail.com": "foxion37",
    "bloodcarter@gmail.com": "bloodcarter",
    "scott@scotttrinh.com": "scotttrinh",
    "quocanh261997@gmail.com": "quocanh261997",
    # contributors (from noreply pattern)
    "35742124+0xbyt4@users.noreply.github.com": "0xbyt4",
    "82637225+kshitijk4poor@users.noreply.github.com": "kshitijk4poor",
    "16443023+stablegenius49@users.noreply.github.com": "stablegenius49",
    "185121704+stablegenius49@users.noreply.github.com": "stablegenius49",
    "101283333+batuhankocyigit@users.noreply.github.com": "batuhankocyigit",
    "126368201+vilkasdev@users.noreply.github.com": "vilkasdev",
    "137614867+cutepawss@users.noreply.github.com": "cutepawss",
    "96793918+memosr@users.noreply.github.com": "memosr",
    "131039422+SHL0MS@users.noreply.github.com": "SHL0MS",
    "77628552+raulvidis@users.noreply.github.com": "raulvidis",
    "145567217+Aum08Desai@users.noreply.github.com": "Aum08Desai",
    "256820943+kshitij-eliza@users.noreply.github.com": "kshitij-eliza",
    "44278268+shitcoinsherpa@users.noreply.github.com": "shitcoinsherpa",
    "104278804+Sertug17@users.noreply.github.com": "Sertug17",
    "112503481+caentzminger@users.noreply.github.com": "caentzminger",
    "258577966+voidborne-d@users.noreply.github.com": "voidborne-d",
    "70424851+insecurejezza@users.noreply.github.com": "insecurejezza",
    "259807879+Bartok9@users.noreply.github.com": "Bartok9",
    # contributors (manual mapping from git names)
    "dmayhem93@gmail.com": "dmahan93",
    "samherring99@gmail.com": "samherring99",
    "desaiaum08@gmail.com": "Aum08Desai",
    "shannon.sands.1979@gmail.com": "shannonsands",
    "shannon@nousresearch.com": "shannonsands",
    "eri@plasticlabs.ai": "Erosika",
    "hjcpuro@gmail.com": "hjc-puro",
    "xaydinoktay@gmail.com": "aydnOktay",
    "abdullahfarukozden@gmail.com": "Farukest",
    "lovre.pesut@gmail.com": "rovle",
    "hakanerten02@hotmail.com": "teyrebaz33",
    "alireza78.crypto@gmail.com": "alireza78a",
    "brooklyn.bb.nicholson@gmail.com": "brooklynnicholson",
    "gpickett00@gmail.com": "gpickett00",
    "mcosma@gmail.com": "wakamex",
    "clawdia.nash@proton.me": "clawdia-nash",
    "pickett.austin@gmail.com": "austinpickett",
    "jaisehgal11299@gmail.com": "jaisup",
    "percydikec@gmail.com": "PercyDikec",
    "dean.kerr@gmail.com": "deankerr",
    "socrates1024@gmail.com": "socrates1024",
    "satelerd@gmail.com": "satelerd",
    "numman.ali@gmail.com": "nummanali",
    "0xNyk@users.noreply.github.com": "0xNyk",
    "0xnykcd@googlemail.com": "0xNyk",
    "buraysandro9@gmail.com": "buray",
    "contact@jomar.fr": "joshmartinelle",
    "camilo@tekelala.com": "tekelala",
    "vincentcharlebois@gmail.com": "vincentcharlebois",
    "aryan@synvoid.com": "aryansingh",
    "johnsonblake1@gmail.com": "blakejohnson",
    "bryan@intertwinesys.com": "bryanyoung",
    "christo.mitov@gmail.com": "christomitov",
    "hermes@nousresearch.com": "NousResearch",
    "openclaw@sparklab.ai": "openclaw",
    "semihcvlk53@gmail.com": "Himess",
    "erenkar950@gmail.com": "erenkarakus",
    "adavyasharma@gmail.com": "adavyas",
    "acaayush1111@gmail.com": "aayushchaudhary",
    "jason@outland.art": "jasonoutland",
    "mrflu1918@proton.me": "SPANISHFLU",
    "morganemoss@gmai.com": "mormio",
    "kopjop926@gmail.com": "cesareth",
    "fuleinist@gmail.com": "fuleinist",
    "jack.47@gmail.com": "JackTheGit",
    "dalvidjr2022@gmail.com": "Jr-kenny",
    "m@statecraft.systems": "mbierling",
    "balyan.sid@gmail.com": "balyansid",
}


def git(*args, cwd=None):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True,
        cwd=cwd or str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"git {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout.strip()


def git_result(*args, cwd=None):
    """Run a git command and return the full CompletedProcess."""
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd or str(REPO_ROOT),
    )


def get_last_tag():
    """Get the most recent CalVer tag."""
    tags = git("tag", "--list", "v20*", "--sort=-v:refname")
    if tags:
        return tags.split("\n")[0]
    return None


def next_available_tag(base_tag: str) -> tuple[str, str]:
    """Return a tag/calver pair, suffixing same-day releases when needed."""
    if not git("tag", "--list", base_tag):
        return base_tag, base_tag.removeprefix("v")

    suffix = 2
    while git("tag", "--list", f"{base_tag}.{suffix}"):
        suffix += 1
    tag_name = f"{base_tag}.{suffix}"
    return tag_name, tag_name.removeprefix("v")


def get_current_version():
    """Read current semver from __init__.py."""
    content = VERSION_FILE.read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "0.0.0"


def bump_version(current: str, part: str) -> str:
    """Bump a semver version string."""
    parts = current.split(".")
    if len(parts) != 3:
        parts = ["0", "0", "0"]
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump part: {part}")

    return f"{major}.{minor}.{patch}"


def update_version_files(semver: str, calver_date: str):
    """Update version strings in source files."""
    # Update __init__.py
    content = VERSION_FILE.read_text()
    content = re.sub(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{semver}"',
        content,
    )
    content = re.sub(
        r'__release_date__\s*=\s*"[^"]+"',
        f'__release_date__ = "{calver_date}"',
        content,
    )
    VERSION_FILE.write_text(content)

    # Update pyproject.toml
    pyproject = PYPROJECT_FILE.read_text()
    pyproject = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{semver}"',
        pyproject,
        flags=re.MULTILINE,
    )
    PYPROJECT_FILE.write_text(pyproject)


def build_release_artifacts(semver: str) -> list[Path]:
    """Build sdist/wheel artifacts for the current release.

    Returns the artifact paths when the local environment has ``python -m build``
    available. If build tooling is missing or the build fails, returns an empty
    list and lets the release proceed without attached Python artifacts.
    """
    dist_dir = REPO_ROOT / "dist"
    shutil.rmtree(dist_dir, ignore_errors=True)

    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  ⚠ Could not build Python release artifacts.")
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        if stderr:
            print(f"    {stderr.splitlines()[-1]}")
        elif stdout:
            print(f"    {stdout.splitlines()[-1]}")
        print("    Install the 'build' package to attach semver-named sdist/wheel assets.")
        return []

    artifacts = sorted(p for p in dist_dir.iterdir() if p.is_file())
    matching = [p for p in artifacts if semver in p.name]
    if not matching:
        print("  ⚠ Built artifacts did not match the expected release version.")
        return []
    return matching


def resolve_author(name: str, email: str) -> str:
    """Resolve a git author to a GitHub @mention."""
    # Try email lookup first
    gh_user = AUTHOR_MAP.get(email)
    if gh_user:
        return f"@{gh_user}"

    # Try noreply pattern
    noreply_match = re.match(r"(\d+)\+(.+)@users\.noreply\.github\.com", email)
    if noreply_match:
        return f"@{noreply_match.group(2)}"

    # Try username@users.noreply.github.com
    noreply_match2 = re.match(r"(.+)@users\.noreply\.github\.com", email)
    if noreply_match2:
        return f"@{noreply_match2.group(1)}"

    # Fallback to git name
    return name


def categorize_commit(subject: str) -> str:
    """Categorize a commit by its conventional commit prefix."""
    subject_lower = subject.lower()

    # Match conventional commit patterns
    patterns = {
        "breaking": [r"^breaking[\s:(]", r"^!:", r"BREAKING CHANGE"],
        "features": [r"^feat[\s:(]", r"^feature[\s:(]", r"^add[\s:(]"],
        "fixes": [r"^fix[\s:(]", r"^bugfix[\s:(]", r"^bug[\s:(]", r"^hotfix[\s:(]"],
        "improvements": [r"^improve[\s:(]", r"^perf[\s:(]", r"^enhance[\s:(]",
                         r"^refactor[\s:(]", r"^cleanup[\s:(]", r"^clean[\s:(]",
                         r"^update[\s:(]", r"^optimize[\s:(]"],
        "docs": [r"^doc[\s:(]", r"^docs[\s:(]"],
        "tests": [r"^test[\s:(]", r"^tests[\s:(]"],
        "chore": [r"^chore[\s:(]", r"^ci[\s:(]", r"^build[\s:(]",
                  r"^deps[\s:(]", r"^bump[\s:(]"],
    }

    for category, regexes in patterns.items():
        for regex in regexes:
            if re.match(regex, subject_lower):
                return category

    # Heuristic fallbacks
    if any(w in subject_lower for w in ["add ", "new ", "implement", "support "]):
        return "features"
    if any(w in subject_lower for w in ["fix ", "fixed ", "resolve", "patch "]):
        return "fixes"
    if any(w in subject_lower for w in ["refactor", "cleanup", "improve", "update "]):
        return "improvements"

    return "other"


def clean_subject(subject: str) -> str:
    """Clean up a commit subject for display."""
    # Remove conventional commit prefix
    cleaned = re.sub(r"^(feat|fix|docs|chore|refactor|test|perf|ci|build|improve|add|update|cleanup|hotfix|breaking|enhance|optimize|bugfix|bug|feature|tests|deps|bump)[\s:(!]+\s*", "", subject, flags=re.IGNORECASE)
    # Remove trailing issue refs that are redundant with PR links
    cleaned = cleaned.strip()
    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def get_commits(since_tag=None):
    """Get commits since a tag (or all commits if None)."""
    if since_tag:
        range_spec = f"{since_tag}..HEAD"
    else:
        range_spec = "HEAD"

    # Format: hash|author_name|author_email|subject
    log = git(
        "log", range_spec,
        "--format=%H|%an|%ae|%s",
        "--no-merges",
    )

    if not log:
        return []

    commits = []
    for line in log.split("\n"):
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        sha, name, email, subject = parts
        commits.append({
            "sha": sha,
            "short_sha": sha[:8],
            "author_name": name,
            "author_email": email,
            "subject": subject,
            "category": categorize_commit(subject),
            "github_author": resolve_author(name, email),
        })

    return commits


def get_pr_number(subject: str) -> str:
    """Extract PR number from commit subject if present."""
    match = re.search(r"#(\d+)", subject)
    if match:
        return match.group(1)
    return None


def generate_changelog(commits, tag_name, semver, repo_url="https://github.com/NousResearch/drewgent-agent",
                       prev_tag=None, first_release=False):
    """Generate markdown changelog from categorized commits."""
    lines = []

    # Header
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    lines.append(f"# Drewgent Agent v{semver} ({tag_name})")
    lines.append("")
    lines.append(f"**Release Date:** {date_str}")
    lines.append("")

    if first_release:
        lines.append("> 🎉 **First official release!** This marks the beginning of regular weekly releases")
        lines.append("> for Drewgent Agent. See below for everything included in this initial release.")
        lines.append("")

    # Group commits by category
    categories = defaultdict(list)
    all_authors = set()
    teknium_aliases = {"@teknium1"}

    for commit in commits:
        categories[commit["category"]].append(commit)
        author = commit["github_author"]
        if author not in teknium_aliases:
            all_authors.add(author)

    # Category display order and emoji
    category_order = [
        ("breaking", "⚠️ Breaking Changes"),
        ("features", "✨ Features"),
        ("improvements", "🔧 Improvements"),
        ("fixes", "🐛 Bug Fixes"),
        ("docs", "📚 Documentation"),
        ("tests", "🧪 Tests"),
        ("chore", "🏗️ Infrastructure"),
        ("other", "📦 Other Changes"),
    ]

    for cat_key, cat_title in category_order:
        cat_commits = categories.get(cat_key, [])
        if not cat_commits:
            continue

        lines.append(f"## {cat_title}")
        lines.append("")

        for commit in cat_commits:
            subject = clean_subject(commit["subject"])
            pr_num = get_pr_number(commit["subject"])
            author = commit["github_author"]

            # Build the line
            parts = [f"- {subject}"]
            if pr_num:
                parts.append(f"([#{pr_num}]({repo_url}/pull/{pr_num}))")
            else:
                parts.append(f"([`{commit['short_sha']}`]({repo_url}/commit/{commit['sha']}))")

            if author not in teknium_aliases:
                parts.append(f"— {author}")

            lines.append(" ".join(parts))

        lines.append("")

    # Contributors section
    if all_authors:
        # Sort contributors by commit count
        author_counts = defaultdict(int)
        for commit in commits:
            author = commit["github_author"]
            if author not in teknium_aliases:
                author_counts[author] += 1

        sorted_authors = sorted(author_counts.items(), key=lambda x: -x[1])

        lines.append("## 👥 Contributors")
        lines.append("")
        lines.append("Thank you to everyone who contributed to this release!")
        lines.append("")
        for author, count in sorted_authors:
            commit_word = "commit" if count == 1 else "commits"
            lines.append(f"- {author} ({count} {commit_word})")
        lines.append("")

    # Full changelog link
    if prev_tag:
        lines.append(f"**Full Changelog**: [{prev_tag}...{tag_name}]({repo_url}/compare/{prev_tag}...{tag_name})")
    else:
        lines.append(f"**Full Changelog**: [{tag_name}]({repo_url}/commits/{tag_name})")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Drewgent Agent Release Tool")
    parser.add_argument("--bump", choices=["major", "minor", "patch"],
                        help="Which semver component to bump")
    parser.add_argument("--publish", action="store_true",
                        help="Actually create the tag and GitHub release (otherwise dry run)")
    parser.add_argument("--date", type=str,
                        help="Override CalVer date (format: YYYY.M.D)")
    parser.add_argument("--first-release", action="store_true",
                        help="Mark as first release (no previous tag expected)")
    parser.add_argument("--output", type=str,
                        help="Write changelog to file instead of stdout")
    args = parser.parse_args()

    # Determine CalVer date
    if args.date:
        calver_date = args.date
    else:
        now = datetime.now()
        calver_date = f"{now.year}.{now.month}.{now.day}"

    base_tag = f"v{calver_date}"
    tag_name, calver_date = next_available_tag(base_tag)
    if tag_name != base_tag:
        print(f"Note: Tag {base_tag} already exists, using {tag_name}")

    # Determine semver
    current_version = get_current_version()
    if args.bump:
        new_version = bump_version(current_version, args.bump)
    else:
        new_version = current_version

    # Get previous tag
    prev_tag = get_last_tag()
    if not prev_tag and not args.first_release:
        print("No previous tags found. Use --first-release for the initial release.")
        print(f"Would create tag: {tag_name}")
        print(f"Would set version: {new_version}")

    # Get commits
    commits = get_commits(since_tag=prev_tag)
    if not commits:
        print("No new commits since last tag.")
        if not args.first_release:
            return

    print(f"{'='*60}")
    print(f"  Drewgent Agent Release Preview")
    print(f"{'='*60}")
    print(f"  CalVer tag:      {tag_name}")
    print(f"  SemVer:          v{current_version} → v{new_version}")
    print(f"  Previous tag:    {prev_tag or '(none — first release)'}")
    print(f"  Commits:         {len(commits)}")
    print(f"  Unique authors:  {len(set(c['github_author'] for c in commits))}")
    print(f"  Mode:            {'PUBLISH' if args.publish else 'DRY RUN'}")
    print(f"{'='*60}")
    print()

    # Generate changelog
    changelog = generate_changelog(
        commits, tag_name, new_version,
        prev_tag=prev_tag,
        first_release=args.first_release,
    )

    if args.output:
        Path(args.output).write_text(changelog)
        print(f"Changelog written to {args.output}")
    else:
        print(changelog)

    if args.publish:
        print(f"\n{'='*60}")
        print("  Publishing release...")
        print(f"{'='*60}")

        # Update version files
        if args.bump:
            update_version_files(new_version, calver_date)
            print(f"  ✓ Updated version files to v{new_version} ({calver_date})")

            # Commit version bump
            add_result = git_result("add", str(VERSION_FILE), str(PYPROJECT_FILE))
            if add_result.returncode != 0:
                print(f"  ✗ Failed to stage version files: {add_result.stderr.strip()}")
                return

            commit_result = git_result(
                "commit", "-m", f"chore: bump version to v{new_version} ({calver_date})"
            )
            if commit_result.returncode != 0:
                print(f"  ✗ Failed to commit version bump: {commit_result.stderr.strip()}")
                return
            print(f"  ✓ Committed version bump")

        # Create annotated tag
        tag_result = git_result(
            "tag", "-a", tag_name, "-m",
            f"Drewgent Agent v{new_version} ({calver_date})\n\nWeekly release"
        )
        if tag_result.returncode != 0:
            print(f"  ✗ Failed to create tag {tag_name}: {tag_result.stderr.strip()}")
            return
        print(f"  ✓ Created tag {tag_name}")

        # Push
        push_result = git_result("push", "origin", "HEAD", "--tags")
        if push_result.returncode == 0:
            print(f"  ✓ Pushed to origin")
        else:
            print(f"  ✗ Failed to push to origin: {push_result.stderr.strip()}")
            print("    Continue manually after fixing access:")
            print("    git push origin HEAD --tags")

        # Build semver-named Python artifacts so downstream packagers
        # (e.g. Homebrew) can target them without relying on CalVer tag names.
        artifacts = build_release_artifacts(new_version)
        if artifacts:
            print("  ✓ Built release artifacts:")
            for artifact in artifacts:
                print(f"    - {artifact.relative_to(REPO_ROOT)}")

        # Create GitHub release
        changelog_file = REPO_ROOT / ".release_notes.md"
        changelog_file.write_text(changelog)

        gh_cmd = [
            "gh", "release", "create", tag_name,
            "--title", f"Drewgent Agent v{new_version} ({calver_date})",
            "--notes-file", str(changelog_file),
        ]
        gh_cmd.extend(str(path) for path in artifacts)

        gh_bin = shutil.which("gh")
        if gh_bin:
            result = subprocess.run(
                gh_cmd,
                capture_output=True, text=True,
                cwd=str(REPO_ROOT),
            )
        else:
            result = None

        if result and result.returncode == 0:
            changelog_file.unlink(missing_ok=True)
            print(f"  ✓ GitHub release created: {result.stdout.strip()}")
            print(f"\n  🎉 Release v{new_version} ({tag_name}) published!")
        else:
            if result is None:
                print("  ✗ GitHub release skipped: `gh` CLI not found.")
            else:
                print(f"  ✗ GitHub release failed: {result.stderr.strip()}")
            print(f"    Release notes kept at: {changelog_file}")
            print(f"    Tag was created locally. Create the release manually:")
            print(
                f"    gh release create {tag_name} --title 'Drewgent Agent v{new_version} ({calver_date})' "
                f"--notes-file .release_notes.md {' '.join(str(path) for path in artifacts)}"
            )
            print(f"\n  ✓ Release artifacts prepared for manual publish: v{new_version} ({tag_name})")
    else:
        print(f"\n{'='*60}")
        print(f"  Dry run complete. To publish, add --publish")
        print(f"  Example: python scripts/release.py --bump minor --publish")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
