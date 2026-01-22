import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import subprocess

class Camera(QObject):
    """
    Camera using GStreamer subprocess (no OpenCV GStreamer dependency needed)
    Similar to C# CameraReader approach
    """
    frame_received = pyqtSignal(np.ndarray)

    def __init__(self, width=640, height=480):
        super().__init__()
        self.width = width
        self.height = height
        self.gst_process = None
        self.running = False
        self.thread = None
        self.camera_type = None

    def start(self):
        if self.running:
            return

        # Use system gst-launch-1.0 (not conda's)
        # BGR format output via fdsink
        pipeline = [
            "/usr/bin/gst-launch-1.0", "-q",
            "nvarguscamerasrc", "sensor-id=0", "!",
            f"video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12", "!",
            "nvvidconv", "!",
            f"video/x-raw, width={self.width}, height={self.height}, format=BGRx", "!",
            "videoconvert", "!",
            "video/x-raw, format=BGR", "!",
            "fdsink", "fd=1", "sync=false"
        ]

        print(f"Starting CSI camera via subprocess...")
        print(f"Pipeline: {' '.join(pipeline)}")

        try:
            self.gst_process = subprocess.Popen(
                pipeline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.width * self.height * 3
            )

            self.camera_type = 'CSI (subprocess)'
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            print(f"✓ Camera started via subprocess")

        except Exception as e:
            print(f"✗ Failed to start camera subprocess: {e}")
            if self.gst_process:
                self.gst_process.kill()
                self.gst_process = None

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.gst_process:
            self.gst_process.kill()
            self.gst_process.wait()
            self.gst_process = None

    def _capture_loop(self):
        frame_size = self.width * self.height * 3  # BGR = 3 bytes per pixel
        frame_count = 0

        while self.running and self.gst_process:
            try:
                # Read one complete frame
                data = self.gst_process.stdout.read(frame_size)

                if len(data) != frame_size:
                    if not self.running:
                        break
                    print(f"Warning: Incomplete frame ({len(data)}/{frame_size} bytes)")
                    time.sleep(0.01)
                    continue

                # Convert bytes to numpy array
                frame = np.frombuffer(data, dtype=np.uint8).reshape((self.height, self.width, 3))
                frame_count += 1

                if frame_count % 30 == 1:
                    print(f"Captured frame {frame_count}: shape={frame.shape}, mean BGR={frame.mean(axis=(0,1))}")

                self.frame_received.emit(frame)

            except Exception as e:
                if self.running:
                    print(f"Error in capture loop: {e}")
                break

        print("Camera capture loop ended")

    def dispose(self):
        self.stop()


if __name__ == "__main__":
    # Test
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    cam = Camera()

    def on_frame(frame):
        print(f"Received frame: {frame.shape}, dtype={frame.dtype}")

    cam.frame_received.connect(on_frame)
    cam.start()

    # Let it run for a few seconds
    import time
    time.sleep(3)

    cam.stop()
    print("Test completed")
