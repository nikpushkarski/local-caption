"""Headless processing; external tools are explicit and never invoked via a shell."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
from typing import Callable

from .captions import display_dimensions, fit_ass_captions, single_line_captions
from .srt import save_new_srt
from .hardware import check_encoder, encoder_args, valid_inference_device
from .subtitle_style import SubtitleStyle

MODES = {
    "transcribe_burn": "Transcribe + burn captions into video",
    "transcribe": "Transcribe to SRT only",
    "burn": "Burn an existing / edited SRT",
    "transcribe_mux": "Transcribe + add selectable subtitle track",
    "mux": "Add existing SRT as selectable track",
}


@dataclass
class Job:
    source: str
    output: str
    mode: str = "transcribe_burn"
    model: str = ""
    srt: str = ""
    ffmpeg: str = ""
    ffprobe: str = ""
    language: str = "en"
    overwrite: bool = False
    transcription_device: str = "cpu"
    video_encoder: str = "cpu"
    subtitle_style: dict = field(default_factory=dict)

    def validate(self):
        SubtitleStyle.from_dict(self.subtitle_style)
        if not valid_inference_device(self.transcription_device):
            raise ValueError("Unsupported transcription device selection.")
        encoder_args(self.video_encoder)  # Validate the allowlist before running any tool.
        if self.mode not in MODES:
            raise ValueError("Unknown processing mode.")
        if self.language not in {"en", "ru", "auto"}:
            raise ValueError("Choose English, Russian or automatic language detection.")
        source, output = Path(self.source), Path(self.output)
        if not source.is_absolute() or not source.is_file():
            raise ValueError("Choose an existing input video using an absolute path.")
        if not output.is_absolute() or output.suffix.lower() != (".srt" if self.mode == "transcribe" else ".mp4"):
            raise ValueError("Output must be an absolute .srt or .mp4 path matching the mode.")
        if same_file(source, output):
            raise ValueError("Input and output must differ. The source is never overwritten.")
        for executable in (self.ffmpeg, self.ffprobe):
            if not executable or not Path(executable).is_absolute() or not Path(executable).is_file():
                raise ValueError("Select trusted local FFmpeg and FFprobe executables in Settings.")
        if self.mode.startswith("transcribe"):
            if not self.model or not Path(self.model).is_absolute() or not Path(self.model).is_file():
                raise ValueError("Select a trusted local Whisper .pt model. Models are never downloaded.")
        else:
            srt = Path(self.srt)
            if not srt.is_file() or srt.suffix.lower() != ".srt" or not srt.stat().st_size:
                raise ValueError("Choose a nonempty existing .srt file.")
            if same_file(srt, output):
                raise ValueError("Output must not replace the subtitle input.")
        if output.exists() and self.mode != "transcribe":
            if not output.is_file() or not self.overwrite:
                raise ValueError("Output exists. Choose a new name or explicitly allow replacement.")
        # Check potentially destructive path combinations before loading any model.
        if self.model and same_file(Path(self.model), output):
            raise ValueError("Output must not replace the model.")


def same_file(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve() or (a.exists() and b.exists() and os.path.samefile(a, b))


def run_tool(arguments: list[str], directory: Path, capture=False):
    """Keep arbitrary tool output out of the worker's JSON event stream."""
    with (directory / "tool.log").open("ab") as log:
        result = subprocess.run(
            arguments, cwd=directory, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    if result.returncode:
        with (directory / "tool.log").open("rb") as log:
            log.seek(0, 2)
            log.seek(max(0, log.tell() - 6000))
            detail = log.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{Path(arguments[0]).name} failed ({result.returncode}):\n{detail}")
    return result.stdout


def publish(staged: Path, output: Path, overwrite: bool):
    if overwrite:
        os.replace(staged, output)
    else:
        # Atomic no-clobber publication, including another app creating the target.
        # Fail safely on filesystems lacking hard-link support rather than truncate.
        os.link(staged, output)
        staged.unlink()


def process(job: Job, directory: Path, emit: Callable):
    job.validate()
    subtitle_style = SubtitleStyle.from_dict(job.subtitle_style)
    if job.mode in {"burn", "transcribe_burn"} and job.video_encoder != "cpu":
        emit("status", f"Checking selected GPU encoder ({job.video_encoder})…")
        compatible, detail = check_encoder(job.ffmpeg, job.video_encoder)
        if not compatible:
            raise RuntimeError("Selected GPU encoder is no longer available. Rescan or choose CPU.\n" + detail)
    source, output = Path(job.source), Path(job.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    emit("status", "Inspecting video…")
    probe = json.loads(run_tool([
        job.ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_streams", "-of", "json", str(source),
    ], directory, capture=True))
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("The input has no video stream.")
    if job.mode.startswith("transcribe") and not any(s.get("codec_type") == "audio" for s in streams):
        raise ValueError("The input has no audio stream to transcribe.")

    if job.mode.startswith("transcribe"):
        emit("status", "Extracting audio locally…")
        audio = directory / "audio.f32"
        run_tool([job.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                  "-protocol_whitelist", "file,pipe", "-i", str(source), "-vn",
                  "-ac", "1", "-ar", "16000", "-f", "f32le", "-y", str(audio)], directory)
        try:
            import numpy as np
            import whisper
        except ImportError as error:
            raise RuntimeError("Transcription dependencies are missing. Install the transcribe extra or use the full build.") from error
        import torch
        device = job.transcription_device
        if device != "cpu":
            index = int(device.partition(":")[2])
            if not torch.cuda.is_available() or index >= torch.cuda.device_count():
                raise RuntimeError("Selected CUDA GPU is unavailable. Rescan or choose CPU; no automatic fallback was made.")
        emit("status", f"Loading local Whisper model ({device})…")
        # Deserialize on CPU first to avoid simultaneously keeping checkpoint and
        # model copies on the GPU. Keep Whisper's float32 LayerNorm parameters.
        try:
            model = whisper.load_model(str(Path(job.model).resolve()), device="cpu")
            if device != "cpu":
                model = model.to(device)
            from .transcription import transcribe
            result = transcribe(model, np.fromfile(audio, dtype=np.float32), job.language, emit, device=device)
        except torch.cuda.OutOfMemoryError as error:
            raise RuntimeError("Not enough GPU memory for this model/audio. Choose CPU, a smaller model, or free GPU memory and rescan.") from error
        captions = single_line_captions(result["segments"], subtitle_style)
        if not captions:
            raise ValueError("No speech captions were produced. No output was replaced.")
        srt = save_new_srt(output.with_suffix(".srt"), captions, preserve_newlines=subtitle_style.max_lines > 1)
        emit("saved", str(srt))
        del model, result
        if device != "cpu":
            with torch.cuda.device(device):
                torch.cuda.empty_cache()
        if job.mode == "transcribe":
            return
    else:
        srt = Path(job.srt)

    staged = directory / "render.mp4"
    if job.mode in {"mux", "transcribe_mux"}:
        emit("status", "Adding selectable subtitle track (does not erase burned-in captions)…")
        command = [job.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                   "-protocol_whitelist", "file,pipe", "-i", str(source),
                   "-protocol_whitelist", "file,pipe", "-i", str(srt),
                   "-map", "0:v:0", "-map", "0:a?", "-map", "0:s?", "-map", "1:0",
                   "-c", "copy", "-c:s", "mov_text", "-movflags", "+faststart", "-y", str(staged)]
    else:
        emit("status", f"Fitting captions on CPU and encoding video ({job.video_encoder})…")
        # Use short local names so filter paths never need shell/filter escaping.
        import shutil
        shutil.copyfile(srt, directory / "captions.srt")
        run_tool([job.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                  "-protocol_whitelist", "file,pipe", "-i", "captions.srt", "-y", "captions.ass"], directory)
        ass = directory / "captions.ass"
        fitted, _ = fit_ass_captions(ass.read_text(encoding="utf-8-sig"), *display_dimensions(video), subtitle_style)
        if not any(line.startswith("Dialogue:") for line in fitted.splitlines()):
            raise ValueError("The SRT contains no renderable cues.")
        ass.write_text(fitted, encoding="utf-8")
        command = [job.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                   "-protocol_whitelist", "file,pipe", "-i", str(source),
                   "-map", "0:v:0", "-map", "0:a?", "-vf", "ass=captions.ass,pad=ceil(iw/2)*2:ceil(ih/2)*2",
                   *encoder_args(job.video_encoder),
                   "-c:a", "aac", "-movflags", "+faststart", "-y", str(staged)]
    run_tool(command, directory)
    if not staged.is_file() or staged.stat().st_size == 0:
        raise RuntimeError("FFmpeg produced no video; output unchanged.")
    publish(staged, output, job.overwrite)
    emit("saved", str(output))
