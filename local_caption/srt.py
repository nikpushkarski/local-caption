"""Small, locally implemented UTF-8 SubRip writer."""

import math
from pathlib import Path
from typing import Iterable, Mapping, TextIO


def timestamp(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Subtitle timestamps must be finite and non-negative.")
    milliseconds = round(seconds * 1000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def write_srt(cues: Iterable[Mapping], stream: TextIO, preserve_newlines=False) -> None:
    previous_end = 0.0
    for index, cue in enumerate(cues, 1):
        start, end = float(cue["start"]), float(cue["end"])
        if not math.isfinite(end) or end <= start or start < previous_end:
            raise ValueError("Subtitle cues must be ordered, non-overlapping and positive-length.")
        raw = str(cue["text"])
        text = ("\n".join(" ".join(line.split()) for line in raw.splitlines() if line.strip())
                if preserve_newlines else " ".join(raw.split())).replace("-->", "→")
        if not text:
            raise ValueError("Subtitle text must not be empty.")
        # Ensure rounding cannot turn a positive-length cue into a zero-length one.
        start_text = timestamp(start)
        end_text = timestamp(max(end, (round(start * 1000) + 1) / 1000))
        stream.write(f"{index}\n{start_text} --> {end_text}\n{text}\n\n")
        previous_end = end


def save_new_srt(path: Path, cues: list[dict], preserve_newlines=False) -> Path:
    """Reserve a numbered name exclusively; never truncate an existing subtitle."""
    from io import StringIO

    buffer = StringIO()
    write_srt(cues, buffer, preserve_newlines=preserve_newlines)  # Validate before touching disk.
    path.parent.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        candidate = path if number == 1 else path.with_name(f"{path.stem}-{number}.srt")
        try:
            stream = candidate.open("x", encoding="utf-8", newline="\n")
        except FileExistsError:
            number += 1
            continue
        try:
            with stream:
                stream.write(buffer.getvalue())
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise
        return candidate
