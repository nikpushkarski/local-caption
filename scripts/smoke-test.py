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

parser = argparse.ArgumentParser()
parser.add_argument("--worker", type=Path, default=Path("dist/LocalCaption/LocalCaptionWorker.exe"))
parser.add_argument("--model", type=Path)
parser.add_argument("--speech", type=Path)
args = parser.parse_args()
ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
if not ffmpeg or not ffprobe:
    parser.error("FFmpeg and FFprobe must be on PATH for this development smoke test.")
with tempfile.TemporaryDirectory(prefix="local-caption smoke ü '") as directory:
    root = Path(directory)
    source = root / "source.mp4"
    command = [ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=25:d=6"]
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
                  srt=str(srt), ffmpeg=ffmpeg, ffprobe=ffprobe)
        job_path = work / "job.json"
        job_path.write_text(json.dumps(asdict(job)), encoding="utf-8")
        print(f"Testing packaged worker: {mode}", flush=True)
        result = subprocess.run([str(args.worker.resolve()), "--worker", str(job_path)], capture_output=True, timeout=600)
        print(result.stdout.decode("utf-8", errors="replace"), flush=True)
        if result.returncode:
            print(result.stderr.decode("utf-8", errors="replace"))
            raise SystemExit(result.returncode)
        assert output.is_file() and output.stat().st_size > 0
        assert json.loads(result.stdout.splitlines()[-1])["event"] == "done"
        if mode.startswith("transcribe"):
            print(output.with_suffix(".srt").read_text(encoding="utf-8"), flush=True)
    print("Packaged worker smoke tests passed.")
