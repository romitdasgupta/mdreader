"""Local upgrades replace the desktop identity without touching user settings."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.romitdasgupta.mdreader"
LEGACY_ID = "io.github.folio.Reader"


@pytest.fixture
def installation(tmp_path):
    prefix = tmp_path / "Local applications café"
    config = tmp_path / "config"
    preferences = config / "folio/settings.json"
    preferences.parent.mkdir(parents=True)
    preferences.write_bytes(b'{"theme": "dark", "zoom": 1.25}\n')
    associations = config / "mimeapps.list"
    associations.write_bytes(b"[Default Applications]\ntext/markdown=another-reader.desktop;\n")
    environment = {
        key: value for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME")
    }
    environment.update(XDG_CONFIG_HOME=str(config), XDG_CACHE_HOME=str(tmp_path / "cache"))
    preserved = {path: path.read_bytes() for path in (preferences, associations)}

    def run(*arguments):
        return subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts/install_local.py"),
             "--prefix", str(prefix), *arguments],
            cwd=tmp_path, env=environment, check=True, capture_output=True, text=True,
        )

    return prefix, environment, preserved, run


def desktop_files(prefix, app_id):
    return (
        prefix / f"share/applications/{app_id}.desktop",
        prefix / f"share/icons/hicolor/scalable/apps/{app_id}.svg",
    )


def seed_legacy_identity(prefix):
    for path in desktop_files(prefix, LEGACY_ID):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Legacy Folio desktop asset\n")


def test_upgrade_replaces_legacy_identity_and_launches_outside_checkout(installation, tmp_path):
    prefix, environment, preserved, install = installation
    seed_legacy_identity(prefix)

    install()

    assert all(not path.exists() for path in desktop_files(prefix, LEGACY_ID))
    assert all(path.is_file() for path in desktop_files(prefix, APP_ID))
    result = subprocess.run(
        [str(prefix / "bin/folio"), "--version"],
        cwd=tmp_path, env=environment, check=True, capture_output=True, text=True,
    )
    assert result.stdout.startswith("Folio ")
    # Exercise the copied package and its CSS without a checkout import or display.
    probe = """
from pathlib import Path
import sys
installed = Path(sys.argv[1])
sys.path.insert(0, str(installed))
import folio
from folio.document import render_markdown
assert Path(folio.__file__).resolve().is_relative_to(installed)
document = render_markdown('# Locally installed\\n\\n**Readable.**')
assert document.title == 'Locally installed'
assert '<strong>Readable.</strong>' in document.html
assert (installed / 'folio/resources/gtk.css').read_text().strip()
"""
    subprocess.run(
        [sys.executable, "-I", "-c", probe, str(prefix / "share/folio-reader")],
        cwd=tmp_path, env=environment, check=True,
    )
    assert all(path.read_bytes() == contents for path, contents in preserved.items())


def test_uninstall_removes_both_identities_and_preserves_settings(installation):
    prefix, _environment, preserved, install = installation
    install()
    seed_legacy_identity(prefix)
    unrelated = prefix / "share/applications/another-reader.desktop"
    unrelated.write_text("Unrelated application\n")

    install("--uninstall")
    # Uninstall is safe to repeat after the application is already absent.
    install("--uninstall")

    assert not (prefix / "bin/folio").exists()
    assert not (prefix / "share/folio-reader").exists()
    for app_id in (APP_ID, LEGACY_ID):
        assert all(not path.exists() for path in desktop_files(prefix, app_id))
    assert unrelated.read_text() == "Unrelated application\n"
    assert all(path.read_bytes() == contents for path, contents in preserved.items())
