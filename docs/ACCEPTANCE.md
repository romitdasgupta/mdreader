# Folio acceptance checklist

This checklist verifies the native GTK 3 and WebKitGTK 4.1 reader defined in [PRODUCT.md](PRODUCT.md). An unchecked box is a check to run, not a claim of a defect. Record automated, visual, and environment-blocked results separately. Open, render, outline, find, themes, keyboard operation, reload, and graceful errors are required; zoom and other optional polish are checked only if implemented.

## Test fixtures

- `sample.md`: six heading levels, paragraphs, emphasis, links, ordered and unordered nested lists, blockquotes, a horizontal rule, fenced code, a table, a task list, Unicode, and a local image.
- A folder with spaces and non-ASCII characters; a Markdown file and image inside it; a linked sibling Markdown document and heading anchor.
- An empty Markdown file, a UTF-8 BOM file, a missing path, an unreadable file, a directory supplied as a file, invalid UTF-8 bytes, and a file exceeding the 10 MiB input limit.
- A long document of at least 10,000 lines, including a very long code line and a wide table.
- An untrusted document with raw HTML, script/event-handler syntax, `javascript:` and `file:` links, remote images, and local image references outside its folder.

## First use and opening documents

- [ ] Launching without a path opens a native application window with a clear way to open a Markdown file.
- [ ] Opening a Markdown file from the native file chooser displays its content and identifies the current file in the window.
- [ ] A command-line path opens that document; a path containing spaces or Unicode works without manual escaping beyond normal shell quoting.
- [ ] Canceling the chooser preserves the current document and scroll position.
- [ ] Opening an empty file is a successful, understandable empty-document state.
- [ ] Missing, unreadable, invalidly encoded, non-file, or larger-than-10-MiB inputs produce an actionable error instead of a crash; the previous valid document remains available. UTF-8 BOM files open correctly.
- [ ] Opening and navigating documents never modifies their contents. Confirm fixture checksums are unchanged after the session.

## Reading quality

- [ ] The sample renders recognizable headings, emphasis, lists, quotations, code, links, tables, task lists, and images supported by the agreed Markdown dialect.
- [ ] Body text uses approximately 17–18 px text and a centered 760–860 px reading column at normal desktop width, with visible heading hierarchy and sufficient line spacing.
- [ ] Code preserves whitespace and uses a monospace face. Long code and wide tables remain accessible without forcing ordinary paragraphs wider than the reading area.
- [ ] Unicode characters remain intact; long words and narrow windows do not hide primary controls.
- [ ] Relative images resolve against the document's directory, including spaces and Unicode; missing or denied images do not prevent the rest of the document from displaying.
- [ ] Relative Markdown links open the intended local document; heading links navigate within the current document.
- [ ] At ordinary desktop sizes, the application remains legible in its supported light and dark appearances.

## Navigation and keyboard flow

- [ ] `Ctrl+O`, `Ctrl+F`, and `Ctrl+R` work from the reading area; standard keyboard scrolling and selectable text still work.
- [ ] Keyboard focus is visible, moves through primary controls predictably, and can return to the document without a pointer.
- [ ] The outline can be collapsed; selecting an entry scrolls to the corresponding heading; duplicate headings do not select the wrong section. A document without headings has no distracting empty sidebar.
- [ ] `Ctrl+F` shows search; matching text is visibly located, Enter and Shift+Enter traverse next/previous matches, a no-match query is clear, and Escape closes search and returns focus to reading.
- [ ] If the MVP includes zoom, repeated increase/decrease operations stay within sensible limits and reset returns to the documented default.
- [ ] Reload displays saved changes to the current file; a reload failure leaves the last successfully rendered content readable and reports the problem.
- [ ] When automatic reload ships, saving the document in another process updates the view after debouncing without stealing focus; reading position is preserved where feasible. Atomic file replacement and temporary deletion do not crash the app.

## Untrusted content and privacy

- [ ] Raw Markdown HTML appears as text and cannot execute scripts or event handlers, open windows, or navigate the reading surface unexpectedly. Trusted application scripts used for reader behavior are separate from document content.
- [ ] `javascript:`, `data:`, and unsupported URI schemes cannot launch applications through document links. Explicit external opening is limited to `http:`, `https:`, and `mailto:`.
- [ ] Remote image URLs are blocked, and merely opening a document makes no unsolicited network requests.
- [ ] Only supported local image assets inside the document's directory tree are embedded. Traversal and symlink references outside that tree are denied gracefully; local Markdown links follow the documented navigation policy.
- [ ] External web links require an explicit click and open through the desktop's external browser flow, rather than replacing the document.
- [ ] The application does not transmit document contents or document paths as analytics.

## Responsiveness and release evidence

- [ ] A 10,000-line document opens and can be scrolled and searched without a crash. Record load time and the test machine; target first render within 2 seconds on a normal developer desktop.
- [ ] Resize, close, and open actions remain responsive during normal use; a parser error cannot terminate the application.
- [ ] The documented clean-machine installation and launch commands work with the declared Linux dependencies.
- [ ] Automated checks pass for parsing/rendering boundaries and safe file/link/resource behavior.
- [ ] A real GUI or virtual-display smoke test verifies window creation, document loading, and clean exit. A display-unavailable result must be recorded as blocked, not passed.
- [ ] A tester records the tested distribution, dependency versions, command used, pass/fail outcome, and remaining limitations.

## Explicit scope limits

The first release is for reading local Markdown. Editing, synchronization, accounts, collaboration, remote document fetching, and publishing are outside the acceptance scope unless the product owner explicitly adds them.
