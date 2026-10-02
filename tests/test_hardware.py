import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from local_caption.engine import Job, process
from local_caption.hardware import check_encoder, encoder_args, nvenc_inventory, probe_rendering, probe_transcription, valid_inference_device
from local_caption.hardware_ui import HardwarePanel


class HardwareTests(unittest.TestCase):
    def test_allowlisted_encoder_options(self):
        for encoder, expected in [("cpu", "libx264"), ("nvenc:0", "h264_nvenc"), ("qsv", "h264_qsv"), ("amf", "h264_amf")]:
            self.assertIn(expected, encoder_args(encoder))
        self.assertEqual(encoder_args("nvenc:2")[-2:], ["-gpu", "2"])
        for value in ("nvenc:-1", "nvenc:0;dir", "libx264 -y", "cuda:0", "garbage"):
            with self.assertRaises(ValueError):
                encoder_args(value)
        self.assertTrue(valid_inference_device("cuda:0"))
        self.assertTrue(valid_inference_device("cpu"))
        self.assertFalse(valid_inference_device("cuda:0 --invalid"))

    def test_invalid_job_devices_rejected_before_file_io(self):
        with self.assertRaisesRegex(ValueError, "transcription device"):
            Job("", "", transcription_device="bad").validate()
        with self.assertRaisesRegex(ValueError, "encoder"):
            Job("", "", video_encoder="bad").validate()

    def test_failed_gpu_preflight_preserves_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.mp4"
            output.write_bytes(b"original")
            job = Job("source.mp4", str(output), mode="burn", video_encoder="nvenc:0", overwrite=True)
            with patch.object(Job, "validate"), patch("local_caption.engine.check_encoder", return_value=(False, "driver unavailable")):
                with self.assertRaisesRegex(RuntimeError, "Rescan or choose CPU"):
                    process(job, Path(directory), lambda *args: None)
            self.assertEqual(output.read_bytes(), b"original")

    def test_cpu_only_runtime_report(self):
        with patch.dict(sys.modules, {"torch": SimpleNamespace(version=SimpleNamespace(cuda=None))}):
            choices, notes = probe_transcription()
        self.assertEqual(choices, [])
        self.assertIn("CPU-only", notes[0])

    def test_cuda_driver_unavailable(self):
        torch = SimpleNamespace(version=SimpleNamespace(cuda="12.8"), cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict(sys.modules, {"torch": torch}):
            choices, notes = probe_transcription()
        self.assertEqual(choices, [])
        self.assertIn("driver", notes[0])

    def test_only_live_passing_encoders_are_enabled(self):
        def check(ffmpeg, encoder):
            return (encoder in {"qsv", "nvenc:1"}, "probe detail")
        cards = [{"id": "0", "name": "GPU 0"}, {"id": "1", "name": "GPU 1"}]
        with patch("local_caption.hardware.check_encoder", side_effect=check), patch("local_caption.hardware.nvenc_inventory", return_value=cards):
            choices, notes = probe_rendering("ffmpeg")
        self.assertEqual([c["id"] for c in choices], ["nvenc:1", "qsv"])
        self.assertEqual(len(notes), 2)

    def test_nvenc_uses_ffmpeg_ordinals_not_inventory_order(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / "ffmpeg.exe"
            tool.touch()
            listing = "[h264_nvenc] [ GPU #1 - < NVIDIA Second Card > has Compute SM 8.9 ]"
            with patch("local_caption.hardware.command", return_value=SimpleNamespace(returncode=1, stderr=listing)):
                self.assertEqual(nvenc_inventory(str(tool)), [{"id": "1", "name": "NVIDIA Second Card"}])

    def test_probe_executes_real_frames_and_handles_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = Path(directory) / "ffmpeg.exe"
            tool.touch()
            with patch("local_caption.hardware.command", return_value=SimpleNamespace(returncode=0, stderr="")) as run:
                self.assertTrue(check_encoder(str(tool), "nvenc:0")[0])
                args = run.call_args.args[0]
                self.assertIn("color=c=black:s=640x360:r=25:d=0.12", args)
                self.assertIn("h264_nvenc", args)
            with patch("local_caption.hardware.command", side_effect=subprocess.TimeoutExpired("ffmpeg", 15)):
                self.assertFalse(check_encoder(str(tool), "nvenc:0")[0])


class HardwareGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = HardwarePanel(auto_scan=False)

    def tearDown(self):
        self.panel.shutdown()
        self.panel.close()

    def test_cpu_default_and_no_gpu_disabled(self):
        self.assertEqual(self.panel.transcription.currentData(), "cpu")
        self.panel.apply_report({"adapters": ["Old card"], "transcription": [], "rendering": []})
        for combo in (self.panel.transcription, self.panel.rendering):
            self.assertEqual(combo.currentData(), "cpu")
            self.assertIn("no compatible GPU found", combo.itemText(1))
            self.assertFalse(combo.model().item(1).isEnabled())

    def test_independent_tasks_and_mode_disabling(self):
        self.panel.apply_report({"adapters": ["NVIDIA", "Intel"], "transcription": [{"id": "cuda:0", "label": "GPU CUDA"}],
                                 "rendering": [{"id": "qsv", "label": "GPU Intel"}]})
        self.panel.transcription.setCurrentIndex(1)
        self.panel.rendering.setCurrentIndex(1)
        self.assertEqual(self.panel.transcription.currentData(), "cuda:0")
        self.assertEqual(self.panel.rendering.currentData(), "qsv")
        self.panel.set_mode("transcribe_mux")
        self.assertTrue(self.panel.transcription.isEnabled())
        self.assertFalse(self.panel.rendering.isEnabled())
        self.panel.set_mode("burn")
        self.assertFalse(self.panel.transcription.isEnabled())
        self.assertTrue(self.panel.rendering.isEnabled())
        self.panel.set_running(True)
        self.assertFalse(self.panel.isEnabled())

    def test_tool_change_invalidates_old_gpu_choices(self):
        self.panel.apply_report({"transcription": [], "rendering": [{"id": "nvenc:0", "label": "NVENC"}]})
        self.panel.rendering.setCurrentIndex(1)
        self.panel.set_ffmpeg("different-ffmpeg.exe")
        self.assertEqual(self.panel.rendering.currentData(), "cpu")
        self.assertFalse(self.panel.rendering.model().item(1).isEnabled())
