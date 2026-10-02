import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from local_caption.app import Window


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Window()

    def tearDown(self):
        self.window.close()

    def test_mode_and_output(self):
        self.window.source.setText(str(Path("example.mp4").resolve()))
        self.assertTrue(self.window.output.text().endswith("example-captioned.mp4"))
        self.window.mode.setCurrentIndex(self.window.mode.findData("transcribe"))
        self.assertTrue(self.window.output.text().endswith("example-captioned.srt"))
        self.assertFalse(self.window.srt.isEnabled())
        self.window.mode.setCurrentIndex(self.window.mode.findData("burn"))
        self.assertTrue(self.window.srt.isEnabled())
        self.assertFalse(self.window.model.isEnabled())

    def test_real_drop_event(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test ü.mp4"
            path.touch()
            data = QMimeData()
            data.setUrls([QUrl.fromLocalFile(str(path))])
            enter = QDragEnterEvent(QPoint(10, 10), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.window, enter)
            self.assertTrue(enter.isAccepted())
            drop = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.window, drop)
            self.assertEqual(Path(self.window.source.text()), path)
