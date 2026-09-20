# Folio

A quiet, native Linux reader for Markdown. GTK provides the desktop interface; WebKitGTK typesets the document. Everything runs locally.

Folio opens local Markdown files with a heading outline, in-document search, light and dark themes, adjustable text size, and automatic reload. It supports tables, task lists, fenced code, and local images. Reading never modifies your source files.

## Run

On this workspace's Linux desktop, the dependencies are already installed:

```sh
./bin/folio examples/welcome.md
```

Or launch the empty reader with `python3 -m folio`. Use `Ctrl+O` or drop a Markdown file into the window to open a document.

### Dependencies on a fresh system

Python 3.11 or newer, PyGObject, GTK 3, WebKitGTK 4.1, and markdown-it-py are required. On Debian/Ubuntu:

```sh
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 python3-markdown-it
/usr/bin/python3 -m folio examples/welcome.md
```

Run that command from this checkout. GTK needs a running graphical Linux desktop. If your `python3` comes from a custom Python installation or virtual environment, use `/usr/bin/python3` so it can find the distro's GTK bindings.

For Python development or a wheel installation, retain access to the system bindings:

```sh
sudo apt install python3-venv
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/folio examples/welcome.md
```

Installing the Python package alone does not install GTK or WebKitGTK.

## Desktop integration

Install a copy of the application, an icon, and a desktop launcher in `~/.local`:

```sh
/usr/bin/python3 scripts/install_local.py
```

Launch **Folio** from your desktop menu, select it with your file manager's **Open With**, or use `~/.local/bin/folio file.md`. The installer does not change your default file associations. Rerun it after updating the source checkout. Uninstall with `python3 scripts/install_local.py --uninstall`; preferences are preserved.

## Reading

| Action | Shortcut |
| --- | --- |
| Open a file | Ctrl+O |
| Find text | Ctrl+F |
| Next / previous result | Enter / Shift+Enter in search |
| Dismiss search | Escape |
| Reload | Ctrl+R |
| Increase / decrease text size | Ctrl++ / Ctrl+− |
| Reset text size | Ctrl+0 |

Use the header controls to toggle the outline or theme. Documents are UTF-8, including UTF-8 with a BOM, up to 10 MiB. Theme and window preferences are saved under `$XDG_CONFIG_HOME/folio` or `~/.config/folio`.

Local Markdown links open in Folio. Web and email links open in the desktop's default handler only when clicked. Raw HTML is displayed as text, remote images are blocked, and supported local images are embedded from the document's directory tree. Images outside that tree are deliberately unavailable. Folio has no editor, cloud account, telemetry, or server.

## Development

Agents and contributors should start with [AGENTS.md](AGENTS.md) for the module
map, development boundaries, and checks appropriate to a change. [AGENT.md](AGENT.md)
is an alternate entry point to the same guide.

```sh
source .venv/bin/activate            # After the development setup above
python3 -m pytest -q                 # Core and regression tests
python3 scripts/smoke_gui.py         # Real GTK/WebKit checks; needs a display
python3 -m build --no-isolation      # Wheel and source archive in dist/
```

The document parser is independent of GTK. The UI consumes a rendered document, outline, and statistics from that module. See [architecture](docs/ARCHITECTURE.md), [product decisions](docs/PRODUCT.md), [acceptance criteria](docs/ACCEPTANCE.md), and [release verification](docs/RELEASE.md).

If `python3 -m build` reports a missing module (including `build.__main__`), use
the development venv after installing `.[dev]`; the system Python can have GTK
without the Python build frontend. For example, run
`make PYTHON=.venv/bin/python build`. Install distro prerequisites as needed;
this workspace's dependencies are not a guarantee about a fresh machine.

### Package verification

A source-tree run cannot verify wheel contents. Install the built wheel in a fresh
environment and check it outside the checkout. `scripts/smoke_gui.py` inserts the
source checkout into Python's path, so using an installed interpreter to run that
script still tests the source. The following recipe verifies the installed package.

Run from the repository root after the development setup above. It builds into a
temporary directory, checks the wheel, then removes the temporary environment:

```sh
.venv/bin/python - <<'PY'
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix="folio-package-") as directory:
    check = Path(directory)
    subprocess.run([sys.executable, "-m", "build", "--no-isolation",
                    "--outdir", str(check / "dist")], check=True)
    subprocess.run(["/usr/bin/python3", "-m", "venv", "--system-site-packages",
                    str(check / "env")], check=True)
    python = str(check / "env/bin/python")
    wheel = next((check / "dist").glob("*.whl"))
    subprocess.run([python, "-m", "pip", "install", str(wheel)], check=True)
    probe = """
import sys
from pathlib import Path
from importlib.resources import files
import folio
from folio.document import render_markdown
assert Path(folio.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
for name in ('reader.css', 'gtk.css'):
    assert files('folio').joinpath('resources', name).read_text().strip()
assert render_markdown('# Installed').title == 'Installed'
print('Installed package, resources and renderer verified outside the checkout.')
"""
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    subprocess.run([python, "-I", "-c", probe], cwd=check, env=environment, check=True)
    subprocess.run([str(check / "env/bin/folio"), "--version"],
                   cwd=check, env=environment, check=True)
PY
```

This is a headless package check, not proof of a native launch. For native changes,
also open a sample with the installed launcher on a display before removing that
environment, using temporary absolute `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` paths.
Test `scripts/install_local.py` with `--prefix` pointing to a temporary directory;
check the generated launcher from another working directory and exercise uninstall.

Built by the requested team roles: two coders, two testers, two PMs, a Steve Jobs-inspired product perspective, and a Linus Torvalds-inspired architecture perspective. These are assigned agent roles, not endorsements by those people.

MIT licensed. This is an initial 0.1 release; distribution packages and Flatpak are future work.
