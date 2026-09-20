# GUI verification

[scripts/smoke_gui.py](../scripts/smoke_gui.py) exercises a real GTK window and
WebKit rendering process. This document describes the checks and how to reproduce
them; dated release results belong in [RELEASE.md](RELEASE.md).

## Run the checks

After the [development setup](../README.md#dependencies-on-a-fresh-system), run
from the repository root on a graphical Linux desktop:

```sh
.venv/bin/python scripts/smoke_gui.py
```

For a headless machine with Xvfb and D-Bus installed:

```sh
xvfb-run -a dbus-run-session -- .venv/bin/python scripts/smoke_gui.py
```

A normal run checks the source checkout. To verify a built wheel outside the
checkout in a disposable environment:

```sh
.venv/bin/python scripts/verify_package.py --gui
```

The consumer Flatpak needs its own installed-runtime check; follow
[distribution verification](DISTRIBUTION.md#verify).
`--installed` rejects source and editable-package imports. A successful source
run does not establish that the distributed package contains the same resources
or can launch with its declared dependencies.

The runner returns exit **0** after all checks pass, **1** on a check failure,
and **2** when GTK/WebKit or a display is unavailable. An unavailable environment
is not a passing GUI result. A watchdog terminates a stuck chooser with a failure
and a Python traceback.

## Covered behavior

- First-use window and disabled document-only controls.
- Native GTK chooser acceptance and cancellation through keyboard dispatch;
  the selected document retains its real path and can display a sibling image.
- Headings, Unicode, local images, code whitespace, tables and task checkboxes.
- Outline selection, duplicate headings, outline visibility and heading links.
- Search shortcuts, next/previous matches, missing queries and dismissal.
- Light/dark appearance, narrow layout and bounded text zoom.
- Relative Markdown links, including destination heading anchors.
- Missing, non-file, invalidly encoded and oversized inputs; failed replacements
  retain the previous page. Empty and UTF-8 BOM documents remain readable.
- Inert raw HTML, blocked script markup and unavailable remote images.
- Explicit reload and monitored changes, including atomic saves, deletion and
  recreation; scroll position, search focus and monitor cleanup.
- A document longer than 10,000 lines, with wide code and table content.
- Unchanged source-document and image checksums after reading and navigation.

Folio deliberately uses GTK's file chooser directly. A portal that exports only
the selected Markdown file can hide adjacent images and linked documents. The
Flatpak's read-only directory access and direct chooser preserve that context
without granting write access to the document folder.

## Inspect the evidence

The runner uses temporary fixtures, configuration and cache directories. It
waits for observable conditions and WebKit load events, and disables GTK
animations in the test process so captures show settled states.

Source runs write `gui-smoke.json` and empty/light/dark/narrow screenshots under
`artifacts/` by default; `--artifacts` selects another output directory. Wheel
verification defaults to `artifacts/package/`. These generated files are ignored
by Git and will not exist in a fresh checkout until the checks run.

Inspect all four fresh screenshots for readable controls, consistent document
and window themes, clipping, and narrow-window behavior. Record the tested
revision, command, environment, result and remaining limitations. The JSON report
includes package provenance, dependency versions and timing measurements. Loading
time is measured in an already-running application; it is not cold startup time
or a performance guarantee for other machines.

## Checks that need separate evidence

The smoke test synthesizes GDK keyboard events; it does not operate physical
input hardware. Desktop-entry launches, drag-and-drop delivery, external browser
launch, screen-reader behavior and Wayland-only sessions need separate checks.
Core tests cover unreadable-file handling independently of GUI process privileges.
DOM assertions and renderer tests check content isolation; the smoke runner does
not capture network traffic.

For a release, also follow the [acceptance checklist](ACCEPTANCE.md) and verify
installation and desktop integration using the actual distributed bundle.
