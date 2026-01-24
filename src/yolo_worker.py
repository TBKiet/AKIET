"""
YOLOWorkerThread - Background thread for YOLO inference
Prevents UI blocking and enables real-time performance
"""
from PyQt5.QtCore import QThread, pyqtSignal
import time
import numpy as np


class YOLOWorkerThread(QThread):
    """
    Background worker thread for YOLO detection.
    Runs inference asynchronously to prevent UI blocking.
    """
    # Signal emitted when detection completes: (circles, inference_time_ms, frame_id)
    detection_complete = pyqtSignal(list, float, int)

    def __init__(self, detector):
        """
        Initialize worker thread.

        Args:
            detector: YOLODetector instance
        """
        super().__init__()
        self.detector = detector
        self.current_frame = None
        self.frame_id = 0
        self.running = True
        self.processing = False

    def add_frame(self, frame):
        """
        Add a new frame for processing.
        Drops old frames if still processing (keeps only latest).

        Args:
            frame: BGR image (numpy array)
        """
        if not self.processing:
            self.current_frame = frame
            self.frame_id += 1
        # Else: drop this frame, we're still processing the previous one

    def run(self):
        """
        Main worker loop - runs in background thread.
        """
        while self.running:
            if self.current_frame is not None:
                self.processing = True
                frame = self.current_frame
                frame_id = self.frame_id
                self.current_frame = None  # Clear immediately to accept new frames

                # Perform YOLO inference (this is the slow part)
                start_time = time.time()
                try:
                    circles = self.detector.detect(frame)
                    inference_time_ms = (time.time() - start_time) * 1000

                    # Emit results back to main thread
                    self.detection_complete.emit(circles, inference_time_ms, frame_id)
                except Exception as e:
                    print(f"YOLO Worker Error: {e}")
                    self.detection_complete.emit([], 0, frame_id)

                self.processing = False
            else:
                # No frame to process, sleep briefly
                self.msleep(5)  # 5ms sleep

    def stop(self):
        """
        Stop the worker thread gracefully.
        """
        self.running = False
        self.wait()  # Wait for thread to finish
