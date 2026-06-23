"""
Feature Flags Configuration
===============================================================================
Controls which features are enabled/disabled
===============================================================================
"""

import os
import json
from pathlib import Path


class FeatureFlags:
    DEFAULT_FLAGS = {
        # Core logging
        "LOGGING_V2_ENABLED": False,
        "LOGGING_V2_AUDIT_ENABLED": False,
        # Growth engine
        "GROWTH_ENGINE_ENABLED": False,
        "GROWTH_AUTO_ANALYZE": False,  # Auto-run analysis periodically
        "GROWTH_AUTO_INSIGHT": False,  # Auto-generate insights
        "GROWTH_REQUIRE_APPROVAL": True,  # Require Drew approval for KB updates
        # Debug
        "LOGGING_V2_DEBUG_PRINT": False,
    }

    def __init__(self):
        self.config_file = Path.home() / ".drewgent" / "feature_flags.json"
        self._flags = {}
        self._load()

    def _load(self):
        self._flags = self.DEFAULT_FLAGS.copy()

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self._flags.update(json.load(f))
            except:
                pass

        # Override with environment variables
        for key in self.DEFAULT_FLAGS:
            env_val = os.environ.get(key)
            if env_val is not None:
                if isinstance(self.DEFAULT_FLAGS[key], bool):
                    self._flags[key] = env_val.lower() in ("true", "1", "yes")
                elif isinstance(self.DEFAULT_FLAGS[key], int):
                    self._flags[key] = int(env_val)
                else:
                    self._flags[key] = env_val

    def save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self._flags, f, indent=2)

    def get(self, key: str, default=None):
        return self._flags.get(key, default)

    def set(self, key: str, value):
        if key not in self.DEFAULT_FLAGS:
            raise ValueError(f"Unknown flag: {key}")
        self._flags[key] = value

    def enable(self, key: str):
        self.set(key, True)

    def disable(self, key: str):
        self.set(key, False)

    def __getattr__(self, key: str):
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self.get(key, self.DEFAULT_FLAGS.get(key))

    def __repr__(self):
        enabled = [k for k, v in self._flags.items() if v]
        disabled = [k for k, v in self._flags.items() if not v]
        return f"FeatureFlags(enabled={enabled})"


flags = FeatureFlags()


def is_enabled(flag: str) -> bool:
    return flags.get(flag, False)
