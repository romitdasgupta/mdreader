#!/usr/bin/env python3
"""Exercise a real GTK/WebKit window with isolated, disposable user data.

Run from a Linux graphical session: python3 scripts/smoke_gui.py
Or use a virtual X11 display: xvfb-run -a python3 scripts/smoke_gui.py
Exit 2 means the required GUI environment is unavailable, not a passing test.
"""

from __future__ import annotations

import argparse
import base64
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument(
        "--installed", action="store_true",
        help="exercise the installed distribution without importing the source checkout",
    )
    args = parser.parse_args()
    if not args.installed:
        sys.path.insert(0, str(ROOT))
    import folio

    package_path = Path(folio.__file__).resolve()
    if args.installed:
        from importlib.metadata import distribution

        installed = distribution("folio-reader")
        packaged_files = {str(path) for path in installed.files or ()}
        expected = Path(installed.locate_file("folio/__init__.py")).resolve()
        if (
            "folio/__init__.py" not in packaged_files
            or package_path != expected
            or package_path == ROOT / "folio/__init__.py"
        ):
            print(f"FAIL: --installed requires a non-editable installation; imported {package_path}")
            return 1
        print(f"Testing installed Folio: {package_path}")
    # X11 permits window screenshots without a desktop screenshot portal.
    if os.environ.get("DISPLAY"):
        os.environ.setdefault("GDK_BACKEND", "x11")
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2
    except (ImportError, ValueError) as exc:
        print(f"BLOCKED: GTK 3 and WebKitGTK 4.1 are required: {exc}")
        return 2
    ready, _ = Gtk.init_check(None)
    if not ready:
        print("BLOCKED: no GTK display. Run on a graphical desktop or with xvfb-run.")
        return 2
    # Snapshot settled states rather than intermediate GTK theme/revealer frames.
    Gtk.Settings.get_default().set_property("gtk-enable-animations", False)

    def wait_for(predicate, description: str, timeout: float = 15.0):
        """Pump the GTK loop until a condition holds; never guess load sleeps."""
        if predicate():
            return
        loop = GLib.MainLoop()
        deadline = time.monotonic() + timeout
        result = []

        def check():
            try:
                if predicate():
                    result.append(True)
                elif time.monotonic() >= deadline:
                    result.append(TimeoutError(f"Timed out waiting for {description}"))
            except BaseException as exc:
                result.append(exc)
            if result:
                loop.quit()
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        GLib.timeout_add(20, check)
        loop.run()
        if isinstance(result[0], BaseException):
            raise result[0]

    original_config = os.environ.get("XDG_CONFIG_HOME")
    original_cache = os.environ.get("XDG_CACHE_HOME")
    original_hook = sys.excepthook
    callback_errors = []

    def exception_hook(kind, value, trace):
        callback_errors.append("".join(traceback.format_exception(kind, value, trace)))
        original_hook(kind, value, trace)

    sys.excepthook = exception_hook
    window = None
    app = None
    checks = []
    measurements = {}
    screenshots = []
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="folio-gui-") as temporary:
        temporary = Path(temporary)
        os.environ["XDG_CONFIG_HOME"] = str(temporary / "config")
        os.environ["XDG_CACHE_HOME"] = str(temporary / "cache")
        try:
            from folio.window import ReaderWindow

            app = Gtk.Application(
                application_id="io.github.folio.Smoke",
                flags=Gio.ApplicationFlags.NON_UNIQUE,
            )
            app.register(None)
            window = ReaderWindow(app)
            window.present()
            loads = []
            window.webview.connect(
                "load-changed",
                lambda _view, event: loads.append(time.monotonic())
                if event == WebKit2.LoadEvent.FINISHED else None,
            )

            def js(expression):
                results = []

                def received(view, result, _data):
                    try:
                        value = view.evaluate_javascript_finish(result)
                        results.append(json.loads(value.to_string()))
                    except BaseException as exc:
                        results.append(exc)

                source = f"JSON.stringify(({expression}))"
                window.webview.evaluate_javascript(
                    source, -1, None, None, None, received, None,
                )
                wait_for(lambda: bool(results), "trusted DOM inspection")
                if isinstance(results[0], BaseException):
                    raise results[0]
                return results[0]

            def loaded(action, description):
                before = len(loads)
                start = time.monotonic()
                assert action() is not False, description
                wait_for(
                    lambda: len(loads) > before and not window.webview.is_loading(),
                    description,
                )
                assert not window.infobar.get_visible(), window.error_label.get_text()
                return time.monotonic() - start

            def frames():
                count = []

                def tick(_widget, _clock):
                    count.append(True)
                    return len(count) < 3

                window.add_tick_callback(tick)
                window.queue_draw()
                wait_for(lambda: len(count) == 3, "rendered GTK frames")

            def screenshot(name):
                frames()
                surface = window.get_window()
                pixels = Gdk.pixbuf_get_from_window(
                    surface, 0, 0, surface.get_width(), surface.get_height(),
                )
                if pixels is None:
                    print(f"SCREENSHOT BLOCKED: {name}; use GDK_BACKEND=x11 or xvfb-run")
                    return
                destination = args.artifacts / name
                pixels.savev(str(destination), "png", [], [])
                screenshots.append(str(destination))

            def key(keyval, modifiers=Gdk.ModifierType(0)):
                """Dispatch a native GDK key event through GTK, including keymap data."""
                mapped, entries = Gdk.Keymap.get_for_display(window.get_display()).get_entries_for_keyval(keyval)
                assert mapped and entries, f"No keyboard mapping for {keyval}"
                for event_type in (Gdk.EventType.KEY_PRESS, Gdk.EventType.KEY_RELEASE):
                    event = Gdk.Event.new(event_type)
                    event.window = window.get_window()
                    event.send_event = True
                    event.time = Gdk.CURRENT_TIME
                    event.keyval = keyval
                    event.state = modifiers
                    event.hardware_keycode = entries[0].keycode
                    event.group = entries[0].group
                    event.set_device(window.get_display().get_default_seat().get_keyboard())
                    Gtk.main_do_event(event)

            def chooser(response, path=None):
                observed = []
                selected = []
                deadline = time.monotonic() + 10

                def answer():
                    dialogs = [item for item in Gtk.Window.list_toplevels()
                               if isinstance(item, Gtk.FileChooserDialog) and item.get_visible()]
                    if not dialogs:
                        if time.monotonic() >= deadline:
                            observed.append("No introspectable GTK file chooser appeared")
                            print(f"FAIL: {observed[-1]}", file=sys.stderr, flush=True)
                            return GLib.SOURCE_REMOVE
                        return GLib.SOURCE_CONTINUE
                    dialog = dialogs[0]
                    if path is not None and not selected:
                        dialog.set_filename(str(path))
                        selected.append(True)
                    if path is not None and dialog.get_filename() != str(path):
                        if time.monotonic() >= deadline:
                            observed.append("Chooser did not select the fixture")
                            dialog.response(Gtk.ResponseType.CANCEL)
                            return GLib.SOURCE_REMOVE
                        return GLib.SOURCE_CONTINUE
                    observed.append(True)
                    dialog.response(response)
                    return GLib.SOURCE_REMOVE

                GLib.timeout_add(20, answer)
                # A portal or unresponsive dialog can leave key dispatch blocked
                # inside a nested native loop. GI catches callback exceptions, so
                # an independent watchdog must turn that hang into a failing exit.
                faulthandler.dump_traceback_later(12, exit=True)
                try:
                    key(Gdk.KEY_o, Gdk.ModifierType.CONTROL_MASK)
                finally:
                    faulthandler.cancel_dump_traceback_later()
                assert observed == [True], observed

            def passed(description):
                assert not callback_errors, "GTK callback raised: " + "\n".join(callback_errors)
                checks.append(description)
                print(f"PASS: {description}", flush=True)

            wait_for(window.get_mapped, "native window mapping")
            assert window.stack.get_visible_child_name() == "empty"
            assert not window.find_button.get_sensitive()
            passed("Native first-use window and empty state")
            screenshot("folio-empty.png")

            folder = temporary / "Notes with spaces café"
            folder.mkdir()
            image_path = folder / "tiny image.png"
            image_path.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNc0AAAAASUVORK5CYII="
            ))
            sample = folder / "Reading café.md"
            source = (
                "# A quiet place to read\n\n"
                "Folio keeps your **ideas** in focus. Café, 日本語, and λ stay intact.\n\n"
                "## The reading experience\n\n"
                "> Good tools let the work speak for itself.\n\n"
                "A familiar desktop, a comfortable measure, and room to think.\n\n"
                "- [x] Open your Markdown\n- [ ] Follow an idea\n\n"
                "| Feature | Detail |\n| --- | --- |\n| Reading | Quiet by design |\n"
                "| Navigation | Your document, at a glance |\n\n"
                "```python\nprint('Hello, reader')\n    preserved = True\n```\n\n"
                "![A local image](tiny%20image.png)\n\n"
                "[Go to the second thought](#second-thought) · [A nearby note](nearby.md#destination)\n\n"
                + "\n\n".join(f"A considered paragraph {i}: searchneedle appears here." for i in range(16))
                + "\n\n## Second thought\n\nA destination worth finding.\n\n"
                "## Repeated\n\nFirst repeated heading.\n\n"
                + "\n\n".join("More space for the next idea." for _ in range(12))
                + "\n\n## Repeated\n\nSecond repeated heading.\n\n"
                "### Third level\n\n#### Fourth level\n\n##### Fifth level\n\n###### Sixth level\n\n"
                + "\n\n".join("A little more room at the end." for _ in range(15))
            )
            sample.write_text(source, encoding="utf-8")
            sibling = folder / "nearby.md"
            sibling.write_text(
                "# A nearby note\n\n" + "\n\n".join("Before the destination." for _ in range(20))
                + "\n\n## Destination\n\nThe linked section.\n\n"
                + "\n\n".join("After the destination." for _ in range(15)), encoding="utf-8",
            )
            checksums = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (sample, sibling, image_path)}
            loaded(lambda: chooser(Gtk.ResponseType.ACCEPT, sample), "native chooser open")
            # Opening through the actual chooser must retain the source directory:
            # a portal-exported single file can hide its sibling images and links.
            assert window.document.path == sample, window.document.path
            wait_for(
                lambda: js("document.querySelector('img')?.naturalWidth > 0"),
                "chooser-selected document's sibling image",
            )
            measurements["sample_load_seconds"] = loaded(lambda: window.open_document(sample), "sample render")
            assert window.document.path == sample
            assert "Reading café.md" in window.get_title()
            assert js("document.querySelector('h1').textContent") == "A quiet place to read"
            assert js("document.querySelectorAll('h1,h2,h3,h4,h5,h6').length") == 9
            assert js("document.querySelectorAll('table tbody tr').length") == 2
            assert js("document.querySelectorAll('input[disabled]').length") == 2
            assert js("document.querySelectorAll('input[checked]').length") == 1
            assert js("document.body.innerText.includes('Café, 日本語, and λ')")
            assert js("document.querySelector('pre code').textContent.includes('    preserved = True')")
            wait_for(lambda: js("document.querySelector('img').naturalWidth > 0"), "local image decode")
            passed("Markdown, Unicode/spaced paths, local image, code, table and task rendering")
            screenshot("folio-light.png")

            js("(window.scrollTo(0, 480), true)")
            chooser(Gtk.ResponseType.CANCEL)
            assert window.document.path == sample and abs(js("window.scrollY") - 480) < 3
            passed("Ctrl+O native chooser acceptance and cancel preserve the current document/scroll")

            rows = window.outline_list.get_children()
            assert len(rows) == 9 and rows[3].anchor != rows[4].anchor
            window.outline_list.emit("row-activated", rows[4])
            wait_for(lambda: js("window.scrollY > 500"), "outline scroll")
            assert abs(js(f"document.getElementById({json.dumps(rows[4].anchor)}).getBoundingClientRect().top") - 32) < 3
            window.lookup_action("outline").activate(None)
            assert not window.sidebar.get_visible()
            window.lookup_action("outline").activate(None)
            assert window.sidebar.get_visible()
            js("(document.querySelector('a[href$=\"#heading-second-thought\"]').click(), true)")
            wait_for(lambda: abs(js("document.getElementById('heading-second-thought').getBoundingClientRect().top") - 32) < 3, "same-document link")
            passed("Outline, duplicate heading IDs, collapse and same-document link navigation")

            assert "<Primary>f" in app.get_accels_for_action("win.find")
            window.webview.grab_focus()
            key(Gdk.KEY_f, Gdk.ModifierType.CONTROL_MASK)
            assert window.search_bar.get_search_mode()
            window.search_entry.set_text("searchneedle")
            wait_for(lambda: "match" in window.search_feedback.get_text(), "search matches")
            assert window.search_feedback.get_text() == "16 matches"
            key(Gdk.KEY_Return)
            key(Gdk.KEY_Return, Gdk.ModifierType.SHIFT_MASK)
            window.search_entry.set_text("unfindable-7a9ce")
            wait_for(lambda: window.search_feedback.get_text() == "No matches", "no-match feedback")
            key(Gdk.KEY_Escape)
            assert not window.search_bar.get_search_mode()
            passed("Ctrl+F, matching text, Enter/Shift+Enter navigation, no-match feedback and Escape")

            loaded(lambda: window.set_theme("dark"), "dark theme")
            assert js("document.body.dataset.theme") == "dark"
            assert Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme")
            js("(window.scrollTo(0, 0), true)")
            screenshot("folio-dark.png")
            loaded(lambda: window.set_theme("light"), "light theme")
            window.outline_button.set_active(False)
            window.resize(680, 600)
            wait_for(lambda: window.get_size().width <= 700, "narrow resize")
            frames()
            assert js("document.documentElement.scrollWidth <= window.innerWidth + 1")
            screenshot("folio-narrow.png")
            for _ in range(30):
                window.lookup_action("zoom-in").activate(None)
            assert window.webview.get_zoom_level() == 2.4
            for _ in range(30):
                window.lookup_action("zoom-out").activate(None)
            assert window.webview.get_zoom_level() == 0.6
            window.lookup_action("zoom-reset").activate(None)
            assert window.webview.get_zoom_level() == 1.0
            passed("Native/document light and dark themes, narrow layout and bounded zoom")

            loaded(lambda: js("(document.querySelector('a[href$=\"nearby.md#destination\"]').click(), true)"), "relative Markdown link")
            assert window.document.path == sibling
            wait_for(lambda: abs(js("document.getElementById('heading-destination').getBoundingClientRect().top") - 32) < 3, "cross-document heading anchor")
            passed("Relative Markdown link with cross-document heading anchor")

            previous_html = js("document.body.innerHTML")
            invalid = folder / "invalid.md"
            invalid.write_bytes(b"\xff\xfe")
            oversized = folder / "large.md"
            with oversized.open("wb") as stream:
                stream.truncate(10 * 1024 * 1024 + 1)
            for path in (folder / "missing.md", folder, invalid, oversized):
                assert window.open_document(path) is False
                assert window.infobar.get_visible() and str(path) in window.error_label.get_text()
                assert window.document.path == sibling
                assert js("document.body.innerHTML") == previous_html
            passed("Missing, directory, invalid UTF-8 and oversized inputs preserve the previous document")

            empty = folder / "empty.md"
            empty.write_text("", encoding="utf-8")
            loaded(lambda: window.open_document(empty), "empty document")
            assert js("document.body.innerText.includes('This document is empty.')")
            assert not window.sidebar.get_visible()
            bom = folder / "bom.md"
            bom.write_bytes(b"\xef\xbb\xbf# UTF-8 BOM\n")
            loaded(lambda: window.open_document(bom), "UTF-8 BOM document")
            assert js("document.querySelector('h1').textContent") == "UTF-8 BOM"
            passed("Empty and UTF-8 BOM documents")

            unsafe = folder / "unsafe.md"
            unsafe.write_text(
                '# Untrusted content\n\n<script>window.folioPwned = true</script>\n\n'
                '<img src="https://example.invalid/track" onerror="window.folioPwned=true">\n\n'
                '[Unsafe](javascript:alert(1))\n\n![Remote](https://example.invalid/track.png)\n',
                encoding="utf-8",
            )
            loaded(lambda: window.open_document(unsafe), "untrusted content")
            assert js("document.querySelectorAll('script,img').length") == 0
            assert js("typeof window.folioPwned") == "undefined"
            assert js("document.querySelectorAll('a[href^=\"javascript:\"]').length") == 0
            assert js("document.body.innerText.includes('<script>')")
            assert not window.webview.get_settings().get_enable_javascript_markup()
            passed("Raw HTML/script and remote image inputs remain inert in WebKit")

            live = folder / "live.md"
            live_source = "# Live document\n\n" + "\n\n".join(f"Paragraph {i}." for i in range(80))
            live.write_text(live_source, encoding="utf-8")
            loaded(lambda: window.open_document(live), "live document")
            js("(window.scrollTo(0, 850), true)")
            before_scroll = js("window.scrollY")
            window.toggle_find()
            window.search_entry.set_text("")
            focus_before = window.get_focus()
            replacement = folder / ".live-save.md"
            replacement.write_text(live_source + "\n\nAtomic save arrived.\n", encoding="utf-8")
            loaded(lambda: replacement.replace(live), "atomic-save automatic reload")
            assert js("document.body.innerText.includes('Atomic save arrived.')")
            wait_for(lambda: abs(js("window.scrollY") - before_scroll) < 3, "reload scroll restoration")
            assert window.get_focus() == focus_before
            loaded(lambda: live.write_text(live_source + "\n\nDirect save arrived.\n", encoding="utf-8"), "in-place-save automatic reload")
            assert js("document.body.innerText.includes('Direct save arrived.')")
            wait_for(lambda: abs(js("window.scrollY") - before_scroll) < 3, "in-place reload scroll restoration")
            live.unlink()
            wait_for(window.infobar.get_visible, "temporary deletion error")
            assert js("document.body.innerText.includes('Direct save arrived.')")
            loaded(lambda: live.write_text(live_source + "\n\nRestored after delete.\n", encoding="utf-8"), "recreated file automatic reload")
            assert js("document.body.innerText.includes('Restored after delete.')")
            before = len(loads)
            window.webview.grab_focus()
            key(Gdk.KEY_r, Gdk.ModifierType.CONTROL_MASK)
            wait_for(lambda: len(loads) > before, "explicit reload action")
            window.hide_find()
            passed("Atomic/in-place save, deletion/recreation live reload, preserved scroll/focus and explicit reload")

            long_document = folder / "ten-thousand-lines.md"
            long_document.write_text(
                "# Ten thousand lines\n\n" + "\n\n".join(
                    f"Line {i}: the reader remains useful. {'finalneedle' if i == 4999 else ''}"
                    for i in range(5000)
                ) + "\n\n```text\n" + "wide-code-" * 200 + "\n```\n\n"
                "| " + " | ".join(f"Column {i}" for i in range(15)) + " |\n"
                "| " + " | ".join("---" for _ in range(15)) + " |\n"
                "| " + " | ".join("wide-cell-" * 8 for _ in range(15)) + " |\n",
                encoding="utf-8",
            )
            measurements["long_document_lines"] = len(long_document.read_text().splitlines())
            measurements["long_document_load_seconds"] = loaded(lambda: window.open_document(long_document), "10,000-line document render")
            assert measurements["long_document_lines"] >= 10000
            assert js("document.querySelectorAll('p').length") == 5000
            assert js("document.documentElement.scrollWidth <= window.innerWidth + 1")
            assert js("document.querySelector('pre').scrollWidth > document.querySelector('pre').clientWidth")
            assert js("document.querySelector('table').scrollWidth > document.querySelector('table').clientWidth")
            window.toggle_find()
            window.search_entry.set_text("finalneedle")
            wait_for(lambda: window.search_feedback.get_text() == "1 match", "long document search")
            assert js("window.scrollY > 10000")
            passed("10,000-line render/search/scroll and horizontally contained wide code/table")
            for path, digest in checksums.items():
                assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Reader modified {path}"
            passed("Reading/navigation left source fixture checksums unchanged")

            window.close()
            wait_for(lambda: window._destroyed, "clean window destruction")
            assert window._monitor is None and not window._reload_timeout
            passed("Clean close cancels file monitor and reload callbacks")
            report = {
                "status": "passed", "platform": platform.platform(),
                "python": platform.python_version(),
                "package_path": str(package_path),
                "package_mode": "installed" if args.installed else "source",
                "gtk": f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}",
                "webkit": f"{WebKit2.get_major_version()}.{WebKit2.get_minor_version()}.{WebKit2.get_micro_version()}",
                "display": Gdk.Display.get_default().get_name(),
                "checks": checks, "measurements": measurements, "screenshots": screenshots,
                "limitations": [
                    "GDK key events traverse GTK accelerator handling; physical hardware input is not automated.",
                    "The application's GTK file chooser is exercised; external browser launch requires manual verification.",
                    "Unreadable file mode depends on user privileges and is covered separately in core tests.",
                ],
            }
            (args.artifacts / "gui-smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(measurements, indent=2))
            print(f"PASS: {len(checks)} GUI checks; artifacts in {args.artifacts}")
            return 0
        except BaseException:
            traceback.print_exc()
            return 1
        finally:
            if window is not None and not window._destroyed:
                window.destroy()
            if app is not None:
                app.quit()
            sys.excepthook = original_hook
            for key, value in (("XDG_CONFIG_HOME", original_config), ("XDG_CACHE_HOME", original_cache)):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
