"""Dedicated Camera Preview Window with live YOLO object detection annotations."""

import time
import collections
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QComboBox

try:
    import cv2
    from ultralytics import YOLO
    HAS_VISION = True
except Exception:
    cv2 = None
    YOLO = None
    HAS_VISION = False


class CameraWindow(QWidget):
    """Dedicated floating camera preview window with YOLO object detection."""

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.cap = None
        self.yolo_model = None
        self.is_running = False

        self.setWindowTitle("J.A.R.V.I.S. Live Camera Vision")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.resize(560, 420)
        self.setStyleSheet("""
            QWidget {
                background-color: #0A1630;
                color: #00F0FF;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #102548;
                color: #00F0FF;
                border: 1.5px solid #00F0FF;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1A3868;
                border: 1.5px solid #FFD700;
            }
            QComboBox {
                background-color: #102548;
                color: #00F0FF;
                border: 1.5px solid #00F0FF;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)

        # UI Layout
        layout = QVBoxLayout(self)

        # Live Video Feed Label
        self.video_label = QLabel("Initializing Camera Feed...", self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #050E20; border: 1.5px solid #00F0FF; border-radius: 8px;")
        layout.addWidget(self.video_label)

        # Bottom Controls
        controls = QHBoxLayout()

        self.cam_select = QComboBox(self)
        self.cam_select.addItems(["Camera 0 (Default)", "Camera 1 (USB Cam)", "Camera 2 (Secondary)"])
        self.cam_select.setCurrentIndex(camera_index)
        self.cam_select.currentIndexChanged.connect(self._change_camera)
        controls.addWidget(self.cam_select)

        self.snap_btn = QPushButton("📷 Snap Photo", self)
        self.snap_btn.clicked.connect(self.snap_photo)
        controls.addWidget(self.snap_btn)

        self.close_btn = QPushButton("✖ Close", self)
        self.close_btn.clicked.connect(self.close_camera)
        controls.addWidget(self.close_btn)

        layout.addLayout(controls)

        # Video Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    def start_camera(self):
        """Start live video capture stream."""
        if not HAS_VISION or cv2 is None:
            self.video_label.setText("Camera/OpenCV unavailable.")
            self.show()
            return

        # Load YOLO model
        if HAS_VISION and YOLO and not self.yolo_model:
            try:
                self.yolo_model = YOLO("yolov8n.pt")
            except Exception:
                pass

        self.cap = cv2.VideoCapture(self.camera_index)
        if self.cap and self.cap.isOpened():
            self.is_running = True
            self.timer.start(33) # ~30 FPS
            self.show()
        else:
            self.video_label.setText(f"Camera {self.camera_index} is unavailable.")
            self.show()

    def _change_camera(self, index: int):
        self.camera_index = index
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index)

    def _update_frame(self):
        if not self.is_running or not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        # Run YOLO detection if loaded
        if self.yolo_model:
            try:
                results = self.yolo_model(frame, verbose=False)
                if results and len(results) > 0:
                    frame = results[0].plot()
            except Exception:
                pass

        # Convert BGR OpenCV frame to RGB QImage
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Scale to label size
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def snap_photo(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                out_dir = Path.home() / ".bishu" / "snapshots"
                out_dir.mkdir(parents=True, exist_ok=True)
                file_path = out_dir / f"snapshot_{int(time.time())}.jpg"
                cv2.imwrite(str(file_path), frame)
                print(f"[CameraWindow] Saved snapshot to {file_path}")

    def close_camera(self):
        self.is_running = False
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.close()

    def closeEvent(self, event):
        self.close_camera()
        event.accept()
