"""Preferences must remain optional even when their file is unavailable or corrupt."""

import json
from pathlib import Path

import pytest

from folio.settings import DEFAULTS, load_settings, save_settings, settings_path


def test_settings_path_obeys_absolute_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom settings"))
    assert settings_path() == tmp_path / "custom settings" / "folio" / "settings.json"


@pytest.mark.parametrize("xdg", [None, "", "relative/config"])
def test_settings_path_falls_back_to_home(monkeypatch, tmp_path, xdg):
    monkeypatch.setenv("HOME", str(tmp_path))
    if xdg is None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", xdg)
    assert settings_path() == tmp_path / ".config" / "folio" / "settings.json"


@pytest.mark.parametrize("contents", [b"{not valid JSON", b"[]", b"null", b'"text"', b"42", b"\xff\xfe"])
def test_unusable_preferences_fall_back_to_defaults(tmp_path, contents):
    path = tmp_path / "settings.json"
    path.write_bytes(contents)
    assert load_settings(path) == DEFAULTS


def test_missing_settings_and_directory_path_are_harmless(tmp_path):
    assert load_settings(tmp_path / "missing.json") == DEFAULTS
    assert load_settings(tmp_path) == DEFAULTS


def test_default_result_is_independent_of_other_loads(tmp_path):
    first = load_settings(tmp_path / "missing.json")
    first["theme"] = "dark"
    assert load_settings(tmp_path / "missing.json")["theme"] == "light"


def test_valid_preferences_round_trip_and_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "new folder" / "settings.json"
    values = {"theme": "dark", "width": 900, "height": 650, "outline": False, "zoom": 1.25, "last_directory": "/home/reader/Notes café"}
    assert save_settings({**values, "unrelated": "ignored"}, path)
    assert load_settings(path) == values
    assert json.loads(path.read_text()) == values
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("values", [
    {"theme": "invalid", "width": 639, "height": 479, "outline": "false", "zoom": 0.59, "last_directory": []},
    {"theme": [], "width": 3841, "height": 2161, "outline": 1, "zoom": 2.41, "last_directory": 42},
    {"width": True, "height": 800.0, "zoom": True},
    {"width": "1000", "height": "800", "zoom": "1.5"},
    {"zoom": float("nan")},
    {"zoom": float("inf")},
])
def test_invalid_values_do_not_reach_window_or_zoom(values, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(values))
    assert load_settings(path) == DEFAULTS


@pytest.mark.parametrize("width,height,zoom", [(640, 480, 0.6), (3840, 2160, 2.4)])
def test_supported_preference_boundaries_are_accepted(tmp_path, width, height, zoom):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"width": width, "height": height, "zoom": zoom}))
    values = load_settings(path)
    assert (values["width"], values["height"], values["zoom"]) == (width, height, zoom)


def test_unavailable_config_parent_does_not_prevent_reading(tmp_path):
    parent = tmp_path / "regular-file"
    parent.write_text("occupied")
    path = parent / "settings.json"
    assert save_settings(DEFAULTS, path) is False
    assert load_settings(path) == DEFAULTS
    assert parent.read_text() == "occupied"


def test_failed_atomic_replace_preserves_existing_preferences(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    assert save_settings({**DEFAULTS, "theme": "dark"}, path)
    before = path.read_bytes()

    def denied_replace(self, target):
        raise PermissionError("Read-only settings destination")

    monkeypatch.setattr(Path, "replace", denied_replace)
    assert save_settings(DEFAULTS, path) is False
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_failed_serialization_preserves_existing_preferences(tmp_path):
    path = tmp_path / "settings.json"
    assert save_settings(DEFAULTS, path)
    before = path.read_bytes()
    assert save_settings({"theme": object()}, path) is False
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
