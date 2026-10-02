"""Responsive device selection. Probes run in a disposable subprocess, never Qt's UI thread."""

import json
import os
from pathlib import Path
import signal
import sys
import tempfile

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QPlainTextEdit, QPushButton

from .hardware import NO_GPU


class HardwarePanel(QGroupBox):
    def __init__(self, auto_scan=True):
        super().__init__("Processing devices")
        self.auto_scan = auto_scan
        self.ffmpeg = ""
        self.mode = "transcribe_burn"
        self.process = None
        self.workspace = None
        self.output = bytearray()
        self.errors = bytearray()
        self.job_running = False
        self.report = {}
        form = QFormLayout(self)
        self.transcription = QComboBox()
        self.rendering = QComboBox()
        for combo in (self.transcription, self.rendering):
            combo.setMinimumContentsLength(22)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.populate(self.transcription, [], "GPU — checking devices…")
        self.populate(self.rendering, [], "GPU — checking devices…")
        form.addRow("Transcription", self.transcription)
        form.addRow("Video encoding", self.rendering)
        self.summary = QLabel("Device scan pending. CPU is always available.")
        self.summary.setWordWrap(True)
        form.addRow(self.summary)
        self.scan_button = QPushButton("Rescan GPUs")
        self.scan_button.clicked.connect(self.scan)
        form.addRow(self.scan_button)
        details_button = QPushButton("Device details / diagnostics")
        details_button.setCheckable(True)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(150)
        self.details.hide()
        details_button.toggled.connect(self.details.setVisible)
        form.addRow(details_button)
        form.addRow(self.details)
        note = QLabel("GPU rendering accelerates video encoding; caption filtering remains on CPU.\n"
                      "Selectable-track jobs copy the picture and need no video encoder.")
        note.setWordWrap(True)
        form.addRow(note)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(600)
        self.debounce.timeout.connect(self.scan)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.setInterval(120000)
        self.deadline.timeout.connect(self.timed_out)

    @staticmethod
    def populate(combo, choices, empty_label=None):
        selected = combo.currentData()
        combo.clear()
        combo.addItem("CPU", "cpu")
        for choice in choices:
            combo.addItem(choice["label"], choice["id"])
            combo.setItemData(combo.count() - 1, choice.get("detail", ""), Qt.ItemDataRole.ToolTipRole)
        if not choices:
            combo.addItem(empty_label or f"GPU — {NO_GPU}", None)
            combo.model().item(1).setEnabled(False)
        previous = combo.findData(selected) if selected is not None else 0
        combo.setCurrentIndex(previous if previous >= 0 else 0)

    def set_ffmpeg(self, path):
        path = str(Path(path).expanduser().resolve()) if path else ""
        if path == self.ffmpeg and self.report:
            return
        self.ffmpeg = path
        self.abort()
        self.report = {}
        self.populate(self.transcription, [], "GPU — checking devices…")
        self.populate(self.rendering, [], "GPU — checking devices…")
        self.summary.setText("Device scan pending. CPU is available while scanning.")
        if self.auto_scan:
            self.debounce.start()

    def set_mode(self, mode):
        self.mode = mode
        self.transcription.setEnabled(mode.startswith("transcribe") and not self.job_running)
        self.rendering.setEnabled(mode in {"burn", "transcribe_burn"} and not self.job_running)
        self.rendering.setToolTip("Not used: this action does not encode video." if mode not in {"burn", "transcribe_burn"} else "")

    def set_running(self, running):
        self.job_running = running
        if running:
            self.debounce.stop()
            self.abort()
        self.setEnabled(not running)
        self.set_mode(self.mode)
        if not running and not self.report and self.auto_scan:
            self.debounce.start()

    def scan(self):
        if self.job_running:
            return
        self.debounce.stop()
        self.abort()
        self.output.clear()
        self.errors.clear()
        self.scan_button.setEnabled(False)
        self.summary.setText("Scanning cards, testing CUDA and hardware video encoders… CPU remains available.")
        self.workspace = tempfile.TemporaryDirectory(prefix="local-caption-devices-")
        request = Path(self.workspace.name) / "request.json"
        request.write_text(json.dumps({"ffmpeg": self.ffmpeg}), encoding="utf-8")
        process = QProcess(self)
        self.process = process
        process.readyReadStandardOutput.connect(lambda: self.output.extend(bytes(process.readAllStandardOutput())))
        process.readyReadStandardError.connect(lambda: self.errors.extend(bytes(process.readAllStandardError())))
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.failed_to_start)
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable).with_name("LocalCaptionWorker.exe" if os.name == "nt" else "LocalCaptionWorker")
            process.start(str(executable), ["--probe-devices", str(request)])
        else:
            process.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
            process.start(sys.executable, ["-u", "-m", "local_caption", "--probe-devices", str(request)])
        self.deadline.start()

    def failed_to_start(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            message = self.process.errorString()
            self.abort()
            self.show_failure("Device probe could not start: " + message)

    def timed_out(self):
        self.abort()
        self.show_failure("Device scan timed out. CPU is available; rescan when the driver responds.")

    def finished(self, code, status):
        if self.process is None:
            return
        self.output.extend(bytes(self.process.readAllStandardOutput()))
        self.errors.extend(bytes(self.process.readAllStandardError()))
        self.deadline.stop()
        self.process.deleteLater()
        self.process = None
        self.scan_button.setEnabled(True)
        self.cleanup()
        try:
            if code:
                raise ValueError(self.errors.decode("utf-8", errors="replace")[-3000:] or f"Probe exited with code {code}.")
            report = json.loads(self.output)
            self.apply_report(report)
        except (ValueError, KeyError, TypeError) as error:
            self.show_failure(f"Device scan failed: {error}")

    def apply_report(self, report):
        self.report = report
        self.populate(self.transcription, report["transcription"])
        self.populate(self.rendering, report["rendering"])
        adapters = "; ".join(report.get("adapters", [])) or "No card names reported by the driver"
        inference = f"{len(report['transcription'])} GPU option(s)" if report["transcription"] else NO_GPU
        rendering = f"{len(report['rendering'])} GPU option(s)" if report["rendering"] else NO_GPU
        self.summary.setText(f"Video cards: {adapters}\nTranscription: {inference}. Video encoding: {rendering}.")
        details = ["Detected adapters: " + adapters]
        for task in ("transcription", "rendering"):
            details.append("\n" + task.upper())
            details.extend(f"{item['label']}: {item.get('detail', '')}" for item in report[task])
            details.extend(report.get(task + "_notes", []))
        details.extend(report.get("notes", []))
        self.details.setPlainText("\n".join(details))
        self.set_mode(self.mode)

    def show_failure(self, message):
        self.apply_report({"adapters": [], "transcription": [], "rendering": [], "notes": [message]})
        self.summary.setText(message + f"\nGPU: {NO_GPU}")

    def cleanup(self):
        if self.workspace:
            try:
                self.workspace.cleanup()
            except OSError:
                pass  # A leftover diagnostic request must not crash shutdown.
            self.workspace = None

    def abort(self):
        self.deadline.stop()
        process, self.process = self.process, None
        if process is not None:
            process.blockSignals(True)
            if process.state() != QProcess.ProcessState.NotRunning:
                if os.name != "nt":
                    try:
                        os.killpg(process.processId(), signal.SIGKILL)
                    except ProcessLookupError:
                        process.kill()
                else:
                    process.kill()
                process.waitForFinished(3000)
            process.deleteLater()
        self.scan_button.setEnabled(True)
        self.cleanup()

    def shutdown(self):
        self.debounce.stop()
        self.abort()
