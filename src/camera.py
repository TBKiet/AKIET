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

    def start(self):
        """Starts the camera capture thread."""
        if self.running:
            return

        # Try different camera options in order
        camera_options = [
            # Option 1: CSI Camera with GStreamer (Jetson Nano/Xavier)
            {
                'name': 'CSI (GStreamer - nvarguscamerasrc)',
                'pipeline': (
                    "nvarguscamerasrc sensor-id=0 ! "
                    "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12 ! "
                    "nvvidconv flip-method=0 ! "
                    "video/x-raw, width=640, height=480, format=BGRx ! "
                    "videoconvert ! "
                    "appsink"
                ),
                'type': 'gstreamer'
            },
            # Option 2: V4L2 with GStreamer (generic Linux)
            {
                'name': 'V4L2 (GStreamer)',
                'pipeline': (
                    "v4l2src device=/dev/video0 ! "
                    "video/x-raw, width=640, height=480, framerate=30/1 ! "
                    "videoconvert ! "
                    "appsink"
                ),
                'type': 'gstreamer'
            },
            # Option 3: Direct USB/V4L2 (OpenCV default)
            {
                'name': 'USB/V4L2 (OpenCV)',
                'id': 0,
                'type': 'v4l2'
            },
            # Option 4: Test pattern (for debugging)
            {
                'name': 'Test Pattern',
                'pipeline': (
                    "videotestsrc pattern=ball ! "
                    "video/x-raw, width=640, height=480, framerate=30/1 ! "
                    "videoconvert ! "
                    "appsink"
                ),
                'type': 'test'
            }
        ]

        for option in camera_options:
            print(f"\nTrying: {option['name']}...")

            try:
                if option['type'] == 'gstreamer' or option['type'] == 'test':
                    print(f"Pipeline: {option['pipeline']}")
                    self.cap = cv2.VideoCapture(option['pipeline'], cv2.CAP_GSTREAMER)
                else:  # v4l2
                    print(f"Device ID: {option['id']}")
                    self.cap = cv2.VideoCapture(option['id'], cv2.CAP_V4L2)
                    if self.cap.isOpened():
                        # Set resolution BEFORE reading any frame
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.cap.set(cv2.CAP_PROP_FPS, 30)
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for low latency
                        print(f"  Requested: 640x480 @ 30fps")

                if self.cap and self.cap.isOpened():
                    # Test read a frame
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        self.camera_type = option['name']
                        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                        print(f"✓ {option['name']} opened successfully!")
                        print(f"  Actual resolution: {actual_width}x{actual_height} @ {actual_fps}fps")
                        print(f"  Frame shape: {frame.shape}")

                        # If resolution is still too large, resize
                        if frame.shape[0] > 480 or frame.shape[1] > 640:
                            print(f"  Note: Will resize frames to 640x480 during capture")
                        break
                    else:
                        print(f"✗ {option['name']} opened but cannot read frame")
                        self.cap.release()
                        self.cap = None
                else:
                    print(f"✗ Failed to open {option['name']}")

            except Exception as e:
                print(f"✗ Error with {option['name']}: {e}")
                if self.cap:
                    self.cap.release()
                self.cap = None

        if self.cap is None or not self.cap.isOpened():
            print("\n❌ ERROR: No camera available!")
            print("\nTroubleshooting tips:")
            print("1. Install OpenCV with GStreamer: pip uninstall opencv-python && pip install opencv-contrib-python")
            print("2. Check camera permissions: ls -l /dev/video*")
            print("3. Add user to video group: sudo usermod -a -G video $USER")
            print("4. Test GStreamer: gst-launch-1.0 v4l2src device=/dev/video0 ! xvimagesink")
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
                # Resize if frame is too large (camera didn't respect resolution setting)
                h, w = frame.shape[:2]
                if h > 480 or w > 640:
                    # Calculate aspect-preserving resize
                    scale = min(640 / w, 480 / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

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
