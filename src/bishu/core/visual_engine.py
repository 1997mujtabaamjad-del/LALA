"""Visual engine providing clean 60 FPS J.A.R.V.I.S. Arc Reactor HUD with safe PyQt5 dragging."""

import sys
import math
import time

try:
    from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
    from PyQt5.QtGui import (
        QPainter, QColor, QRadialGradient, QLinearGradient,
        QPen, QBrush, QPolygonF, QFont, QPainterPath
    )
    from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton
    HAS_QT_GUI = True
except ImportError:
    HAS_QT_GUI = False
    QWidget = object
    QLineEdit = object
    QPushButton = object
    QPainter = object
    QColor = object
    QRadialGradient = object
    QLinearGradient = object
    QPen = object
    QBrush = object
    QPainterPath = object
    QPolygonF = object
    QFont = object
    pyqtSignal = lambda *args: None


class VisualEngine(QWidget if HAS_QT_GUI else object):
    """J.A.R.V.I.S. Arc Reactor HUD Interface with Centered Glass Command Input Bar & Camera Button."""

    command_entered = pyqtSignal(str) if HAS_QT_GUI else None
    camera_requested = pyqtSignal() if HAS_QT_GUI else None

    def __init__(self, parent=None):
        if HAS_QT_GUI:
            super().__init__(parent)
        self.rotation = 0.0
        self.is_thinking = False
        self.is_alert = False
        self.is_task_flash = False

        self._start_time = time.time()
        self._audio_level = 0.0
        self._cpu_val = 25.0
        self._ram_val = 50.0

        if HAS_QT_GUI:
            self.input_box = QLineEdit(self)
            self.input_box.setPlaceholderText("Type or ask Laalaa (e.g. 'open youtube', 'open camera', 'how are you')...")
            self.input_box.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(8, 20, 45, 240);
                    color: #00F0FF;
                    border: 2px solid #00F0FF;
                    border-radius: 10px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 14px;
                }
                QLineEdit:focus {
                    border: 2px solid #FFD700;
                    background-color: rgba(15, 38, 75, 255);
                }
            """)
            self.input_box.returnPressed.connect(self._on_text_submitted)

            self.cam_button = QPushButton("📷 CAM", self)
            self.cam_button.setToolTip("Open Live Camera Vision Window")
            self.cam_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(10, 25, 55, 240);
                    color: #00F0FF;
                    border: 2px solid #00F0FF;
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(20, 50, 95, 255);
                    color: #FFD700;
                    border: 2px solid #FFD700;
                }
            """)
            self.cam_button.clicked.connect(self.camera_requested.emit)

    def _on_text_submitted(self):
        text = self.input_box.text().strip()
        if text:
            self.input_box.clear()
            if self.command_entered:
                self.command_entered.emit(text)

    def mousePressEvent(self, event):
        """Allow clicking anywhere on the HUD to drag the window smoothly around the screen."""
        if HAS_QT_GUI and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """Move the Arc Reactor HUD window following mouse drag."""
        if HAS_QT_GUI and event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def set_cpu_ram(self, cpu: float, ram: float):
        """Set CPU and RAM gauge values from background monitor thread."""
        self._cpu_val = cpu
        self._ram_val = ram
        if HAS_QT_GUI:
            self.update()

    def set_thinking(self, thinking: bool):
        self.is_thinking = thinking
        self.update()

    def set_alert(self, alert: bool):
        self.is_alert = alert
        self.update()

    def set_task_flash(self, flashing: bool):
        self.is_task_flash = flashing
        self.update()

    def set_audio_level(self, level: float):
        self._audio_level = level
        self.update()

    def setWindowFlags(self, flags):
        if HAS_QT_GUI:
            super().setWindowFlags(flags)

    def setAttribute(self, attr, value=True):
        if HAS_QT_GUI:
            super().setAttribute(attr, value)

    def resize(self, *args):
        if HAS_QT_GUI:
            super().resize(*args)
            w = self.width()
            h = self.height()
            cx = w / 2.0
            cy = h / 2.0 - 60
            r = min(w, h) * 0.25
            if hasattr(self, "input_box") and self.input_box:
                box_w = min(480, w - 220)
                box_x = int(cx - box_w / 2.0 - 45)
                box_y = int(cy + r * 1.82)
                self.input_box.setGeometry(box_x, box_y, box_w, 42)
            if hasattr(self, "cam_button") and self.cam_button:
                cam_x = int(cx + box_w / 2.0 - 35)
                cam_y = int(cy + r * 1.82)
                self.cam_button.setGeometry(cam_x, cam_y, 85, 42)

    def move(self, *args):
        if HAS_QT_GUI:
            super().move(*args)

    def show(self):
        if HAS_QT_GUI:
            super().show()
        else:
            print("[VisualEngine] Realistic Arc Reactor HUD shown.")

    def hide(self):
        if HAS_QT_GUI:
            super().hide()
        else:
            print("[VisualEngine] Realistic Arc Reactor HUD hidden.")

    def raise_(self):
        if HAS_QT_GUI:
            super().raise_()

    def activateWindow(self):
        if HAS_QT_GUI:
            super().activateWindow()

    def width(self):
        if HAS_QT_GUI:
            return super().width()
        return 1100

    def height(self):
        if HAS_QT_GUI:
            return super().height()
        return 1100

    def update(self):
        if HAS_QT_GUI:
            super().update()

    def paintEvent(self, event):
        if not HAS_QT_GUI:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0 - 60
        t = time.time() - self._start_time

        r = min(w, h) * 0.25

        if self.is_alert:
            c_main = QColor(255, 0, 68, 245)
            c_glow = QColor(255, 0, 68, 110)
            c_hud  = QColor(255, 120, 100, 230)
        elif self.is_thinking:
            c_main = QColor(170, 0, 255, 245)
            c_glow = QColor(190, 80, 255, 110)
            c_hud  = QColor(220, 140, 255, 230)
        elif self.is_task_flash:
            c_main = QColor(0, 255, 150, 245)
            c_glow = QColor(50, 255, 180, 110)
            c_hud  = QColor(150, 255, 210, 230)
        else:
            c_main = QColor(0, 240, 255, 245)
            c_glow = QColor(0, 210, 255, 110)
            c_hud  = QColor(120, 240, 255, 230)

        c_gold = QColor(255, 215, 0, 230)

        # 1. Outer Radial Power Aura Glow
        aura_r = r * 1.70
        aura = QRadialGradient(cx, cy, aura_r)
        aura.setColorAt(0.0, c_glow)
        aura.setColorAt(0.65, QColor(c_glow.red(), c_glow.green(), c_glow.blue(), 25))
        aura.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(aura))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - aura_r, cy - aura_r, aura_r * 2.0, aura_r * 2.0))

        # 2. Outer Precision Degree Scale & Tick Marks
        painter.save()
        painter.translate(cx, cy)
        for i in range(36):
            deg = i * 10
            rad = math.radians(deg)
            is_major = (i % 3 == 0)
            len_tick = 10 if is_major else 5
            r_out = r * 1.50
            x1 = float(math.cos(rad) * r_out)
            y1 = float(math.sin(rad) * r_out)
            x2 = float(math.cos(rad) * (r_out + len_tick))
            y2 = float(math.sin(rad) * (r_out + len_tick))
            
            painter.setPen(QPen(c_hud if is_major else QColor(0, 240, 255, 90), 1.4 if is_major else 1.0))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            if is_major:
                tx = float(math.cos(rad) * (r_out + 20))
                ty = float(math.sin(rad) * (r_out + 20))
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.setPen(QPen(c_hud))
                painter.drawText(QRectF(tx - 15, ty - 8, 30, 16), Qt.AlignCenter, f"{deg}°")
        painter.restore()

        # 3. Rotating Outer Radar Line Sweep
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(t * 40.0)
        radar_path = QPainterPath()
        radar_path.moveTo(0, 0)
        radar_path.arcTo(QRectF(-r * 1.50, -r * 1.50, r * 3.0, r * 3.0), 0, 45)
        radar_path.closeSubpath()
        radar_grad = QRadialGradient(0, 0, r * 1.50)
        radar_grad.setColorAt(0.0, QColor(c_main.red(), c_main.green(), c_main.blue(), 0))
        radar_grad.setColorAt(1.0, QColor(c_main.red(), c_main.green(), c_main.blue(), 70))
        painter.setBrush(QBrush(radar_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPath(radar_path)
        painter.restore()

        # 4. Real-Time Circular Gauges (CPU Left Arc, RAM Right Arc)
        painter.save()
        painter.translate(cx, cy)
        
        cpu_span = float((self._cpu_val / 100.0) * 120)
        pen_bg = QPen(QColor(20, 50, 90, 180), 5)
        painter.setPen(pen_bg)
        painter.drawArc(QRectF(-r * 1.35, -r * 1.35, r * 2.70, r * 2.70), 120 * 16, 120 * 16)
        pen_cpu = QPen(c_gold if self._cpu_val > 80 else c_main, 5)
        painter.setPen(pen_cpu)
        painter.drawArc(QRectF(-r * 1.35, -r * 1.35, r * 2.70, r * 2.70), int(120 * 16), int(cpu_span * 16))

        ram_span = float((self._ram_val / 100.0) * 120)
        painter.setPen(pen_bg)
        painter.drawArc(QRectF(-r * 1.35, -r * 1.35, r * 2.70, r * 2.70), -60 * 16, 120 * 16)
        pen_ram = QPen(QColor(255, 0, 68) if self._ram_val >= 90 else c_main, 5)
        painter.setPen(pen_ram)
        painter.drawArc(QRectF(-r * 1.35, -r * 1.35, r * 2.70, r * 2.70), int(-60 * 16), int(ram_span * 16))
        painter.restore()

        # 5. Inner Rotating Segmented Arc Ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-self.rotation * 1.8)
        pen_outer = QPen(c_hud, 2.5, Qt.SolidLine)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.NoBrush)

        arc_r = r * 1.20
        for deg in [0, 90, 180, 270]:
            painter.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2.0, arc_r * 2.0), int((deg + 12) * 16), int(66 * 16))

        for deg in [0, 90, 180, 270]:
            rad = math.radians(deg)
            px = float(math.cos(rad) * (arc_r + 8))
            py = float(math.sin(rad) * (arc_r + 8))
            poly = QPolygonF([
                QPointF(px, py),
                QPointF(float(px - math.sin(rad) * 6 - math.cos(rad) * 8), float(py + math.cos(rad) * 6 - math.sin(rad) * 8)),
                QPointF(float(px + math.sin(rad) * 6 - math.cos(rad) * 8), float(py - math.cos(rad) * 6 - math.sin(rad) * 8)),
            ])
            painter.setBrush(QBrush(c_main))
            painter.drawPolygon(poly)
        painter.restore()

        # 6. 12 Electromagnetic Reactor Coils
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.rotation * 2.2)
        coil_count = 12
        for i in range(coil_count):
            angle = (360.0 / coil_count) * i
            rad = math.radians(angle)
            x1 = float(math.cos(rad) * (r * 0.78))
            y1 = float(math.sin(rad) * (r * 0.78))
            x2 = float(math.cos(rad) * (r * 1.00))
            y2 = float(math.sin(rad) * (r * 1.00))
            coil_pen = QPen(c_main, 5.0, Qt.SolidLine)
            painter.setPen(coil_pen)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.restore()

        # 7. Center Arc Power Core Sphere
        core_grad = QRadialGradient(cx, cy, r * 0.75)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        core_grad.setColorAt(0.35, c_main)
        core_grad.setColorAt(0.82, QColor(0, 30, 90, 235))
        core_grad.setColorAt(1.0, QColor(0, 10, 30, 250))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(c_hud, 2.0))
        painter.drawEllipse(QRectF(cx - r * 0.75, cy - r * 0.75, r * 1.50, r * 1.50))

        # 8. Glowing Central Arc Triangle Emblem
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.rotation * 0.6)
        tri_size = r * 0.40
        tri_poly = QPolygonF([
            QPointF(0, -tri_size),
            QPointF(float(tri_size * 0.866), float(tri_size * 0.5)),
            QPointF(float(-tri_size * 0.866), float(tri_size * 0.5)),
        ])
        tri_pen = QPen(QColor(255, 255, 255, 245), 2.5)
        painter.setPen(tri_pen)
        painter.setBrush(QBrush(QColor(c_main.red(), c_main.green(), c_main.blue(), 110)))
        painter.drawPolygon(tri_poly)
        painter.restore()

        # 9. Floating Glass Panels
        float_y = math.sin(t * 2.0) * 5.0
        panel_w, panel_h = 160, 54

        p_border = QColor(255, 0, 68, 220) if self.is_alert else QColor(0, 240, 255, 150)

        p1_x, p1_y = cx - r * 1.80 - panel_w, cy - r * 1.20 + float_y
        self._draw_glass_panel(painter, p1_x, p1_y, panel_w, panel_h, p_border, "CPU.PROCESSOR", f"USAGE: {self._cpu_val:.1f}%")

        p2_x, p2_y = cx + r * 1.80, cy - r * 1.20 - float_y
        self._draw_glass_panel(painter, p2_x, p2_y, panel_w, panel_h, p_border, "RAM.MEMORY", f"ALLOC: {self._ram_val:.1f}%")

        p3_x, p3_y = cx - r * 1.80 - panel_w, cy + r * 0.90 - float_y
        self._draw_glass_panel(painter, p3_x, p3_y, panel_w, panel_h, p_border, "VOICE.STT", "ACTIVE")

        p4_x, p4_y = cx + r * 1.80, cy + r * 0.90 + float_y
        self._draw_glass_panel(painter, p4_x, p4_y, panel_w, panel_h, p_border, "JARVIS.CORE", "ONLINE")

        # 10. Real-Time Audio Equalizer
        spec_w = 260
        spec_x = cx - spec_w / 2.0
        spec_y = cy + r * 1.58
        bar_count = 18
        bar_w = spec_w / bar_count

        painter.save()
        for i in range(bar_count):
            bar_phase = t * 10.0 + i * 0.4
            bar_h = 4 + math.sin(bar_phase) * 14 + self._audio_level * 32
            bx = spec_x + i * bar_w
            by = spec_y - bar_h / 2.0
            b_col = QColor(0, 240, 255, 220) if not self.is_alert else QColor(255, 0, 68, 220)
            painter.setBrush(QBrush(b_col))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(bx + 1, by, bar_w - 2, bar_h))
        painter.restore()

    def _draw_glass_panel(self, painter, x, y, w, h, border_color, title, subtitle):
        painter.save()
        painter.setBrush(QBrush(QColor(10, 22, 48, 185)))
        painter.setPen(QPen(border_color, 1.4))
        painter.drawRoundedRect(QRectF(x, y, w, h), 5, 5)

        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QPen(border_color))
        painter.drawText(QRectF(x + 10, y + 8, w - 20, 18), Qt.AlignLeft, title)

        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.setPen(QPen(QColor(220, 245, 255, 230)))
        painter.drawText(QRectF(x + 10, y + 28, w - 20, 20), Qt.AlignLeft, subtitle)
        painter.restore()
