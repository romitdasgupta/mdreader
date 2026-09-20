# Native GUI verification

The final GUI smoke run passed all 14 check groups against a realized GTK window and a real WebKit rendering process. The test runner is [scripts/smoke_gui.py](../scripts/smoke_gui.py).

```sh
python3 scripts/smoke_gui.py
```

The runner uses temporary document fixtures, configuration and cache directories. It restores its environment, closes the window, and checks monitor cleanup. It waits for observable conditions and WebKit load events. Missing GUI dependencies or a missing display return exit code 2 with `BLOCKED`; they do not count as a pass. GTK animations are disabled within the test process so screenshots capture settled appearances. `GTK_USE_PORTAL=0` selects the introspectable native GTK chooser fallback.

## Environment

| Component | Tested value |
| --- | --- |
| Distribution | Ubuntu 26.04 LTS, x86-64 |
| Processor | AMD Ryzen 9 7950X3D |
| Python | 3.14.4 |
| GTK | 3.24.52 |
| WebKitGTK | 2.52.6, introspection API 4.1 |
| Display | X11/XWayland `:0`, 2× display scale |
| Desktop theme | Yaru family; light and dark appearances |

## Verified behavior

- Native first-use window, disabled document-only controls, and empty-state presentation.
- `Ctrl+O` dispatched through GTK with a native GDK key event: chooser acceptance opens the selected Unicode path; cancel preserves the document and scroll position.
- Real rendered headings through level six, duplicate headings, Unicode, local images with spaces in their names, code whitespace, tables and task checkboxes.
- Outline selection scrolls to the correct duplicate heading. Outline collapse and same-document heading links work.
- `Ctrl+F`, Enter, Shift+Enter and Escape traverse GTK keyboard handling. Matching and absent queries produce the expected feedback.
- Both native controls and the reading surface switch between light and dark. A 680 × 600 logical-pixel window retains readable content and controls. Zoom respects its bounds and reset.
- A relative Markdown link opens the neighboring document and reaches its unprefixed `#destination` heading anchor.
- Missing paths, directories, invalid UTF-8 and oversized files show errors while retaining the previous rendered document. Empty and UTF-8 BOM files open successfully.
- Raw HTML/script markup remains visible as inert text; no injected script/image elements appear, and remote image inputs are removed from the rendered page.
- Automatic reload handles atomic replacement, in-place writes, deletion and recreation. Successful reloads preserve scroll position and search focus; failure retains the last readable page. `Ctrl+R` reloads explicitly.
- A 10,009-line document renders and finds a word near its end. Very wide code and table content scroll inside their own containers without widening the page.
- Reading and navigation leave fixture checksums unchanged. Closing the window cancels its file monitor and queued reload callback.

The 10,009-line fixture reached WebKit's finished-load event in approximately **0.12–0.13 seconds** on this machine, including synchronous file reading and Markdown conversion. This measures loading in an already-running application, not cold application startup. Timing is recorded on every run in the JSON artifact.

## Visual evidence

Full-window screenshots were generated and visually inspected. Headers, controls, outline, document content and status text remain legible. Light mode uses light native chrome; dark mode uses dark native chrome with readable button icons. The narrow capture preserves the full toolbar and wraps the reading layout.

- [First use](../artifacts/folio-empty.png)
- [Light appearance](../artifacts/folio-light.png)
- [Dark appearance](../artifacts/folio-dark.png)
- [Narrow window](../artifacts/folio-narrow.png)
- [Machine-readable results and measurements](../artifacts/gui-smoke.json)

These artifacts are regenerated locally by the runner and are not required to launch the application.

## Limits of this run

The test synthesizes GDK keyboard events with keymap information; it does not operate physical input hardware. Desktop portal chooser integration, drag-and-drop, external browser launch, screen-reader behavior and a Wayland-only session still require separate checks. Unreadable-file behavior depends on process privileges and is covered by the separate core test suite. Network capture was not performed; GUI assertions verify the generated inert DOM, while parser/resource policy has separate unit coverage. Package installation and command-line entry-point verification are reported separately.
