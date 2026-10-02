"""Paired local video players with one transport and a shared timeline."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QWindow
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton, QSlider, QStackedWidget, QVBoxLayout, QWidget

from .sample_preview import SamplePreview


class DropVideo(QVideoWidget):
    fileDropped = Signal(str)

    def __init__(self, allow_drop=False):
        super().__init__()
        self.allow_drop = allow_drop
        self.setAcceptDrops(True)
        self.setMinimumSize(220, 150)
        self.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        # QVideoWidget embeds a native QWindow via QWindowContainer on Windows.
        # Explorer drops land on that window, not on this QWidget. It is reparented
        # outside our QObject subtree, so intercept its events at application level.
        QApplication.instance().installEventFilter(self)

    def dropped_path(self, event):
        urls = event.mimeData().urls()
        if self.allow_drop and self.isEnabled() and len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.is_file() and path.suffix.lower() not in {".srt", ".pt", ".exe"}:
                return path
        return None

    def handle_drag(self, event):
        path = self.dropped_path(event)
        if path is None:
            event.ignore()
        else:
            event.acceptProposedAction()
            if event.type() == QEvent.Type.Drop:
                self.fileDropped.emit(str(path))

    def eventFilter(self, watched, event):
        if isinstance(watched, QWindow) and event.type() in {
            QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop,
        } and self.isVisible():
            owner = self.window().windowHandle()
            if owner is not None and (watched is owner or owner.isAncestorOf(watched)):
                point = self.mapFromGlobal(watched.mapToGlobal(event.position().toPoint()))
                if self.rect().contains(point):
                    self.handle_drag(event)
                    return True  # Do not let native video/root handlers reject or reroute it.
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        self.handle_drag(event)

    def dragMoveEvent(self, event):
        self.handle_drag(event)

    def dropEvent(self, event):
        self.handle_drag(event)


class VideoPane(QWidget):
    def __init__(self, title, placeholder, allow_drop=False, sample_preview=False):
        super().__init__()
        self.placeholder = placeholder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header_container = QWidget()
        header_container.setFixedHeight(self.fontMetrics().height() + 14)
        header = QHBoxLayout(header_container)
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(QLabel(title))
        self.view_choice = None
        if sample_preview:
            self.view_choice = QComboBox()
            self.view_choice.addItems(["Sample captions", "Rendered video"])
            self.view_choice.model().item(1).setEnabled(False)
            header.addWidget(self.view_choice)
        layout.addWidget(header_container)
        self.video = DropVideo(allow_drop)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.video)
        self.sample = SamplePreview() if sample_preview else None
        if self.sample is not None:
            self.stack.addWidget(self.sample)
            self.stack.setCurrentWidget(self.sample)
        layout.addWidget(self.stack, 1)
        self.message = QLabel(placeholder)
        self.message.setWordWrap(True)
        self.message.setMaximumHeight(42)
        layout.addWidget(self.message)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.errorOccurred.connect(self.show_error)
        self.player.tracksChanged.connect(self.enable_subtitles)
        self.player.mediaStatusChanged.connect(self.preroll)

    def load(self, path):
        url = QUrl.fromLocalFile(str(Path(path).resolve())) if path and Path(path).is_file() and Path(path).suffix.lower() != ".srt" else QUrl()
        if url == self.player.source():
            return
        self.player.stop()
        self.player.setSource(url)
        self.message.setText(Path(path).name if not url.isEmpty() else self.placeholder)
        self.message.setToolTip(str(path) if path else "")

    def clear(self):
        self.player.stop()
        self.player.setSource(QUrl())
        self.message.setText(self.placeholder)

    def show_error(self, error, detail):
        self.message.setText("Preview unavailable: " + detail)
        self.message.setToolTip(detail + "\nPreview errors do not prevent FFmpeg processing.")

    def preroll(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            # Decode a poster frame without auto-playing video or sound.
            self.player.pause()

    def enable_subtitles(self):
        if self.player.subtitleTracks():
            self.player.setActiveSubtitleTrack(0)


class ComparisonPreview(QWidget):
    inputDropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.playing = False
        self.scrubbing = False
        self.resume_after_seek = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        panes = QHBoxLayout()
        self.input = VideoPane("Input — drop a video here", "Choose or drop an input video", True)
        self.output = VideoPane("Output", "Rendered video will appear here", sample_preview=True)
        self.output_path = ""
        self.input.video.fileDropped.connect(self.inputDropped)
        for pane in self.panes:
            panes.addWidget(pane, 1)
            pane.player.durationChanged.connect(self.update_timeline)
            pane.player.positionChanged.connect(self.update_timeline)
            pane.player.mediaStatusChanged.connect(self.media_status)
        layout.addLayout(panes)
        self.setMinimumHeight(260)
        self.setMaximumHeight(360)
        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        self.back_button = QPushButton("−5 s")
        self.back_button.clicked.connect(lambda: self.seek(self.position - 5000))
        self.forward_button = QPushButton("+5 s")
        self.forward_button.clicked.connect(lambda: self.seek(self.position + 5000))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self.begin_scrub)
        self.slider.sliderReleased.connect(self.end_scrub)
        self.slider.sliderMoved.connect(self.scrub_to)
        self.slider.valueChanged.connect(self.slider_changed)
        self.time_label = QLabel("0:00 / 0:00")
        self.audio_choice = QComboBox()
        self.audio_choice.addItems(["Input audio", "Output audio", "Muted"])
        self.audio_choice.currentIndexChanged.connect(self.set_audio)
        for widget in (self.play_button, self.stop_button, self.back_button, self.forward_button, self.slider, self.time_label, self.audio_choice):
            transport.addWidget(widget, 1 if widget is self.slider else 0)
        layout.addLayout(transport)
        self.set_audio()
        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(250)
        self.sync_timer.timeout.connect(self.synchronize)
        self.output.view_choice.currentIndexChanged.connect(self.change_output_view)
        self.input.video.videoSink().videoFrameChanged.connect(self.sample_frame_changed)
        self.update_timeline()

    @property
    def panes(self):
        return (self.input, self.output)

    @property
    def master(self):
        # Prefer the input timeline; fall back to an independently selected output.
        return self.input.player if self.input.player.duration() > 0 else self.output.player

    @property
    def duration(self):
        return self.master.duration()

    @property
    def position(self):
        return self.master.position()

    @property
    def showing_sample(self):
        return self.output.view_choice.currentIndex() == 0

    def set_audio(self):
        selected = self.audio_choice.currentIndex()
        if self.showing_sample:
            self.input.audio.setMuted(selected == 2)
            self.output.audio.setMuted(True)
        else:
            for index, pane in enumerate(self.panes):
                pane.audio.setMuted(selected != index)

    def sample_frame_changed(self, frame):
        if self.showing_sample:
            self.output.sample.set_frame(frame)

    def set_subtitle_style(self, style):
        self.output.sample.set_style(style)
        if not self.showing_sample:
            self.output.view_choice.setCurrentIndex(0)
        else:
            self.sample_frame_changed(self.input.video.videoSink().videoFrame())

    def set_input(self, path):
        self.stop()
        self.output.sample.clear()
        self.input.load(path)
        self.output.view_choice.blockSignals(True)
        self.output.view_choice.setCurrentIndex(0)
        self.output.view_choice.blockSignals(False)
        self.change_output_view()
        self.update_timeline()

    def set_output(self, path, show_rendered=True):
        self.output_path = str(path) if path and Path(path).is_file() and Path(path).suffix.lower() != ".srt" else ""
        self.output.view_choice.model().item(1).setEnabled(bool(self.output_path))
        target = 1 if self.output_path and (show_rendered or not self.showing_sample) else 0
        self.output.view_choice.blockSignals(True)
        self.output.view_choice.setCurrentIndex(target)
        self.output.view_choice.blockSignals(False)
        self.change_output_view()

    def change_output_view(self):
        self.pause()
        if self.showing_sample:
            self.output.player.stop()
            self.output.player.setSource(QUrl())
            self.output.stack.setCurrentWidget(self.output.sample)
            self.output.message.setText("Sample only — not rendered or saved")
            self.output.sample.set_frame(self.input.video.videoSink().videoFrame())
        else:
            self.output.stack.setCurrentWidget(self.output.video)
            self.output.load(self.output_path)
            self.seek(self.position)
        self.set_audio()
        self.update_timeline()

    def release_output(self):
        # Release the destination before the worker attempts atomic replacement.
        self.stop()
        self.output.clear()
        self.output.sample.clear()
        self.update_timeline()

    def toggle_play(self):
        if self.playing:
            self.pause()
        else:
            if self.duration and self.position >= self.duration - 50:
                self.seek(0)
            self.playing = True
            self.play_button.setText("Pause")
            self.synchronize()
            for pane in self.panes:
                if not pane.player.source().isEmpty():
                    pane.player.play()
            self.sync_timer.start()

    def pause(self):
        self.playing = False
        self.sync_timer.stop()
        self.play_button.setText("Play")
        for pane in self.panes:
            pane.player.pause()

    def stop(self):
        self.pause()
        for pane in self.panes:
            pane.player.stop()
            pane.player.setPosition(0)
            if not pane.player.source().isEmpty():
                pane.player.pause()  # Decode the opening frame without playing sound.
        self.update_timeline()

    def seek(self, milliseconds):
        target = max(0, min(int(milliseconds), self.duration))
        for pane in self.panes:
            if pane.player.isSeekable():
                pane.player.setPosition(min(target, pane.player.duration()))
                if self.playing and target < pane.player.duration():
                    pane.player.play()
        self.update_timeline()

    def begin_scrub(self):
        self.scrubbing = True
        self.resume_after_seek = self.playing
        self.pause()

    def scrub_to(self, value):
        self.seek(round(value * self.duration / 1000))

    def end_scrub(self):
        self.scrub_to(self.slider.value())
        self.scrubbing = False
        if self.resume_after_seek:
            self.toggle_play()

    def slider_changed(self, value):
        # Keyboard/wheel and groove clicks should seek too, not only handle drags.
        if not self.scrubbing:
            self.scrub_to(value)

    @staticmethod
    def clock(milliseconds):
        seconds = max(0, milliseconds // 1000)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"

    def update_timeline(self, *args):
        ready = self.duration > 0
        for widget in (self.play_button, self.stop_button, self.back_button, self.forward_button, self.slider):
            widget.setEnabled(ready)
        if not self.scrubbing:
            self.slider.blockSignals(True)
            self.slider.setValue(round(self.position * 1000 / self.duration) if ready else 0)
            self.slider.blockSignals(False)
        self.time_label.setText(f"{self.clock(self.position)} / {self.clock(self.duration)}")

    def media_status(self, status):
        if self.master.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self.pause()
        elif status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.seek(self.position)
        self.update_timeline()

    def synchronize(self):
        # Separate decoders aren't frame-locked; periodically correct visible drift.
        master = self.master
        for pane in self.panes:
            player = pane.player
            if player is master or not player.isSeekable():
                continue
            target = min(master.position(), player.duration())
            if abs(player.position() - target) > 120:
                player.setPosition(target)
            if self.playing and target < player.duration() and player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                player.play()

    def close_media(self):
        self.stop()
        for pane in self.panes:
            pane.clear()
        self.output.sample.clear()
