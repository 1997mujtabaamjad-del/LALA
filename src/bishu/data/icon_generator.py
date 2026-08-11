"""Generates authentic Iron Man Arc Reactor App Icon Logo (PNG and ICO) for Laalaa."""

import os
import math
import struct
import zlib
from pathlib import Path

try:
    from PyQt5.QtCore import Qt, QRectF, QPointF
    from PyQt5.QtGui import QImage, QPainter, QColor, QRadialGradient, QBrush, QPen, QPolygonF
    HAS_QT_IMG = True
except Exception:
    HAS_QT_IMG = False


def generate_raw_png(width=128, height=128):
    """Generate valid PNG byte stream for Arc Reactor Icon when PIL/PyQt are unavailable."""
    def make_chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    raw_data = bytearray()
    cx, cy = width / 2.0, height / 2.0
    r = width * 0.4

    for y in range(height):
        raw_data.append(0) # Filter type 0
        for x in range(width):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            if dist <= r * 0.35: # Central Arc Triangle Core
                raw_data.extend([255, 255, 255, 255]) # White core
            elif dist <= r * 0.7: # Inner Glowing Ring
                raw_data.extend([0, 240, 255, 240]) # Cyan Glow
            elif dist <= r: # Outer Dark Ring with Coils
                angle = math.atan2(y - cy, x - cx)
                deg = (math.degrees(angle) + 360) % 360
                if int(deg) % 30 < 10:
                    raw_data.extend([255, 215, 0, 255]) # Gold Coil
                else:
                    raw_data.extend([10, 25, 55, 255]) # Dark Metallic Ring
            elif dist <= r * 1.25: # Outer Aura
                alpha = int(120 * (1.0 - (dist - r) / (r * 0.25)))
                raw_data.extend([0, 220, 255, max(0, min(120, alpha))])
            else:
                raw_data.extend([0, 0, 0, 0]) # Transparent

    png_header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_chunk = make_chunk(b"IHDR", ihdr)
    idat_chunk = make_chunk(b"IDAT", zlib.compress(raw_data))
    iend_chunk = make_chunk(b"IEND", b"")

    return png_header + ihdr_chunk + idat_chunk + iend_chunk


def generate_ico_from_png(png_bytes, width=128, height=128):
    """Package PNG byte stream into Windows .ICO container format."""
    # ICO Header: Reserved (2 bytes), Type 1=Icon (2 bytes), Image Count 1 (2 bytes)
    ico_header = struct.pack("<HHH", 0, 1, 1)
    
    # ICO Directory Entry: Width, Height, Colors (0), Reserved (0), Planes (1), BPP (32), Size, Offset
    w_byte = width if width < 256 else 0
    h_byte = height if height < 256 else 0
    data_size = len(png_bytes)
    data_offset = 6 + 16 # Header (6) + 1 Directory Entry (16)
    
    ico_entry = struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, data_size, data_offset)
    return ico_header + ico_entry + png_bytes


def generate_arc_reactor_icon(output_dir: Path = None):
    """Generate high-res Iron Man Arc Reactor App Icon Logo in PNG and ICO format."""
    if output_dir is None:
        output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    png_path = output_dir / "reactor_icon.png"
    ico_path = output_dir / "reactor_icon.ico"

    if HAS_QT_IMG:
        try:
            size = 256
            cx, cy = size / 2.0, size / 2.0
            r = size * 0.38

            img = QImage(size, size, QImage.Format_ARGB32)
            img.fill(Qt.transparent)

            painter = QPainter(img)
            painter.setRenderHint(QPainter.Antialiasing)

            aura = QRadialGradient(cx, cy, r * 1.3)
            aura.setColorAt(0.0, QColor(0, 220, 255, 120))
            aura.setColorAt(0.7, QColor(0, 180, 255, 40))
            aura.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(aura))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - r * 1.3, cy - r * 1.3, r * 2.6, r * 2.6))

            painter.setBrush(QBrush(QColor(10, 25, 55, 240)))
            painter.setPen(QPen(QColor(0, 240, 255, 255), 4))
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2.0, r * 2.0))

            coil_count = 12
            for i in range(coil_count):
                angle = (360.0 / coil_count) * i
                rad = math.radians(angle)
                x1 = cx + math.cos(rad) * (r * 0.72)
                y1 = cy + math.sin(rad) * (r * 0.72)
                x2 = cx + math.cos(rad) * (r * 0.98)
                y2 = cy + math.sin(rad) * (r * 0.98)
                painter.setPen(QPen(QColor(0, 240, 255, 255), 5))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            core_r = r * 0.68
            core_grad = QRadialGradient(cx, cy, core_r)
            core_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
            core_grad.setColorAt(0.4, QColor(0, 220, 255, 240))
            core_grad.setColorAt(1.0, QColor(0, 30, 90, 250))
            painter.setBrush(QBrush(core_grad))
            painter.setPen(QPen(QColor(255, 215, 0, 240), 3))
            painter.drawEllipse(QRectF(cx - core_r, cy - core_r, core_r * 2.0, core_r * 2.0))

            tri_r = r * 0.38
            poly = QPolygonF([
                QPointF(cx, cy - tri_r),
                QPointF(cx + tri_r * 0.866, cy + tri_r * 0.5),
                QPointF(cx - tri_r * 0.866, cy + tri_r * 0.5)
            ])
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.setPen(QPen(QColor(0, 240, 255, 255), 2))
            painter.drawPolygon(poly)

            painter.end()
            img.save(str(png_path), "PNG")
            img.save(str(ico_path), "ICO")
            print(f"[IconGenerator] Arc Reactor App Icon generated via PyQt5: {png_path.name}, {ico_path.name}")
            return png_path, ico_path
        except Exception:
            pass

    # Pure Python byte stream fallback
    png_bytes = generate_raw_png()
    with open(png_path, "wb") as f:
        f.write(png_bytes)

    ico_bytes = generate_ico_from_png(png_bytes)
    with open(ico_path, "wb") as f:
        f.write(ico_bytes)

    print(f"[IconGenerator] Arc Reactor App Icon generated via byte stream: {png_path.name}, {ico_path.name}")
    return png_path, ico_path


if __name__ == "__main__":
    generate_arc_reactor_icon()
