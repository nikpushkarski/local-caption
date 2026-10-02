"""Caption layout adapted from the user's working backup (no auto_subtitle code)."""

import math
import re

MAX_CAPTION_WORDS = 4
MAX_CAPTION_CHARS = 24
MAX_CAPTION_SECONDS = 1.5
CAPTION_PAUSE_SECONDS = 0.35
MIN_RENDER_CAPTION_SECONDS = 0.2

def single_line_captions(segments):
    """Split Whisper word timestamps into short cues without inventing word times.

    A single unusually long word is preserved, even if it exceeds the limits.
    SRT players may still wrap text; WrapStyle=2 applies to burned-in captions.
    """
    captions = []
    for segment in segments:
        words = segment.get("words", [])
        if segment.get("text", "").strip() and not words:
            raise ValueError("Word timestamps missing; cannot build short timed captions.")
        chunk = []

        def text(items):
            return " ".join("".join(item["word"] for item in items).split())

        def flush():
            if chunk:
                start = max(0.0, float(chunk[0]["start"]))
                if captions:
                    start = max(start, captions[-1]["end"])
                end = max(start + 0.001, float(chunk[-1]["end"]))
                captions.append({"start": start, "end": end, "text": text(chunk)})
                chunk.clear()

        for word in words:
            start, end = float(word["start"]), float(word["end"])
            if not math.isfinite(start) or not math.isfinite(end) or end < start:
                raise ValueError("Invalid word timestamps.")
            if not word["word"].strip():
                continue
            if chunk and (
                len(text(chunk + [word]).split()) > MAX_CAPTION_WORDS
                or len(text(chunk + [word])) > MAX_CAPTION_CHARS
                or float(word["end"]) - float(chunk[0]["start"]) > MAX_CAPTION_SECONDS
                or float(word["start"]) - float(chunk[-1]["end"]) > CAPTION_PAUSE_SECONDS
            ):
                flush()
            chunk.append(word)
            if word["word"].rstrip().endswith((".", "!", "?", ",", ";", ":")):
                flush()
        flush()
    return captions


def display_dimensions(stream):
    width, height = int(stream["width"]), int(stream["height"])
    if width <= 0 or height <= 0:
        raise ValueError("Video dimensions must be positive.")
    rotation = stream.get("tags", {}).get("rotate", 0)
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            rotation = side_data["rotation"]
            break
    if round(float(rotation)) % 180 == 90:
        width, height = height, width
    return width, height


def caption_layout(width, height):
    # Pixel-based font sizing, with a width cap for portrait/square videos.
    font_size = max(1, round(min(height * 28 / 288, width * 0.075)))
    margin = max(1, round(width * 0.06))
    outline = max(1, round(font_size * 0.09))
    return {
        "font_size": font_size, "margin": margin, "outline": outline,
        "available_width": max(1, width - 2 * (margin + outline)),
        "bottom_margin": max(1, round(height * 0.04)),
    }


def measure_caption(text, font_size):
    """Use the same cross-platform font family requested from libass."""
    from PySide6.QtGui import QFont, QFontMetricsF

    font = QFont("Arial")
    font.setPixelSize(font_size)
    font.setBold(True)
    return QFontMetricsF(font).horizontalAdvance(text)


def fit_caption_font(text, layout):
    size = layout["font_size"]
    # Leave extra room for differences between GDI and libass font rendering.
    measured = measure_caption(text, size) * 1.15
    if measured > layout["available_width"]:
        size = max(1, int(size * layout["available_width"] / measured))
    while measure_caption(text, size) * 1.15 > layout["available_width"]:
        if size == 1:
            raise ValueError("A caption is too long to fit even at the smallest font size.")
        size -= 1
    return size


def visible_ass_cues(ass_text):
    """Repair sub-frame cues in the render copy, without moving cue starts."""
    lines = ass_text.splitlines()
    events = [(index, line.split(",", 9)) for index, line in enumerate(lines) if line.startswith("Dialogue:")]

    def timestamp(value):
        hours, minutes, seconds = value.strip().split(":")
        return round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 100)

    def formatted(value):
        seconds, fraction = divmod(value, 100)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02}:{seconds:02}.{fraction:02}"

    minimum = round(MIN_RENDER_CAPTION_SECONDS * 100)
    changed = 0
    for position, (index, parts) in enumerate(events):
        start, end = timestamp(parts[1]), timestamp(parts[2])
        if end - start >= minimum:
            continue
        new_end = max(end, start + minimum)
        if position + 1 < len(events):
            next_start = timestamp(events[position + 1][1][1])
            if next_start > start:
                new_end = min(new_end, next_start)
        if new_end > end:
            parts[2] = formatted(new_end)
            lines[index] = ",".join(parts)
            changed += 1
    if changed:
        print(f"Made {changed} very short caption(s) visible in the render copy; SRT unchanged.", flush=True)
    return "\n".join(lines) + "\n"


def fit_ass_captions(ass_text, width, height):
    """Use real video coordinates and a separately fitted font size for each cue."""
    layout = caption_layout(width, height)
    style_values = {
        "Fontname": "Arial", "Fontsize": str(layout["font_size"]), "Bold": "-1",
        "PrimaryColour": "&H00FFFFFF", "OutlineColour": "&H00000000",
        "BorderStyle": "1", "Outline": str(layout["outline"]), "Shadow": "1",
        "Alignment": "2", "MarginL": str(layout["margin"]),
        "MarginR": str(layout["margin"]), "MarginV": str(layout["bottom_margin"]),
    }
    fitted = []
    sizes = []
    style_fields = None
    # FFmpeg's SRT-to-ASS conversion preserves cue times and handles SRT markup.
    for line in ass_text.splitlines():
        if line.startswith(("PlayResX:", "PlayResY:", "WrapStyle:")):
            continue
        if line.strip() == "[Script Info]":
            fitted.extend([line, f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 2"])
        elif line.startswith("Format: Name,"):
            style_fields = [field.strip() for field in line.partition(":")[2].split(",")]
            fitted.append(line)
        elif line.startswith("Style:"):
            values = line.partition(":")[2].strip().split(",")
            if style_fields is None or len(values) != len(style_fields):
                raise ValueError("Cannot parse the converted ASS subtitle style.")
            for index, field in enumerate(style_fields):
                if field in style_values:
                    values[index] = style_values[field]
            fitted.append("Style: " + ",".join(values))
        elif line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) != 10:
                raise ValueError("Cannot parse the converted ASS subtitle cue.")
            text = re.sub(r"\{[^}]*\}", "", parts[9])
            text = " ".join(text.replace(r"\N", " ").replace(r"\n", " ").replace(r"\h", " ").split())
            size = fit_caption_font(text, layout)
            sizes.append(size)
            # Remove embedded SRT styling so it cannot override the fitted font.
            # Literal braces/backslashes must not become libass override commands.
            text = text.replace("\\", "＼").replace("{", "｛").replace("}", "｝")
            parts[9] = r"{\fs" + str(size) + "}" + text
            fitted.append(",".join(parts))
        else:
            fitted.append(line)
    style = (
        f"Fontname=Arial,Fontsize={layout['font_size']},Bold=1,PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,BorderStyle=1,Outline={layout['outline']},Shadow=1,"
        f"Alignment=2,MarginL={layout['margin']},MarginR={layout['margin']},"
        f"MarginV={layout['bottom_margin']},WrapStyle=2"
    )
    if sizes:
        print(f"Caption layout: {width}x{height}, fitted font {min(sizes)}-{max(sizes)} px.", flush=True)
    # Embed the style in the ASS itself: the direct `ass` filter has no force_style.
    return visible_ass_cues("\n".join(fitted) + "\n"), style


