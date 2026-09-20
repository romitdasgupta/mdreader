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

```sh
source .venv/bin/activate            # After the development setup above
python3 -m pytest -q                 # Core and regression tests
python3 scripts/smoke_gui.py         # Real GTK/WebKit checks; needs a display
python3 -m build --no-isolation      # Wheel and source archive in dist/
```

The document parser is independent of GTK. The UI consumes a rendered document, outline, and statistics from that module. See [architecture](docs/ARCHITECTURE.md), [product decisions](docs/PRODUCT.md), [acceptance criteria](docs/ACCEPTANCE.md), and [release verification](docs/RELEASE.md).

Built by the requested team roles: two coders, two testers, two PMs, a Steve Jobs-inspired product perspective, and a Linus Torvalds-inspired architecture perspective. These are assigned agent roles, not endorsements by those people.

MIT licensed. This is an initial 0.1 release; distribution packages and Flatpak are future work.
