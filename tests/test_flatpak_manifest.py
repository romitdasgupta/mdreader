"""Flatpak defaults keep the WebKitGTK Wayland renderer usable."""

import json
from pathlib import Path


MANIFEST = Path(__file__).parents[1] / "packaging/flatpak/io.github.romitdasgupta.mdreader.json"


def test_flatpak_disables_problematic_webkit_dmabuf_wayland_path():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "--env=WEBKIT_DISABLE_DMABUF_RENDERER=1" in manifest["finish-args"]
