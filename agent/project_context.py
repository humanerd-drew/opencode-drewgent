"""Project context management for Drewgent.

Manages project-specific context stored in:
    ~/.drewgent/projects/<name>/.brain/

Structure:
    .brain/
        index.md      - Links to relevant Obsidian notes
        state.json    - Project state (workdir, permissions, failure patterns)
        linked_notes/ - Symlinks to Obsidian notes (optional)

Purpose:
    When a user says "work on clientX project", Drewgent:
    1. Loads project context from .brain/state.json
    2. Injects workdir, permission boundaries, failure patterns into prompt
    3. Resolves linked Obsidian notes for additional context

This prevents:
    - Repeating "where should I work?" questions
    - Hitting permission errors that were already solved before
    - Losing project-specific knowledge between sessions
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from agent.obsidian_graph import wiki_link
from drewgent_constants import get_drewgent_home

logger = logging.getLogger(__name__)


# Default brain directory name within each project
_BRAIN_DIR = ".brain"
_STATE_FILE = "state.json"
_INDEX_FILE = "index.md"


@dataclass
class ProjectState:
    """State for a single project.

    Stored in <project>/.brain/state.json
    """

    workdir: Optional[str] = None
    permission_boundary: Optional[str] = None
    failure_patterns: list[dict] = field(default_factory=list)
    last_session_id: Optional[str] = None
    notes: list[str] = field(default_factory=list)  # Linked Obsidian notes

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ProjectState":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class OrphanNote:
    """An orphan note that isn't linked from any project."""

    note_path: str
    note_name: str
    linked_by_projects: list[str] = field(default_factory=list)


@dataclass
class OrphanReport:
    """Report of orphan notes across all projects."""

    orphan_notes: list[OrphanNote]
    total_projects_checked: int
    total_notes_found: int


class ProjectContextManager:
    """Manage project contexts for Drewgent.

    Args:
        projects_root: Root directory for all projects (default: ~/.drewgent/projects)
        obsidian_vault: Path to Obsidian vault for note linking
    """

    def __init__(
        self,
        projects_root: Optional[Path] = None,
        obsidian_vault: Optional[Path] = None,
    ):
        self.projects_root = projects_root or (get_drewgent_home() / "projects")
        self.obsidian_vault = obsidian_vault

        # Ensure projects root exists
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def _get_project_brain(self, project_name: str) -> Path:
        """Get the .brain directory path for a project."""
        return self.projects_root / project_name / _BRAIN_DIR

    def _get_state_path(self, project_name: str) -> Path:
        """Get the state.json path for a project."""
        return self._get_project_brain(project_name) / _STATE_FILE

    def _get_index_path(self, project_name: str) -> Path:
        """Get the index.md path for a project."""
        return self._get_project_brain(project_name) / _INDEX_FILE

    def create_project(self, project_name: str) -> Path:
        """Create a new project with .brain structure.

        Args:
            project_name: Name of the project (e.g., "clientX")

        Returns:
            Path to the project directory
        """
        brain = self._get_project_brain(project_name)
        brain.mkdir(parents=True, exist_ok=True)

        # Create state.json with defaults
        state = ProjectState()
        self._get_state_path(project_name).write_text(state.to_json())

        # Create index.md with header
        self._get_index_path(project_name).write_text(
            "---\n"
            f"title: {project_name} Brain\n"
            "tags: [project, brain]\n"
            "links:\n"
            "  - \"[[P5-ego/SELF_MODEL]]\"\n"
            "---\n\n"
            f"# {project_name} Brain\n\n"
            f"This project is managed by Drewgent.\n"
            f"Linked Obsidian notes:\n"
        )

        logger.info(f"Created project brain at {brain}")
        return self.projects_root / project_name

    def load_state(self, project_name: str) -> Optional[ProjectState]:
        """Load state for a project.

        Args:
            project_name: Name of the project

        Returns:
            ProjectState if project exists, None otherwise
        """
        state_path = self._get_state_path(project_name)
        if not state_path.exists():
            return None

        try:
            return ProjectState.from_json(state_path.read_text())
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to load state for {project_name}: {e}")
            return None

    def save_state(self, project_name: str, state: ProjectState) -> None:
        """Save state for a project.

        Args:
            project_name: Name of the project
            state: ProjectState to save
        """
        # Ensure project exists
        if not self._get_project_brain(project_name).exists():
            self.create_project(project_name)

        self._get_state_path(project_name).write_text(state.to_json())
        logger.debug(f"Saved state for {project_name}")

    def add_failure_pattern(
        self,
        project_name: str,
        pattern: str,
        remedy: str,
    ) -> None:
        """Add a failure pattern and remedy for a project.

        Args:
            project_name: Name of the project
            pattern: Error pattern or keyword (e.g., "sudo: permission denied")
            remedy: How to solve this (e.g., "use docker instead")
        """
        state = self.load_state(project_name)
        if state is None:
            self.create_project(project_name)
            state = self.load_state(project_name)

        # Check for duplicate patterns
        for fp in state.failure_patterns:
            if fp.get("pattern") == pattern:
                # Update existing remedy if different
                if fp.get("remedy") != remedy:
                    fp["remedy"] = remedy
                    self.save_state(project_name, state)
                return

        # Add new pattern
        state.failure_patterns.append({"pattern": pattern, "remedy": remedy})
        self.save_state(project_name, state)
        logger.info(f"Added failure pattern for {project_name}: {pattern}")

    def get_project_context(self, project_name: str) -> Optional[dict]:
        """Get full project context as a dict.

        Args:
            project_name: Name of the project

        Returns:
            Dict with project context, or None if project doesn't exist
        """
        state = self.load_state(project_name)
        if state is None:
            return None

        brain = self._get_project_brain(project_name)

        return {
            "project_name": project_name,
            "workdir": state.workdir,
            "permission_boundary": state.permission_boundary,
            "failure_patterns": state.failure_patterns,
            "last_session_id": state.last_session_id,
            "linked_notes": self.get_linked_notes(project_name),
            "brain_path": str(brain),
        }

    def list_projects(self) -> list[str]:
        """List all project names.

        Returns:
            List of project names (directory names under projects_root)
        """
        if not self.projects_root.exists():
            return []

        projects = []
        for item in self.projects_root.iterdir():
            if item.is_dir() and (item / _BRAIN_DIR).exists():
                projects.append(item.name)

        return sorted(projects)

    def link_obsidian_note(self, project_name: str, note_name: str) -> None:
        """Link an Obsidian note to a project.

        Updates the project's .brain/index.md to reference the note.

        Args:
            project_name: Name of the project
            note_name: Name of the Obsidian note (without .md extension)
        """
        brain = self._get_project_brain(project_name)
        if not brain.exists():
            self.create_project(project_name)

        index_path = self._get_index_path(project_name)
        index_content = index_path.read_text()

        # Check if already linked (case-insensitive check for note name)
        note_lower = note_name.lower()
        for line in index_content.splitlines():
            if line.strip().lower() == f"- [[{note_lower}]]" or \
               line.strip().lower().endswith(f"[[{note_lower}]]"):
                return

        # Add link to index. Preserve explicit vault-relative note paths when
        # callers provide them; Obsidian accepts both bare names and paths.
        link_line = f"- {wiki_link(note_name)}\n"

        # Append to index
        index_content += link_line
        index_path.write_text(index_content)

        logger.info(f"Linked note {note_name} to project {project_name}")

    def get_linked_notes(self, project_name: str) -> list[str]:
        """Get list of note names linked to a project.

        Args:
            project_name: Name of the project

        Returns:
            List of note names (without .md extension)
        """
        index_path = self._get_index_path(project_name)
        if not index_path.exists():
            return []

        content = index_path.read_text()
        notes = []

        # Parse [[path/note]] or [[note]] links
        import re

        # Match [[anything/note]] where note is the last part
        pattern = r'\[\[.*?/([^]]+?)\]\]'
        matches = re.findall(pattern, content)

        # Also match simple [[note]] without path (but not [[note|alias]])
        # Only match if there's no / before the ]]
        simple_pattern = r'\[\[([^]|/]+)\]\]'
        simple_matches = re.findall(simple_pattern, content)

        # Combine and deduplicate
        for match in matches + simple_matches:
            note = match.strip().replace(".md", "")
            if note and note not in notes:
                notes.append(note)

        return notes

    def find_orphan_notes(self) -> list[OrphanNote]:
        """Find Obsidian notes that aren't linked from any project.

        Returns:
            List of OrphanNote objects
        """
        if not self.obsidian_vault or not self.obsidian_vault.exists():
            return []

        # Get all markdown files in vault
        all_notes: dict[str, Path] = {}
        for md_file in self.obsidian_vault.rglob("*.md"):
            note_name = md_file.stem  # filename without extension
            all_notes[note_name] = md_file

        # Get all linked notes across all projects
        linked_notes: set[str] = set()
        projects_checked = 0

        for project_name in self.list_projects():
            projects_checked += 1
            for note_name in self.get_linked_notes(project_name):
                linked_notes.add(note_name)

        # Find orphans
        orphans = []
        for note_name, note_path in all_notes.items():
            # Skip index files and hidden files
            if note_name.startswith(".") or note_name == "index":
                continue

            if note_name not in linked_notes:
                orphans.append(
                    OrphanNote(
                        note_path=str(note_path),
                        note_name=note_name,
                    )
                )

        return orphans

    def get_orphan_report(self) -> OrphanReport:
        """Get a full orphan notes report.

        Returns:
            OrphanReport with all orphan information
        """
        orphans = self.find_orphan_notes()

        return OrphanReport(
            orphan_notes=orphans,
            total_projects_checked=len(self.list_projects()),
            total_notes_found=len(orphans),
        )

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists.

        Args:
            project_name: Name of the project

        Returns:
            True if project exists
        """
        return self._get_project_brain(project_name).exists()


# ---------------------------------------------------------------------------
# File-based current project (for cross-process communication)
# ---------------------------------------------------------------------------

_CURRENT_PROJECT_FILE = get_drewgent_home() / ".current_project"


def save_current_project(project_name: str) -> None:
    """Save the current project name to a file.

    This allows the CLI and agent to communicate across processes.

    Args:
        project_name: Name of the project to set as current
    """
    _CURRENT_PROJECT_FILE.write_text(project_name)


def get_current_project_name() -> Optional[str]:
    """Get the current project name from file.

    Returns:
        Project name if set, None otherwise
    """
    if not _CURRENT_PROJECT_FILE.exists():
        return None
    return _CURRENT_PROJECT_FILE.read_text().strip() or None


def clear_current_project() -> None:
    """Clear the current project."""
    if _CURRENT_PROJECT_FILE.exists():
        _CURRENT_PROJECT_FILE.unlink()


def _detect_current_project() -> Optional[str]:
    """Auto-detect the current project from git worktree or nearest .brain directory.

    Detection priority:
    1. Already set: return `.current_project` content if exists
    2. Git worktree: find worktree containing current CWD, use its name
    3. Nearest `.brain` ancestor: search parent dirs for `.brain/` directory
    4. Fallback: None (no project set)

    Returns:
        Project name string or None if no project detected
    """
    # Priority 1: Already set
    existing = get_current_project_name()
    if existing:
        return existing

    import subprocess, os

    # Priority 2: Git worktree detection
    try:
        cwd = os.getcwd()
        result = subprocess.run(
            ["git", "worktree", "list", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            import json as _json

            try:
                worktrees = _json.loads(result.stdout)
                for wt in worktrees:
                    wt_path = wt.get("path", "")
                    if wt_path and cwd.startswith(wt_path):
                        # Extract project name from worktree path
                        # e.g., /Users/drew/projects/clientX → clientX
                        project_name = Path(wt_path).name
                        save_current_project(project_name)
                        return project_name
            except _json.JSONDecodeError:
                # Fallback to line parsing
                for line in result.stdout.splitlines():
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 1:
                        wt_path = Path(parts[0]).resolve()
                        if cwd.startswith(str(wt_path)):
                            project_name = wt_path.name
                            save_current_project(project_name)
                            return project_name
    except Exception:
        pass

    # Priority 3: Nearest `.brain` ancestor
    cwd_path = Path.cwd()
    for parent in [cwd_path] + list(cwd_path.parents):
        brain_dir = parent / ".brain"
        if brain_dir.is_dir():
            project_name = parent.name
            save_current_project(project_name)
            return project_name

    return None


def build_project_context_prompt() -> str:
    """Build a project context prompt from the current project.

    Call this when building the system prompt to inject project context.
    Auto-detects project if none is currently set.

    Returns:
        Project context string if a project is set, empty string otherwise
    """
    project_name = get_current_project_name()
    if not project_name:
        project_name = _detect_current_project()
    if not project_name:
        return ""

    manager = ProjectContextManager()
    ctx = manager.get_project_context(project_name)
    if not ctx:
        return ""

    parts = [f"# Project Context: {project_name}\n"]

    if ctx.get("workdir"):
        parts.append(f"- Workdir: {ctx['workdir']}")

    if ctx.get("permission_boundary"):
        parts.append(f"- Permission boundary: {ctx['permission_boundary']}")

    patterns = ctx.get("failure_patterns", [])
    if patterns:
        parts.append(f"- Known failure patterns ({len(patterns)}):")
        for fp in patterns:
            parts.append(f"  - {fp['pattern']}: {fp['remedy']}")

    notes = ctx.get("linked_notes", [])
    if notes:
        parts.append(f"- Linked Obsidian notes: {', '.join(notes)}")

    return "\n".join(parts)
