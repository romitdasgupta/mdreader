"""Native application lifecycle and command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="folio", description="A quiet, native Markdown reader for Linux."
    )
    parser.add_argument("file", nargs="?", help="Markdown or text document to open")
    parser.add_argument("--version", action="version", version="Folio 0.1.1")
    args = parser.parse_args(argv)
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gio, GLib, Gtk
        from .window import ReaderWindow
    except (ImportError, ValueError) as exc:
        print(
            "Folio needs GTK 3, WebKitGTK 4.1, PyGObject and markdown-it-py. "
            "See the installation instructions in README.md.\n" + str(exc),
            file=sys.stderr,
        )
        return 1

    ready, _ = Gtk.init_check(None)
    if not ready:
        print("Folio needs a graphical Linux desktop (Wayland or X11).", file=sys.stderr)
        return 1
    GLib.set_application_name("Folio")

    class FolioApplication(Gtk.Application):
        def __init__(self):
            super().__init__(application_id="io.github.romitdasgupta.mdreader", flags=Gio.ApplicationFlags.HANDLES_OPEN)
            self.window = None

        def do_activate(self):
            if self.window is None:
                self.window = ReaderWindow(self)
                self.window.connect("destroy", self._window_closed)
            self.window.present()

        def do_open(self, files, _count, _hint):
            self.do_activate()
            if files:
                path = files[0].get_path()
                if path:
                    self.window.open_document(path)
                else:
                    self.window.show_error("Open a local Markdown file to read it in Folio.")

        def _window_closed(self, _window):
            self.window = None

    application = FolioApplication()
    arguments = ["folio"]
    if args.file:
        arguments.append(str(Path(args.file).expanduser().absolute()))
    return application.run(arguments)
