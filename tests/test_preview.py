import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from local_caption.preview import ComparisonPreview


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg fixture generator required")
class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.temp.name) / "preview ü.mp4"
        subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=8",
                        "-c:v", "libx264", str(cls.source)], check=True)
        cls.output = Path(cls.temp.name) / "output.mp4"
        shutil.copyfile(cls.source, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.preview = ComparisonPreview()
        self.preview.show()

    def tearDown(self):
        self.preview.close_media()
        self.preview.close()
        self.app.processEvents()

    def wait_for(self, condition, seconds=8):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertTrue(condition())

    def load_pair(self):
        self.preview.set_input(str(self.source))
        self.preview.set_output(str(self.output))
        self.wait_for(lambda: all(p.player.duration() == 8000 and p.player.isSeekable() for p in self.preview.panes))

    def test_poster_frames_without_autoplay(self):
        self.load_pair()
        self.wait_for(lambda: all(p.video.videoSink().videoFrame().isValid() for p in self.preview.panes))
        self.assertFalse(self.preview.playing)
        self.assertTrue(all(p.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState for p in self.preview.panes))

    def test_shared_transport_and_audio(self):
        self.load_pair()
        self.assertTrue(self.preview.output.audio.isMuted())
        self.assertFalse(self.preview.input.audio.isMuted())
        self.preview.audio_choice.setCurrentIndex(1)
        self.assertTrue(self.preview.input.audio.isMuted())
        self.assertFalse(self.preview.output.audio.isMuted())
        self.preview.seek(2000)
        self.assertTrue(all(p.player.position() == 2000 for p in self.preview.panes))
        self.preview.toggle_play()
        self.wait_for(lambda: all(p.player.position() > 2300 for p in self.preview.panes))
        self.assertLess(abs(self.preview.input.player.position() - self.preview.output.player.position()), 250)
        self.preview.pause()
        self.assertTrue(all(p.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState for p in self.preview.panes))
        self.preview.forward_button.click()
        self.assertGreaterEqual(self.preview.position, 7300)
        self.preview.back_button.click()
        self.assertLess(self.preview.position, 3000)
        self.preview.slider.setValue(500)
        self.assertEqual(self.preview.position, 4000)
        self.preview.stop()
        self.assertTrue(all(p.player.position() == 0 for p in self.preview.panes))

    def test_drift_correction_and_release(self):
        self.load_pair()
        self.preview.input.player.setPosition(3000)
        self.preview.output.player.setPosition(1000)
        self.preview.synchronize()
        self.assertEqual(self.preview.output.player.position(), 3000)
        self.preview.release_output()
        self.assertTrue(self.preview.output.player.source().isEmpty())
        # Exercise Windows file-handle release, not just player state.
        self.app.processEvents()
        moved = self.output.with_suffix(".moved")
        self.output.rename(moved)
        moved.rename(self.output)

    def test_drop_directly_on_input_video(self):
        paths = []
        self.preview.inputDropped.connect(paths.append)
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(str(self.source))])
        enter = QDragEnterEvent(QPoint(5, 5), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.preview.input.video, enter)
        drop = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.preview.input.video, drop)
        self.assertEqual(paths, [str(self.source)])

    def native_drop(self, pane, urls, via_owner=False):
        self.app.processEvents()
        global_point = pane.video.mapToGlobal(pane.video.rect().center())
        owner = self.preview.windowHandle()
        native = next(w for w in self.app.allWindows()
                      if w.metaObject().className() == "QVideoWindow" and owner.isAncestorOf(w)
                      and w.geometry().contains(owner.mapFromGlobal(global_point)))
        if via_owner:
            native = owner
        point = native.mapFromGlobal(global_point)
        data = QMimeData()
        data.setUrls(urls)
        accepted = []
        for event in (
            QDragEnterEvent(point, Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier),
            QDragMoveEvent(point, Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier),
            QDropEvent(QPointF(point), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier),
        ):
            QApplication.sendEvent(native, event)
            accepted.append(event.isAccepted())
        return accepted

    def test_drop_on_actual_native_render_window(self):
        paths = []
        self.preview.inputDropped.connect(paths.append)
        self.assertEqual(self.native_drop(self.preview.input, [QUrl.fromLocalFile(str(self.source))]), [True] * 3)
        self.assertEqual(paths, [str(self.source)])

    def test_native_drop_via_top_level_window(self):
        paths = []
        self.preview.inputDropped.connect(paths.append)
        self.assertEqual(self.native_drop(self.preview.input, [QUrl.fromLocalFile(str(self.source))], via_owner=True), [True] * 3)
        self.assertEqual(paths, [str(self.source)])

    def test_native_drop_while_video_playing(self):
        self.load_pair()
        self.preview.toggle_play()
        paths = []
        self.preview.inputDropped.connect(paths.append)
        self.assertEqual(self.native_drop(self.preview.input, [QUrl.fromLocalFile(str(self.output))]), [True] * 3)
        self.assertEqual(paths, [str(self.output)])

    def test_native_drop_rejected_for_output_disabled_and_urls(self):
        paths = []
        self.preview.inputDropped.connect(paths.append)
        local = [QUrl.fromLocalFile(str(self.source))]
        self.preview.set_output(str(self.output))  # Native output surface is only visible in rendered mode.
        self.assertEqual(self.native_drop(self.preview.output, local), [False] * 3)
        self.assertEqual(self.native_drop(self.preview.input, [QUrl("https://example.com/video.mp4")]), [False] * 3)
        self.preview.setEnabled(False)
        self.assertEqual(self.native_drop(self.preview.input, local), [False] * 3)
        self.assertEqual(paths, [])

    def test_live_sample_without_output_file(self):
        from local_caption.subtitle_style import SAMPLE_TEXT, SubtitleStyle
        self.preview.set_input(str(self.source))
        self.wait_for(lambda: not self.preview.output.sample.image.isNull())
        self.assertTrue(self.preview.showing_sample)
        self.assertTrue(self.preview.output.player.source().isEmpty())
        self.assertFalse(self.preview.output.view_choice.model().item(1).isEnabled())
        layout, lines, size = self.preview.output.sample.caption_geometry(320, 180)
        self.assertEqual(" ".join(lines), SAMPLE_TEXT)
        self.preview.set_subtitle_style(SubtitleStyle(font="Courier New", font_size=18, chars_per_line=12, max_lines=3))
        layout, lines, size = self.preview.output.sample.caption_geometry(320, 180)
        self.assertEqual(layout["font_family"], "Courier New")
        self.assertGreater(len(lines), 1)
        self.assertLessEqual(len(lines), 3)
        self.assertLessEqual(size, 18)
        self.preview.toggle_play()
        self.wait_for(lambda: self.preview.position > 300)
        self.assertFalse(self.preview.output.sample.image.isNull())

    def test_style_edit_returns_rendered_view_to_sample(self):
        from local_caption.subtitle_style import SubtitleStyle
        self.load_pair()
        self.assertFalse(self.preview.showing_sample)
        self.preview.set_subtitle_style(SubtitleStyle(max_lines=2))
        self.assertTrue(self.preview.showing_sample)
        self.assertTrue(self.preview.output.player.source().isEmpty())
        self.assertTrue(self.preview.output.view_choice.model().item(1).isEnabled())
        self.preview.output.view_choice.setCurrentIndex(1)
        self.assertFalse(self.preview.showing_sample)
        self.wait_for(lambda: self.preview.output.player.duration() > 0)

    def test_missing_or_srt_output_is_empty(self):
        self.preview.set_output("missing.mp4")
        self.assertTrue(self.preview.output.player.source().isEmpty())
        self.assertFalse(self.preview.play_button.isEnabled())
