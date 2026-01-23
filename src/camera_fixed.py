import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import cv2

class Camera(QObject):
    """
    CSI Camera using GStreamer pipeline (optimized for Jetson)
    Falls back to USB if CSI not available
    """
    frame_received = pyqtSignal(np.ndarray)

    def __init__(self, width=640, height=480, fps=60):
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.running = False
        self.thread = None
        self.frame_count = 0
        self.camera_type = None

    def _gstreamer_pipeline(self):
        """GStreamer pipeline for CSI camera"""
        return (
            f"nvarguscamerasrc sensor-id=0 ! "
            f"video/x-raw(memory:NVMM), "
            f"width=(int)1280, height=(int)720, "
            f"format=(string)NV12, framerate=(fraction){self.fps}/1 ! "
            f"nvvidconv flip-method=0 ! "
            f"video/x-raw, width=(int){self.width}, height=(int){self.height}, format=(string)BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=(string)BGR ! appsink"
        )

    def start(self):
        if self.running:
            return

        # Try CSI camera first
        print(f"Trying CSI camera: {self.width}x{self.height} @ {self.fps}fps")
        try:
            pipeline = self._gstreamer_pipeline()
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

            if self.cap.isOpened():
                # Test read
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.camera_type = "CSI"
                    print("✓ CSI camera started")
                else:
                    self.cap.release()
                    self.cap = None
        except Exception as e:
            print(f"CSI camera failed: {e}")
            if self.cap:
                self.cap.release()
            self.cap = None

        # Fallback to USB camera
        if not self.cap or not self.cap.isOpened():
            print("Trying USB camera...")
            try:
                self.cap = cv2.VideoCapture(0)

                if self.cap.isOpened():
                    # Set properties
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Test read
                    for _ in range(5):
                        self.cap.read()

                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        self.camera_type = "USB"
                        print("✓ USB camera started")
                    else:
                        self.cap.release()
                        self.cap = None
            except Exception as e:
                print(f"USB camera failed: {e}")
                if self.cap:
                    self.cap.release()
                self.cap = None

        if not self.cap or not self.cap.isOpened():
            print("✗ No camera available")
            return False

        # Start capture thread
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

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

        print(f"Starting capture loop ({self.camera_type} camera)...")

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
                    time.sleep(0.05)  # Wait before retry

            except Exception as e:
                if self.running:
                    print(f"Capture error: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        break
                    time.sleep(0.05)

        print(f"Camera capture ended (captured {self.frame_count} frames)")
        self.running = False

    def dispose(self):
        self.stop()
