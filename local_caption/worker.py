"""JSON-lines worker protocol. Stdout is reserved for events."""

import contextlib
import json
import os
from pathlib import Path
import sys
import traceback


def main(job_path: str) -> int:
    from .process_tree import isolate_worker
    protocol = sys.stdout

    def emit(event, value):
        protocol.write(json.dumps({"event": event, "value": value}, ensure_ascii=True) + "\n")
        protocol.flush()

    try:
        isolate_worker()
        # No windows are created, but use native font discovery on desktop OSes.
        # Qt's Windows offscreen plugin can return box-glyph metrics instead.
        os.environ["QT_QPA_PLATFORM"] = "windows" if os.name == "nt" else "cocoa" if sys.platform == "darwin" else "offscreen"
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance() or QGuiApplication([])
        from .engine import Job, process
        path = Path(job_path).resolve()
        job = Job(**json.loads(path.read_text(encoding="utf-8")))
        with contextlib.redirect_stdout(sys.stderr):
            process(job, path.parent, emit)
        emit("done", "Completed")
        return 0
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        emit("error", str(error))
        return 1
