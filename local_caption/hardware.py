"""Local capability probes. Inventory alone never qualifies a GPU as usable."""

import csv
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

NO_GPU = "no compatible GPU found"


def valid_inference_device(device):
    return device == "cpu" or bool(re.fullmatch(r"cuda:[0-9]{1,2}", device))


def encoder_args(encoder):
    """One allowlisted mapping shared by the live capability test and rendering."""
    if encoder == "cpu":
        return ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"]
    if re.fullmatch(r"nvenc:(auto|[0-9]{1,2})", encoder):
        args = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p"]
        if encoder != "nvenc:auto":
            args += ["-gpu", encoder.partition(":")[2]]
        return args
    if encoder == "qsv":
        return ["-c:v", "h264_qsv", "-preset", "medium", "-global_quality", "18", "-pix_fmt", "nv12"]
    if encoder == "amf":
        return ["-c:v", "h264_amf", "-usage", "transcoding", "-quality", "quality", "-rc", "cqp", "-qp_i", "18", "-qp_p", "18", "-pix_fmt", "nv12"]
    raise ValueError("Unsupported video encoder selection.")


def command(arguments, timeout=15):
    return subprocess.run(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, text=True,
                          encoding="utf-8", errors="replace",
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def adapter_inventory():
    names, nvidia, notes = [], [], []
    if os.name == "nt":
        powershell = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        try:
            result = command([str(powershell), "-NoProfile", "-NonInteractive", "-Command",
                              "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); @(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) | ConvertTo-Json -Compress"])
            if result.returncode == 0:
                value = json.loads(result.stdout.lstrip("\ufeff"))
                names = [value] if isinstance(value, str) else value if isinstance(value, list) else []
            else:
                notes.append("Windows adapter inventory unavailable; live backend tests still run.")
        except (OSError, ValueError, subprocess.TimeoutExpired):
            notes.append("Windows adapter inventory unavailable; live backend tests still run.")
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            result = command([smi, "--query-gpu=index,name", "--format=csv,noheader"], timeout=10)
            if result.returncode == 0:
                for row in csv.reader(io.StringIO(result.stdout)):
                    if len(row) == 2 and row[0].strip().isdigit():
                        index, name = row[0].strip(), row[1].strip()
                        nvidia.append({"id": index, "name": name})
                        if name not in names:
                            names.append(name)
        except (OSError, subprocess.TimeoutExpired):
            notes.append("NVIDIA inventory query failed; the default NVENC adapter will be tested.")
    return names, nvidia, notes


def probe_transcription():
    choices, diagnostics = [], []
    try:
        import torch
        if not torch.version.cuda:
            return [], ["This build has CPU-only PyTorch. Use the CUDA build for NVIDIA GPU transcription."]
        if not torch.cuda.is_available():
            return [], ["CUDA is unavailable: check the NVIDIA GPU, driver and this build's CUDA runtime."]
        for index in range(min(torch.cuda.device_count(), 100)):
            device = f"cuda:{index}"
            try:
                with torch.cuda.device(index), torch.inference_mode():
                    # Execute kernels, not just enumerate a driver-visible device.
                    sample = torch.ones((32, 32), device=device, dtype=torch.float16)
                    result = sample @ sample
                    spectrum = torch.fft.rfft(torch.ones(400, device=device))
                    torch.cuda.synchronize(index)
                    if not torch.isfinite(result).all().item() or not torch.isfinite(spectrum).all().item():
                        raise RuntimeError("GPU computation returned non-finite values")
                    props = torch.cuda.get_device_properties(index)
                    free, total = torch.cuda.mem_get_info(index)
                    choices.append({"id": device, "label": f"GPU — {props.name} (CUDA {index})",
                                    "detail": f"{free / 2**30:.1f} GiB free / {total / 2**30:.1f} GiB total VRAM; CUDA kernels passed. Model fit is not guaranteed."})
                    del sample, result, spectrum
                    torch.cuda.empty_cache()
            except Exception as error:
                diagnostics.append(f"{device}: {error}")
    except Exception as error:
        diagnostics.append(f"GPU transcription probe failed: {error}")
    return choices, diagnostics


def check_encoder(ffmpeg, encoder):
    """Try real frames through the selected driver with production encoding options."""
    if not ffmpeg or not Path(ffmpeg).is_absolute() or not Path(ffmpeg).is_file():
        return False, "Select a trusted local FFmpeg executable to test GPU encoding."
    try:
        result = command([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                          "-f", "lavfi", "-i", "color=c=black:s=640x360:r=25:d=0.12",
                          "-frames:v", "3", "-an", *encoder_args(encoder), "-f", "null", "-"], timeout=15)
        if result.returncode == 0:
            return True, "Live three-frame H.264 encoding test passed."
        return False, (result.stderr.strip() or f"FFmpeg exited with code {result.returncode}")[-2000:]
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        return False, str(error)


def probe_rendering(ffmpeg, nvidia):
    candidates = [(f"nvenc:{card['id']}", f"GPU — {card['name']} (NVENC {card['id']})") for card in nvidia]
    if not candidates:
        candidates.append(("nvenc:auto", "GPU — NVIDIA NVENC (driver-selected adapter)"))
    candidates += [("qsv", "GPU — Intel Quick Sync (driver-selected adapter)"),
                   ("amf", "GPU — AMD AMF (driver-selected adapter)")]
    choices, diagnostics = [], []
    for identifier, label in candidates:
        passed, detail = check_encoder(ffmpeg, identifier)
        if passed:
            choices.append({"id": identifier, "label": label, "detail": detail})
        else:
            diagnostics.append(f"{label}: {detail}")
    return choices, diagnostics


def scan(ffmpeg):
    adapters, nvidia, notes = adapter_inventory()
    transcription, inference_notes = probe_transcription()
    rendering, rendering_notes = probe_rendering(ffmpeg, nvidia)
    return {"adapters": adapters, "transcription": transcription, "rendering": rendering,
            "notes": notes, "transcription_notes": inference_notes, "rendering_notes": rendering_notes}


def main(request_path):
    """Background probe entry point, using the same process-tree isolation as jobs."""
    import contextlib
    import sys
    from .process_tree import isolate_worker
    isolate_worker()
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    with contextlib.redirect_stdout(sys.stderr):
        report = scan(request.get("ffmpeg", ""))
    print(json.dumps(report, ensure_ascii=True), flush=True)
    return 0
