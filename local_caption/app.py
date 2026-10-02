"""Desktop frontend. All expensive / third-party processing runs in a child process."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

from PySide6.QtCore import QDir, QProcess, QSettings, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .engine import Job, MODES
from .preview import ComparisonPreview


class FileField(QWidget):
    def __init__(self, title, file_filter="All files (*)", save=False):
        super().__init__()
        self.title, self.file_filter, self.save = title, file_filter, save
        self.edit = QLineEdit()
        self.edit.editingFinished.connect(lambda: self.setText(self.text()))
        self.edit.setPlaceholderText("Drop a local file here, or browse…")
        button = QPushButton("Browse…")
        button.clicked.connect(self.browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        layout.addWidget(button)
        self.setAcceptDrops(True)
        self.edit.setAcceptDrops(False)

    def text(self):
        return QDir.toNativeSeparators(self.edit.text().strip().strip('"'))

    def setText(self, value):
        self.edit.setText(QDir.toNativeSeparators(str(value).strip().strip('"')))

    def browse(self):
        method = QFileDialog.getSaveFileName if self.save else QFileDialog.getOpenFileName
        path, _ = method(self, self.title, self.text(), self.file_filter)
        if path:
            self.setText(path)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).is_file():
            self.setText(urls[0].toLocalFile())
            event.acceptProposedAction()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Caption — offline subtitles")
        self.resize(1120, 940)
        self.setAcceptDrops(True)
        self.settings = QSettings("LocalCaption", "LocalCaption")
        self.process = None
        self.workspace = None
        self.pending = b""
        self.cancelled = False
        self.done = False
        self.started = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        root = QWidget()
        layout = QVBoxLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        heading = QLabel("Drop a video to begin. Processing stays on this machine.")
        heading.setStyleSheet("font-size: 17px; font-weight: bold; padding: 8px 0;")
        layout.addWidget(heading)
        self.inputs = QGroupBox("Job")
        job_layout = QVBoxLayout(self.inputs)
        self.preview = ComparisonPreview()
        job_layout.addWidget(self.preview)
        form = QFormLayout()
        job_layout.addLayout(form)
        self.source = FileField("Input video")
        self.output = FileField("Save output", "Output (*.mp4 *.srt)", save=True)
        self.srt = FileField("Existing subtitles", "SubRip (*.srt)")
        self.mode = QComboBox()
        for key, label in MODES.items():
            self.mode.addItem(label, key)
        self.language = QComboBox()
        self.language.addItems(["en", "ru", "auto"])
        self.overwrite = QCheckBox("Allow replacing the output video after successful rendering")
        for label, field in [("Video", self.source), ("Action", self.mode), ("Output", self.output),
                             ("Existing SRT", self.srt), ("Language", self.language), ("", self.overwrite)]:
            form.addRow(label, field)
        layout.addWidget(self.inputs)

        self.tools = QGroupBox("Local tools and model — choose files you trust")
        tools = QFormLayout(self.tools)
        self.model = FileField("Local Whisper model", "Whisper checkpoint (*.pt)")
        self.ffmpeg = FileField("FFmpeg executable")
        self.ffprobe = FileField("FFprobe executable")
        for key, field in [("model", self.model), ("ffmpeg", self.ffmpeg), ("ffprobe", self.ffprobe)]:
            default = shutil.which(key) or "" if key != "model" else ""
            field.setText(str(self.settings.value(key, default)))
            tools.addRow(key, field)
        layout.addWidget(self.tools)
        note = QLabel("No automatic downloads. SRT files are always preserved using numbered names.\n"
                      "Burning re-encodes video; selectable tracks preserve the picture. Use originals to avoid double captions.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel("Ready")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.elapsed = QLabel("")
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.elapsed)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setMaximumHeight(100)
        layout.addWidget(self.log, 1)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        open_button = QPushButton("Open output folder")
        open_button.clicked.connect(self.open_folder)
        for button in (self.start_button, self.cancel_button, open_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.source.edit.textChanged.connect(self.suggest_output)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.mode_changed()
        self.preview.inputDropped.connect(self.source.setText)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(350)
        self.preview_timer.timeout.connect(self.refresh_previews)
        self.source.edit.textChanged.connect(lambda: self.preview_timer.start())
        self.output.edit.textChanged.connect(lambda: self.preview_timer.start())
        self.mode.currentIndexChanged.connect(lambda: self.preview_timer.start())

    def refresh_previews(self):
        if self.process is not None:
            return
        source = self.source.text()
        source_url = QUrl.fromLocalFile(str(Path(source).resolve())) if source and Path(source).is_file() else QUrl()
        if source_url != self.preview.input.player.source():
            self.preview.set_input(source)
        output = self.output.text() if self.mode.currentData() != "transcribe" else ""
        self.preview.set_output(output)
        if self.mode.currentData() == "transcribe":
            self.preview.output.message.setText("SRT-only job — no output video")

    def suggest_output(self):
        if self.source.text():
            source = Path(self.source.text()).expanduser().resolve()
            suffix = ".srt" if self.mode.currentData() == "transcribe" else ".mp4"
            self.output.setText(str(source.with_name(source.stem + "-captioned" + suffix)))

    def mode_changed(self):
        transcribing = self.mode.currentData().startswith("transcribe")
        self.srt.setEnabled(not transcribing)
        self.model.setEnabled(transcribing)
        self.language.setEnabled(transcribing)
        self.overwrite.setEnabled(self.mode.currentData() != "transcribe")
        self.suggest_output()

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if self.process is None and len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if self.process is None and len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.is_file():
                if path.suffix.lower() == ".srt":
                    self.srt.setText(str(path))
                else:
                    self.source.setText(str(path))
                event.acceptProposedAction()

    def start(self):
        def absolute(field):
            return str(Path(field.text()).expanduser().resolve()) if field.text() else ""
        job = Job(source=absolute(self.source), output=absolute(self.output), mode=self.mode.currentData(),
                  model=absolute(self.model), srt=absolute(self.srt), ffmpeg=absolute(self.ffmpeg),
                  ffprobe=absolute(self.ffprobe), language=self.language.currentText(), overwrite=self.overwrite.isChecked())
        try:
            job.validate()
            if job.overwrite and job.mode != "transcribe" and Path(job.output).exists():
                if QMessageBox.question(self, "Replace output?", f"Replace this file only after successful rendering?\n{job.output}") != QMessageBox.StandardButton.Yes:
                    return
            Path(job.output).parent.mkdir(parents=True, exist_ok=True)
            self.workspace = tempfile.TemporaryDirectory(prefix=".local-caption-", dir=Path(job.output).parent)
            job_path = Path(self.workspace.name) / "job.json"
            job_path.write_text(json.dumps(asdict(job)), encoding="utf-8")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot start", str(error))
            self.cleanup()
            return
        for key, field in [("model", self.model), ("ffmpeg", self.ffmpeg), ("ffprobe", self.ffprobe)]:
            self.settings.setValue(key, field.text())
        self.preview_timer.stop()
        self.preview.release_output()
        self.log.clear()
        self.pending = b""
        self.cancelled = self.done = False
        self.started = time.monotonic()
        self.inputs.setEnabled(False)
        self.tools.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Starting local worker…")
        self.progress.setRange(0, 0)
        self.timer.start(1000)
        process = QProcess(self)
        self.process = process
        process.readyReadStandardOutput.connect(self.read_events)
        process.readyReadStandardError.connect(self.read_errors)
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        if getattr(sys, "frozen", False):
            worker = Path(sys.executable).with_name("LocalCaptionWorker.exe" if os.name == "nt" else "LocalCaptionWorker")
            process.start(str(worker), ["--worker", str(job_path)])
        else:
            process.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
            process.start(sys.executable, ["-u", "-m", "local_caption", "--worker", str(job_path)])

    def tick(self):
        self.elapsed.setText(f"Elapsed: {int(time.monotonic() - self.started)} seconds. Progress advances at confirmed audio checkpoints; ETA is unknown.")

    def read_events(self):
        if self.process is None:
            return
        self.pending += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.pending:
            line, self.pending = self.pending.split(b"\n", 1)
            try:
                event = json.loads(line)
                kind, value = event["event"], event["value"]
            except (ValueError, KeyError):
                self.log.appendPlainText(line.decode("utf-8", errors="replace"))
                continue
            if kind == "progress":
                self.progress.setRange(0, 100)
                self.progress.setValue(int(value))
            elif kind == "status":
                self.status.setText(str(value))
                self.progress.setRange(0, 0)
                self.log.appendPlainText(str(value))
            elif kind == "done":
                self.done = True
            else:
                self.log.appendPlainText(f"{kind.upper()}: {value}")

    def read_errors(self):
        if self.process is not None:
            self.log.appendPlainText(bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace").rstrip())

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText("Worker could not start: " + self.process.errorString())
            self.finished(1, QProcess.ExitStatus.CrashExit)

    def finished(self, code, exit_status):
        if self.process is None:
            return
        self.read_events()
        self.read_errors()
        self.timer.stop()
        success = code == 0 and self.done
        self.status.setText("Completed" if success else "Cancelled — already saved outputs are retained" if self.cancelled else "Failed — see details below")
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else 0)
        self.process.deleteLater()
        self.process = None
        self.inputs.setEnabled(True)
        self.tools.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.cleanup()
        self.refresh_previews()

    def cleanup(self):
        if self.workspace:
            try:
                self.workspace.cleanup()
                self.workspace = None
            except OSError as error:
                self.log.appendPlainText(f"Temporary files could not be removed: {error}")

    def cancel(self):
        if self.process is None:
            return
        self.cancelled = True
        self.status.setText("Cancelling…")
        self.cancel_button.setEnabled(False)
        if os.name != "nt":
            try:
                os.killpg(self.process.processId(), signal.SIGKILL)
            except ProcessLookupError:
                self.process.kill()
        else:
            # The worker's kill-on-close Windows Job Object kills FFmpeg children.
            self.process.kill()

    def open_folder(self):
        if self.output.text():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.output.text()).resolve().parent)))

    def closeEvent(self, event):
        if self.process is not None:
            if QMessageBox.question(self, "Cancel job?", "Cancel the running job before closing?") != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.cancel()
            if self.process is not None:
                self.process.waitForFinished(5000)
            if self.process is not None:
                event.ignore()
                return
        self.preview_timer.stop()
        self.preview.close_media()
        self.cleanup()
        event.accept()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Local Caption desktop app")
    parser.add_argument("--input", help="Preselect a local input video (does not start processing)")
    parser.add_argument("--output", help="Preselect the output path / comparison video")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    window = Window()
    if args.input:
        window.source.setText(str(Path(args.input).expanduser().resolve()))
    if args.output:
        window.output.setText(str(Path(args.output).expanduser().resolve()))
    window.show()
    return app.exec()
