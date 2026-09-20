# Folio

Folio is a native Linux application for reading Markdown files. Its promise is simple: open a document and enjoy reading it immediately.

This document records the product decisions of the requested Steve Jobs-inspired product role. The role describes a design perspective, not the real person.

## The experience

The document is the product. Use native desktop controls around a calm, carefully typeset reading surface. Keep the first screen understandable without instructions and keep the reading screen free of unnecessary controls.

Build a reader, not an editor. A user should be able to open a README, follow its outline, search its contents, and read code, tables, and images comfortably.

## Required v1 features

1. **Open a local document.** Support a native file chooser and a file path passed on the command line. Accept `.md`, `.markdown`, and plain text when explicitly selected. Opening another document replaces the current document. The window title identifies the open file.
2. **Render real Markdown clearly.** Support headings, paragraphs, emphasis, links, lists, blockquotes, thematic breaks, inline code, fenced code, and local images. Include tables, task lists, and strikethrough where supported by the selected parser. Preserve whitespace in code and provide scrolling for wide content. Malformed Markdown remains readable.
3. **Navigate a heading outline.** Show a collapsible sidebar with document headings and a clear hierarchy. Clicking a heading moves to that section. Hide or gracefully empty the outline for documents without headings. Do not reserve a large blank sidebar unnecessarily.
4. **Find text.** `Ctrl+F` exposes document search. Enter and Shift+Enter navigate matches; Escape dismisses search. Indicate when a query has no matches. Search is scoped to the current document.
5. **Read in light or dark mode.** Provide an obvious theme control, maintain adequate contrast, and apply the choice to both the surrounding interface and the document. Remember the preference if practical.
6. **Operate from the keyboard.** At minimum, implement `Ctrl+O` to open, `Ctrl+F` to find, `Ctrl+R` to reload, and Escape to dismiss transient search UI. Preserve standard scrolling and selectable text.
7. **Handle failure gracefully.** Missing or unreadable files produce a helpful message containing the relevant file name. A failed open must not destroy the current readable document. Empty files are a valid state, not an error.

## Desirable only after the core works

- Automatic reload when the open file changes, preserving reading position where possible; avoid stealing keyboard focus.
- Remember the last chosen theme, window dimensions, and outline visibility.
- Drag and drop one local Markdown file.
- Increase, decrease, and reset text size with standard shortcuts.
- Native desktop launcher and file association metadata.

These should not delay a reliable opening, reading, searching, and navigation loop. If automatic reload is omitted, the explicit Reload command remains available.

## Visual direction

- **Window:** One resizable window. A compact native header presents the Folio name or document name, Open, outline visibility, Find, and theme. Use icons with tooltips or short unambiguous text labels, depending on available native controls.
- **Reading surface:** A comfortable centered column, approximately 760–860 logical pixels at normal text size, with generous side padding. Let wider code and tables scroll instead of clipping content. At narrow window widths, reduce margins before sacrificing legibility.
- **Typography:** Prefer an installed system sans serif for interface and prose, with a system monospace for code. Use roughly 17–18 logical pixels for body text, generous line height, and an unmistakable heading hierarchy. Avoid downloading fonts.
- **Color:** Light mode uses a soft neutral or warm white page with dark text. Dark mode uses deep charcoal with softened white text. A restrained blue accent identifies links and active controls. Native theme fidelity takes precedence over forcing every color.
- **Outline:** Quiet secondary text, generous enough row height, indentation by heading level, and a visible selection state. The document remains visually dominant.
- **Empty state:** A restrained document symbol, the line “A quiet place for your Markdown.”, and one prominent “Open a document” action. A secondary line may mention `Ctrl+O`. Do not introduce onboarding steps or demo dashboards.
- **Errors:** Plain language, actionable, and visually distinct. Keep the previous document visible when a replacement cannot open.

## Content behavior

- Resolve relative images and local document links against the open file's directory.
- Navigate same-document heading links inside the reader.
- Open local Markdown links in the current window when supported; external web links use the user's default browser.
- Treat raw HTML and script content as untrusted. Markdown must not execute scripts or silently load remote active content.
- Prefer local images; remote image support is outside the required v1 scope.
- Keep source files unchanged. Reading and reloading never write to a document.

## Explicitly out of scope

No editing, accounts, synchronization, cloud services, AI features, plugin marketplace, multi-document tab management, document library, PDF export, or publishing workflow. Do not introduce a web server or require a browser window for the application experience.

## Acceptance priorities

### P0: it must ship

- A documented command launches a native Linux desktop window.
- The native chooser and command-line opening both display a real Markdown file.
- Headings, emphasis, lists, links, code blocks, blockquotes, and local images render legibly.
- Heading outline navigation and document search work in a document long enough to require scrolling.
- Light and dark modes are readable; the window remains usable when resized.
- Failed opens and empty documents are handled gracefully without crashing.
- The user can reload a file changed by another program.
- A clean setup guide states required system dependencies and the exact launch command.

### P1: polish and confidence

- Tables, task lists, long lines, Unicode text, and duplicate heading names are exercised.
- Keyboard shortcuts work without interfering with ordinary document selection and scrolling.
- Local image paths containing spaces work; unavailable images degrade gracefully.
- A sample Markdown document demonstrates the features and provides a useful first manual check.
- If automatic reload ships, a changed document refreshes without snapping unnecessarily to the top.

## Decision rule

When time is limited, choose the smallest implementation that makes opening and reading a real document feel complete. Reliability, typography, search, and navigation outweigh feature count.

## Final product review

**Approved for the initial release from a product and visual-design perspective.** The final native GTK screenshots were inspected directly: [first use](../artifacts/folio-empty.png), [light mode](../artifacts/folio-light.png), [dark mode](../artifacts/folio-dark.png), and [narrow window](../artifacts/folio-narrow.png).

The delivered experience matches the intended scope: an obvious first action, restrained native controls, a useful heading hierarchy, comfortable prose, legible code and tables, and coherent light and dark appearances. The narrow view preserves the reading surface with the outline hidden. Native desktop accent colors are acceptable under the theme-fidelity rule above.

The final captures confirm that the light-mode chrome mismatch is resolved and both themes have readable toolbar controls. The earlier pale buttons in a dark-mode capture were an intermediate GTK animation frame; deterministic captures after the transition show correct contrast. No further product or design changes are required for v1.

Behavioral evidence comes from the separately recorded core and native GUI verification, including real GDK keyboard dispatch, native chooser acceptance/cancel, outline navigation, search, reload, error recovery, and long-document reading. See [release verification](RELEASE.md) for the test environment, results, and remaining limits; visual approval does not assert untested distribution or desktop-integration coverage.
