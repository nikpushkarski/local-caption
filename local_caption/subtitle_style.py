"""Validated settings shared by generated cues, sample preview and ASS rendering."""

from dataclasses import dataclass
import textwrap

SAMPLE_TEXT = "subs example, lorem ipsum"


@dataclass(frozen=True)
class SubtitleStyle:
    font: str = "Arial"
    font_size: int | None = None  # None keeps the original resolution-dependent sizing.
    chars_per_line: int = 24
    max_lines: int = 1

    def validate(self):
        if not isinstance(self.font, str) or not self.font.strip() or len(self.font) > 150 or any(c in ",{}\\" or ord(c) < 32 for c in self.font):
            raise ValueError("Choose a valid font family.")
        if self.font_size is not None and (type(self.font_size) is not int or not 1 <= self.font_size <= 512):
            raise ValueError("Font size must be Auto or an integer from 1 to 512 pixels.")
        if type(self.chars_per_line) is not int or not 6 <= self.chars_per_line <= 120:
            raise ValueError("Target line width must be 6–120 characters.")
        if type(self.max_lines) is not int or self.max_lines not in {1, 2, 3}:
            raise ValueError("Choose 1, 2 or 3 maximum subtitle lines.")
        return self

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Subtitle settings must be an object.")
        try:
            return cls(**value).validate()
        except TypeError as error:
            raise ValueError("Unknown or invalid subtitle settings.") from error


def wrap_caption(text, style):
    """Aim for a character width without losing words or exceeding the line count.

    Edited SRTs and the fixed sample may exceed the target character budget. Widen
    those lines as needed, then the common font fitter handles actual pixel width.
    A single unusually long word is never split or discarded.
    """
    text = " ".join(text.split())
    if not text:
        return []
    if style.max_lines == 1:
        return [text]

    def wrapped(width):
        return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)

    low, high = style.chars_per_line, max(style.chars_per_line, len(text))
    while low < high:
        middle = (low + high) // 2
        if len(wrapped(middle)) <= style.max_lines:
            high = middle
        else:
            low = middle + 1
    return wrapped(low)
