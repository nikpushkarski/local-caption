import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys
import time
from unittest.mock import patch
from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from local_caption.app import Window
from local_caption import __version__

BUILD_DIR = Path(f"dist/v{__version__}/LocalCaption")


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Window(auto_scan_hardware=False)

    def tearDown(self):
        self.window.close()

    @unittest.skipUnless(os.name == "nt", "Windows-native separator check")
    def test_native_path_display(self):
        self.window.model.setText('"C:/Models/Whisper/medium.pt"')
        self.assertEqual(self.window.model.edit.text(), r"C:\Models\Whisper\medium.pt")
        self.window.model.edit.setText("C:/Models/medium.pt")
        self.window.model.edit.editingFinished.emit()
        self.assertEqual(self.window.model.edit.text(), r"C:\Models\medium.pt")

    def test_mode_and_output(self):
        self.window.source.setText(str(Path("example.mp4").resolve()))
        self.assertTrue(self.window.output.text().endswith("example-captioned.mp4"))
        self.window.mode.setCurrentIndex(self.window.mode.findData("transcribe"))
        self.assertTrue(self.window.output.text().endswith("example-captioned.srt"))
        self.assertFalse(self.window.srt.isEnabled())
        self.window.mode.setCurrentIndex(self.window.mode.findData("burn"))
        self.assertTrue(self.window.srt.isEnabled())
        self.assertFalse(self.window.model.isEnabled())

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg fixture generator required")
    def test_input_immediately_shows_sample_and_style_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.mp4"
            subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=s=320x180:d=1",
                            "-c:v", "libx264", str(source)], check=True)
            self.window.show()
            self.window.source.setText(str(source))
            deadline = time.monotonic() + 8
            while self.window.preview.output.sample.image.isNull() and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertFalse(self.window.preview.output.sample.image.isNull())
            self.assertTrue(self.window.preview.showing_sample)
            self.assertFalse(Path(self.window.output.text()).exists())
            self.window.subtitle_controls.size.setEditText("42")
            self.window.subtitle_controls.lines.setCurrentIndex(2)
            self.assertEqual(self.window.preview.output.sample.style.font_size, 42)
            self.assertEqual(self.window.preview.output.sample.style.max_lines, 3)
            self.assertLess(self.window.subtitle_controls.y(), self.window.source.y())
            self.window.preview_timer.stop()
            self.window.preview.close_media()

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_gui_worker_lifecycle(self):
        self.run_gui_job(False)

    @unittest.skipUnless((BUILD_DIR / "LocalCaptionWorker.exe").is_file() and shutil.which("ffmpeg"), "Packaged worker required")
    def test_gui_packaged_worker_lifecycle(self):
        self.run_gui_job(True)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_replace_output_while_preview_loaded(self):
        self.run_gui_job(False, rerender=True)

    def run_gui_job(self, frozen, rerender=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video, srt = root / "input.mp4", root / "input.srt"
            subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=s=320x240:d=1", "-c:v", "libx264", str(video)], check=True)
            srt.write_text("1\n00:00:00,000 --> 00:00:00,900\nHello\n", encoding="utf-8")
            self.window.settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            self.window.mode.setCurrentIndex(self.window.mode.findData("burn"))
            self.window.source.setText(str(video))
            self.window.srt.setText(str(srt))
            self.window.ffmpeg.setText(shutil.which("ffmpeg"))
            self.window.ffprobe.setText(shutil.which("ffprobe"))
            if frozen:
                with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str((BUILD_DIR / "LocalCaption.exe").resolve())):
                    self.window.start()
            else:
                self.window.start()
            deadline = time.monotonic() + 30
            while self.window.process is not None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            if self.window.process is not None:
                self.window.cancel()
                self.window.process.waitForFinished(5000)
                self.fail("Worker did not complete in time")
            self.assertEqual(self.window.status.text(), "Completed", self.window.log.toPlainText())
            self.assertTrue(Path(self.window.output.text()).is_file())
            self.assertIsNone(self.window.workspace)
            self.assertTrue(self.window.start_button.isEnabled())
            self.assertFalse(self.window.preview.showing_sample)
            if rerender:
                deadline = time.monotonic() + 5
                while self.window.preview.output.player.duration() == 0 and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(.01)
                self.assertGreater(self.window.preview.output.player.duration(), 0)
                self.window.overwrite.setChecked(True)
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                    self.window.start()
                deadline = time.monotonic() + 30
                while self.window.process is not None and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(.01)
                self.assertIsNone(self.window.process)
                self.assertEqual(self.window.status.text(), "Completed", self.window.log.toPlainText())
            self.window.preview.close_media()
            self.app.processEvents()

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
