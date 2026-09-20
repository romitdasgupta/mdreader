# Folio first release

Status: Folio 0.1 is implemented and its core and native GUI checks pass on the
tested Ubuntu desktop. Remaining environment-specific verification is explicit
below. The complete behavioral checklist is in [ACCEPTANCE.md](ACCEPTANCE.md), with scope
and implementation decisions in [PRODUCT.md](PRODUCT.md) and
[ARCHITECTURE.md](ARCHITECTURE.md).

## Release scope and priority

1. **P0 — complete the reading loop.** A native Linux window opens local Markdown
   through its chooser or a command-line path, renders it legibly, navigates a
   heading outline, searches the current document, switches appearance, and
   reloads saved changes. Required shortcuts are `Ctrl+O`, `Ctrl+F`, `Ctrl+R`,
   Enter/Shift+Enter in search, and Escape. Failed opens preserve the current
   document; empty files open successfully.
2. **P0 — make setup reproducible.** Ship accurate dependency and launch
   instructions, packaged reader styles, a useful example, and verified source
   and installed-wheel launches. The native desktop dependencies come from the
   Linux distribution; installing the Python wheel alone is insufficient.
3. **P1 — establish confidence and reading quality.** Exercise Unicode, repeated
   headings, paths containing spaces, wide code/tables, local images, untrusted
   content, a long document, narrow windows, and both appearances. Inspect an
   actual rendered window and record the result.
4. **P1 — include polish only when it works.** Automatic reload, saved preferences,
   zoom, drag and drop, and desktop integration are optional product features.
   Their presence adds the corresponding acceptance checks; it does not replace
   the required manual reload and launch paths.

## Setup contract

- Support Python 3.11+ with PyGObject, GTK 3, WebKitGTK 4.1, and markdown-it-py.
  README must name the exact packages for each distribution it claims to support.
- Source launch commands are `python3 -m folio` and `./bin/folio`; both accept
  a local document path. Run from the repository root until the launcher is
  explicitly verified from another working directory.
- Use a Python interpreter that can import the distribution's `gi` package.
  If documenting a virtual environment, create it with `--system-site-packages`
  from the distribution Python. Do not suggest changing a managed system Python
  with an unrestricted global pip install.
- A local installer and desktop entry must retain a stable executable path,
  preserve quoted filenames, and accept a document through `%f` or `%F`.
  Desktop `Exec` values do not expand shell variables or `~`. Document how to
  remove the local installation and whether moving the checkout breaks it.
- Verify package data by building and launching an installed wheel from outside
  the source directory. A source-tree run alone cannot prove packaging works.

## Release verification matrix

Historical evidence recorded on **2026-09-19** against the initial working tree,
subsequently committed as `464dac1`. These results do not verify later changes.
The test environment was Ubuntu 26.04 with GNOME, Python 3.14.4,
GTK 3.24.52 and WebKitGTK 2.52.6 using the WebKit2 4.1 API. Results below are
reported by the core tester, GUI tester, native UI coder and integrator. The
GUI runner passed 14 groups; its evidence is in `artifacts/gui-smoke.json` and
[GUI_TEST_REPORT.md](GUI_TEST_REPORT.md). Product and architecture reviews are
approved. A partial result is not a pass for the entire gate.

| Gate | Planned verification | Owner | Actual result / evidence |
| --- | --- | --- | --- |
| Core rendering and input handling | Run the project's pytest suite; cover duplicate/Unicode headings, Markdown features, BOM/invalid UTF-8, empty/missing/non-file/oversize input and unchanged source files. | Core tester | Automated pass: `python3 -m pytest -q tests/test_document.py tests/test_settings.py` reports 74 passed in 0.16 s: 50 document tests and 24 settings tests. |
| Resource and navigation boundaries | Exercise raw HTML, unsafe schemes, remote images, image traversal and symlinks; verify local images and allowed links. | Core tester + GUI tester | Core and native WebKit checks pass, including inert HTML/scripts, blocked remote images, local images and same/cross-document links. Actual external browser launch remains unverified. |
| Source launch | Run `python3 -m folio` and `./bin/folio` with no argument and with a quoted document path containing spaces; verify native window creation and close. | Integrator + GUI tester | Pass: help/version commands succeed; both actual entry points were exercised from outside the checkout via runpy, with empty state and a Unicode filename containing spaces. The native window, loaded document path and clean close were verified. |
| Reading loop | On a real display, open through the native chooser, navigate the outline, search next/previous/no-match, reload, and exercise required shortcuts. | GUI tester | Pass: `python3 scripts/smoke_gui.py` exercises native chooser acceptance/cancel with GTK_USE_PORTAL=0; GDK key events drive Ctrl+O, Ctrl+F, Enter/Shift+Enter, Escape and Ctrl+R. Portal chooser integration remains unverified. |
| Failure recovery | With a readable document open, attempt missing and unreadable replacement files; confirm the prior content remains available. Open an empty document. | GUI tester | Pass: missing, directory, invalid UTF-8 and oversized replacements preserve the previous document. Empty and BOM files open. Permission errors are covered in core tests. |
| Visual quality | Capture and inspect light/dark screenshots and a narrow window; check body text, heading hierarchy, wide code/tables, local images, outline and visible focus. | GUI tester | Pass: tester, integrator and product reviewer inspected full-window empty/light/dark/narrow screenshots in `artifacts/folio-*.png`. Native controls and document theme agree; wide content stays contained. Test-only GTK animations are disabled for deterministic screenshots. |
| Automatic reload, if shipped | Edit, atomically replace and temporarily remove the open file; check focus, preserved position, recovery and clean shutdown. | GUI tester | Pass: direct saves, atomic replacement, deletion/recreation, scroll/focus retention and monitor cleanup are exercised. |
| Long document | Open, scroll and search at least 10,000 lines. Record hardware/environment and elapsed first-render time; target under 2 seconds. | GUI tester | Pass: 10,009-line fixture rendered in 0.121 s on this environment and supports final-paragraph search and scrolling. Separate duplicate-heading benchmark: 8,000 identical headings parse in 0.080 s after the architecture review fix. These are local measurements, not cross-machine guarantees. |
| Wheel packaging | Build a wheel, inspect bundled CSS, install into a fresh compatible environment, change outside the checkout and launch a sample. | Integrator | Pass: `.venv/bin/python -m build --no-isolation` built wheel and sdist. Installed wheel with `--no-deps` into fresh `artifacts/wheel-env` created with `--system-site-packages`; ran from `/tmp`, instantiated a real GTK `ReaderWindow`, and verified welcome-sample DOM content. Both CSS assets are present. Build log: `artifacts/build.log`. |
| Documented installation | Follow README verbatim on a clean supported environment; record distribution and dependency versions. | Integrator / release verifier | Not run |
| Desktop integration, if shipped | Install locally, launch from the desktop and through a document association, including paths with spaces; verify removal instructions. | Integrator + GUI tester | Partial pass: local installer tested in an isolated prefix containing spaces; `desktop-file-validate` passes; launcher preserves working directory and spaced arguments; uninstall removes its own files. Actual desktop-menu and file-association launches remain unverified. |

A result entry should include the date, command or manual steps, tested commit,
distribution, relevant dependency versions, pass/fail/blocked status, and an
artifact or concise observation. A missing display is **blocked**, never a GUI
pass. Keep any untested distribution support and performance claims explicit.

## Deferred features

The product explicitly excludes editing, accounts, synchronization, cloud
services, AI features, a plugin marketplace, multiple-document tabs, a document
library, PDF export, and publishing. Folio does not require a web server or an
external browser window to read a document. Automatically fetched remote images
are outside required v1 scope.

Automatic reload, saved theme/window/outline preferences, zoom, drag and drop,
and desktop association metadata are implemented. Reload, preferences, zoom and
installer behavior are verified as above; actual drag-and-drop delivery and
desktop-menu/file-association launches remain manual checks. The initial release
does not include Flatpak or distribution packages. Clean installation on another
Linux distribution has not been tested.
