import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import cv2

class Camera(QObject):
    """
    USB Camera fallback for when CSI camera is not available
    """
    frame_received = pyqtSignal(np.ndarray)

    def __init__(self, width=640, height=480, fps=30):
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.running = False
        self.thread = None
        self.frame_count = 0

    def start(self):
        if self.running:
            return

        print(f"Starting USB camera: {self.width}x{self.height} @ {self.fps}fps")

        try:
            # Try to open USB camera
            self.cap = cv2.VideoCapture(0)

            if not self.cap.isOpened():
                print("✗ Failed to open camera")
                return False

            # Set properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

            # Warm up camera
            for _ in range(5):
                self.cap.read()
                time.sleep(0.05)

            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            print(f"✓ USB camera started")
            return True

        except Exception as e:
            print(f"✗ Failed to start camera: {e}")
            if self.cap:
                self.cap.release()
                self.cap = None
            return False

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
        """Capture loop with proper error handling"""
        consecutive_failures = 0
        max_failures = 10

        while self.running and self.cap:
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None and frame.size > 0:
                    consecutive_failures = 0
                    self.frame_count += 1

                    # Resize if needed
                    if frame.shape[0] != self.height or frame.shape[1] != self.width:
                        frame = cv2.resize(frame, (self.width, self.height))

                    # Emit copy to avoid memory corruption
                    self.frame_received.emit(frame.copy())
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print(f"✗ Too many consecutive failures ({max_failures}), stopping camera")
                        break
                    time.sleep(0.1)  # Wait before retry

            except Exception as e:
                if self.running:
                    print(f"Capture error: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        break
                    time.sleep(0.1)

        print("Camera capture ended")
        self.running = False

    def dispose(self):
        self.stop()
