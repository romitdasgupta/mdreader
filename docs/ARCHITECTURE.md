# Architecture

Folio uses Python 3.11+, PyGObject, GTK 3, WebKitGTK 4.1 and markdown-it-py.
GTK provides the desktop controls; WebKit renders an inert HTML document produced
by the Markdown parser. The application runs locally without an application server.

## Module boundaries

| Area | Files | Responsibility |
| --- | --- | --- |
| Document | `folio/document.py`, `folio/resources/reader.css` | File loading, Markdown parsing, safe HTML, headings and statistics |
| Window | `folio/window.py`, `folio/resources/gtk.css` | Native controls, rendering, navigation, search and reload |
| Lifecycle | `folio/app.py`, `folio/__main__.py` | Command line and GTK application lifecycle |
| Preferences | `folio/settings.py` | Validated settings, XDG paths and atomic persistence |
| Distribution | `pyproject.toml`, `packaging/flatpak/`, `data/`, `scripts/` | Python package, Flatpak, desktop metadata and installation |
| Verification | `tests/`, `scripts/smoke_gui.py`, `scripts/verify_package.py` | Core contracts and installed application checks |

`document.py` and `settings.py` run without `gi` or a display. The window consumes
the renderer's result and does not implement another Markdown parser. GTK widgets
and their callbacks belong on the GTK thread.

## Document contract

```python
def render_markdown(source: str, *, source_path: Path | None = None,
                    theme: str = "light") -> RenderedDocument: ...
def load_document(path: str | Path, *, theme: str = "light") -> RenderedDocument: ...
```

`RenderedDocument` is an immutable value containing `title`, complete `html`,
`headings`, `word_count`, `reading_minutes`, resolved `path` and `source_text`.
Each immutable `Heading` contains its `level`, plain-text `title` and `anchor`.
Themes are `light` and `dark`.

`load_document` accepts UTF-8, including a BOM, up to 10 MiB. Missing, unreadable,
non-file and invalid UTF-8 inputs raise `DocumentError`. Reading and reloading
never modify the source. The title comes from the first level-one heading, then
the filename stem, then `Untitled`.

Heading IDs are deterministic, unique and prefixed with `heading-`. A global set
and per-base suffix counters handle repeated headings and literal numeric suffix
collisions without repeatedly scanning from the first suffix. Reading statistics
are computed without a browser, with an estimate of 220 words per minute and zero
minutes for empty input.

## Content isolation

Markdown and linked files are untrusted input. Raw HTML is escaped, attributes
are escaped, and the generated page has a restrictive content security policy.
Supported Markdown includes fenced code, tables, task lists and strikethrough.

Local PNG, JPEG, GIF and WebP images are recognized by their bytes, restricted to
the document's resolved directory tree and embedded as data URIs. Limits are
5 MiB per image and 20 MiB of image bytes per document. Unsupported, missing or
blocked images produce readable fallback text. Remote images, SVG and image data
URIs supplied by Markdown are not loaded.

WebKit permits trusted `evaluate_javascript` calls for navigation and scroll
restoration. JavaScript markup is separately disabled, and CSP blocks document
scripts. Keep these controls separate: disabling all JavaScript also breaks
trusted application operations. Never interpolate document text into executable
JavaScript; serialize values where needed.

Navigation checks keep heading fragments in the reader and open supported local
Markdown/text links through the document loader. Explicit HTTP, HTTPS and mailto
clicks use the desktop handler. Other schemes, popups and unrelated navigation
are blocked. Opening a document never fetches remote resources. The HTML base URI
is the document directory with a trailing slash; embedded images avoid dependence
on WebKit's file-resource access.

## Native behavior and state

`Gtk.Application` uses `HANDLES_OPEN` and one reader window. Its application ID,
desktop entry and icon use `io.github.romitdasgupta.mdreader`. GTK provides the
outline, controls, chooser and status line. WebKit provides document layout,
selection, scrolling and the find controller.

The open action uses `Gtk.FileChooserDialog` to retain the original file path.
A portal's individual-file export can hide sibling images and linked documents,
and interfere with directory monitoring. The GTK chooser works with the Flatpak's
read-only filesystem access while preserving those document relationships.

Opening or reloading prepares a replacement before discarding the current page.
Failures leave the last readable page visible and show a nonfatal error. Gio
monitors the document's parent directory so atomic saves remain observable;
events are debounced for 400 milliseconds. Reload preserves reading position and
focus where feasible. Closing the window disconnects monitors and removes timers.

Preferences store theme, size, outline visibility, zoom and the last directory in
`$XDG_CONFIG_HOME/folio/settings.json`, falling back to `~/.config/folio/settings.json`.
Invalid values use defaults. Writes use atomic replacement, and save failures do
not prevent reading. Flatpak supplies an application-private XDG configuration
directory, separate from source installations.

## Distribution and verification

The consumer package is a Flatpak using GNOME Platform 50 for Python, PyGObject,
GTK 3 and WebKitGTK 4.1. The manifest bundles hash-pinned markdown-it-py and mdurl;
the SDK and setuptools are build dependencies. Read-only host filesystem access
supports sibling resources and directory monitoring. The sandbox has no network
permission and retains Flatpak's reserved-path restrictions.

Python wheels include the application and its CSS, and declare markdown-it-py as
a dependency. Source and wheel installations obtain native libraries from system
packages. A Python package installation alone does not supply the desktop stack.

Core tests exercise renderer, settings and installer contracts. GUI smoke checks
exercise a real GTK/WebKit window, including chooser paths, images, search,
navigation, reload and source preservation. Installed-package checks run outside
the checkout and reject source imports; Flatpak checks run against the Platform
runtime. Screenshots support visual review. An unavailable display is a blocked
check, not a pass.

See [development setup](../README.md#development-and-contributing),
[distribution](DISTRIBUTION.md) and [release verification](RELEASE.md) for commands.
