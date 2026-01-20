import cv2
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import subprocess

class Camera(QObject):
    """
    Handles camera capture in a separate thread to prevent blocking the UI.
    Emits the 'frame_received' signal when a new frame is available.
    """
    frame_received = pyqtSignal(np.ndarray)

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.cap = None
        self.running = False
        self.thread = None
        self.camera_type = None  # 'csi', 'usb', or None

    def _test_csi_camera(self):
        """Test if CSI camera is available using gst-launch-1.0"""
        try:
            print("Testing CSI camera availability...")
            # Test simple pipeline for 1 second
            cmd = [
                "gst-launch-1.0", "-q",
                "nvarguscamerasrc", "num-buffers=10", "sensor-id=0", "!",
                "fakesink"
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode == 0:
                print("✓ CSI camera detected!")
                return True
            else:
                print(f"✗ CSI camera test failed: {result.stderr.decode()}")
                return False
        except Exception as e:
            print(f"✗ CSI camera test error: {e}")
            return False

    def start(self):
        """Starts the camera capture thread."""
        if self.running:
            return

        print(f"Camera type: {self.camera_type}")
        # Try CSI camera first (for Jetson)
        csi_available = self._test_csi_camera()

        if csi_available:
            print("Attempting to open CSI camera with GStreamer pipeline...")
            # Pipeline GStreamer working cho Jetson CSI camera
            # Use 1280x720 @ 60fps (native sensor mode) for better performance
            pipeline = (
                "nvarguscamerasrc sensor-id=0 ! "
                "video/x-raw(memory:NVMM), width=1280, height=720, framerate=60/1, format=(string)NV12 ! "
                "nvvidconv flip-method=0 ! "
                "video/x-raw, width=640, height=480, format=(string)BGRx ! "
                "videoconvert ! "
                "appsink"
            )
            print(f"Pipeline: {pipeline}")
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

            if self.cap.isOpened():
                self.camera_type = 'csi'
                print("✓ CSI camera opened successfully!")
            else:
                print("✗ Failed to open CSI camera with OpenCV")
                self.cap = None

        # Fallback to USB camera
        if self.cap is None or not self.cap.isOpened():
            print("Trying USB camera (camera_id=0)...")
            self.cap = cv2.VideoCapture(self.camera_id)

            if self.cap.isOpened():
                self.camera_type = 'usb'
                print("✓ USB camera opened successfully!")
                # Set resolution for USB camera
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            else:
                print("✗ Failed to open USB camera")
                print("ERROR: No camera available!")
                return

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the camera capture thread and releases resources."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap:
            self.cap.release()

    def _capture_loop(self):
        """Internal loop for reading frames."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_received.emit(frame)
            else:
                print("Warning: Failed to read frame")
                time.sleep(0.1)

            # Limit frame rate to ~30 FPS to save resources
            time.sleep(0.015)

if __name__ == "__main__":
    # Test stub
    cam = Camera(0)
    cam.start()
    time.sleep(2)
    cam.stop()
    print("Camera test completed.")
