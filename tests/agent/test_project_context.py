"""Tests for project context management (TDD approach).

This module tests the ProjectContextManager which manages:
- ~/.drewgent/projects/<name>/.brain/ structure
- Project-specific memory (workdir, permission boundaries, failure patterns)
- Obsidian note linking
- Orphan node detection
"""

import json
import os
import pytest
from pathlib import Path

# Import the module under test
from agent.project_context import ProjectContextManager, ProjectState, OrphanReport


@pytest.fixture
def projects_root(tmp_path):
    """Create a temporary projects root directory."""
    root = tmp_path / "projects"
    root.mkdir()
    return root


@pytest.fixture
def obsidian_vault(tmp_path):
    """Create a mock Obsidian vault with some notes."""
    vault = tmp_path / "Obsidian" / "vault"
    vault.mkdir(parents=True)

    # Create some notes
    (vault / "project-alpha.md").write_text("# Project Alpha\n\nClient project.\n")
    (vault / "meeting-notes.md").write_text("# Meeting Notes\n\nGeneric notes.\n")
    (vault / "orphan-note.md").write_text("# Orphan Note\n\nNo links to this.\n")
    (vault / "index.md").write_text("# Index\n\nEntry point.\n")

    return vault


class TestProjectState:
    """Tests for ProjectState dataclass."""

    def test_default_state(self):
        """Default state should have sensible defaults."""
        state = ProjectState()

        assert state.workdir is None
        assert state.permission_boundary is None
        assert state.failure_patterns == []
        assert state.last_session_id is None

    def test_full_state(self):
        """Full state with all fields."""
        state = ProjectState(
            workdir="/home/user/projects/clientX",
            permission_boundary="/home/user",
            failure_patterns=[
                {"pattern": "sudo.*permission denied", "remedy": "use docker instead"},
                {"pattern": "npm install failed", "remedy": "use yarn"},
            ],
            last_session_id="session-123",
        )

        assert state.workdir == "/home/user/projects/clientX"
        assert state.permission_boundary == "/home/user"
        assert len(state.failure_patterns) == 2
        assert state.last_session_id == "session-123"

    def test_serialization(self):
        """State should serialize to/from JSON."""
        state = ProjectState(
            workdir="/home/user/projects/clientX",
            failure_patterns=[{"pattern": "sudo", "remedy": "docker"}],
        )

        json_str = state.to_json()
        restored = ProjectState.from_json(json_str)

        assert restored.workdir == state.workdir
        assert restored.failure_patterns == state.failure_patterns


class TestProjectContextManager:
    """Tests for ProjectContextManager."""

    def test_init_creates_projects_root(self, projects_root, obsidian_vault):
        """Manager should create projects root if it doesn't exist."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        assert projects_root.exists()

    def test_init_with_existing_projects_root(self, projects_root, obsidian_vault):
        """Manager should work with existing projects root."""
        # projects_root already created by fixture

        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        assert manager.projects_root == projects_root

    def test_create_project(self, projects_root, obsidian_vault):
        """Creating a project should set up .brain directory."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        project_path = manager.create_project("clientX")

        assert project_path.exists()
        assert (project_path / ".brain").is_dir()
        assert (project_path / ".brain" / "state.json").exists()
        assert (project_path / ".brain" / "index.md").exists()

    def test_create_project_twice_returns_same_path(self, projects_root, obsidian_vault):
        """Creating the same project twice should return the same path."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        path1 = manager.create_project("clientX")
        path2 = manager.create_project("clientX")

        assert path1 == path2

    def test_save_and_load_state(self, projects_root, obsidian_vault):
        """Saving and loading state should preserve all fields."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")

        state = ProjectState(
            workdir="/home/user/projects/clientX",
            permission_boundary="/home/user",
            failure_patterns=[
                {"pattern": "sudo", "remedy": "use docker"}
            ],
        )
        manager.save_state("clientX", state)

        loaded = manager.load_state("clientX")

        assert loaded is not None
        assert loaded.workdir == "/home/user/projects/clientX"
        assert loaded.permission_boundary == "/home/user"
        assert len(loaded.failure_patterns) == 1

    def test_load_nonexistent_project_returns_none(self, projects_root, obsidian_vault):
        """Loading a nonexistent project should return None."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        result = manager.load_state("nonexistent")

        assert result is None

    def test_add_failure_pattern(self, projects_root, obsidian_vault):
        """Adding a failure pattern should update the state."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.add_failure_pattern("clientX", "sudo failed", "use docker instead")

        state = manager.load_state("clientX")
        assert len(state.failure_patterns) == 1
        assert state.failure_patterns[0]["pattern"] == "sudo failed"
        assert state.failure_patterns[0]["remedy"] == "use docker instead"

    def test_add_failure_pattern_deduplicates(self, projects_root, obsidian_vault):
        """Adding the same pattern twice should not duplicate."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.add_failure_pattern("clientX", "sudo failed", "use docker")
        manager.add_failure_pattern("clientX", "sudo failed", "use docker")

        state = manager.load_state("clientX")
        assert len(state.failure_patterns) == 1

    def test_get_project_context(self, projects_root, obsidian_vault):
        """Getting project context should return a summary dict."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.save_state(
            "clientX",
            ProjectState(
                workdir="/home/user/projects/clientX",
                permission_boundary="/home/user",
                failure_patterns=[{"pattern": "sudo", "remedy": "docker"}],
            ),
        )

        context = manager.get_project_context("clientX")

        assert context is not None
        assert context["project_name"] == "clientX"
        assert context["workdir"] == "/home/user/projects/clientX"
        assert context["permission_boundary"] == "/home/user"
        assert len(context["failure_patterns"]) == 1
        assert "brain_path" in context

    def test_get_project_context_nonexistent(self, projects_root, obsidian_vault):
        """Getting context for nonexistent project should return None."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        result = manager.get_project_context("nonexistent")

        assert result is None

    def test_link_obsidian_note(self, projects_root, obsidian_vault):
        """Linking an Obsidian note should update index.md."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.link_obsidian_note("clientX", "project-alpha")

        index_content = (projects_root / "clientX" / ".brain" / "index.md").read_text()
        assert "project-alpha" in index_content
        # Uses simple [[note-name]] format
        assert "- [[project-alpha]]" in index_content

    def test_link_obsidian_note_idempotent(self, projects_root, obsidian_vault):
        """Linking the same note twice should not duplicate."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.link_obsidian_note("clientX", "project-alpha")
        manager.link_obsidian_note("clientX", "project-alpha")

        index_content = (projects_root / "clientX" / ".brain" / "index.md").read_text()
        # Should appear only once
        assert index_content.count("project-alpha") == 1

    def test_get_linked_notes(self, projects_root, obsidian_vault):
        """Getting linked notes should return list of note names."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.link_obsidian_note("clientX", "project-alpha")
        manager.link_obsidian_note("clientX", "meeting-notes")

        notes = manager.get_linked_notes("clientX")

        assert "project-alpha" in notes
        assert "meeting-notes" in notes

    def test_list_projects(self, projects_root, obsidian_vault):
        """Listing projects should return all project names."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.create_project("clientY")
        manager.create_project("clientZ")

        projects = manager.list_projects()

        assert "clientX" in projects
        assert "clientY" in projects
        assert "clientZ" in projects
        assert len(projects) == 3


class TestOrphanDetection:
    """Tests for orphan note detection."""

    def test_find_orphan_notes(self, projects_root, obsidian_vault):
        """Should detect notes not linked from any .brain/index.md."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        # Create a project and link only project-alpha
        manager.create_project("clientX")
        manager.link_obsidian_note("clientX", "project-alpha")

        orphans = manager.find_orphan_notes()

        # orphan-note.md is not linked from any project
        assert any("orphan-note" in o.note_path for o in orphans)
        # meeting-notes is also not linked
        assert any("meeting-notes" in o.note_path for o in orphans)
        # project-alpha is linked, should not be orphan
        assert not any("project-alpha" in o.note_path for o in orphans)

    def test_find_orphan_notes_multiple_projects(self, projects_root, obsidian_vault):
        """Orphan detection should check all projects."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.create_project("clientY")
        manager.link_obsidian_note("clientX", "project-alpha")
        manager.link_obsidian_note("clientY", "meeting-notes")

        orphans = manager.find_orphan_notes()

        # orphan-note.md is not linked from any project
        assert len(orphans) == 1
        assert "orphan-note" in orphans[0].note_path

    def test_orphan_report_format(self, projects_root, obsidian_vault):
        """Orphan report should have correct structure."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        # Don't link any notes

        report = manager.get_orphan_report()

        assert isinstance(report, OrphanReport)
        assert "clientX" in report.orphan_notes or len(report.orphan_notes) > 0
        assert report.total_projects_checked >= 1

    def test_no_orphans_when_all_linked(self, projects_root, obsidian_vault):
        """No orphans when all notes are linked."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.link_obsidian_note("clientX", "project-alpha")
        manager.link_obsidian_note("clientX", "meeting-notes")
        manager.link_obsidian_note("clientX", "orphan-note")

        orphans = manager.find_orphan_notes()

        assert len(orphans) == 0


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_project_workflow(self, projects_root, obsidian_vault):
        """Test the complete project context workflow."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        # 1. Create project
        project_path = manager.create_project("clientX")
        assert project_path.name == "clientX"

        # 2. Set up initial state
        manager.save_state(
            "clientX",
            ProjectState(
                workdir="/home/user/projects/clientX",
                permission_boundary="/home/user",
            ),
        )

        # 3. Link relevant Obsidian notes
        manager.link_obsidian_note("clientX", "project-alpha")

        # 4. Later, agent encounters a permission error
        manager.add_failure_pattern(
            "clientX",
            "sudo: permission denied",
            "use docker exec instead of sudo",
        )

        # 5. Get context for the project
        context = manager.get_project_context("clientX")

        assert context["workdir"] == "/home/user/projects/clientX"
        assert context["permission_boundary"] == "/home/user"
        assert len(context["failure_patterns"]) == 1
        assert "docker" in context["failure_patterns"][0]["remedy"]
        assert "project-alpha" in context["linked_notes"]

        # 6. Verify linked notes
        notes = manager.get_linked_notes("clientX")
        assert "project-alpha" in notes

    def test_permission_error_recovery_workflow(self, projects_root, obsidian_vault):
        """Test the permission error → remedy stored → used next time workflow."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        # Create project
        manager.create_project("clientX")
        manager.save_state(
            "clientX",
            ProjectState(workdir="/work/clientX"),
        )

        # First time: agent hits permission error
        manager.add_failure_pattern(
            "clientX",
            "permission denied: /root",
            "use sudo docker container instead",
        )

        # Verify pattern stored
        state = manager.load_state("clientX")
        assert len(state.failure_patterns) == 1

        # Second time: get context should include the remedy
        context = manager.get_project_context("clientX")
        assert any(
            "docker" in fp["remedy"]
            for fp in context["failure_patterns"]
        )

    def test_project_workdir_auto_set(self, projects_root, obsidian_vault):
        """When workdir is set, it should be usable directly."""
        manager = ProjectContextManager(
            projects_root=projects_root,
            obsidian_vault=obsidian_vault,
        )

        manager.create_project("clientX")
        manager.save_state(
            "clientX",
            ProjectState(workdir="/home/user/projects/clientX"),
        )

        context = manager.get_project_context("clientX")

        # The workdir should be returned in a format ready to use
        assert context["workdir"] == "/home/user/projects/clientX"
        # This can be used directly in terminal tool workdir parameter
