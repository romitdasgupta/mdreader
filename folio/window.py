"""GTK owns the reader controls; WebKit owns only the document surface."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango, WebKit2

from .document import DocumentError, load_document, render_markdown
from .settings import load_settings, save_settings


class ReaderWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Folio")
        self.set_icon_name("io.github.folio.Reader")
        self.preferences = load_settings()
        self.theme = self.preferences["theme"]
        self.document = None
        self._monitor = None
        self._reload_timeout = 0
        self._generation = 0
        self._pending_scroll = 0.0
        self._pending_anchor = None
        self._base_uri = "about:blank"
        self._destroyed = False
        self.set_default_size(self.preferences["width"], self.preferences["height"])
        self.set_size_request(640, 480)
        self.get_style_context().add_class("folio")
        self._load_css()
        self._build_header()
        self._build_content()
        self._install_actions(application)
        self._apply_native_theme()
        self.connect("delete-event", self._on_delete)
        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self._on_key)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._on_drop)
        self.show_all()
        self.infobar.hide()
        self.search_bar.set_search_mode(False)
        self.sidebar.hide()
        self.statusbar.hide()
        self._update_controls()

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).parent / "resources" / "gtk.css"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _button(self, icon, tooltip, callback, toggle=False):
        button = Gtk.ToggleButton() if toggle else Gtk.Button()
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_tooltip_text(tooltip)
        button.get_accessible().set_name(tooltip.split(" (")[0])
        button.connect("toggled" if toggle else "clicked", callback)
        return button

    def _build_header(self):
        self.header = Gtk.HeaderBar(title="Folio", show_close_button=True)
        self.set_titlebar(self.header)
        open_button = Gtk.Button(label="Open")
        open_button.set_image(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON))
        open_button.set_always_show_image(True)
        open_button.set_tooltip_text("Open a document (Ctrl+O)")
        open_button.connect("clicked", lambda *_: self.choose_document())
        self.header.pack_start(open_button)
        self.outline_button = self._button(
            "view-list-symbolic", "Show outline (F9)", self._on_outline_toggled, toggle=True
        )
        self.outline_button.set_active(self.preferences["outline"])
        self.header.pack_start(self.outline_button)
        menu_button = Gtk.MenuButton()
        menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_button.set_tooltip_text("Reader options")
        menu = Gio.Menu()
        size = Gio.Menu()
        size.append("Larger text", "win.zoom-in")
        size.append("Smaller text", "win.zoom-out")
        size.append("Reset text size", "win.zoom-reset")
        menu.append_section(None, size)
        file_menu = Gio.Menu()
        file_menu.append("Reload document", "win.reload")
        file_menu.append("Keyboard shortcuts", "win.shortcuts")
        file_menu.append("About Folio", "win.about")
        menu.append_section(None, file_menu)
        menu_button.set_menu_model(menu)
        self.header.pack_end(menu_button)
        self.theme_button = self._button("weather-clear-night-symbolic", "Switch to dark mode", lambda *_: self.set_theme("dark" if self.theme == "light" else "light"))
        self.header.pack_end(self.theme_button)
        self.find_button = self._button("edit-find-symbolic", "Find in document (Ctrl+F)", lambda *_: self.toggle_find())
        self.header.pack_end(self.find_button)

    def _build_content(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        self.infobar = Gtk.InfoBar(message_type=Gtk.MessageType.ERROR, show_close_button=True)
        self.infobar.set_no_show_all(True)
        self.infobar.connect("response", lambda *_: self.infobar.hide())
        self.error_label = Gtk.Label(xalign=0, wrap=True)
        self.error_label.set_max_width_chars(100)
        self.error_label.get_style_context().add_class("error-message")
        self.infobar.get_content_area().add(self.error_label)
        self.error_label.show()
        root.pack_start(self.infobar, False, False, 0)
        self.search_bar = Gtk.SearchBar()
        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        search_row.get_style_context().add_class("search-row")
        self.search_entry = Gtk.SearchEntry(width_chars=32, placeholder_text="Find in document…")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("key-press-event", self._on_search_key)
        self.search_bar.connect_entry(self.search_entry)
        search_row.pack_start(self.search_entry, True, True, 0)
        self.search_feedback = Gtk.Label(label="", width_chars=12, xalign=0)
        self.search_feedback.get_style_context().add_class("search-feedback")
        search_row.pack_start(self.search_feedback, False, False, 0)
        search_row.pack_start(self._button("go-up-symbolic", "Previous match (Shift+Enter)", lambda *_: self.find_controller.search_previous()), False, False, 0)
        search_row.pack_start(self._button("go-down-symbolic", "Next match (Enter)", lambda *_: self.find_controller.search_next()), False, False, 0)
        search_row.pack_start(self._button("window-close-symbolic", "Close search (Escape)", lambda *_: self.hide_find()), False, False, 0)
        self.search_bar.add(search_row)
        root.pack_start(self.search_bar, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        root.pack_start(self.stack, True, True, 0)
        self.stack.add_named(self._empty_state(), "empty")
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.set_size_request(210, -1)
        self.sidebar.set_no_show_all(True)
        self.sidebar.get_style_context().add_class("outline")
        heading = Gtk.Label(label="CONTENTS", xalign=0)
        heading.set_margin_start(20)
        heading.set_margin_top(23)
        heading.set_margin_bottom(15)
        heading.get_style_context().add_class("outline-title")
        self.sidebar.pack_start(heading, False, False, 0)
        outline_scroll = Gtk.ScrolledWindow()
        outline_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.outline_list = Gtk.ListBox()
        self.outline_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.outline_list.set_activate_on_single_click(True)
        self.outline_list.get_style_context().add_class("outline-list")
        self.outline_list.connect("row-activated", self._on_heading_activated)
        outline_scroll.add(self.outline_list)
        self.sidebar.pack_start(outline_scroll, True, True, 0)
        self.sidebar.get_children()[0].show()
        outline_scroll.show_all()
        self.paned.pack1(self.sidebar, resize=False, shrink=False)
        settings = WebKit2.Settings()
        # WebKit requires this for our trusted navigation/scroll evaluations.
        # Authored script markup remains disabled here and by the renderer CSP.
        settings.set_enable_javascript(True)
        settings.set_enable_javascript_markup(False)
        settings.set_javascript_can_open_windows_automatically(False)
        settings.set_allow_file_access_from_file_urls(False)
        settings.set_allow_universal_access_from_file_urls(False)
        settings.set_enable_html5_database(False)
        settings.set_enable_html5_local_storage(False)
        self.webview = WebKit2.WebView.new_with_settings(settings)
        self.webview.set_zoom_level(self.preferences["zoom"])
        self.webview.connect("decide-policy", self._on_decide_policy)
        self.webview.connect("load-changed", self._on_load_changed)
        self.webview.connect("load-failed", self._on_load_failed)
        self.webview.connect("create", lambda *_: None)
        self.webview.connect("permission-request", self._on_permission_request)
        self.find_controller = self.webview.get_find_controller()
        self.find_controller.connect("found-text", self._on_found_text)
        self.find_controller.connect("failed-to-find-text", self._on_failed_find)
        self.paned.pack2(self.webview, resize=True, shrink=False)
        self.paned.set_position(220)
        self.stack.add_named(self.paned, "document")
        self.statusbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.statusbar.get_style_context().add_class("statusbar")
        self.statusbar.set_no_show_all(True)
        self.file_label = Gtk.Label(xalign=0)
        self.file_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.stats_label = Gtk.Label(xalign=1)
        self.statusbar.pack_start(self.file_label, True, True, 0)
        self.statusbar.pack_end(self.stats_label, False, False, 0)
        root.pack_end(self.statusbar, False, False, 0)
        self.statusbar.get_children()[0].show()
        self.statusbar.get_children()[1].show()
        self.stack.set_visible_child_name("empty")

    def _empty_state(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_spacing(17)
        outer.get_style_context().add_class("empty-state")
        icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(62)
        icon.get_style_context().add_class("empty-icon")
        outer.pack_start(icon, False, False, 6)
        title = Gtk.Label(label="A quiet place for your Markdown.")
        title.set_line_wrap(True)
        title.set_justify(Gtk.Justification.CENTER)
        title.get_style_context().add_class("empty-title")
        outer.pack_start(title, False, False, 0)
        description = Gtk.Label(label="Open a document. Settle in.")
        description.get_style_context().add_class("empty-subtitle")
        outer.pack_start(description, False, False, 0)
        button = Gtk.Button(label="Open a document")
        button.set_halign(Gtk.Align.CENTER)
        button.set_margin_top(12)
        button.get_style_context().add_class("suggested-action")
        button.get_style_context().add_class("empty-open")
        button.connect("clicked", lambda *_: self.choose_document())
        outer.pack_start(button, False, False, 0)
        shortcut = Gtk.Label(label="Ctrl+O  ·  or drop a Markdown file here")
        shortcut.get_style_context().add_class("empty-subtitle")
        outer.pack_start(shortcut, False, False, 0)
        return outer

    def _install_actions(self, application):
        actions = {
            "open": (self.choose_document, ["<Primary>o"]),
            "find": (self.toggle_find, ["<Primary>f"]),
            "reload": (self.reload_document, ["<Primary>r"]),
            "outline": (lambda: self.outline_button.set_active(not self.outline_button.get_active()), ["F9"]),
            "zoom-in": (lambda: self.change_zoom(0.1), ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"]),
            "zoom-out": (lambda: self.change_zoom(-0.1), ["<Primary>minus", "<Primary>KP_Subtract"]),
            "zoom-reset": (lambda: self.change_zoom(reset=True), ["<Primary>0", "<Primary>KP_0"]),
            "close": (self.close, ["<Primary>w", "<Primary>q"]),
            "shortcuts": (self.show_shortcuts, ["<Primary>question"]),
            "about": (self.show_about, []),
        }
        for name, (callback, accelerators) in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _parameter, cb=callback: cb())
            self.add_action(action)
            if application:
                application.set_accels_for_action("win." + name, accelerators)

    def choose_document(self):
        chooser = Gtk.FileChooserNative.new("Open a document", self, Gtk.FileChooserAction.OPEN, "Open", "Cancel")
        markdown_filter = Gtk.FileFilter()
        markdown_filter.set_name("Markdown and text documents")
        for pattern in ("*.md", "*.markdown", "*.mdown", "*.mkd", "*.txt", "*.MD", "*.MARKDOWN"):
            markdown_filter.add_pattern(pattern)
        chooser.add_filter(markdown_filter)
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        chooser.add_filter(all_filter)
        directory = self.document.path.parent if self.document and self.document.path else self.preferences["last_directory"]
        if directory:
            chooser.set_current_folder(str(directory))
        if chooser.run() == Gtk.ResponseType.ACCEPT:
            path = chooser.get_filename()
            if path:
                self.open_document(path)
        chooser.destroy()

    def open_document(self, path, *, anchor=None):
        try:
            document = load_document(path, theme=self.theme)
        except DocumentError as exc:
            self.show_error(str(exc))
            return False
        self._generation += 1
        self._pending_anchor = anchor
        self._display_document(document, scroll=0)
        self._watch_document()
        return True

    def _display_document(self, document, *, scroll=0):
        self.document = document
        self._pending_scroll = scroll
        self.infobar.hide()
        self._base_uri = document.path.parent.as_uri() + "/" if document.path else "about:blank"
        self.stack.set_visible_child_name("document")
        self.header.set_title(document.title)
        self.header.set_subtitle(document.path.name if document.path else "Folio")
        self.set_title(f"{document.path.name if document.path else document.title} — Folio")
        self.file_label.set_text(str(document.path) if document.path else "Untitled document")
        self.file_label.set_tooltip_text(str(document.path) if document.path else "")
        self.stats_label.set_text(f"{document.word_count:,} words  ·  {document.reading_minutes} min read")
        self.statusbar.show()
        if document.path:
            self.preferences["last_directory"] = str(document.path.parent)
        for row in self.outline_list.get_children():
            self.outline_list.remove(row)
        minimum = min((heading.level for heading in document.headings), default=1)
        for heading in document.headings:
            row = Gtk.ListBoxRow()
            row.anchor = heading.anchor
            label = Gtk.Label(label=heading.title, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(26)
            label.set_margin_start((heading.level - minimum) * 12)
            label.set_tooltip_text(heading.title)
            row.add(label)
            self.outline_list.add(row)
        self.outline_list.show_all()
        self.outline_list.unselect_all()
        self._update_controls()
        self.webview.load_html(document.html, self._base_uri)

    def reload_document(self):
        if not self.document or not self.document.path:
            return False
        try:
            document = load_document(self.document.path, theme=self.theme)
        except DocumentError as exc:
            self.show_error(str(exc))
            return False
        self._replace_preserving_scroll(document)
        return True

    def _replace_preserving_scroll(self, document):
        self._generation += 1
        generation = self._generation
        def replace(scroll):
            if not self._destroyed and generation == self._generation:
                self._display_document(document, scroll=scroll)
        self._capture_scroll(replace)

    def _capture_scroll(self, callback):
        def received(view, result, _data):
            try:
                value = view.evaluate_javascript_finish(result)
                scroll = max(0.0, value.to_double())
            except GLib.Error:
                scroll = 0.0
            callback(scroll)
        self.webview.evaluate_javascript("window.scrollY", -1, None, None, None, received, None)

    def _evaluate(self, script):
        if not self._destroyed:
            self.webview.evaluate_javascript(script, -1, None, None, None, None, None)

    def scroll_to_heading(self, anchor):
        if self.document:
            anchors = {heading.anchor for heading in self.document.headings}
            if anchor not in anchors and "heading-" + anchor in anchors:
                anchor = "heading-" + anchor
        self._evaluate("document.getElementById(" + json.dumps(anchor) + ")?.scrollIntoView({block: 'start'})")

    def _on_heading_activated(self, _list, row):
        self.scroll_to_heading(row.anchor)

    def _on_outline_toggled(self, _button):
        if hasattr(self, "sidebar"):
            self.preferences["outline"] = self.outline_button.get_active()
            self._update_controls()

    def _update_controls(self):
        present = self.document is not None
        has_outline = bool(present and self.document.headings)
        self.outline_button.set_sensitive(has_outline)
        self.find_button.set_sensitive(present)
        self.sidebar.set_visible(has_outline and self.outline_button.get_active())
        for name in ("reload", "find", "zoom-in", "zoom-out", "zoom-reset"):
            action = self.lookup_action(name)
            if action:
                action.set_enabled(present)

    def toggle_find(self):
        if self.document is None:
            return
        self.search_bar.set_search_mode(True)
        self.search_entry.grab_focus()
        self.search_entry.select_region(0, -1)
        if self.search_entry.get_text():
            self._on_search_changed(self.search_entry)

    def hide_find(self):
        self.search_bar.set_search_mode(False)
        self.find_controller.search_finish()
        self.webview.grab_focus()

    def _on_search_changed(self, entry):
        query = entry.get_text()
        self.search_feedback.get_style_context().remove_class("search-no-results")
        if not query:
            self.find_controller.search_finish()
            self.search_feedback.set_text("")
            return
        self.find_controller.search(query, WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND, 10000)

    def _on_found_text(self, _controller, count):
        self.search_feedback.get_style_context().remove_class("search-no-results")
        self.search_feedback.set_text(f"{count:,} {'match' if count == 1 else 'matches'}")

    def _on_failed_find(self, _controller):
        self.search_feedback.set_text("No matches")
        self.search_feedback.get_style_context().add_class("search-no-results")

    def _on_search_key(self, _entry, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if event.state & Gdk.ModifierType.SHIFT_MASK:
                self.find_controller.search_previous()
            else:
                self.find_controller.search_next()
            return True
        if event.keyval == Gdk.KEY_Escape:
            self.hide_find()
            return True
        return False

    def _on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape and self.search_bar.get_search_mode():
            self.hide_find()
            return True
        return False

    def set_theme(self, theme):
        if theme not in ("light", "dark"):
            return
        self.theme = theme
        self.preferences["theme"] = theme
        self._apply_native_theme()
        if self.document:
            document = render_markdown(self.document.source_text, source_path=self.document.path, theme=theme)
            self._replace_preserving_scroll(document)
        self._save_preferences()

    def _apply_native_theme(self):
        settings = Gtk.Settings.get_default()
        theme_name = settings.get_property("gtk-theme-name")
        if theme_name.lower().endswith("-dark"):
            base_name = theme_name[:-5]
            theme_roots = [Path.home() / ".themes", Path(GLib.get_user_data_dir()) / "themes"]
            theme_roots.extend(Path(directory) / "themes" for directory in GLib.get_system_data_dirs())
            if base_name in ("Adwaita", "HighContrast") or any(
                (root / base_name / "gtk-3.0" / "gtk.css").is_file() for root in theme_roots
            ):
                # An explicit desktop '-dark' theme ignores prefer-dark=False.
                # Select its installed base for this process, preserving the family.
                settings.set_property("gtk-theme-name", base_name)
        settings.set_property("gtk-application-prefer-dark-theme", self.theme == "dark")
        icon = "weather-clear-symbolic" if self.theme == "dark" else "weather-clear-night-symbolic"
        self.theme_button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        self.theme_button.set_tooltip_text("Switch to light mode" if self.theme == "dark" else "Switch to dark mode")
        background = Gdk.RGBA()
        background.parse("#1d2025" if self.theme == "dark" else "#fbfaf7")
        self.webview.set_background_color(background)

    def change_zoom(self, amount=0, *, reset=False):
        zoom = 1.0 if reset else round(min(2.4, max(0.6, self.webview.get_zoom_level() + amount)), 2)
        self.webview.set_zoom_level(zoom)
        self.preferences["zoom"] = zoom

    def show_error(self, message):
        self.error_label.set_text(message)
        self.infobar.show()

    def _on_load_changed(self, _view, event):
        if event == WebKit2.LoadEvent.FINISHED:
            if self._pending_anchor:
                self.scroll_to_heading(self._pending_anchor)
                self._pending_anchor = None
            elif self._pending_scroll:
                self._evaluate(f"window.scrollTo(0, {float(self._pending_scroll)})")
            self._pending_scroll = 0.0
            if self.search_bar.get_search_mode() and self.search_entry.get_text():
                self._on_search_changed(self.search_entry)

    def _on_load_failed(self, _view, _event, _uri, error):
        if not self._destroyed:
            self.show_error("The document could not be displayed. " + error.message)
        return True

    def _on_permission_request(self, _view, request):
        request.deny()
        return True

    def _on_decide_policy(self, _view, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
            decision.ignore()
            return True
        if decision_type != WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        uri = action.get_request().get_uri()
        parts = urlsplit(uri)
        if action.get_navigation_type() == WebKit2.NavigationType.OTHER and uri in (self._base_uri, "about:blank"):
            decision.use()
            return True
        decision.ignore()
        if parts.scheme in ("http", "https", "mailto"):
            if action.is_user_gesture():
                try:
                    Gio.AppInfo.launch_default_for_uri(uri, self.get_display().get_app_launch_context())
                except GLib.Error as exc:
                    self.show_error("The link could not be opened. " + exc.message)
            return True
        if parts.scheme == "file" and parts.netloc in ("", "localhost"):
            path = Path(unquote(parts.path))
            fragment = unquote(parts.fragment)
            if self.document and self.document.path:
                if path in (self.document.path, self.document.path.parent) and fragment:
                    self.scroll_to_heading(fragment)
                    return True
            if path.suffix.lower() in (".md", ".markdown", ".mdown", ".mkd", ".txt"):
                self.open_document(path, anchor=fragment or None)
            else:
                self.show_error("This link is not a Markdown or text document.")
        elif not parts.scheme and parts.fragment:
            self.scroll_to_heading(unquote(parts.fragment))
        return True

    def _watch_document(self):
        self._stop_monitor()
        if not self.document or not self.document.path:
            return
        try:
            directory = Gio.File.new_for_path(str(self.document.path.parent))
            self._monitor = directory.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            self._monitor.connect("changed", self._on_file_changed)
        except GLib.Error:
            self._monitor = None

    def _on_file_changed(self, _monitor, file, other_file, _event):
        if not self.document or not self.document.path:
            return
        watched = str(self.document.path)
        if watched not in (file.get_path() if file else None, other_file.get_path() if other_file else None):
            return
        if self._reload_timeout:
            GLib.source_remove(self._reload_timeout)
        self._reload_timeout = GLib.timeout_add(400, self._reload_from_monitor)

    def _reload_from_monitor(self):
        self._reload_timeout = 0
        if not self._destroyed:
            self.reload_document()
        return GLib.SOURCE_REMOVE

    def _stop_monitor(self):
        if self._reload_timeout:
            GLib.source_remove(self._reload_timeout)
            self._reload_timeout = 0
        if self._monitor:
            self._monitor.cancel()
            self._monitor = None

    def _on_drop(self, _widget, context, _x, _y, selection, _info, timestamp):
        success = False
        uris = selection.get_uris()
        if uris:
            file = Gio.File.new_for_uri(uris[0])
            path = file.get_path()
            if path:
                success = self.open_document(path)
        Gtk.drag_finish(context, success, False, timestamp)

    def _save_preferences(self):
        if not self.is_maximized():
            width, height = self.get_size()
            self.preferences.update(width=width, height=height)
        self.preferences["outline"] = self.outline_button.get_active()
        save_settings(self.preferences)

    def _on_delete(self, *_args):
        self._save_preferences()
        return False

    def _on_destroy(self, *_args):
        self._destroyed = True
        self._generation += 1
        self._stop_monitor()

    def show_shortcuts(self):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE, text="Keyboard shortcuts")
        dialog.format_secondary_text("Ctrl+O   Open document\nCtrl+F   Find in document\nEnter / Shift+Enter   Next / previous match\nEscape   Close search\nCtrl+R   Reload document\nF9   Show or hide outline\nCtrl++ / Ctrl+−   Larger / smaller text\nCtrl+0   Reset text size\nCtrl+W   Close window")
        dialog.connect("response", lambda widget, *_: widget.destroy())
        dialog.show()

    def show_about(self):
        dialog = Gtk.AboutDialog(transient_for=self, modal=True, program_name="Folio", version="0.1.0", comments="A quiet place for your Markdown.", logo_icon_name="text-x-generic", license_type=Gtk.License.MIT_X11)
        dialog.connect("response", lambda widget, *_: widget.destroy())
        dialog.show()
