import subprocess
import sys
import unittest


class FontTests(unittest.TestCase):
    def test_worker_uses_real_font_metrics(self):
        code = (
            "from local_caption.worker import font_application; app=font_application(); "
            "from local_caption.captions import measure_caption; "
            "assert measure_caption('WWWW',40) > measure_caption('iiii',40)*2, 'Box-glyph or monospace metrics'; "
            "assert measure_caption('Привет',40)>0"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
