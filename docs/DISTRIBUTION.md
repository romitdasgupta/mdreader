# Distributing Folio

Folio's consumer package is an x86-64 Flatpak bundle published on GitHub Releases.
It uses GNOME Platform 50 for Python, PyGObject, GTK 3 and WebKitGTK 4.1, and bundles
hash-pinned markdown-it-py and mdurl wheels. The SDK and build backend are build-time
dependencies. A wheel alone cannot supply the native desktop stack.

The application ID is `io.github.romitdasgupta.mdreader`, matching the source repository.
The display name remains Folio. The source installer removes its initial
`io.github.folio.Reader` launcher/icon when rerun. Flatpak keeps its preferences
separately from a source installation.

## Build

Install Flatpak, flatpak-builder and Python 3.11 or newer using your distribution's
package manager. On Ubuntu 24.04 or newer, the build prerequisites are:

```sh
sudo apt install flatpak flatpak-builder python3
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
sh scripts/build_flatpak.sh
```

Run from a checked-out release revision. The script installs the GNOME SDK/runtime,
builds without network access inside the build sandbox, and emits the bundle and
its `.sha256` file under `artifacts/flatpak/`. Source downloads happen before the
sandboxed build and are checked against manifest hashes. Initial SDK downloads need
several gigabytes of disk space. An optional output directory must be under
`artifacts/` or `dist/`, or outside the checkout, to avoid recursive source copying.

GitHub Actions builds this manifest and runs the installed GUI smoke checks on
each push/PR. It uploads a bundle only if those checks pass. A `v*` tag must match
the version in `pyproject.toml`. The workflow produces artifacts; publishing remains
an explicit maintainer action.

## Verify the consumer package

Use a disposable user account, VM or container with a graphical session. Start
with no application or GNOME runtime installed, then follow the README's install
command. Accept the runtime repository prompt. The runtime URL is embedded in the
bundle so Flatpak can resolve the native dependencies. Do not use `--no-deps`.

For automated UI verification after installing, from the checkout:

```sh
flatpak run --command=python3 io.github.romitdasgupta.mdreader -I \
  "$PWD/scripts/smoke_gui.py" --installed --artifacts /var/data/verification
```

On a headless test machine, prefix that command with
`xvfb-run -a dbus-run-session --` after installing `dbus-x11`, `xvfb` and `xauth`.
The report and screenshots are in
`~/.var/app/io.github.romitdasgupta.mdreader/data/verification/`.
The probe rejects source/editable imports and exercises the installed code on
the Platform runtime, without the SDK. Exit 2 is an unavailable GUI, not a pass.

Folio uses GTK's file chooser directly. A portal's individual-file export can
hide the document's siblings even with read-only directory permission; retaining
the original path preserves images, links and monitoring. The smoke check verifies
the selected path and image rendering. Also open a document through the installed
launcher, follow a relative Markdown link, then atomically replace the current
file from another program and observe the reload. Check menu and Open With launches.

The sandbox grants read-only host filesystem access so sibling resources and
parent-directory monitoring work across ordinary document locations. Flatpak
still hides reserved/system-private paths; this is not a promise to read every
host path. Folio has no network permission and retains its renderer's containment,
size limits, CSP and navigation checks. Writable application data is confined to
Flatpak's normal private directories.

## Publish and maintain

Before publishing, run core tests, wheel verification, the installed Flatpak smoke
and desktop-launcher check. Validate desktop/AppStream metadata. Review source and release
contents, and make sure the source repository is public. Commit the verified
revision and tag it `v0.1.0`; attach only the matching `.flatpak` and `.sha256` files
to the GitHub release. Keep builds, caches and test evidence out of Git. The release
notes should state x86-64 Linux support and link the README installation steps.

Users install newer bundles with the same `flatpak install --user` command.
There is no automatic application update feed yet. `flatpak update --user` keeps
the shared runtime updated. Track GNOME runtime support and refresh the manifest
before its branch becomes unsupported; update Python pins and hashes deliberately,
then rerun the same checks.

Flatpak and Flathub are separate. This release uses Flatpak's package format and
Flathub's shared GNOME runtime without a Folio store listing. A later Flathub
submission needs a public tagged source, published screenshots, and human review.
Follow [the current submission requirements](https://docs.flathub.org/docs/for-app-authors/requirements),
including disclosure of generated application/packaging material and their rules
requiring human-authored submission interactions. This repository's implementation
and packaging were developed with AI agents.

References: [bundles and runtime discovery](https://docs.flatpak.org/en/latest/single-file-bundles.html),
[sandbox permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html),
[GNOME 50 runtime contents](https://gitlab.gnome.org/GNOME/gnome-build-meta/-/blob/gnome-50/elements/sdk-platform.bst).
