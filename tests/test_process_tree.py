import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class ProcessTreeTests(unittest.TestCase):
    def test_worker_death_stops_child(self):
        with tempfile.TemporaryDirectory() as d:
            heartbeat = Path(d) / "heartbeat"
            child_code = "import time; from pathlib import Path; p=Path(" + repr(str(heartbeat)) + ");\nwhile True: p.write_text(str(time.time())); time.sleep(.05)"
            worker_code = (
                "from local_caption.process_tree import isolate_worker; isolate_worker(); "
                "import subprocess,sys,time; "
                f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
                "print(child.pid,flush=True); time.sleep(60)"
            )
            worker = subprocess.Popen([sys.executable, "-u", "-c", worker_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 10
                while not heartbeat.exists() and time.monotonic() < deadline and worker.poll() is None:
                    time.sleep(.05)
                self.assertTrue(heartbeat.exists(), "Child did not start")
                if os.name == "nt":
                    worker.kill()
                else:
                    os.killpg(worker.pid, signal.SIGKILL)
                worker.wait(timeout=5)
                time.sleep(.3)
                first = heartbeat.read_text()
                time.sleep(.3)
                self.assertEqual(heartbeat.read_text(), first, "Child survived cancellation")
            finally:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate(timeout=5)
