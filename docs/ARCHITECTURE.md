# Folio architecture

Decision: use Python 3.11+, PyGObject, GTK 3, WebKitGTK 4.1, and
markdown-it-py. Folio is a native GTK desktop application with a WebKit document
surface. There is no application server, Electron runtime, or JavaScript build.

This decision follows the requested Linus Torvalds-inspired architecture review:
choose a small implementation with an explicit boundary and dependencies that
actually run on the target machine. It does not claim endorsement by him.

## Environment evidence

The project machine has Python 3.14.4, PyGObject, GTK 3, WebKit2 4.1,
markdown-it-py, and pytest. Importing GTK 3 and WebKit2 4.1 in a fresh process
succeeds. GTK 4 and libadwaita are installed, but the corresponding WebKit 6
namespace is absent. GTK 3 avoids replacing the installed rendering stack.
A graphical GNOME session is available for real application smoke tests.

## Module boundary and ownership

| Owner | Files | Responsibility |
| --- | --- | --- |
| Core coder | `folio/document.py`, `folio/resources/reader.css` | Read Markdown, produce a complete safe HTML document, heading outline and statistics |
| Native UI coder | `folio/app.py`, `folio/window.py`, `folio/settings.py`, `folio/__main__.py` | GTK application lifecycle, native controls, rendering view, search, reload, preferences |
| Integrator | `folio/__init__.py`, `pyproject.toml`, `bin/folio`, desktop/icon assets, README and examples | Installation, launchers, packaging, end-to-end assembly |
| Testers | `tests/` | Core behavior, hostile inputs, native UI smoke and regression tests |

The core never imports `gi`; core tests run without a graphical display. The UI
depends on the core's public types and functions, and does not parse Markdown.
The initial core coder may add `tests/test_document.py`; coordinate before a
tester edits the same file.

## Exact core API

```python
from dataclasses import dataclass
from pathlib import Path

class DocumentError(Exception):
    """A user-presentable failure to read or prepare a document."""

@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    anchor: str

@dataclass(frozen=True)
class RenderedDocument:
    title: str
    html: str
    headings: tuple[Heading, ...]
    word_count: int
    reading_minutes: int
    path: Path | None
    source_text: str

def render_markdown(
    source: str,
    *,
    source_path: Path | None = None,
    theme: str = "light",
) -> RenderedDocument: ...

def load_document(
    path: str | Path,
    *,
    theme: str = "light",
) -> RenderedDocument: ...
```

`theme` accepts `light` and `dark`. `load_document` resolves the source path,
accepts UTF-8 including a BOM, rejects input above 10 MiB, and turns missing,
unreadable, non-file and decode failures into `DocumentError`. It does not mutate
the source file. The title is the first level-one heading, then the filename
stem, then `Untitled`. Outline titles are plain text. Anchor IDs are deterministic,
unique and prefixed with `heading-`; repeated headings receive numeric suffixes.

`html` contains a complete document, embedded packaged stylesheet and the chosen
theme. Core supports CommonMark-style Markdown with raw HTML disabled, fenced
code, tables and strikethrough. Word count reflects readable text. Estimated
reading time is zero for an empty document, otherwise at least one minute at
roughly 220 words per minute. These metadata values must not require a browser.

## Rendering and resource policy

Markdown is input data. Explicitly configure `html=False`; markdown-it-py's
CommonMark preset otherwise permits raw HTML. Heading anchors and attribute
values are escaped. Do not introduce plugins that emit arbitrary HTML.

Links retain same-document fragments, relative local paths, HTTP, HTTPS and
mailto destinations. Reject other explicit schemes. When embedding supported
local images, resolve against the document parent, require the resolved target
to remain inside that directory tree, cap individual asset sizes, and emit data
URIs. Missing, blocked and unsupported images should have readable fallback text.
Remote images are not fetched automatically. Raster PNG/JPEG/GIF/WebP support is
required; SVG support is optional and must not introduce executable markup.

Use a content security policy allowing only the inline packaged styles and
embedded image data needed by the reader. Document HTML contains no scripts,
iframes or remote styles/fonts. The UI may evaluate small trusted scripts for
anchor navigation, theme application and scroll restoration; never interpolate
Markdown text into JavaScript. Serialize strings with JSON when needed.

Use WebKit's navigation policy to keep fragment navigation in the reader, open
local Markdown links through `load_document`, and dispatch explicit HTTP/HTTPS/
mailto clicks to the desktop URI handler. Block unrelated navigation and popup
windows. Handle URL decoding and fragments before constructing filesystem paths.
Do not launch arbitrary executable files or arbitrary URI schemes.

WebKit `load_html` resolves relative resources against its base URI and restricts
absolute file resources outside that base. Embedded images remove this coupling.
Set the base URI to the document directory URI with a trailing slash when a path
exists. The UI must not accidentally navigate the rendering surface to a website.

## Native application behavior

Use `Gtk.Application` with one primary reader window and `HANDLES_OPEN` so desktop
file associations and command-line paths work. GTK owns the header bar, open
chooser, heading sidebar, find controls, menus and status line. WebKit owns only
document layout, selection and scrolling. Use the WebKit find controller for
document search, including next/previous navigation and a clear no-results state.

Opening a document prepares the new value before replacing the visible document.
Failures show a native, nonfatal message and preserve the current page. Empty
documents render an intentional empty state. Theme and text zoom affect both
native controls and the document consistently where applicable.

Monitor the active document with Gio, debounce bursty editor saves, and replace
the monitor when switching documents. Preserve the current scroll position or
reading fraction after reload where possible. Atomic-save replacements must
continue to be observed; monitoring the parent directory is an acceptable simple
approach. Disconnect monitors and remove timeout sources when destroying a
window. A failed reload leaves the last successfully rendered content visible.

Persist small preferences and recent paths under `$XDG_CONFIG_HOME/folio/`,
falling back to `~/.config/folio/`. Invalid settings fall back to defaults.
Use atomic JSON replacement, tolerate unavailable config directories, and never
make preference persistence a prerequisite for reading a document.

## Distribution and verification

System packages supply Python, PyGObject and the native GTK/WebKit libraries.
Python packaging declares markdown-it-py and includes `reader.css` as package
data. Document distro prerequisites and source launch instructions. Do not claim
that `pip install` supplies the entire system desktop stack.

Test pure rendering with pytest, exercising duplicate/Unicode headings, code,
tables, malformed text, size and decoding errors, local assets and unsafe URLs.
Test the GTK window on the available display, including open, search, theme,
outline, monitor reload and close. A screenshot provides visual QA; imported
modules alone do not verify the application. Test the installed wheel separately
so missing styles and resource-path assumptions are caught.

## Upstream references

- [WebKitGTK 4.1 `load_html`](https://webkitgtk.org/reference/webkit2gtk/stable/method.WebView.load_html.html)
- [WebKitGTK find controller](https://webkitgtk.org/reference/webkit2gtk/stable/method.WebView.get_find_controller.html)
- [markdown-it-py security defaults](https://markdown-it-py.readthedocs.io/en/latest/security.html)

## Implementation review

Reviewed the implemented renderer, native window/application, settings and local
installation scripts. The implementation preserves the intended core/UI boundary,
uses the installed native toolkit, prevents document scripts and automatic remote
resource loading, constrains embedded images, and handles preferences independently
of source documents. The integrator additionally verified a built wheel by opening
the sample in the installed reader outside the source checkout.

One performance defect found during review was fixed: duplicate heading IDs
previously restarted their suffix search for every heading. The final implementation
keeps a per-base suffix counter and a global collision set. An independent repeat
of the benchmark rendered 8,000 identical headings in 0.080 seconds, down from
2.345 seconds; all IDs remained unique, including collisions with headings whose
titles already contain numeric suffixes. Core test validation reported 74 passing
tests after this change.

Architecture review approved with no remaining identified correctness, security,
or performance blockers. Native interaction testing and visual acceptance remain
separate release checks.
