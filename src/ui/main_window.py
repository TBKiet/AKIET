import sys
import cv2
import time
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QFrame, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor

# Use original CSI camera (works with subprocess + GStreamer)
from src.camera import Camera

from src.detector import CircleDetector  # Use Hough Circle - fast on CPU

# Try to import YOLO detector
try:
    from src.detector_yolo import YOLODetector
    YOLO_AVAILABLE = True
except Exception as e:
    YOLO_AVAILABLE = False
    print(f"YOLO detector not available: {e}")

from src.calibration import CalibrationManager
from src.classifier import Classifier
from src.planner import PathPlanner
from src.ui.widgets import CameraWidget, SimulationWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV & Robot Sim")  # Shorter title
        self.resize(320, 180)  # Very compact for tiny display

        # Initialize Core Modules
        self.camera = Camera(480, 360, 60)  # Optimized: 480x360@60fps

        # Choose detector based on availability and user preference
        # TEMPORARY: Force use Hough detector for testing
        USE_YOLO = False
        YOLO_AVAILABLE = False  # Force disable
        
        if False:  # Disabled for now
            try:
                print("Loading YOLOv5 detector (GPU)...")
                self.detector = YOLODetector(conf_threshold=0.5)
                print("✓ YOLOv5 Detector loaded (GPU-accelerated)")
            except Exception as e:
                print(f"Failed to load YOLO: {e}")
                print("Falling back to Hough Circle Detector...")
                self.detector = CircleDetector()
                print("✓ Hough Circle Detector loaded (CPU-optimized)")
        else:
            self.detector = CircleDetector()
            print("✓ Hough Circle Detector loaded (CPU-optimized)")

        self.calibration = CalibrationManager(scale_factor=1.0) # Default 1mm/px (needs calib)
        self.planner = PathPlanner()
        self.classifier = Classifier()

        # State
        self.is_running = False
        self.detected_objects = [] # Stores current frame's detections

        # UI Setup
        self._setup_ui()

        # Signals - Use Qt.QueuedConnection for thread-safe signal handling
        self.camera.frame_received.connect(self._process_frame, Qt.QueuedConnection)

        # Timer for robot animation
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate_robot)
        self.anim_path = []
        self.anim_idx = 0

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout: HBox [Left: Camera | Right: Sim]
        main_layout = QHBoxLayout(central_widget)

        # --- Left Panel: Camera ---
        left_layout = QVBoxLayout()

        # Add label
        camera_label = QLabel("Live Camera Feed")
        left_layout.addWidget(camera_label)

        # Add camera widget with explicit sizing
        self.camera_widget = CameraWidget()
        self.camera_widget.setSizePolicy(
            QSizePolicy.Expanding if hasattr(QSizePolicy, 'Expanding') else QSizePolicy.Policy.Expanding,
            QSizePolicy.Expanding if hasattr(QSizePolicy, 'Expanding') else QSizePolicy.Policy.Expanding
        )
        left_layout.addWidget(self.camera_widget, stretch=10)  # Give it high stretch priority

        # Controls
        controls_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Camera")
        self.btn_start.clicked.connect(self._toggle_camera)

        self.btn_calibrate = QPushButton("Calibrate (Using 5cm Disc)")
        self.btn_calibrate.clicked.connect(self._calibrate)

        self.btn_sort = QPushButton("Simulate Sort")
        self.btn_sort.clicked.connect(self._start_simulation)

        controls_layout.addWidget(self.btn_start)
        controls_layout.addWidget(self.btn_calibrate)
        controls_layout.addWidget(self.btn_sort)
        left_layout.addLayout(controls_layout)

        left_data_layout = QVBoxLayout()
        self.lbl_stats = QLabel("Status: Ready")
        left_data_layout.addWidget(self.lbl_stats)
        left_layout.addLayout(left_data_layout)

        # --- Right Panel: Simulation ---
        right_layout = QVBoxLayout()
        self.sim_widget = SimulationWidget()
        right_layout.addWidget(QLabel("Robot Simulation Environment"))
        right_layout.addWidget(self.sim_widget)

        # Add layouts
        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addLayout(right_layout, stretch=2)

    def _toggle_camera(self):
        if not self.is_running:
            self.camera.start()
            self.btn_start.setText("Stop Camera")
            self.is_running = True
        else:
            self.camera.stop()
            self.btn_start.setText("Start Camera")
            self.is_running = False

    def _process_frame(self, frame):
        """
        Main loop logic: Detect -> Measure -> Draw -> Display
        """
        # Track FPS
        if not hasattr(self, '_frame_count'):
            self._frame_count = 0
            self._last_fps_time = time.time()
        self._frame_count += 1

        # Calculate FPS every 30 frames
        if self._frame_count % 30 == 0:
            elapsed = time.time() - self._last_fps_time
            fps = 30 / elapsed if elapsed > 0 else 0
            print(f"FPS: {fps:.1f}")
            self._last_fps_time = time.time()

        vis_frame = frame.copy()

        # Hough Circle Detection (fast on CPU)
        try:
            # 1. Detect Circles
            circles = self.detector.detect(frame)

            # 2. Process Detections
            self.detected_objects = []

            for (x, y, radius) in circles:
                # Measure
                radius_mm = self.calibration.pixel_to_mm(radius)
                size_class = self.classifier.classify(radius_mm)

                # Store
                obj = {
                    'x': x, 'y': y, 'radius_px': radius,
                    'radius_mm': radius_mm, 'class': size_class
                }
                self.detected_objects.append(obj)

                # Draw on Camera Frame
                cv2.circle(vis_frame, (x, y), radius, (0, 255, 0), 2)
                cv2.circle(vis_frame, (x, y), 2, (0, 0, 255), 3)
                text = f"{size_class} ({radius_mm:.1f}mm)"
                cv2.putText(vis_frame, text, (x - 20, y - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            # Show detection count
            cv2.putText(vis_frame, f"Detected: {len(circles)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        except Exception as e:
            # If detection fails, show error but continue
            cv2.putText(vis_frame, f"Error: {str(e)[:30]}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        cv2.putText(vis_frame, f"Frame {self._frame_count}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Update UI
        self.camera_widget.update_frame(vis_frame)

    def _calibrate(self):
        """
        Simple calibration: assumes the first detected object is exactly 50mm diameter.
        """
        if not self.detected_objects:
            self.lbl_stats.setText("Status: No object detected for calibration!")
            return

        # Take the first object
        ref_obj = self.detected_objects[0]
        # Diameter = radius * 2
        ref_px = ref_obj['radius_px'] * 2

        # Set to 50mm reference
        self.calibration.set_scale_from_reference(ref_px, 50.0)
        self.lbl_stats.setText(f"Status: Calibrated! Scale={self.calibration.scale_factor:.4f} mm/px")

    def _start_simulation(self):
        """
        Triggers the robot path planning demo.
        Target: The largest object detected.
        """
        if not self.detected_objects:
            return

        # Find largest object
        target = max(self.detected_objects, key=lambda x: x['radius_mm'])

        # Simulation coordinates (matched with _process_frame mapping)
        start_x, start_y = (50, 350) # Robot base
        end_x, end_y = (target['x'] // 2 + 50, target['y'] // 2)

        path = self.planner.generate_path((start_x, start_y), (end_x, end_y))

        self.sim_widget.set_robot_path(path)
        self.anim_path = path
        self.anim_idx = 0
        self.anim_timer.start(20) # 50 FPS for animation

    def _animate_robot(self):
        if self.anim_idx < len(self.anim_path):
            x, y = self.anim_path[self.anim_idx]
            self.sim_widget.set_robot_pos(x, y)
            self.anim_idx += 1
        else:
            self.anim_timer.stop()

    def closeEvent(self, event):
        self.camera.stop()
        event.accept()
