"""Preferences management for Pongogo.

This module handles organic user preference learning, storing preferences
in .pongogo/preferences.yaml for behavior, communication, and approach settings.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

import yaml


# Preference modes for trigger behaviors
BehaviorMode = Literal["auto", "ask", "skip"]

# Communication verbosity levels
Verbosity = Literal["concise", "balanced", "verbose"]

# Communication tone levels
Tone = Literal["casual", "balanced", "professional"]


DEFAULT_PREFERENCES: dict[str, Any] = {
    "version": 1,
    "learned_at": None,  # Set on first preference learned
    
    # Behavior preferences: How proactive should Pongogo be?
    "behaviors": {},
    
    # Communication preferences: How should Pongogo communicate?
    "communication": {
        "use_acronyms": True,  # Default: use acronyms
        "verbosity": "balanced",
        "tone": "balanced",
        "use_emojis": False,
    },
    
    # Approach commitments: Validated techniques to keep using
    "approaches": {},
    
    # Action bundling configuration
    "bundling": {
        "task_completion": [
            "work_log_on_task_completion",
            "decision_capture",
            "strategic_insight_capture",
        ],
        "epic_completion": [
            "retro_on_epic_completion",
            "work_log_on_task_completion",
        ],
    },
}


# Known behavior triggers with descriptions
BEHAVIOR_TRIGGERS = {
    # Work Completion
    "work_log_on_task_completion": "Create work log entry when task finishes",
    "retro_on_epic_completion": "Conduct L2 retrospective when epic closes",
    "retro_on_milestone_completion": "Conduct L3 retrospective when milestone closes",
    
    # Learning Capture
    "rca_on_incident": "Start RCA when incident detected",
    "rca_followup_tracking": "Track RCA follow-up actions",
    
    # PI System
    "pi_threshold_prompt": "Suggest instruction creation at 3+ occurrences",
    
    # Knowledge Institutionalization
    "decision_capture": "Capture architectural decisions",
    "strategic_insight_capture": "Note strategic insights",
    "approach_commitment": "Commit validated approaches",
    "glossary_candidate": "Suggest glossary entry at 3+ uses",
    "faq_candidate": "Suggest FAQ entry at 3+ questions",
    
    # Issue Lifecycle (GitHub PM conditional)
    "issue_template_apply": "Apply template to new issues",
    "issue_status_verify": "Verify prerequisites on status change",
    "issue_completion_comment": "Add completion comment",
    "issue_closure": "Final closure actions",
}


PREFERENCES_HEADER = """\
# Pongogo Preferences
# Auto-generated through use - edit via /pongogo-config
#
# Behaviors: How proactive Pongogo is for each trigger (auto/ask/skip)
# Communication: How Pongogo communicates (acronyms, verbosity, tone)
# Approaches: Validated techniques Pongogo remembers to use
#
# Documentation: https://github.com/pongogo/pongogo-to-go/blob/main/docs/reference/preferences.md

"""


def get_preferences_path(project_root: Path) -> Path:
    """Get the path to preferences.yaml.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Path to .pongogo/preferences.yaml
    """
    return project_root / ".pongogo" / "preferences.yaml"


def load_preferences(project_root: Path) -> dict[str, Any]:
    """Load preferences from YAML file.
    
    If file doesn't exist, returns default preferences.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Preferences dictionary
    """
    prefs_path = get_preferences_path(project_root)
    
    if not prefs_path.exists():
        return DEFAULT_PREFERENCES.copy()
    
    with open(prefs_path) as f:
        prefs = yaml.safe_load(f) or {}
    
    # Merge with defaults for any missing keys
    merged = DEFAULT_PREFERENCES.copy()
    merged.update(prefs)
    
    # Deep merge nested dicts
    for key in ["behaviors", "communication", "approaches", "bundling"]:
        if key in prefs:
            merged[key] = {**DEFAULT_PREFERENCES.get(key, {}), **prefs[key]}
    
    return merged


def save_preferences(project_root: Path, preferences: dict[str, Any]) -> None:
    """Save preferences to YAML file.
    
    Args:
        project_root: Root directory of the project
        preferences: Preferences dictionary to save
    """
    prefs_path = get_preferences_path(project_root)
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(prefs_path, "w") as f:
        f.write(PREFERENCES_HEADER)
        yaml.dump(preferences, f, default_flow_style=False, sort_keys=False)


def get_behavior_mode(
    preferences: dict[str, Any],
    trigger: str,
) -> Optional[BehaviorMode]:
    """Get the behavior mode for a trigger.
    
    Args:
        preferences: Loaded preferences dictionary
        trigger: Trigger name (e.g., 'work_log_on_task_completion')
        
    Returns:
        Behavior mode ('auto', 'ask', 'skip') or None if not set
    """
    behaviors = preferences.get("behaviors", {})
    trigger_prefs = behaviors.get(trigger, {})
    return trigger_prefs.get("mode")


def set_behavior_mode(
    project_root: Path,
    trigger: str,
    mode: BehaviorMode,
    learned_from: Optional[str] = None,
) -> dict[str, Any]:
    """Set the behavior mode for a trigger.
    
    Args:
        project_root: Root directory of the project
        trigger: Trigger name
        mode: Behavior mode to set
        learned_from: Optional context about how preference was learned
        
    Returns:
        Updated preferences dictionary
    """
    prefs = load_preferences(project_root)
    now = datetime.now(timezone.utc).isoformat()
    
    # Set learned_at if this is first preference
    if prefs.get("learned_at") is None:
        prefs["learned_at"] = now
    
    # Initialize behaviors if needed
    if "behaviors" not in prefs:
        prefs["behaviors"] = {}
    
    prefs["behaviors"][trigger] = {
        "mode": mode,
        "learned_at": now,
    }
    
    if learned_from:
        prefs["behaviors"][trigger]["learned_from"] = learned_from
    
    save_preferences(project_root, prefs)
    return prefs


def get_communication_preference(
    preferences: dict[str, Any],
    key: str,
) -> Any:
    """Get a communication preference.
    
    Args:
        preferences: Loaded preferences dictionary
        key: Preference key (e.g., 'verbosity', 'use_acronyms')
        
    Returns:
        Preference value or default
    """
    comm = preferences.get("communication", {})
    return comm.get(key, DEFAULT_PREFERENCES["communication"].get(key))


def set_communication_preference(
    project_root: Path,
    key: str,
    value: Any,
    learned_from: Optional[str] = None,
) -> dict[str, Any]:
    """Set a communication preference.
    
    Args:
        project_root: Root directory of the project
        key: Preference key
        value: Preference value
        learned_from: Optional context about how preference was learned
        
    Returns:
        Updated preferences dictionary
    """
    prefs = load_preferences(project_root)
    now = datetime.now(timezone.utc).isoformat()
    
    if prefs.get("learned_at") is None:
        prefs["learned_at"] = now
    
    if "communication" not in prefs:
        prefs["communication"] = DEFAULT_PREFERENCES["communication"].copy()
    
    prefs["communication"][key] = value
    prefs["communication"][f"{key}_learned_at"] = now
    
    if learned_from:
        prefs["communication"][f"{key}_learned_from"] = learned_from
    
    save_preferences(project_root, prefs)
    return prefs


def get_approach(
    preferences: dict[str, Any],
    problem_type: str,
) -> Optional[dict[str, Any]]:
    """Get a committed approach for a problem type.
    
    Args:
        preferences: Loaded preferences dictionary
        problem_type: Type of problem (e.g., 'root_cause_analysis')
        
    Returns:
        Approach dictionary or None if not committed
    """
    approaches = preferences.get("approaches", {})
    return approaches.get(problem_type)


def commit_approach(
    project_root: Path,
    problem_type: str,
    technique: str,
    validated_count: int = 3,
    committed_from: Optional[str] = None,
) -> dict[str, Any]:
    """Commit an approach for a problem type.
    
    Args:
        project_root: Root directory of the project
        problem_type: Type of problem
        technique: Technique description
        validated_count: Number of times validated
        committed_from: Optional context about commitment
        
    Returns:
        Updated preferences dictionary
    """
    prefs = load_preferences(project_root)
    now = datetime.now(timezone.utc).isoformat()
    
    if prefs.get("learned_at") is None:
        prefs["learned_at"] = now
    
    if "approaches" not in prefs:
        prefs["approaches"] = {}
    
    prefs["approaches"][problem_type] = {
        "technique": technique,
        "validated_count": validated_count,
        "committed_at": now,
    }
    
    if committed_from:
        prefs["approaches"][problem_type]["committed_from"] = committed_from
    
    save_preferences(project_root, prefs)
    return prefs


def should_use_acronyms(preferences: dict[str, Any]) -> bool:
    """Check if Pongogo should use acronyms.
    
    Args:
        preferences: Loaded preferences dictionary
        
    Returns:
        True if acronyms should be used
    """
    return get_communication_preference(preferences, "use_acronyms")


def should_use_emojis(preferences: dict[str, Any]) -> bool:
    """Check if Pongogo should use emojis.
    
    Args:
        preferences: Loaded preferences dictionary
        
    Returns:
        True if emojis should be used
    """
    return get_communication_preference(preferences, "use_emojis")


def get_verbosity(preferences: dict[str, Any]) -> Verbosity:
    """Get the verbosity preference.
    
    Args:
        preferences: Loaded preferences dictionary
        
    Returns:
        Verbosity level
    """
    return get_communication_preference(preferences, "verbosity")


def get_tone(preferences: dict[str, Any]) -> Tone:
    """Get the tone preference.
    
    Args:
        preferences: Loaded preferences dictionary
        
    Returns:
        Tone level
    """
    return get_communication_preference(preferences, "tone")


def list_behavior_triggers() -> dict[str, str]:
    """List all known behavior triggers with descriptions.
    
    Returns:
        Dictionary of trigger name to description
    """
    return BEHAVIOR_TRIGGERS.copy()
