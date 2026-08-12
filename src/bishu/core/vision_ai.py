"""YOLO Computer Vision AI Engine supporting separate camera selection and live video preview."""

import os
import time
import collections
import threading
from pathlib import Path
from bishu.config import CAMERA_INDEX

try:
    import cv2
    from PIL import ImageGrab
    from ultralytics import YOLO
    HAS_YOLO = True
except Exception as e:
    cv2 = None
    YOLO = None
    HAS_YOLO = False
    print(f"[VisionAIEngine] YOLO Vision AI info: {e}")


class VisionAIEngine:
    """YOLOv8 Computer Vision Object Detection Engine with camera selection."""

    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = None
        self.active_camera = CAMERA_INDEX
        self.vision_dir = Path.home() / ".bishu" / "vision"
        self.vision_dir.mkdir(parents=True, exist_ok=True)

        if HAS_YOLO and YOLO:
            try:
                print(f"[VisionAIEngine] Loading YOLO model '{model_name}'...")
                self.model = YOLO(model_name)
                print("[VisionAIEngine] YOLO Object Detection Model loaded successfully!")
            except Exception as err:
                print(f"[VisionAIEngine] YOLO model load info: {err}")

    def set_camera_index(self, index: int) -> str:
        """Switch active camera index (0, 1, 2...)."""
        self.active_camera = index
        print(f"[VisionAIEngine] Active camera index set to: {index}")
        return f"Switched active camera to Index {index}."

    def open_live_camera_preview(self, duration: int = 10) -> tuple:
        """Open a live window showing real-time YOLO object detection bounding boxes."""
        if not HAS_YOLO or not self.model:
            return False, "YOLO Computer Vision model is not initialized."

        def _preview_worker():
            try:
                cap = cv2.VideoCapture(self.active_camera)
                if not cap or not cap.isOpened():
                    print(f"[VisionAIEngine] Camera {self.active_camera} unavailable.")
                    return

                start_t = time.time()
                while time.time() - start_t < duration:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break

                    results = self.model(frame, verbose=False)
                    if results and len(results) > 0:
                        annotated = results[0].plot()
                        cv2.imshow(f"J.A.R.V.I.S. YOLO Vision - Camera {self.active_camera}", annotated)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                cap.release()
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"[VisionAIEngine] Live camera preview info: {e}")

        threading.Thread(target=_preview_worker, daemon=True).start()
        return True, f"Opened live camera preview on Camera {self.active_camera}."

    def scan_and_detect(self) -> tuple:
        """Capture frame from selected camera and run YOLO object detection."""
        if not HAS_YOLO or not self.model:
            return False, "YOLO Computer Vision model is not initialized."

        image_path = None
        try:
            # 1. Capture from selected camera index
            cap = cv2.VideoCapture(self.active_camera)
            if cap and cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    image_path = self.vision_dir / "webcam_frame.jpg"
                    cv2.imwrite(str(image_path), frame)

            # 2. Fallback to desktop screenshot if camera unavailable
            if not image_path or not image_path.exists():
                screen_img = ImageGrab.grab()
                image_path = self.vision_dir / "screen_frame.jpg"
                screen_img.save(str(image_path))

            # 3. Run YOLOv8 Object Detection
            results = self.model(str(image_path), verbose=False)
            if not results or len(results) == 0:
                return True, "No distinct objects detected."

            annotated_frame = results[0].plot()
            out_file = self.vision_dir / f"scan_{int(time.time())}.jpg"
            cv2.imwrite(str(out_file), annotated_frame)

            detected_names = []
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                name = self.model.names.get(cls_id, "object")
                detected_names.append(name)

            if not detected_names:
                return True, "No distinct objects detected in frame."

            counts = collections.Counter(detected_names)
            summary_parts = [f"{count} {name}{'s' if count > 1 else ''}" for name, count in counts.items()]
            summary_text = ", ".join(summary_parts)

            return True, f"Camera {self.active_camera} scan detected: {summary_text}."

        except Exception as e:
            return False, f"YOLO Vision scan error: {e}"
