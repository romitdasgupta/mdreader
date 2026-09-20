"""Headless contract tests for Markdown rendering and local file boundaries."""

import base64
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

import pytest

from folio.document import DocumentError, load_document, render_markdown


class HTML(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def attrs(self, tag):
        return [attrs for name, attrs in self.elements if name == tag]


IMAGES = {
    "png": ("image/png", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"),
    "gif": ("image/gif", "R0lGODdhAQABAIEAAP///wAAAAAAAAAAACwAAAAAAQABAAAIBAABBAQAOw=="),
    "webp": ("image/webp", "UklGRiQAAABXRUJQVlA4IBgAAAAwAQCdASoBAAEAAUAmJaQAA3AA/vz0AAA="),
    "jpg": ("image/jpeg", "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q=="),
}


def test_common_markdown_renders_structure_and_code_is_escaped():
    source = '''# A **clear** title

Some *emphasis*, **strength**, ~~old text~~, and `inline <code>`.

> A quotation

1. First
2. Second

- Parent
  - Child

---

```python
if a < b:
    print("<script>alert('code')</script>")
```

| Name | Value |
| --- | --- |
| Reading | 42 |
'''
    result = render_markdown(source)
    parsed = HTML(result.html)
    tags = {tag for tag, _ in parsed.elements}
    assert {"h1", "p", "em", "strong", "s", "code", "pre", "blockquote", "ol", "ul", "li", "hr", "table", "th", "td"} <= tags
    assert "script" not in tags
    assert "if a < b:\n    print(\"<script>alert('code')</script>\")\n" in parsed.text
    assert result.title == "A clear title"
    assert result.source_text == source


def test_task_items_remain_readable():
    parsed = HTML(render_markdown("- [x] Read document\n- [ ] Read next document\n").html)
    assert len(parsed.attrs("li")) == 2
    checkboxes = parsed.attrs("input")
    assert len(checkboxes) == 2
    assert all(item.get("type") == "checkbox" and "disabled" in item for item in checkboxes)
    assert "checked" in checkboxes[0]
    assert "checked" not in checkboxes[1]
    text = "".join(parsed.text)
    assert "Read document" in text
    assert "Read next document" in text


def test_heading_outline_is_plain_text_unique_and_deterministic():
    source = "# **Hello** `world`\n## Repeat\n## Repeat\n## Repeat-2\n### Café 東京\n###### Last\n"
    first = render_markdown(source)
    second = render_markdown(source)
    assert first.headings == second.headings
    assert [heading.level for heading in first.headings] == [1, 2, 2, 2, 3, 6]
    assert [heading.title for heading in first.headings] == ["Hello world", "Repeat", "Repeat", "Repeat-2", "Café 東京", "Last"]
    anchors = [heading.anchor for heading in first.headings]
    assert all(anchor.startswith("heading-") for anchor in anchors)
    assert len(set(anchors)) == len(anchors)
    document_ids = [attrs["id"] for _, attrs in HTML(first.html).elements if "id" in attrs]
    assert all(document_ids.count(anchor) == 1 for anchor in anchors)


@pytest.mark.parametrize("heading,fragment", [("Hello world", "hello-world"), ("Café 東京", "caf%C3%A9-%E6%9D%B1%E4%BA%AC")])
def test_standard_heading_fragments_resolve_to_generated_ids(heading, fragment):
    result = render_markdown(f"# {heading}\n\n[Jump](#{fragment})\n")
    links = HTML(result.html).attrs("a")
    assert links[0]["href"] == f"#{result.headings[0].anchor}"


def test_title_uses_first_h1_then_filename_then_untitled(tmp_path):
    assert render_markdown("## Prelude\n# First\n# Second\n").title == "First"
    assert render_markdown("## Prelude", source_path=tmp_path / "Café notes.md").title == "Café notes"
    assert render_markdown("## Prelude").title == "Untitled"


def test_empty_document_has_zero_statistics_and_complete_html():
    result = render_markdown("")
    parsed = HTML(result.html)
    assert result.word_count == 0
    assert result.reading_minutes == 0
    assert result.headings == ()
    assert result.path is None
    assert {"html", "head", "body", "style"} <= {tag for tag, _ in parsed.elements}
    assert "<!doctype html" in result.html.lower()


def test_statistics_count_readable_words_and_reading_minutes():
    result = render_markdown(" ".join(["read"] * 440))
    assert result.word_count == 440
    assert result.reading_minutes == 2
    short = render_markdown("[Two words](https://example.com/not/extra/words)")
    assert short.word_count == 2
    assert short.reading_minutes == 1


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_theme_and_packaged_stylesheet_are_included(theme):
    result = render_markdown("# Styled", theme=theme)
    parsed = HTML(result.html)
    assert parsed.attrs("style")
    assert any(theme in str(value) for _, attrs in parsed.elements for value in attrs.values())
    assert "font-family" in result.html
    assert "line-height" in result.html


def test_raw_html_cannot_add_active_elements_or_attributes():
    source = '''# <img src=x onerror=alert(1)>
<script>alert("execute")</script>
<iframe src="https://example.com"></iframe>
<style>@import "https://example.com/x.css";</style>
<a href="javascript:alert(1)">bad</a>
'''
    result = render_markdown(source)
    parsed = HTML(result.html)
    tags = {tag for tag, _ in parsed.elements}
    assert not {"script", "iframe", "img"} & tags
    assert len(parsed.attrs("style")) == 1
    assert not any(key.lower().startswith("on") for _, attrs in parsed.elements for key in attrs)
    assert '<script>alert("execute")</script>' in "".join(parsed.text)


def test_html_has_content_security_policy_without_remote_sources():
    parsed = HTML(render_markdown("# Offline").html)
    policies = [attrs["content"] for attrs in parsed.attrs("meta") if attrs.get("http-equiv", "").lower() == "content-security-policy"]
    assert len(policies) == 1
    policy = policies[0]
    assert "default-src 'none'" in policy
    assert "img-src data:" in policy
    assert "https:" not in policy and "http:" not in policy
    assert not parsed.attrs("script")
    assert not parsed.attrs("link")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,attack", "file:///etc/passwd", "ftp://example.com/file", "custom-app:launch"])
def test_unsafe_explicit_link_schemes_are_not_clickable(url):
    parsed = HTML(render_markdown(f"[Readable label]({url})").html)
    assert not any(attrs.get("href", "").lower().startswith(url.split(":")[0].lower() + ":") for attrs in parsed.attrs("a"))
    assert "Readable label" in "".join(parsed.text)


@pytest.mark.parametrize("url", ["https://example.com/read?q=hello&sort=new", "http://example.com", "mailto:reader@example.com", "notes.md", "../sibling.md", "notes.md#hello"])
def test_allowed_link_destinations_survive_rendering(url):
    parsed = HTML(render_markdown(f"[A link]({url})").html)
    assert parsed.attrs("a")[0]["href"] == url


def test_load_utf8_bom_unicode_path_and_preserve_source_bytes(tmp_path):
    directory = tmp_path / "Notes café"
    directory.mkdir()
    source = b"\xef\xbb\xbf" + "# 東京 notes\n\nRead café.\n".encode("utf-8")
    path = directory / "my notes.md"
    path.write_bytes(source)
    result = load_document(path)
    assert result.title == "東京 notes"
    assert not result.source_text.startswith("\ufeff")
    assert result.path == path.resolve()
    assert "café" in result.html
    assert path.read_bytes() == source


def test_load_empty_file_succeeds(tmp_path):
    path = tmp_path / "empty.md"
    path.touch()
    result = load_document(path)
    assert result.title == "empty"
    assert result.word_count == result.reading_minutes == 0


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid_utf8", "too_large"])
def test_load_failures_are_user_presentable(kind, tmp_path):
    path = tmp_path / f"{kind}.md"
    if kind == "directory":
        path.mkdir()
    elif kind == "invalid_utf8":
        path.write_bytes(b"# Bad\n\xff\xfe")
    elif kind == "too_large":
        with path.open("wb") as stream:
            stream.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(DocumentError) as error:
        load_document(path)
    assert str(error.value)
    assert path.name in str(error.value)


@pytest.mark.parametrize("extension", IMAGES)
def test_supported_local_raster_images_embed_bytes(extension, tmp_path):
    mime, encoded = IMAGES[extension]
    image_path = tmp_path / f"local.{extension}"
    image_path.write_bytes(base64.b64decode(encoded))
    result = render_markdown(f"![Local picture](local.{extension})", source_path=tmp_path / "notes.md")
    images = HTML(result.html).attrs("img")
    assert len(images) == 1
    assert images[0]["src"] == f"data:{mime};base64,{encoded}"
    assert images[0]["alt"] == "Local picture"


@pytest.mark.parametrize("link", ["<assets/café picture.png>", "assets/caf%C3%A9%20picture.png"])
def test_local_images_allow_spaces_and_unicode(link, tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    image_path = assets / "café picture.png"
    image_path.write_bytes(base64.b64decode(IMAGES["png"][1]))
    result = render_markdown(f"![Readable image]({link})", source_path=tmp_path / "notes.md")
    assert HTML(result.html).attrs("img")[0]["src"].startswith("data:image/png;base64,")


@pytest.mark.parametrize("kind", ["traversal", "encoded_traversal", "symlink", "absolute", "remote", "network_path", "missing", "svg"])
def test_denied_images_have_readable_fallback_without_fetchable_source(kind, tmp_path):
    docs = tmp_path / "documents"
    docs.mkdir()
    outside = tmp_path / "secret.png"
    outside.write_bytes(base64.b64decode(IMAGES["png"][1]))
    (docs / "escape.png").symlink_to(outside)
    (docs / "unsafe.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    links = {
        "traversal": "../secret.png",
        "encoded_traversal": "%2E%2E/secret.png",
        "symlink": "escape.png",
        "absolute": outside.as_posix(),
        "remote": "https://example.com/tracker.png",
        "network_path": "//example.com/tracker.png",
        "missing": "missing.png",
        "svg": "unsafe.svg",
    }
    result = render_markdown(f"![Picture description]({links[kind]})\n\nContinue reading.", source_path=docs / "notes.md")
    parsed = HTML(result.html)
    assert not parsed.attrs("img")
    assert "Picture description" in "".join(parsed.text)
    assert "Continue reading." in "".join(parsed.text)


def test_core_import_does_not_require_gi_or_a_display():
    code = "import sys; sys.modules['gi'] = None; from folio.document import render_markdown; assert render_markdown('# Headless').title == 'Headless'"
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_unreadable_document_becomes_document_error(monkeypatch, tmp_path):
    path = tmp_path / "private.md"
    path.write_text("# Private")
    original_open = Path.open

    def denied_open(self, *args, **kwargs):
        if self == path:
            raise PermissionError("Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied_open)
    with pytest.raises(DocumentError, match="private.md"):
        load_document(path)


def test_image_over_five_mib_is_not_embedded(tmp_path):
    image_path = tmp_path / "too-large.png"
    with image_path.open("wb") as stream:
        stream.write(base64.b64decode(IMAGES["png"][1]))
        stream.truncate(5 * 1024 * 1024 + 1)
    parsed = HTML(render_markdown("![Large picture](too-large.png)", source_path=tmp_path / "notes.md").html)
    assert not parsed.attrs("img")
    assert "Large picture" in "".join(parsed.text)


def test_image_type_comes_from_bytes_not_extension(tmp_path):
    path = tmp_path / "pretend.png"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    parsed = HTML(render_markdown("![False image](pretend.png)", source_path=tmp_path / "notes.md").html)
    assert not parsed.attrs("img")
    assert not parsed.attrs("svg")
    assert not parsed.attrs("script")
    assert "False image" in "".join(parsed.text)


def test_reading_page_image_budget_limits_total_embedded_bytes(monkeypatch, tmp_path):
    from folio import document

    payload = base64.b64decode(IMAGES["png"][1])
    (tmp_path / "picture.png").write_bytes(payload)
    monkeypatch.setattr(document, "MAX_EMBEDDED_IMAGE_BYTES", len(payload) * 2)
    result = render_markdown("![First](picture.png)\n![Second](picture.png)\n![Third](picture.png)", source_path=tmp_path / "notes.md")
    parsed = HTML(result.html)
    assert len(parsed.attrs("img")) == 2
    assert "Third" in "".join(parsed.text)


def test_relative_document_links_resolve_with_spaces_and_heading(tmp_path):
    source = tmp_path / "My notes café.md"
    target = tmp_path / "next page.md"
    result = render_markdown("[Next](next%20page.md#hello)", source_path=source)
    assert HTML(result.html).attrs("a")[0]["href"] == target.as_uri() + "#hello"
