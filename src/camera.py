import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import subprocess

class Camera(QObject):
    """
    Optimized camera with higher FPS and lower latency
    """
    frame_received = pyqtSignal(np.ndarray)

    def __init__(self, width=480, height=360, fps=60):  # Lower resolution, higher FPS
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.gst_process = None
        self.running = False
        self.thread = None
        self.camera_type = None
        self.frame_count = 0

    def start(self):
        if self.running:
            return

        # Optimized pipeline: use 720p@60fps sensor mode, downscale to 480x360
        pipeline = [
            "/usr/bin/gst-launch-1.0", "-q",
            "nvarguscamerasrc", "sensor-id=0", "!",
            f"video/x-raw(memory:NVMM), width=1280, height=720, framerate={self.fps}/1, format=NV12", "!",
            "nvvidconv", "!",
            f"video/x-raw, width={self.width}, height={self.height}, format=BGRx", "!",
            "videoconvert", "!",
            "video/x-raw, format=BGR", "!",
            "fdsink", "fd=1", "sync=false"
        ]

        print(f"Starting optimized CSI camera: {self.width}x{self.height} @ {self.fps}fps")

        try:
            self.gst_process = subprocess.Popen(
                pipeline,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Suppress stderr for performance
                bufsize=self.width * self.height * 3 * 2  # Larger buffer
            )

            self.camera_type = 'CSI (optimized)'
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            print(f"✓ Optimized camera started")

        except Exception as e:
            print(f"✗ Failed to start camera: {e}")
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

        while self.running and self.gst_process:
            try:
                # Read exact frame size
                data = self.gst_process.stdout.read(frame_size)

                if len(data) != frame_size:
                    if not self.running:
                        break
                    print(f"Warning: incomplete frame, got {len(data)} bytes, expected {frame_size}")
                    continue

                # Safely create frame copy
                frame = np.frombuffer(data, dtype=np.uint8).reshape((self.height, self.width, 3)).copy()
                self.frame_count += 1

                # Emit copy to avoid memory corruption
                self.frame_received.emit(frame)

            except Exception as e:
                if self.running:
                    print(f"Capture error: {e}")
                break

        print("Camera capture ended")

    def dispose(self):
        self.stop()
