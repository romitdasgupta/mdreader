"""Read local Markdown and turn it into an inert, self-contained reading page.

This module deliberately has no GTK dependency. The native window consumes the
document and its outline without knowing anything about Markdown tokenization.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from importlib.resources import files
import math
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token


MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_EMBEDDED_IMAGE_BYTES = 20 * 1024 * 1024
_WORDS = re.compile(r"\b\w+(?:[’'-]\w+)*\b", re.UNICODE)
_TASK_MARKER = re.compile(r"^\[([ xX])\](?:[ \t]+|$)")


class DocumentError(Exception):
    """A user-presentable failure to read or prepare a document."""


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    anchor: str


@dataclass(frozen=True)
class RenderedDocument:
    title: str
    html: str
    headings: tuple[Heading, ...]
    word_count: int
    reading_minutes: int
    path: Path | None
    source_text: str


def _plain_text(tokens: list[Token]) -> str:
    parts = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            parts.append(token.content)
        elif token.type == "image":
            parts.append(_plain_text(token.children or []) or token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts)


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", normalized).strip("-") or "section"


def _headings(tokens: list[Token]) -> tuple[Heading, ...]:
    headings = []
    used = set()
    next_suffix = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        inline = tokens[index + 1]
        title = _plain_text(inline.children or []).strip()
        base = "heading-" + _slug(title)
        anchor = base
        suffix = next_suffix.get(base, 2)
        while anchor in used:
            anchor = f"{base}-{suffix}"
            suffix += 1
        next_suffix[base] = suffix
        used.add(anchor)
        token.attrSet("id", anchor)
        headings.append(Heading(int(token.tag[1:]), title, anchor))
    return tuple(headings)


def _task_lists(tokens: list[Token]) -> None:
    for index, token in enumerate(tokens):
        if (
            token.type != "inline"
            or index < 2
            or tokens[index - 1].type != "paragraph_open"
            or tokens[index - 2].type != "list_item_open"
            or not token.children
            or token.children[0].type != "text"
        ):
            continue
        first = token.children[0]
        match = _TASK_MARKER.match(first.content)
        if not match:
            continue
        checked = match[1].lower() == "x"
        first.content = first.content[match.end():]
        checkbox = Token("html_inline", "", 0)
        checkbox.content = (
            '<input class="task-checkbox" type="checkbox" disabled'
            + (' checked aria-label="Completed"' if checked else ' aria-label="Not completed"')
            + "> "
        )
        token.children.insert(0, checkbox)
        tokens[index - 2].attrJoin("class", "task-list-item")


def _image_type(data: bytes) -> str | None:
    # Inspect bytes instead of trusting a filename extension. In particular,
    # renaming an SVG to .png must never embed executable markup.
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _embed_image(token: Token, root: Path | None, remaining: int) -> int:
    alt = _plain_text(token.children or []) or token.content or "Image"
    src = token.attrGet("src") or ""
    reason = "The image is unavailable."
    try:
        parts = urlsplit(src)
        if parts.scheme or parts.netloc:
            reason = "Remote and embedded source images are not loaded."
            raise ValueError(reason)
        if root is None or not parts.path:
            raise ValueError("No local image path.")
        image_path = (root / unquote(parts.path)).resolve()
        if not image_path.is_relative_to(root):
            reason = "Images must be inside the document’s folder."
            raise ValueError(reason)
        if not image_path.is_file():
            raise ValueError("Not a regular image file.")
        limit = min(MAX_IMAGE_BYTES, remaining)
        if image_path.stat().st_size > limit:
            reason = "The image exceeds the reading page’s size limit."
            raise ValueError(reason)
        with image_path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Image is too large.")
        mime = _image_type(data)
        if mime is None:
            reason = "This image format is not supported; use PNG, JPEG, GIF, or WebP."
            raise ValueError(reason)
        token.attrSet("src", f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}")
        token.attrSet("loading", "lazy")
        token.attrSet("decoding", "async")
        return len(data)
    except (OSError, ValueError, RuntimeError):
        # Generated markup contains only escaped text, never the original URL.
        token.type = "html_inline"
        token.tag = ""
        token.children = None
        token.attrs = {}
        token.content = (
            f'<span class="image-fallback" role="img" title="{escape(reason, quote=True)}">'
            f"Image unavailable: {escape(alt)}</span>"
        )
        return 0


def _safe_link(href: str, path: Path | None, fragments: dict[str, str]) -> str | None:
    try:
        parts = urlsplit(href)
        if parts.scheme:
            return href if parts.scheme.lower() in {"https", "http", "mailto"} else None
        if parts.netloc:
            return None
        fragment = parts.fragment
        if not parts.path:
            fragment = fragments.get(unquote(fragment), fragment)
            return urlunsplit(("", "", "", parts.query, fragment))
        if path is None:
            return href
        target = (path.parent / unquote(parts.path)).resolve()
        if target == path:
            fragment = fragments.get(unquote(fragment), fragment)
        return target.as_uri() + (f"?{parts.query}" if parts.query else "") + (
            f"#{fragment}" if fragment else ""
        )
    except (OSError, ValueError, RuntimeError):
        return None


def _resources(tokens: list[Token], path: Path | None, headings: tuple[Heading, ...]) -> None:
    fragments = {heading.anchor.removeprefix("heading-"): heading.anchor for heading in headings}
    fragments.update({heading.anchor: heading.anchor for heading in headings})
    remaining = MAX_EMBEDDED_IMAGE_BYTES
    for token in tokens:
        if not token.children:
            continue
        link_tags = []
        for child in token.children:
            if child.type == "image":
                remaining -= _embed_image(child, path.parent if path else None, remaining)
            elif child.type == "link_open":
                href = _safe_link(child.attrGet("href") or "", path, fragments)
                if href is None:
                    child.tag = "span"
                    child.attrs.pop("href", None)
                    child.attrJoin("class", "blocked-link")
                else:
                    child.attrSet("href", href)
                    child.attrSet("rel", "noreferrer noopener")
                link_tags.append(child.tag)
            elif child.type == "link_close" and link_tags:
                child.tag = link_tags.pop()


def render_markdown(
    source: str,
    *,
    source_path: Path | None = None,
    theme: str = "light",
) -> RenderedDocument:
    """Render Markdown with packaged styling and strictly local, bounded assets."""
    if theme not in {"light", "dark"}:
        raise ValueError("theme must be 'light' or 'dark'")
    path = Path(source_path).expanduser().resolve() if source_path is not None else None
    parser = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    tokens = parser.parse(source)
    headings = _headings(tokens)
    title = next((heading.title for heading in headings if heading.level == 1 and heading.title), None)
    title = title or (path.stem if path else "Untitled")
    _task_lists(tokens)
    readable = " ".join(
        _plain_text(token.children or []) if token.type == "inline" else token.content
        for token in tokens
        if token.type in {"inline", "code_block", "fence"}
    )
    word_count = len(_WORDS.findall(readable))
    reading_minutes = max(1, math.ceil(word_count / 220)) if source.strip() else 0
    _resources(tokens, path, headings)
    content = parser.renderer.render(tokens, parser.options, {})
    if not source.strip():
        content = '<div class="empty-document"><p>This document is empty.</p><p>Its next words are still ahead.</p></div>'
    stylesheet = files("folio").joinpath("resources/reader.css").read_text(encoding="utf-8")
    csp = (
        "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; "
        "img-src data:; font-src 'none'; connect-src 'none'; object-src 'none'; "
        "frame-src 'none'; base-uri 'none'; form-action 'none'"
    )
    html = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{escape(csp, quote=True)}">\n'
        '<meta name="referrer" content="no-referrer">\n'
        f"<title>{escape(title)}</title>\n<style>\n{stylesheet}\n</style>\n</head>\n"
        f'<body data-theme="{theme}"><main class="document">\n{content}\n</main></body>\n</html>\n'
    )
    return RenderedDocument(title, html, headings, word_count, reading_minutes, path, source)


def load_document(path: str | Path, *, theme: str = "light") -> RenderedDocument:
    """Read a UTF-8 file without modifying it, reporting useful failures to the UI."""
    display_name = str(path)
    try:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            if resolved.exists():
                raise DocumentError(f"Cannot open ‘{display_name}’: choose a regular file.")
            raise DocumentError(f"Cannot open ‘{display_name}’: the file does not exist.")
        if resolved.stat().st_size > MAX_DOCUMENT_BYTES:
            raise DocumentError(f"Cannot open ‘{display_name}’: documents must be 10 MiB or smaller.")
        with resolved.open("rb") as stream:
            data = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise DocumentError(f"Cannot open ‘{display_name}’: documents must be 10 MiB or smaller.")
        source = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise DocumentError(f"Cannot open ‘{display_name}’: save the file with UTF-8 encoding.") from exc
    except (OSError, ValueError, RuntimeError) as exc:
        raise DocumentError(f"Cannot open ‘{display_name}’: {exc}.") from exc
    return render_markdown(source, source_path=resolved, theme=theme)
