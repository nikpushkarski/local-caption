import io
from pathlib import Path
import tempfile
import unittest

from local_caption.srt import save_new_srt, timestamp, write_srt
from local_caption.captions import display_dimensions, single_line_captions, visible_ass_cues


class SrtTests(unittest.TestCase):
    def test_rounding_and_hours(self):
        self.assertEqual(timestamp(59.9996), "00:01:00,000")
        self.assertEqual(timestamp(360000), "100:00:00,000")
        for value in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                timestamp(value)

    def test_unicode_and_format(self):
        stream = io.StringIO()
        write_srt([dict(start=0, end=1.234, text=" Привет\nмир! ")], stream)
        self.assertEqual(stream.getvalue(), "1\n00:00:00,000 --> 00:00:01,234\nПривет мир!\n\n")

    def test_preserve_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.srt"
            path.write_text("original", encoding="utf-8")
            result = save_new_srt(path, [dict(start=0, end=1, text="hello")])
            self.assertEqual(result.name, "clip-2.srt")
            self.assertEqual(path.read_text(), "original")

    def test_invalid_cues(self):
        for cue in [dict(start=2, end=1, text="x"), dict(start=0, end=1, text=" ")]:
            with self.assertRaises(ValueError):
                write_srt([cue], io.StringIO())
        with self.assertRaises(ValueError):
            single_line_captions([{"words": [{"word": "x", "start": 0, "end": float("nan")}]}])

    def test_rotation(self):
        self.assertEqual(display_dimensions(dict(width=1920, height=1080, side_data_list=[{"rotation": -90}])), (1080, 1920))

    def test_visibility_repair(self):
        text = "Dialogue: 0,0:00:00.00,0:00:00.01,Default,,0,0,0,,Hi\nDialogue: 0,0:00:00.10,0:00:01.00,Default,,0,0,0,,there\n"
        self.assertIn("0:00:00.00,0:00:00.10", visible_ass_cues(text))
