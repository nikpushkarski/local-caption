"""The four user-adjustable subtitle settings; all other style choices stay fixed."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase, QIntValidator
from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLabel

from .subtitle_style import SubtitleStyle

AUTO_SIZE = "Auto — video-scaled (default)"
DEFAULT_WIDTH = "24 (default)"


class SubtitleControls(QGroupBox):
    changed = Signal()

    def __init__(self):
        super().__init__("Subtitles")
        self.mode = "transcribe_burn"
        layout = QGridLayout(self)
        self.font = QComboBox()
        self.font.setMinimumContentsLength(18)
        self.font.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.font.addItem("Arial (default)", "Arial")
        for family in sorted(QFontDatabase.families(), key=str.casefold):
            if family.casefold() == "arial":
                continue
            try:
                SubtitleStyle(font=family).validate()
            except ValueError:
                continue
            self.font.addItem(family, family)
        self.size = QComboBox()
        self.size.setEditable(True)
        self.size.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.size.addItem(AUTO_SIZE)
        self.size.addItems([str(n) for n in (12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72, 96, 128)])
        self.size.lineEdit().setValidator(QIntValidator(1, 512, self))
        self.size.setToolTip("Auto preserves the original sizing formula. Manual values are source-video pixels, not preview-window pixels. Oversized text is fitted to the video.")
        self.width = QComboBox()
        self.width.setEditable(True)
        self.width.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.width.addItem(DEFAULT_WIDTH)
        self.width.addItems([str(n) for n in (8, 12, 16, 20, 32, 40, 48, 64, 80, 120)])
        self.width.lineEdit().setValidator(QIntValidator(6, 120, self))
        self.width.setToolTip("Target characters per line, not an exact pixel width. A word is never cut. The fixed example is not shortened when only one line is allowed.")
        self.lines = QComboBox()
        self.lines.addItem("1 (default)", 1)
        self.lines.addItem("2", 2)
        self.lines.addItem("3", 3)
        for column, (title, widget) in enumerate((("Font (bold)", self.font), ("Font size (px)", self.size),
                                                ("Target chars / line", self.width), ("Maximum lines", self.lines))):
            layout.addWidget(QLabel(title), 0, column)
            layout.addWidget(widget, 1, column)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint, 2, 0, 1, 4)
        for widget in (self.font, self.size, self.width, self.lines):
            widget.currentTextChanged.connect(self.on_change)
        self.set_mode(self.mode)

    def value(self):
        size_text = self.size.currentText().strip()
        width_text = self.width.currentText().strip()
        try:
            size = None if size_text == AUTO_SIZE else int(size_text)
            width = 24 if width_text == DEFAULT_WIDTH else int(width_text)
        except ValueError as error:
            raise ValueError("Enter a whole-number font size (1–512) and line width (6–120), or select a default.") from error
        return SubtitleStyle(font=self.font.currentData(), font_size=size,
                             chars_per_line=width, max_lines=self.lines.currentData()).validate()

    def on_change(self):
        try:
            self.value()
        except ValueError as error:
            self.hint.setText(str(error))
            return
        self.set_mode(self.mode)
        self.changed.emit()

    def set_mode(self, mode):
        self.mode = mode
        if mode in {"burn", "transcribe_burn"}:
            self.hint.setText("Sample text is illustrative. These settings apply to the burned captions; the white/bold/bottom-centered style stays fixed.")
        elif mode == "mux":
            self.hint.setText("Example only for this action: the edited SRT is kept unchanged, and the video player chooses its font and size.")
        else:
            self.hint.setText("Line width/count apply to generated SRT cues. Font and size are a sample only here: SRT/video players choose their own styling.")
