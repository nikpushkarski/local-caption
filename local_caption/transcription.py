"""Report confirmed Whisper audio checkpoints, without pretending to know an ETA."""

import importlib
from types import SimpleNamespace


def transcribe(model, audio, language, emit, device="cpu"):
    module = importlib.import_module("whisper.transcribe")
    original = module.tqdm

    class Progress:
        def __init__(self, total, **kwargs):
            self.total = total
            self.done = 0
            emit("status", f"Transcribing locally ({device}, beam 10); first checkpoint may take several minutes…")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def update(self, amount):
            self.done += amount
            emit("progress", min(99, int(100 * self.done / self.total)) if self.total else 0)

    try:
        # Worker process is single-job: no global changes leak into other jobs/UI.
        module.tqdm = SimpleNamespace(tqdm=Progress)
        return model.transcribe(audio, beam_size=10, language=None if language == "auto" else language,
                                fp16=device.startswith("cuda:"), word_timestamps=True, verbose=None)
    finally:
        module.tqdm = original
