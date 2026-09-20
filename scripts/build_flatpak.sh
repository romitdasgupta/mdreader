#!/bin/sh
# Build the consumer bundle. Flatpak/flatpak-builder and Flathub are prerequisites.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$root/artifacts/flatpak"}
mkdir -p "$output"
output=$(CDPATH= cd -- "$output" && pwd)
case "$output" in
    "$root/artifacts"|"$root/artifacts/"*|"$root/dist"|"$root/dist/"*) ;;
    "$root"|"$root/"*)
        printf 'Use artifacts/, dist/, or a directory outside the checkout for build output.\n' >&2
        exit 1 ;;
esac
version=$(python3 -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' "$root/pyproject.toml")
arch=$(flatpak --default-arch)
bundle="folio-$version-$arch.flatpak"

flatpak-builder --user --install-deps-from=flathub --disable-rofiles-fuse \
    --force-clean --state-dir="$output/state" --repo="$output/repo" \
    "$output/build" "$root/packaging/flatpak/io.github.romitdasgupta.mdreader.json"
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "$output/repo" "$output/$bundle" io.github.romitdasgupta.mdreader
(cd "$output" && sha256sum "$bundle" > "$bundle.sha256")
printf 'Built %s\n' "$output/$bundle"
