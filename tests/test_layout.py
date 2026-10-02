"""Native-font layout regression; the Windows offscreen plugin uses box metrics."""

import os
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name == "nt", "Native Windows layout check")
class NativeLayoutTests(unittest.TestCase):
    def test_compact_columns_fit_with_long_gpu_choices(self):
        code = r'''
import os
os.environ["QT_QPA_PLATFORM"] = "windows"
from PySide6.QtWidgets import QApplication
from local_caption.app import Window
app = QApplication([])
window = Window(auto_scan_hardware=False)
window.show()
report = {
    "adapters": ["NVIDIA GeForce RTX 4070 Laptop GPU", "Intel(R) UHD Graphics"],
    "transcription": [{"id": "cuda:0", "label": "GPU — NVIDIA GeForce RTX 4070 Laptop GPU (CUDA 0)"}],
    "rendering": [{"id": "nvenc:0", "label": "GPU — NVIDIA GeForce RTX 4070 Laptop GPU (NVENC 0)"}],
}
try:
    for populated in (False, True):
        if populated:
            window.hardware.apply_report(report)
            window.hardware.transcription.setCurrentIndex(1)
            window.hardware.rendering.setCurrentIndex(1)
        for width in (1120, 1000):
            window.resize(width, 940)
            app.processEvents()
            app.processEvents()
            assert window.centralWidget().horizontalScrollBar().maximum() == 0, (width, populated)
            for left, right in ((window.subtitle_controls, window.job_fields), (window.tools, window.hardware)):
                a, b = left.geometry(), right.geometry()
                assert a.right() < b.left() and a.top() == b.top(), (a, b)
                assert abs(a.width() - b.width()) <= 2, (a, b)
finally:
    window.close()
'''
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
