import sys
import cv2
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QFrame, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor

from src.camera import Camera
from src.detector import CircleDetector
from src.calibration import CalibrationManager
from src.classifier import Classifier
from src.planner import PathPlanner
from src.ui.widgets import CameraWidget, SimulationWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Innovation: Computer Vision & Robot Simulation")
        self.resize(1200, 700)

        # Initialize Core Modules
        self.camera = Camera(0) # Default camera
        self.detector = CircleDetector()
        self.calibration = CalibrationManager(scale_factor=1.0) # Default 1mm/px (needs calib)
        self.planner = PathPlanner()
        self.classifier = Classifier()

        # State
        self.is_running = False
        self.detected_objects = [] # Stores current frame's detections

        # UI Setup
        self._setup_ui()

        # Signals - Use Qt.QueuedConnection for thread-safe signal handling
        from PyQt5.QtCore import Qt as QtCore
        self.camera.frame_received.connect(
            self._process_frame,
            type=QtCore.ConnectionType.QueuedConnection if hasattr(QtCore, 'ConnectionType') else QtCore.QueuedConnection
        )

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
        # Debug: print frame info
        if not hasattr(self, '_frame_count'):
            self._frame_count = 0
        self._frame_count += 1
        if self._frame_count % 30 == 1:  # Print every 30 frames
            print(f"Processing frame {self._frame_count}: shape={frame.shape}, dtype={frame.dtype}")
            print(f"  Frame min/max values: {frame.min()}/{frame.max()}")
            print(f"  Frame first pixel: {frame[0,0]}")

        # BYPASS DETECTOR FOR NOW - just show raw frame
        vis_frame = frame.copy()

        # Add debug text to show it's working
        cv2.putText(vis_frame, "CAMERA FEED WORKING!", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(vis_frame, f"Frame {self._frame_count}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Update Widget - bypass all detection for now
        self.camera_widget.update_frame(vis_frame)

        # Update Stats
        self.lbl_stats.setText(f"Status: Running | Frame: {self._frame_count}")
        return  # EARLY RETURN TO BYPASS DETECTION

        # === ORIGINAL CODE BELOW (DISABLED FOR DEBUG) ===
        # copy frame to avoid modifying the original buffer in place if needed
        # vis_frame = frame.copy()

        # 1. Detect Circles
        circles = self.detector.detect(frame)

        # 2. Process Detections
        self.detected_objects = []
        sim_discs = []

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
            # Green circle
            cv2.circle(vis_frame, (x, y), radius, (0, 255, 0), 2)
            # Center point
            cv2.circle(vis_frame, (x, y), 2, (0, 0, 255), 3)
            # Text info
            text = f"{size_class} ({radius_mm:.1f}mm)"
            cv2.putText(vis_frame, text, (x - 20, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            # Prepare data for simulation (mapping visualization)
            # Important: Map camera coordinates to simulation canvas if sizes differ
            # For now assume direct mapping but scale if needed

            # Color logic based on new classes
            if "Medium" in size_class:
                color = QColor("yellow")
            elif "Small" in size_class:
                color = QColor("red")
            else:
                color = QColor("green")

            sim_discs.append({
                'x': x // 2 + 50, # Simple mapping offset
                'y': y // 2,
                'radius': radius // 2, # Scale down for potential resolution diff
                'color': color
            })

        # Update Widgets
        self.camera_widget.update_frame(vis_frame)
        self.sim_widget.set_discs(sim_discs)

        # Update Stats
        self.lbl_stats.setText(f"Status: Running | Detected: {len(circles)}")

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
