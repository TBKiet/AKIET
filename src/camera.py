import cv2
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

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

    def start(self):
        """Starts the camera capture thread."""
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_id}")
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
