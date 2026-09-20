# Folio 0.1.0

Folio's first release provides a native Linux Markdown reader with a heading
outline, document search, light and dark themes, adjustable text size, and
automatic reload. It supports tables, task lists, fenced code, local images,
and links between documents. Reading never modifies source files.

The downloadable package is `folio-0.1.0-x86_64.flatpak`, available from
[GitHub Releases](https://github.com/romitdasgupta/mdreader/releases/tag/v0.1.0).
Follow the [installation instructions](../README.md#install). Flatpak installs
the required GNOME runtime automatically; a separate Python installation is not
needed. The first installation requires internet access. Folio itself has no
network permission.

## Verification

Release verification completed on **2026-09-20**. The
[passing package build](https://github.com/romitdasgupta/mdreader/actions/runs/35497969853)
built the package, installed it, passed all 14 GUI checks, and uploaded the bundle
and checksum. That run tested application revision
[`a117897`](https://github.com/romitdasgupta/mdreader/commit/a1178977bac7fdb8df8f6f042ba4896147d22153).
See [GitHub Actions](https://github.com/romitdasgupta/mdreader/actions/workflows/flatpak.yml)
for subsequent builds.

Tests used Ubuntu 26.04 on x86-64, including disposable containers with Xvfb and
D-Bus. The installed application ran on GNOME Platform 50 with Python 3.13,
GTK 3, and WebKitGTK 2.54 through the WebKit2 4.1 API.

| Check | Result |
| --- | --- |
| Core tests | 76 passed, covering rendering, preferences, input errors, content isolation, and source-installer migration. |
| Installed GUI | 14 checks passed locally and in GitHub Actions, including heading navigation, search, themes, zoom, error recovery, and a 10,009-line document. |
| Fresh Flatpak installation | An account without the application or runtime installed the bundle and its native dependencies successfully. Both ordinary-user and root test installations passed. |
| File chooser and nearby resources | The installed chooser retained the original document path; nearby images rendered and sibling Markdown links opened. An external atomic file replacement triggered reload without modifying document or image contents. |
| Desktop launcher and removal | The exported desktop entry launched both an empty window and a file through `gio launch`. Uninstall removed the launcher and preserved documents and preferences. |
| Appearance | Fresh light, dark, and narrow-window screenshots were inspected. |
| Python distribution | Source archive and wheel built successfully. A disposable wheel installation verified packaged styles, rendering, and the launcher outside the checkout. |
| Package metadata | AppStream, desktop entry, Flatpak manifest, dependency hashes, and dependency license files validated. |

The chooser uses GTK's file dialog directly so document paths retain access to
sibling images, links, and directory monitoring inside the read-only sandbox.
The GUI regression verifies the selected path and nearby image before reopening
any document directly.

## Supported scope and limits

- The binary release targets **x86-64 Linux desktops with Flatpak**. Other CPU
  architectures and other Linux distributions have not been independently tested.
- GUI verification used X11 and Xvfb. Wayland-only sessions remain unverified.
- Exported desktop launches were tested; individual desktop-menu and file-manager
  implementations were not independently exercised.
- Actual external browser and email-handler launches remain unverified.
- Updates to Folio require downloading and installing a newer bundle. Shared
  runtimes receive updates through `flatpak update`; there is no automatic Folio
  update feed or Flathub listing.

For repeatable build and release commands, see
[Distributing Folio](DISTRIBUTION.md). Product scope and implementation contracts
are documented in [PRODUCT.md](PRODUCT.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
