import unittest
from types import SimpleNamespace
from unittest.mock import patch

from local_caption.transcription import transcribe


class TranscriptionTests(unittest.TestCase):
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
