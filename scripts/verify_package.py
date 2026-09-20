#!/usr/bin/env python3
"""Build and verify Folio's installed wheel outside the source checkout.

Run with the development interpreter; add --gui for the full GTK/WebKit smoke.
The disposable environment retains system packages for distro GTK bindings.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]

PROBE = """
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path
import sys
import folio
from folio.document import render_markdown

package = Path(folio.__file__).resolve()
assert package.is_relative_to(Path(sys.prefix).resolve()), package
installed = distribution('folio-reader')
assert package == Path(installed.locate_file('folio/__init__.py')).resolve()
assert installed.version == folio.__version__
for name in ('reader.css', 'gtk.css'):
    assert files('folio').joinpath('resources', name).read_text().strip(), name
document = render_markdown('# Installed\\n\\nA **packaged** reader.')
assert document.title == 'Installed'
assert '<strong>packaged</strong>' in document.html
print(f'PASS: installed package, resources and renderer: {package}')
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="verify an existing wheel instead of building")
    parser.add_argument("--gui", action="store_true", help="also run installed GTK/WebKit checks")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts/package")
    args = parser.parse_args()
    wheel = args.wheel.expanduser().resolve() if args.wheel else None
    artifacts = args.artifacts.expanduser().resolve()
    environment = {
        key: value for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME")
    }
    with tempfile.TemporaryDirectory(prefix="folio-package-") as directory:
        temporary = Path(directory)
        environment["XDG_CONFIG_HOME"] = str(temporary / "config")
        environment["XDG_CACHE_HOME"] = str(temporary / "cache")
        if wheel is None:
            subprocess.run(
                [sys.executable, "-m", "build", "--no-isolation", "--outdir",
                 str(temporary / "dist"), str(ROOT)],
                cwd=temporary, env=environment, check=True,
            )
            wheel, = (temporary / "dist").glob("*.whl")
        venv.EnvBuilder(system_site_packages=True, with_pip=True).create(temporary / "env")
        python = str(temporary / "env/bin/python")
        subprocess.run(
            [python, "-I", "-m", "pip", "install", "--disable-pip-version-check", str(wheel)],
            cwd=temporary, env=environment, check=True,
        )
        subprocess.run(
            [python, "-I", "-c", PROBE], cwd=temporary, env=environment, check=True,
        )
        subprocess.run(
            [str(temporary / "env/bin/folio"), "--version"],
            cwd=temporary, env=environment, check=True,
        )
        if args.gui:
            result = subprocess.run(
                [python, "-I", str(ROOT / "scripts/smoke_gui.py"), "--installed",
                 "--artifacts", str(artifacts)],
                cwd=temporary, env=environment,
            )
            return result.returncode
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: package verification command exited {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)
