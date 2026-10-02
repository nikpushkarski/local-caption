"""Exercise an actual packaged worker with generated media, optionally local speech/model.

Run from the repository root. No model download or modification is performed.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from local_caption.engine import Job
from local_caption import __version__

parser = argparse.ArgumentParser()
parser.add_argument("--worker", type=Path, default=Path(f"dist/v{__version__}/LocalCaption/LocalCaptionWorker.exe"))
parser.add_argument("--model", type=Path)
parser.add_argument("--speech", type=Path)
parser.add_argument("--transcription-device", default="cpu")
parser.add_argument("--video-encoder", default="cpu")
parser.add_argument("--source-worker", action="store_true", help="Test Python source instead of the frozen worker")
parser.add_argument("--font", default="Arial")
parser.add_argument("--font-size", type=int)
parser.add_argument("--line-width", type=int, default=24)
parser.add_argument("--lines", type=int, default=1)
args = parser.parse_args()
ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
if not ffmpeg or not ffprobe:
    parser.error("FFmpeg and FFprobe must be on PATH for this development smoke test.")
with tempfile.TemporaryDirectory(prefix="local-caption smoke ü '") as directory:
    root = Path(directory)
    source = root / "source.mp4"
    command = [ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=25:d=6"]
    if args.speech:
        command += ["-i", str(args.speech.resolve()), "-c:a", "aac", "-shortest"]
    command += ["-c:v", "libx264", "-y", str(source)]
    subprocess.run(command, check=True)
    srt = root / "edited.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello мир\n", encoding="utf-8")
    modes = ["burn", "mux"]
    if args.model and args.speech:
        modes.append("transcribe_burn")
    for mode in modes:
        work = root / mode
        work.mkdir()
        output = root / f"{mode}.mp4"
        job = Job(str(source), str(output), mode, model=str(args.model.resolve()) if args.model else "",
                  srt=str(srt), ffmpeg=ffmpeg, ffprobe=ffprobe,
                  transcription_device=args.transcription_device, video_encoder=args.video_encoder,
                  subtitle_style={"font": args.font, "font_size": args.font_size,
                                  "chars_per_line": args.line_width, "max_lines": args.lines})
        job_path = work / "job.json"
        job_path.write_text(json.dumps(asdict(job)), encoding="utf-8")
        print(f"Testing {'source' if args.source_worker else 'packaged'} worker: {mode} ({args.transcription_device}, {args.video_encoder})", flush=True)
        worker = [sys.executable, "-m", "local_caption"] if args.source_worker else [str(args.worker.resolve())]
        result = subprocess.run([*worker, "--worker", str(job_path)], capture_output=True, timeout=600)
        print(result.stdout.decode("utf-8", errors="replace"), flush=True)
        if result.returncode:
            print(result.stderr.decode("utf-8", errors="replace"))
            raise SystemExit(result.returncode)
        assert output.is_file() and output.stat().st_size > 0
        assert json.loads(result.stdout.splitlines()[-1])["event"] == "done"
        if mode.startswith("transcribe"):
            print(output.with_suffix(".srt").read_text(encoding="utf-8"), flush=True)
    print("Packaged worker smoke tests passed.")
