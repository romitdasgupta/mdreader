"""Small, optional preferences stored independently of reader documents."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


DEFAULTS = {
    "theme": "light",
    "width": 1120,
    "height": 800,
    "outline": True,
    "zoom": 1.0,
    "last_directory": "",
}


def settings_path() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    directory = Path(root) if root and Path(root).is_absolute() else Path.home() / ".config"
    return directory / "folio" / "settings.json"


def load_settings(path: Path | None = None) -> dict:
    """Return validated values; corrupt or unavailable settings are harmless."""
    result = DEFAULTS.copy()
    try:
        values = json.loads((path or settings_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return result
    if not isinstance(values, dict):
        return result
    if values.get("theme") in ("light", "dark"):
        result["theme"] = values["theme"]
    for key, low, high in (("width", 640, 3840), ("height", 480, 2160)):
        value = values.get(key)
        if type(value) is int and low <= value <= high:
            result[key] = value
    if isinstance(values.get("outline"), bool):
        result["outline"] = values["outline"]
    zoom = values.get("zoom")
    if type(zoom) in (int, float) and 0.6 <= zoom <= 2.4:
        result["zoom"] = float(zoom)
    if isinstance(values.get("last_directory"), str):
        result["last_directory"] = values["last_directory"]
    return result


def save_settings(values: dict, path: Path | None = None) -> bool:
    """Atomically replace preferences, without making failures user-visible."""
    destination = path or settings_path()
    temporary = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=".settings-", suffix=".json", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump({key: values.get(key, value) for key, value in DEFAULTS.items()}, stream, indent=2)
            stream.write("\n")
        temporary.replace(destination)
        return True
    except (OSError, ValueError, TypeError):
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
