# Distributing Folio

Folio is distributed as an x86-64 Flatpak bundle through
[GitHub Releases](https://github.com/romitdasgupta/mdreader/releases).
GNOME Platform 50 supplies Python, PyGObject, GTK 3, and WebKitGTK 4.1.
The package includes hash-pinned markdown-it-py and mdurl dependencies; the SDK
and Python build backend are needed only when building.

The application ID is `io.github.romitdasgupta.mdreader`. Its display name is
Folio. See the [release verification](RELEASE.md) for tested behavior and limits.

## Build

Install Flatpak, flatpak-builder, and Python 3.11 or newer. On Ubuntu 24.04 or newer:

```sh
sudo apt install flatpak flatpak-builder python3
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
sh scripts/build_flatpak.sh
```

Run from the repository root at the revision being released. The script installs
the GNOME SDK/runtime and writes the bundle and `.sha256` file under
`artifacts/flatpak/`. It verifies dependency downloads against manifest hashes,
then builds without network access inside the build sandbox. Allow several
gigabytes for the initial SDK/runtime download and build cache.

To choose another output directory, pass it as the script's first argument. Use
`artifacts/`, `dist/`, or a directory outside the checkout so build output is not
copied back into the application's sources.

[GitHub Actions](https://github.com/romitdasgupta/mdreader/blob/main/.github/workflows/flatpak.yml) also builds the package on
pushes and pull requests. It installs and tests the application on GNOME Platform
before uploading the bundle and checksum. A `v*` tag must match the version in
`pyproject.toml`. The workflow produces artifacts; publishing is a separate step.

## Verify

Use a disposable user account, VM, or container. Start without Folio or the GNOME
runtime installed and follow the [consumer installation steps](../README.md#install).
Accept runtime installation when prompted. The bundle embeds the runtime
repository URL so Flatpak can resolve native dependencies; do not use `--no-deps`.

After installation, run the GUI suite from the repository root:

```sh
flatpak run --command=python3 io.github.romitdasgupta.mdreader -I \
  "$PWD/scripts/smoke_gui.py" --installed --artifacts /var/data/verification
```

On a headless test machine, install `dbus-x11`, `xvfb`, and `xauth`, then prefix
that command with `xvfb-run -a dbus-run-session --`. Minimal containers also need
the desktop services configured in the [CI workflow](https://github.com/romitdasgupta/mdreader/blob/main/.github/workflows/flatpak.yml).
The report and screenshots are written to
`~/.var/app/io.github.romitdasgupta.mdreader/data/verification/`.
The probe rejects source/editable imports and tests the installed application on
the runtime, without the SDK. Exit 2 means GUI verification was unavailable.

Inspect the light, dark, and narrow screenshots. Also open a document through the
installed launcher, follow a relative Markdown link, and replace the current file
atomically from another program to verify reload. Check the exported desktop
entry's file launch and uninstall behavior using disposable documents and preferences.

## Files and permissions

The sandbox grants read-only host filesystem access so nearby images, relative
links, and directory monitoring work across ordinary document locations. Flatpak
still hides reserved and private system paths. Folio uses GTK's file dialog
directly because a portal's single-file export can hide sibling resources.

The package has no network permission. Preferences use Flatpak's private
application directory and are separate from a source installation. The renderer's
image containment, size limits, content security policy, and navigation checks
remain in effect.

## Publish and maintain

Before a release, update the version in `pyproject.toml`, `folio/__init__.py`,
`folio/app.py`, and the AppStream release metadata. Update installation examples
and release notes to match. Run the core tests, wheel verification, installed
Flatpak GUI checks, and desktop-launcher checks, then validate desktop and
AppStream metadata.

Commit and tag the release revision, wait for its GitHub Actions build to pass,
and download that run's `folio-flatpak-x86_64` artifact. Verify the checksum with
`sha256sum -c <bundle>.sha256`. Attach the matching `.flatpak` and `.sha256` files
to the GitHub release. Keep build output, caches, and temporary test evidence out
of Git. Release notes should state the supported architecture, link the
installation instructions, and describe any unverified behavior.

Users upgrade by downloading a newer bundle and running
`flatpak install --user ./<new-bundle>.flatpak`. There is no automatic Folio
update feed. `flatpak update --user` updates shared runtimes. Refresh the GNOME
runtime branch before it becomes unsupported, and update Python dependency
versions and hashes deliberately, followed by the same verification.

Folio uses Flathub's shared runtime but has no Flathub application listing. A later
submission needs public tagged sources, published screenshots, and a human
maintainer following the [current Flathub requirements](https://docs.flathub.org/docs/for-app-authors/requirements),
including disclosure of generated material and human-authored submission interactions.

References: [bundles and runtime discovery](https://docs.flatpak.org/en/latest/single-file-bundles.html),
[sandbox permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html),
[GNOME 50 runtime contents](https://gitlab.gnome.org/GNOME/gnome-build-meta/-/blob/gnome-50/elements/sdk-platform.bst).
