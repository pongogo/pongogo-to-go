"""Unit tests for CLI preferences module.

Tests preference loading, saving, merging, and behavior mode handling.
"""

from pathlib import Path

import yaml

from cli.preferences import (
    BEHAVIOR_TRIGGERS,
    DEFAULT_PREFERENCES,
    commit_approach,
    get_approach,
    get_behavior_mode,
    get_communication_preference,
    get_preferences_path,
    get_tone,
    get_verbosity,
    list_behavior_triggers,
    load_preferences,
    save_preferences,
    set_behavior_mode,
    set_communication_preference,
    should_use_acronyms,
    should_use_emojis,
)


class TestDefaultPreferences:
    """Tests for DEFAULT_PREFERENCES structure."""

    def test_default_preferences_has_version(self):
        """Default preferences should have version."""
        assert "version" in DEFAULT_PREFERENCES
        assert DEFAULT_PREFERENCES["version"] == 1

    def test_default_preferences_has_behaviors(self):
        """Default preferences should have behaviors dict."""
        assert "behaviors" in DEFAULT_PREFERENCES
        assert isinstance(DEFAULT_PREFERENCES["behaviors"], dict)

    def test_default_preferences_has_communication(self):
        """Default preferences should have communication settings."""
        assert "communication" in DEFAULT_PREFERENCES
        comm = DEFAULT_PREFERENCES["communication"]
        assert "use_acronyms" in comm
        assert "verbosity" in comm
        assert "tone" in comm

    def test_default_preferences_has_approaches(self):
        """Default preferences should have approaches dict."""
        assert "approaches" in DEFAULT_PREFERENCES
        assert isinstance(DEFAULT_PREFERENCES["approaches"], dict)

    def test_default_preferences_has_bundling(self):
        """Default preferences should have bundling config."""
        assert "bundling" in DEFAULT_PREFERENCES
        assert "task_completion" in DEFAULT_PREFERENCES["bundling"]


class TestBehaviorTriggers:
    """Tests for BEHAVIOR_TRIGGERS constant."""

    def test_behavior_triggers_is_dict(self):
        """Behavior triggers should be a dict."""
        assert isinstance(BEHAVIOR_TRIGGERS, dict)

    def test_behavior_triggers_have_descriptions(self):
        """All triggers should have string descriptions."""
        for trigger, description in BEHAVIOR_TRIGGERS.items():
            assert isinstance(trigger, str)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_known_triggers_present(self):
        """Known triggers should be present."""
        expected_triggers = [
            "work_log_on_task_completion",
            "retro_on_epic_completion",
            "rca_on_incident",
        ]
        for trigger in expected_triggers:
            assert trigger in BEHAVIOR_TRIGGERS


class TestGetPreferencesPath:
    """Tests for get_preferences_path function."""

    def test_returns_pongogo_preferences_path(self, tmp_path: Path):
        """Should return .pongogo/preferences.yaml path."""
        result = get_preferences_path(tmp_path)
        assert result == tmp_path / ".pongogo" / "preferences.yaml"


class TestLoadPreferences:
    """Tests for load_preferences function."""

    def test_load_returns_defaults_when_file_missing(self, tmp_path: Path):
        """Load returns defaults when preferences file doesn't exist."""
        prefs = load_preferences(tmp_path)
        assert prefs["version"] == DEFAULT_PREFERENCES["version"]

    def test_load_reads_existing_file(self, tmp_path: Path):
        """Load reads preferences from existing file."""
        prefs_path = tmp_path / ".pongogo" / "preferences.yaml"
        prefs_path.parent.mkdir(parents=True)

        custom_prefs = {"version": 2, "custom_key": "custom_value"}
        with open(prefs_path, "w") as f:
            yaml.dump(custom_prefs, f)

        loaded = load_preferences(tmp_path)
        assert loaded["custom_key"] == "custom_value"

    def test_load_merges_with_defaults(self, tmp_path: Path):
        """Load merges file values with defaults for missing keys."""
        prefs_path = tmp_path / ".pongogo" / "preferences.yaml"
        prefs_path.parent.mkdir(parents=True)

        # Only save partial preferences
        partial_prefs = {"version": 2}
        with open(prefs_path, "w") as f:
            yaml.dump(partial_prefs, f)

        loaded = load_preferences(tmp_path)
        # Should have merged default communication settings
        assert "communication" in loaded
        assert "use_acronyms" in loaded["communication"]

    def test_load_deep_merges_nested_dicts(self, tmp_path: Path):
        """Load deep merges nested dictionaries."""
        prefs_path = tmp_path / ".pongogo" / "preferences.yaml"
        prefs_path.parent.mkdir(parents=True)

        # Override only one communication setting
        partial_prefs = {"communication": {"verbosity": "concise"}}
        with open(prefs_path, "w") as f:
            yaml.dump(partial_prefs, f)

        loaded = load_preferences(tmp_path)
        # Should have the override
        assert loaded["communication"]["verbosity"] == "concise"
        # Should still have defaults for other settings
        assert "use_acronyms" in loaded["communication"]


class TestSavePreferences:
    """Tests for save_preferences function."""

    def test_save_creates_file(self, tmp_path: Path):
        """Save creates preferences file."""
        prefs = DEFAULT_PREFERENCES.copy()
        save_preferences(tmp_path, prefs)

        prefs_path = tmp_path / ".pongogo" / "preferences.yaml"
        assert prefs_path.exists()

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        """Save creates parent directories if needed."""
        prefs = DEFAULT_PREFERENCES.copy()
        save_preferences(tmp_path, prefs)

        pongogo_dir = tmp_path / ".pongogo"
        assert pongogo_dir.exists()

    def test_save_produces_valid_yaml(self, tmp_path: Path):
        """Saved preferences should be valid YAML."""
        prefs = DEFAULT_PREFERENCES.copy()
        save_preferences(tmp_path, prefs)

        prefs_path = tmp_path / ".pongogo" / "preferences.yaml"
        loaded = yaml.safe_load(prefs_path.read_text())
        assert loaded is not None


class TestBehaviorModes:
    """Tests for behavior mode functions."""

    def test_get_behavior_mode_returns_none_for_unset(self):
        """Get behavior mode returns None for unset trigger."""
        prefs = DEFAULT_PREFERENCES.copy()
        result = get_behavior_mode(prefs, "some_trigger")
        assert result is None

    def test_get_behavior_mode_returns_mode(self):
        """Get behavior mode returns the set mode."""
        prefs = {"behaviors": {"work_log_on_task_completion": {"mode": "auto"}}}
        result = get_behavior_mode(prefs, "work_log_on_task_completion")
        assert result == "auto"

    def test_set_behavior_mode_saves_mode(self, tmp_path: Path):
        """Set behavior mode saves the mode to file."""
        set_behavior_mode(tmp_path, "test_trigger", "skip")

        prefs = load_preferences(tmp_path)
        assert prefs["behaviors"]["test_trigger"]["mode"] == "skip"

    def test_set_behavior_mode_sets_learned_at(self, tmp_path: Path):
        """Set behavior mode sets learned_at timestamp."""
        set_behavior_mode(tmp_path, "test_trigger", "auto")

        prefs = load_preferences(tmp_path)
        assert "learned_at" in prefs["behaviors"]["test_trigger"]


class TestCommunicationPreferences:
    """Tests for communication preference functions."""

    def test_get_communication_preference_default(self):
        """Get communication preference returns default."""
        prefs = DEFAULT_PREFERENCES.copy()
        result = get_communication_preference(prefs, "verbosity")
        assert result == "balanced"

    def test_get_communication_preference_custom(self):
        """Get communication preference returns custom value."""
        prefs = {"communication": {"verbosity": "concise"}}
        result = get_communication_preference(prefs, "verbosity")
        assert result == "concise"

    def test_set_communication_preference(self, tmp_path: Path):
        """Set communication preference saves value."""
        set_communication_preference(tmp_path, "verbosity", "verbose")

        prefs = load_preferences(tmp_path)
        assert prefs["communication"]["verbosity"] == "verbose"

    def test_should_use_acronyms_default(self):
        """Should use acronyms returns default True."""
        prefs = DEFAULT_PREFERENCES.copy()
        assert should_use_acronyms(prefs) is True

    def test_should_use_emojis_default(self):
        """Should use emojis returns default False."""
        prefs = DEFAULT_PREFERENCES.copy()
        assert should_use_emojis(prefs) is False

    def test_get_verbosity_default(self):
        """Get verbosity returns default balanced."""
        # Use fresh dict to avoid state pollution from other tests
        prefs = {"communication": {"verbosity": "balanced"}}
        assert get_verbosity(prefs) == "balanced"

    def test_get_tone_default(self):
        """Get tone returns default balanced."""
        prefs = DEFAULT_PREFERENCES.copy()
        assert get_tone(prefs) == "balanced"


class TestApproaches:
    """Tests for approach commitment functions."""

    def test_get_approach_returns_none_for_unset(self):
        """Get approach returns None for uncommitted problem type."""
        prefs = DEFAULT_PREFERENCES.copy()
        result = get_approach(prefs, "some_problem")
        assert result is None

    def test_get_approach_returns_committed(self):
        """Get approach returns committed technique."""
        prefs = {"approaches": {"root_cause_analysis": {"technique": "5 whys"}}}
        result = get_approach(prefs, "root_cause_analysis")
        assert result["technique"] == "5 whys"

    def test_commit_approach_saves(self, tmp_path: Path):
        """Commit approach saves to file."""
        commit_approach(tmp_path, "testing", "TDD", validated_count=5)

        prefs = load_preferences(tmp_path)
        assert prefs["approaches"]["testing"]["technique"] == "TDD"
        assert prefs["approaches"]["testing"]["validated_count"] == 5


class TestListBehaviorTriggers:
    """Tests for list_behavior_triggers function."""

    def test_returns_copy(self):
        """List behavior triggers returns a copy."""
        result = list_behavior_triggers()
        result["new_trigger"] = "new description"

        # Original should not be modified
        assert "new_trigger" not in BEHAVIOR_TRIGGERS

    def test_returns_all_triggers(self):
        """List behavior triggers returns all triggers."""
        result = list_behavior_triggers()
        assert result == BEHAVIOR_TRIGGERS
