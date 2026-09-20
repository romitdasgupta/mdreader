# A quiet place for your Markdown

Welcome to **Folio**, a small native reader for Linux. Open a README, a set of notes, or a long-form document and settle in.

> Good tools leave room for the work.

## Make yourself at home

Use the outline on the left to move between sections. Press **Ctrl+F** to find a word, or switch to the dark theme for evening reading. Your documents stay exactly as you wrote them.

| Action | Shortcut |
| :--- | :--- |
| Open a document | Ctrl+O |
| Find in this document | Ctrl+F |
| Reload from disk | Ctrl+R |
| Larger text | Ctrl++ |
| Smaller text | Ctrl+− |
| Reset text size | Ctrl+0 |

## Words, with a little structure

Markdown is plain text with just enough structure to make ideas clear. Folio understands *emphasis*, **strong emphasis**, ~~strikethrough~~, and `inline code`.

1. Start with an idea.
2. Give it a little room to breathe.
3. Read it with fresh eyes.

### A checklist for the day

- [x] Find a quiet corner
- [x] Open something worth reading
- [ ] Follow an interesting idea

## Code deserves good typography

Fenced code keeps indentation and long lines intact. The code below is displayed as text; nothing in a document is executed.

```python
from pathlib import Path

def collect_notes(folder: Path) -> list[Path]:
    """Small tools, useful things."""
    return sorted(folder.glob("*.md"))

for note in collect_notes(Path("~/notes").expanduser()):
    print(note.name)
```

### Local images

Images stored beside your document can be read offline. Folio keeps remote images from making background network requests.

![A blue circle, a page, and the words: space to think.](assets/reading.png)

## A document can be a doorway

Follow [a local Markdown link](field-notes.md) to open another document, or jump back to [the beginning](#a-quiet-place-for-your-markdown). Web links open in your default browser when you choose to follow them.

### Notes in every language

Bring your own words: café, naïve, 日本語, Ελληνικά, العربية. Unicode belongs in ordinary documents.

---

Keep your favorite editor open alongside Folio. When you save, the reader refreshes. **Ctrl+R** is always available for an explicit reload.
