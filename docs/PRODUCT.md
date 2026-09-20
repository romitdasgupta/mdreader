# Product scope

Folio is a native Linux application for reading local Markdown. It should make
opening a README, following its structure and reading prose, code and tables feel
straightforward. Reliability and comfortable typography guide feature decisions.

## Reading experience

- Open a document through the GTK chooser, command line, desktop file association
  or drag and drop. One window displays one document; its title identifies the file.
- Render headings, paragraphs, emphasis, links, lists, quotes, fenced code, tables,
  task lists, strikethrough and supported local images. Preserve code whitespace
  and let wide code and tables scroll within the reading column.
- Navigate a collapsible heading outline and follow local Markdown links.
- Search the current document with `Ctrl+F`; use Enter and Shift+Enter for the
  next and previous result, and Escape to dismiss search. Show clear no-match
  feedback.
- Switch between light and dark themes and adjust text size. Remember theme,
  window size, outline visibility and zoom when settings can be saved.
- Reload automatically after file changes, including atomic saves, while
  preserving reading position where feasible. `Ctrl+R` provides explicit reload.
- Keep the current page readable when a replacement cannot open. Missing or
  unreadable files receive a nonfatal error; empty documents have an empty state.

## Visual principles

Use one resizable window with a compact native header and an obvious Open action.
The document should remain the focus, with quiet outline text, useful tooltips
and ordinary keyboard navigation.

Use a centered reading column with generous spacing, system fonts, clear heading
levels and a monospace face for code. Narrow windows reduce padding and allow the
outline to be hidden. Both themes should keep native controls and document
content readable; status information should remain secondary.

The first screen offers a single clear action to open a document. Errors explain
what happened without replacing the current reading surface. Avoid onboarding
steps, dashboards and controls unrelated to reading.

## Content and installation

Reading never changes source files. Relative images and local links resolve
against the document's original directory. Supported raster images stay within
that directory tree; missing or blocked images have readable fallback text.
Raw HTML is displayed as text, document scripts are blocked and remote images
are not fetched. External links open through the desktop handler when clicked.

The consumer Flatpak installs the required runtime dependencies and adds a desktop
launcher without changing default file associations. The first binary release
supports x86-64 Linux desktops. See the [README](../README.md) for installation,
shortcuts and file-size limits.

## Scope limits

Folio does not edit documents or provide accounts, synchronization, cloud
services, AI features, plugins, document libraries, multi-document tabs, PDF
export or document publishing. It runs locally without a browser window or
application server.

Changes should improve opening, navigating and reading real documents while
preserving source files and keeping the application small. Technical boundaries
are documented in [architecture](ARCHITECTURE.md); release checks are in
[release verification](RELEASE.md).
