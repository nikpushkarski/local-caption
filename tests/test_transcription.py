import unittest
from types import SimpleNamespace
from unittest.mock import patch

from local_caption.transcription import transcribe


class TranscriptionTests(unittest.TestCase):
    def test_cuda_uses_fp16_and_reports_device(self):
        module = SimpleNamespace(tqdm=object())
        events = []
        options = {}

        class Model:
            def transcribe(self, audio, **kwargs):
                options.update(kwargs)
                with module.tqdm.tqdm(total=100) as progress:
                    progress.update(100)
                return {"segments": []}

        with patch("local_caption.transcription.importlib.import_module", return_value=module):
            transcribe(Model(), [], "en", lambda *event: events.append(event), device="cuda:1")
        self.assertTrue(options["fp16"])
        self.assertTrue(any("cuda:1" in str(value) for kind, value in events if kind == "status"))

    def test_progress_and_restore_on_failure(self):
        original = object()
        module = SimpleNamespace(tqdm=original)
        events = []

        class Model:
            def transcribe(self, audio, **kwargs):
                assert kwargs == dict(beam_size=10, language=None, fp16=False, word_timestamps=True, verbose=None)
                with module.tqdm.tqdm(total=100) as progress:
                    progress.update(50)
                    progress.update(50)
                raise RuntimeError("test failure")

        with patch("local_caption.transcription.importlib.import_module", return_value=module):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                transcribe(Model(), [], "auto", lambda *event: events.append(event))
        self.assertIs(module.tqdm, original)
        self.assertEqual([value for event, value in events if event == "progress"], [50, 99])
