import io
import unittest

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QImage

from local_caption.sample_preview import SamplePreview

from local_caption.captions import caption_layout, single_line_captions
from local_caption.srt import write_srt
from local_caption.style_ui import AUTO_SIZE, DEFAULT_WIDTH, SubtitleControls
from local_caption.subtitle_style import SAMPLE_TEXT, SubtitleStyle, wrap_caption
from test_captions import segment


class StyleTests(unittest.TestCase):
    def test_default_layout_unchanged(self):
        style = SubtitleStyle()
        self.assertEqual(style.font, "Arial")
        self.assertEqual(style.chars_per_line, 24)
        self.assertEqual(style.max_lines, 1)
        self.assertIsNone(style.font_size)
        for width, height in [(1920, 1080), (1080, 1920), (640, 360)]:
            layout = caption_layout(width, height)
            self.assertEqual(layout["font_size"], max(1, round(min(height * 28 / 288, width * .075))))
            self.assertEqual(layout["bottom_margin"], max(1, round(height * .04)))

    def test_style_validation(self):
        for value in [{"font": "Arial\nDialogue: injection"}, {"font": "bad,font"}, {"font_size": 0},
                      {"font_size": 513}, {"font_size": True}, {"font_size": "24"}, {"chars_per_line": 1},
                      {"max_lines": 4}, {"unknown": 1}]:
            with self.assertRaises(ValueError):
                SubtitleStyle.from_dict(value)

    def test_wrapping_preserves_text_and_line_limit(self):
        for maximum in (1, 2, 3):
            for width in (6, 12, 24, 80):
                lines = wrap_caption(SAMPLE_TEXT, SubtitleStyle(chars_per_line=width, max_lines=maximum))
                self.assertEqual(" ".join(lines), SAMPLE_TEXT)
                self.assertLessEqual(len(lines), maximum)
        long_word = "supercalifragilisticexpialidocious"
        self.assertIn(long_word, wrap_caption(long_word + " hello", SubtitleStyle(chars_per_line=6, max_lines=3)))

    def test_multiline_cues_use_original_word_times(self):
        item = segment(["One", "two", "three", "four", "five", "six"])
        result = single_line_captions([item], SubtitleStyle(max_lines=2))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], 0)
        self.assertAlmostEqual(result[0]["end"], 1.2)
        self.assertIn("\n", result[0]["text"])
        self.assertEqual(" ".join(result[0]["text"].split()), item["text"])

    def test_srt_can_preserve_intentional_line_breaks(self):
        stream = io.StringIO()
        write_srt([dict(start=0, end=1, text="First line\nSecond line")], stream, preserve_newlines=True)
        self.assertIn("First line\nSecond line\n\n", stream.getvalue())


class StyleGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_sample_has_white_text_near_bottom_without_mutating_frame(self):
        canvas = SamplePreview()
        canvas.resize(640, 360)
        canvas.image = QImage(640, 360, QImage.Format.Format_RGB32)
        canvas.image.fill(QColor("blue"))
        canvas.show()
        self.app.processEvents()
        try:
            image = canvas.grab().toImage()
            white = [(x, y) for y in range(0, 360, 2) for x in range(0, 640, 2)
                     if all(channel > 220 for channel in image.pixelColor(x, y).getRgb()[:3])]
            self.assertGreater(len(white), 40)
            self.assertTrue(all(y > 250 for x, y in white))
            self.assertEqual(canvas.image.pixelColor(320, 330), QColor("blue"))
        finally:
            canvas.close()

    def test_controls_default_markers_and_manual_values(self):
        controls = SubtitleControls()
        try:
            self.assertEqual(controls.value(), SubtitleStyle())
            for combo in (controls.font, controls.size, controls.width, controls.lines):
                self.assertIn("default", combo.currentText())
            controls.size.setEditText("55")
            controls.width.setEditText("18")
            controls.lines.setCurrentIndex(2)
            self.assertEqual(controls.value().font_size, 55)
            self.assertEqual(controls.value().chars_per_line, 18)
            self.assertEqual(controls.value().max_lines, 3)
            controls.size.setEditText("invalid")
            with self.assertRaises(ValueError):
                controls.value()
            controls.size.setCurrentText(AUTO_SIZE)
            controls.width.setCurrentText(DEFAULT_WIDTH)
            self.assertIsNone(controls.value().font_size)
            self.assertEqual(controls.value().chars_per_line, 24)
        finally:
            controls.close()
