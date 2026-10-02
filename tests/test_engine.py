import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from local_caption.engine import Job, process, publish

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


class SafetyTests(unittest.TestCase):
    def test_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            staged, output = Path(d) / "staged", Path(d) / "output"
            staged.write_text("new")
            output.write_text("old")
            with self.assertRaises(FileExistsError):
                publish(staged, output, False)
            self.assertEqual(output.read_text(), "old")
            publish(staged, output, True)
            self.assertEqual(output.read_text(), "new")

    def test_source_protection(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "source.mp4"
            source.touch()
            with self.assertRaisesRegex(ValueError, "Input and output"):
                Job(str(source), str(source), overwrite=True).validate()
            alias = Path(d) / "alias.mp4"
            os.link(source, alias)
            with self.assertRaisesRegex(ValueError, "Input and output"):
                Job(str(source), str(alias), overwrite=True).validate()

    def test_failure_preserves_output(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            output = folder / "out.mp4"
            output.write_bytes(b"precious")
            job = Job(str(folder / "in.mp4"), str(output), "burn", srt=str(folder / "sub.srt"), overwrite=True)
            with patch.object(Job, "validate"), patch("local_caption.engine.run_tool", side_effect=RuntimeError("failed")):
                with self.assertRaises(RuntimeError):
                    process(job, folder, lambda *args: None)
            self.assertEqual(output.read_bytes(), b"precious")


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg and FFprobe required")
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="caption test ü '")
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "source ' ü.mp4"
        cls.srt = cls.root / "edited.srt"
        cls.srt.write_text("1\n00:00:00,000 --> 00:00:00,500\nHello мир\n\n2\n00:00:00,600 --> 00:00:01,000\nSecond cue\n", encoding="utf-8")
        subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
                        "-c:v", "libx264", "-y", str(cls.source)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def worker(self, mode, style=None):
        from dataclasses import asdict
        name = mode + ("-custom" if style else "")
        directory = self.root / name
        directory.mkdir(exist_ok=True)
        output = self.root / f"{name}.mp4"
        job = Job(str(self.source), str(output), mode, srt=str(self.srt), ffmpeg=FFMPEG, ffprobe=FFPROBE,
                  subtitle_style=style or {})
        job_file = directory / "job.json"
        job_file.write_text(json.dumps(asdict(job)), encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "local_caption", "--worker", str(job_file)], capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(events[-1]["event"], "done")
        self.assertGreater(output.stat().st_size, 0)
        return output

    def test_burn_silent_video(self):
        before = self.srt.read_bytes()
        output = self.worker("burn")
        # Compare decoded frames to prove that captions actually changed pixels.
        def frame(path):
            return subprocess.check_output([FFMPEG, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
        self.assertNotEqual(frame(self.source), frame(output))
        self.assertEqual(self.srt.read_bytes(), before)

    def test_custom_font_and_multiline_render_copy(self):
        before = self.srt.read_bytes()
        self.worker("burn", {"font": "Courier New", "font_size": 18, "chars_per_line": 6, "max_lines": 3})
        ass = (self.root / "burn-custom" / "captions.ass").read_text(encoding="utf-8")
        self.assertIn("Courier New,18", ass)
        self.assertIn(r"Hello\Nмир", ass)
        self.assertEqual(self.srt.read_bytes(), before)

    def test_mux_silent_video(self):
        output = self.worker("mux")
        probe = json.loads(subprocess.check_output([FFPROBE, "-v", "error", "-show_streams", "-of", "json", str(output)]))
        self.assertIn("mov_text", [s["codec_name"] for s in probe["streams"]])

    def test_silent_transcription_fails_before_model_load(self):
        job = Job(str(self.source), str(self.root / "silent.srt"), "transcribe", model=str(self.srt), ffmpeg=FFMPEG, ffprobe=FFPROBE)
        with self.assertRaisesRegex(ValueError, "no audio"):
            process(job, self.root, lambda *args: None)
