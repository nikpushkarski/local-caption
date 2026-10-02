"""Live illustrative output: input frames plus the same caption layout as rendering.

This does not generate media or load a model. Qt paints the sample, while the real
burn uses libass, so font rasterization can differ slightly.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .captions import caption_layout, fit_caption_font
from .subtitle_style import SAMPLE_TEXT, SubtitleStyle, wrap_caption


class SamplePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(220, 150)
        self.setAcceptDrops(True)
        self.image = QImage()
        self.style = SubtitleStyle()
        self._layout_key = None
        self._geometry = None

    def set_style(self, style):
        self.style = style.validate()
        self._layout_key = None
        self.update()

    def set_frame(self, frame):
        if frame.isValid():
            self.image = frame.toImage()
            self.update()

    def clear(self):
        self.image = QImage()
        self._layout_key = None
        self.update()

    def caption_geometry(self, width, height):
        key = (width, height, self.style)
        if key != self._layout_key:
            layout = caption_layout(width, height, self.style)
            lines = wrap_caption(SAMPLE_TEXT, self.style)
            size = fit_caption_font("\n".join(lines), layout)
            self._geometry = (layout, lines, size)
            self._layout_key = key
        return self._geometry

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("black"))
        if self.image.isNull():
            painter.setPen(QColor("#cccccc"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sample captions appear when the video is ready")
            return
        width, height = self.image.width(), self.image.height()
        scale = min(self.width() / width, self.height() / height)
        left, top = (self.width() - width * scale) / 2, (self.height() - height * scale) / 2
        painter.translate(left, top)
        painter.scale(scale, scale)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF(0, 0, width, height), self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        layout, lines, size = self.caption_geometry(width, height)
        font = QFont(self.style.font)
        font.setPixelSize(size)
        font.setBold(True)
        metrics = QFontMetricsF(font)
        line_height = metrics.height()
        baseline = height - layout["bottom_margin"] - metrics.descent() - (len(lines) - 1) * line_height
        for line in lines:
            path = QPainterPath()
            x = (width - metrics.horizontalAdvance(line)) / 2
            path.addText(QPointF(x, baseline), font, line)
            painter.save()
            painter.translate(1, 1)
            painter.setPen(QPen(QColor("black"), layout["outline"] * 2, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(QColor("black"))
            painter.drawPath(path)
            painter.restore()
            painter.setPen(QPen(QColor("black"), layout["outline"] * 2, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(QColor("black"))
            painter.drawPath(path)
            # Fill after stroking: QPainter's normal stroke overlaps the glyph
            # interior, whereas an ASS outline sits behind its white foreground.
            painter.fillPath(path, QColor("white"))
            baseline += line_height

    def dragEnterEvent(self, event):
        event.acceptProposedAction()  # Swallow output-pane drops; never replace the input.

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
