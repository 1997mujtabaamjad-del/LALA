"""Live 2D Visual Character Avatar with Real-Time Expressions, 8 Gesture Motions, and Vocal Lip-Sync."""

import math
import time

try:
    from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
    from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient, QFont, QPainterPath
    from PyQt5.QtWidgets import QWidget
    HAS_QT5 = True
except Exception:
    HAS_QT5 = False
    QWidget = object
    Qt = object
    QTimer = object


class AvatarWindow(QWidget if HAS_QT5 else object):
    """Interactive Live 2D Visual Character Avatar with 8 Gesture Motions & Lip-Sync."""

    EXPRESSIONS = ["NEUTRAL", "TALKING", "THINKING", "HAPPY", "ALERT", "SURPRISED"]
    GESTURES = ["NOD", "WAVE", "THINK", "BOW", "TALK_GENTLE", "TALK_EXCITED", "SHRUG", "ALERT_FLASH"]

    def __init__(self, parent=None):
        if HAS_QT5:
            super().__init__(parent)
            self.setWindowTitle("Laalaa Live 2D Avatar")
            self.resize(400, 480)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.expression = "NEUTRAL"
        self.gesture = "NOD"
        self.vocal_sync_level = 0.0
        self.eye_blink = False
        self.gesture_time = 0.0
        self.start_time = time.time()

        if HAS_QT5:
            # Timers
            self.anim_timer = QTimer(self)
            self.anim_timer.timeout.connect(self._update_animation)
            self.anim_timer.start(33) # 30 FPS smooth rendering

            self.blink_timer = QTimer(self)
            self.blink_timer.timeout.connect(self._trigger_blink)
            self.blink_timer.start(3500)

    def set_expression(self, expr: str):
        """Set avatar facial expression."""
        if expr.upper() in self.EXPRESSIONS:
            self.expression = expr.upper()
            if HAS_QT5:
                self.update()

    def set_gesture(self, gesture: str):
        """Trigger 1 of 8 unique gesture motions."""
        if gesture.upper() in self.GESTURES:
            self.gesture = gesture.upper()
            self.gesture_time = time.time()
            if HAS_QT5:
                self.update()

    def set_vocal_sync(self, audio_level: float):
        """Set real-time speech lip-sync audio volume height."""
        self.vocal_sync_level = min(1.0, max(0.0, audio_level * 2.5))
        if self.vocal_sync_level > 0.05:
            self.expression = "TALKING"
        if HAS_QT5:
            self.update()

    def _trigger_blink(self):
        self.eye_blink = True
        if HAS_QT5:
            QTimer.singleShot(180, self._stop_blink)

    def _stop_blink(self):
        self.eye_blink = False
        if HAS_QT5:
            self.update()

    def _update_animation(self):
        if HAS_QT5:
            self.update()

    def mousePressEvent(self, event):
        """Allow mouse dragging around screen."""
        if HAS_QT5 and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if HAS_QT5 and event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def paintEvent(self, event):
        if not HAS_QT5:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0 - 20
        t = time.time() - self.start_time

        # Gesture Motion Modifiers
        head_offset_x, head_offset_y = 0.0, 0.0
        arm_left_angle, arm_right_angle = 0.0, 0.0

        if self.gesture == "NOD":
            head_offset_y = math.sin(t * 8.0) * 8.0
        elif self.gesture == "WAVE":
            arm_right_angle = math.sin(t * 10.0) * 0.4 - 0.8
        elif self.gesture == "THINK":
            head_offset_x = 10.0
            arm_right_angle = -1.2
        elif self.gesture == "BOW":
            head_offset_y = 18.0
        elif self.gesture == "TALK_GENTLE":
            head_offset_y = math.sin(t * 4.0) * 4.0
        elif self.gesture == "TALK_EXCITED":
            head_offset_y = math.sin(t * 12.0) * 12.0
            arm_left_angle = math.sin(t * 10.0) * 0.3
            arm_right_angle = -math.sin(t * 10.0) * 0.3
        elif self.gesture == "SHRUG":
            arm_left_angle = 0.5
            arm_right_angle = -0.5
        elif self.gesture == "ALERT_FLASH":
            head_offset_y = math.sin(t * 16.0) * 6.0

        # 1. Glowing Cyber Aura Background
        aura = QRadialGradient(cx, cy, 160)
        c_glow = QColor(0, 220, 255, 90) if self.expression != "ALERT" else QColor(255, 0, 80, 110)
        aura.setColorAt(0.0, c_glow)
        aura.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(aura))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - 160, cy - 160, 320, 320))

        # 2. Body / Torso Silhouette
        painter.save()
        painter.translate(cx, cy + 120)
        body_path = QPainterPath()
        body_path.moveTo(-60, 100)
        body_path.lineTo(-40, 0)
        body_path.lineTo(40, 0)
        body_path.lineTo(60, 100)
        body_path.closeSubpath()
        painter.setBrush(QBrush(QColor(18, 38, 78, 240)))
        painter.setPen(QPen(QColor(0, 240, 255, 200), 2))
        painter.drawPath(body_path)
        painter.restore()

        # 3. Arms / Gestures
        painter.save()
        painter.translate(cx - 40, cy + 120)
        painter.rotate(arm_left_angle * 57.3)
        painter.setPen(QPen(QColor(0, 240, 255, 220), 8, Qt.RoundCap))
        painter.drawLine(0, 0, -35, 60)
        painter.restore()

        painter.save()
        painter.translate(cx + 40, cy + 120)
        painter.rotate(arm_right_angle * 57.3)
        painter.setPen(QPen(QColor(0, 240, 255, 220), 8, Qt.RoundCap))
        painter.drawLine(0, 0, 35, 60)
        painter.restore()

        # 4. Avatar Head Base
        hx, hy = cx + head_offset_x, cy + head_offset_y - 20
        painter.save()
        painter.setBrush(QBrush(QColor(12, 28, 62, 245)))
        painter.setPen(QPen(QColor(0, 240, 255, 240), 2.5))
        painter.drawEllipse(QRectF(hx - 70, hy - 80, 140, 150))

        # Hair / Crown Accent
        hair_path = QPainterPath()
        hair_path.moveTo(hx - 75, hy - 30)
        hair_path.cubicTo(hx - 40, hy - 110, hx + 40, hy - 110, hx + 75, hy - 30)
        painter.setBrush(QBrush(QColor(0, 180, 255, 120)))
        painter.drawPath(hair_path)

        # 5. Eyes
        eye_y = hy - 15
        eye_h = 2 if self.eye_blink else (16 if self.expression in ["HAPPY", "SURPRISED"] else 12)

        # Left Eye
        painter.setBrush(QBrush(QColor(0, 255, 255, 255)))
        painter.drawEllipse(QRectF(hx - 40, eye_y - eye_h / 2.0, 22, eye_h))

        # Right Eye
        painter.drawEllipse(QRectF(hx + 18, eye_y - eye_h / 2.0, 22, eye_h))

        # Pupils
        if not self.eye_blink:
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(hx - 32, eye_y - 3, 6, 6))
            painter.drawEllipse(QRectF(hx + 26, eye_y - 3, 6, 6))

        # 6. Musical Vocal Sync Mouth Lip-Sync Movement
        mouth_y = hy + 35
        lip_open = self.vocal_sync_level * 22.0

        if self.expression == "TALKING" or lip_open > 2.0:
            mouth_h = max(4.0, lip_open)
            painter.setBrush(QBrush(QColor(255, 0, 100, 220)))
            painter.drawEllipse(QRectF(hx - 16, mouth_y - mouth_h / 2.0, 32, mouth_h))
        elif self.expression == "HAPPY":
            m_path = QPainterPath()
            m_path.moveTo(hx - 18, mouth_y)
            m_path.quadTo(hx, mouth_y + 14, hx + 18, mouth_y)
            painter.setPen(QPen(QColor(0, 255, 200, 240), 3))
            painter.drawPath(m_path)
        else:
            painter.setPen(QPen(QColor(0, 240, 255, 220), 2.5))
            painter.drawLine(QPointF(hx - 14, mouth_y), QPointF(hx + 14, mouth_y))

        # 7. Expression Badge & Name Label
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.setPen(QPen(QColor(0, 240, 255, 220)))
        painter.drawText(QRectF(hx - 80, hy + 85, 160, 20), Qt.AlignCenter, f"LAALAA 2D AVATAR ({self.expression})")
        painter.restore()
