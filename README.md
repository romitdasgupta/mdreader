# Folio

A quiet, native Linux reader for Markdown. GTK provides the desktop interface; WebKitGTK typesets the document. Everything runs locally.

Folio opens local Markdown files with a heading outline, in-document search, light and dark themes, adjustable text size, and automatic reload. It supports tables, task lists, fenced code, and local images. Reading never modifies your source files.

## Install

Download `folio-0.1.0-x86_64.flatpak` from [GitHub Releases](https://github.com/romitdasgupta/mdreader/releases/latest). The initial binary release supports x86-64 Linux desktops with Flatpak. It includes Folio's Python packages and automatically installs the shared GNOME runtime containing Python, GTK and WebKitGTK.

If Flatpak is not installed, follow [the setup instructions for your distribution](https://flatpak.org/setup/). On Ubuntu, install it with `sudo apt install flatpak`; log out and back in after first setting up Flatpak so desktop launchers appear.

From the directory containing the download:

```sh
flatpak install --user ./folio-0.1.0-x86_64.flatpak
flatpak run io.github.romitdasgupta.mdreader
```

Accept the runtime installation when prompted. The first install needs internet access and may download several hundred megabytes; shared runtimes are reused by other applications. Launch **Folio** from your application menu or choose it in your file manager's **Open With** menu. It does not change your default file associations.

To open a document from a terminal:

```sh
flatpak run io.github.romitdasgupta.mdreader /absolute/path/to/document.md
```

The sandbox has read-only access to host files so nearby images, relative document links and automatic reload work. It has no network permission. Preferences stay in Flatpak's private application directory. This is an online installer, not an offline bundle of the runtime.

For a new Folio version, download its bundle and run `flatpak install --user ./<new-bundle>.flatpak` again. `flatpak update --user` updates shared runtimes; this direct-download channel does not provide automatic Folio updates. Uninstall with `flatpak uninstall --user io.github.romitdasgupta.mdreader`; documents and preferences are preserved unless you explicitly request deletion of application data.

Folio is distributed directly through GitHub, and is not currently listed on Flathub. See [distribution and release instructions](docs/DISTRIBUTION.md) for building and checking a release.

## Run from source

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

### Source install with desktop integration

After installing the source dependencies above, install a copy of the application, an icon, and a desktop launcher in `~/.local`:

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

A source-tree run cannot verify wheel contents. This builds the source archive and
wheel, installs into a disposable environment, and checks the package outside the
checkout. Add `--gui` on a graphical desktop to run the full installed GTK/WebKit
smoke suite; screenshots go under `artifacts/package/`.

```sh
.venv/bin/python scripts/verify_package.py --gui
```

Omit `--gui` for headless package verification. `scripts/smoke_gui.py` normally tests
the checkout; `--installed` deliberately tests the installed distribution and rejects
an editable/source import. Test `scripts/install_local.py` only with a disposable
`--prefix`. The consumer Flatpak has a separate [build and verification recipe](docs/DISTRIBUTION.md).

Built by the requested team roles: two coders, two testers, two PMs, a Steve Jobs-inspired product perspective, and a Linus Torvalds-inspired architecture perspective. These are assigned agent roles, not endorsements by those people.

MIT licensed. This is the initial 0.1 release.
