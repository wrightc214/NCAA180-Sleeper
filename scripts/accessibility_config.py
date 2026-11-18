"""Validated owner accessibility settings; safe fallbacks if config is missing or partial."""
import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "palettes": {
        "standard": {"light": {"positive": "#1a7f37", "negative": "#b42318", "neutral": "#6b7484"}, "dark": {"positive": "#4fc785", "negative": "#ff7b72", "neutral": "#8a96ab"}},
        "rg": {"light": {"positive": "#0758a8", "negative": "#a65300"}, "dark": {"positive": "#79b9ff", "negative": "#ffb45d"}},
        "by": {"light": {"positive": "#007b73", "negative": "#b42318"}, "dark": {"positive": "#65d4c6", "negative": "#ff7b72"}},
        "none": {"light": {"positive": "#252525", "negative": "#595959"}, "dark": {"positive": "#f2f2f2", "negative": "#c5c5c5"}},
    },
    "appearance": {
        "soft": {"light": {"positive": "#e3f3e8", "negative": "#fbe4e1"}, "dark": {"positive": "#173a2a", "negative": "#4a2024"}},
        "alternate_soft": {"light": {"positive": "#e9eef2", "negative": "#f1edf0"}, "dark": {"positive": "#26313a", "negative": "#342c32"}},
        "fill_text": "#ffffff",
        "monochrome_fills": {"positive": "#3c3c3c", "negative": "#656565"},
    },
    "contrast": {"minimum_ratio": 4.5, "distinguishability_ratio": 1.5, "light_background": "#ffffff", "dark_background": "#171b22"},
    "defaults": {"mode": "standard", "motion": "system", "emphasis": False, "auto_contrast": True},
    "labels": {
        "auto_contrast": "Automatically improve contrast",
        "low_light": "Selected colours may be difficult to read on light backgrounds.",
        "low_dark": "Selected colours may be difficult to read on dark backgrounds.",
        "low_fill": "White text on solid fills may be difficult to read.",
        "similar": "Positive and negative colours may be difficult to distinguish; automatic contrast correction cannot guarantee distinguishability.",
    },
}

def _merge(default, override):
    if isinstance(default, dict):
        override = override if isinstance(override, dict) else {}
        return {k: _merge(v, override.get(k)) for k, v in default.items()}
    if isinstance(default, str):
        if default.startswith("#"):
            return override if isinstance(override, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", override) else default
        return override if isinstance(override, str) and override.strip() else default
    if isinstance(default, bool):
        return override if isinstance(override, bool) else default
    if isinstance(default, (float, int)):
        return override if isinstance(override, (float, int)) and not isinstance(override, bool) and 1 <= override <= 21 else default
    return deepcopy(default)

def accessibility_config(path=None):
    path = Path(path) if path is not None else ROOT / "config" / "accessibility.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    result = _merge(DEFAULTS, raw)
    if result["defaults"]["mode"] not in ("standard", "rg", "by", "none", "custom"):
        result["defaults"]["mode"] = "standard"
    if result["defaults"]["motion"] not in ("system", "on", "off"):
        result["defaults"]["motion"] = "system"
    return result
