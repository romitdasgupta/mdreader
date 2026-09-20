#!/usr/bin/env python3
"""Install a self-contained source copy and desktop entry under a local prefix."""
import argparse
from pathlib import Path
import shlex
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    prefix = args.prefix.expanduser().resolve()
    root = Path(__file__).resolve().parent.parent
    app = prefix / "share/folio-reader"
    launcher = prefix / "bin/folio"
    desktop = prefix / "share/applications/io.github.romitdasgupta.mdreader.desktop"
    icon = prefix / "share/icons/hicolor/scalable/apps/io.github.romitdasgupta.mdreader.svg"
    # Remove the initial source install's old identity when upgrading/uninstalling.
    for old in ("applications/io.github.folio.Reader.desktop",
                "icons/hicolor/scalable/apps/io.github.folio.Reader.svg"):
        (prefix / "share" / old).unlink(missing_ok=True)
    if args.uninstall:
        for path in (launcher, desktop, icon):
            path.unlink(missing_ok=True)
        if app.exists():
            shutil.rmtree(app)
        print(f"Uninstalled Folio from {prefix}. Preferences were preserved.")
        return
    for path in (launcher, desktop, icon):
        path.parent.mkdir(parents=True, exist_ok=True)
    app.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "folio", app / "folio", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(root / "examples", app / "examples", dirs_exist_ok=True)
    shutil.copy2(root / "LICENSE", app / "LICENSE")
    # Keep the caller's working directory so relative document paths still work.
    (app / "launch.py").write_text(
        "from folio.app import main\nraise SystemExit(main())\n"
    )
    # Pin the interpreter used to install: it already has the required bindings.
    launcher.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
                        + shlex.quote(str(app / "launch.py")) + " \"$@\"\n")
    launcher.chmod(0o755)
    # Desktop Exec has its own quoting rules, unlike a shell command.
    escaped = str(launcher).replace("\\", "\\\\\\\\").replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop.write_text((root / "data/io.github.romitdasgupta.mdreader.desktop").read_text()
                       .replace("Exec=folio %f", f'Exec="{escaped}" %f'))
    shutil.copy2(root / "data/icons/io.github.romitdasgupta.mdreader.svg", icon)
    print(f"Installed Folio. Launch with {launcher} or your desktop application menu.")


if __name__ == "__main__":
    main()
