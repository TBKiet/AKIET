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
    from src.yolo_worker import YOLOWorkerThread
    YOLO_AVAILABLE = True
except Exception as e:
    YOLO_AVAILABLE = False
    YOLOWorkerThread = None
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
        # Set to True to enable YOLO with background threading
        USE_YOLO = YOLO_AVAILABLE  # Enable YOLO if available

        self.yolo_worker = None
        self.latest_detections = []  # Store latest YOLO results
        self.yolo_inference_time = 0

        if USE_YOLO and YOLO_AVAILABLE:
            try:
                print("Loading YOLOv5 detector (GPU)...")
                yolo_detector = YOLODetector(conf_threshold=0.5)
                print("✓ YOLOv5 Detector loaded (GPU-accelerated)")

                # Create background worker thread
                self.yolo_worker = YOLOWorkerThread(yolo_detector)
                self.yolo_worker.detection_complete.connect(self._on_yolo_detection_complete)
                self.yolo_worker.start()
                print("✓ YOLO Worker Thread started")

                # Use Hough as fallback for visualization
                self.detector = CircleDetector()
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
        self.anim_stage = 0  # 0: move to disc, 1: pick, 2: move to bin, 3: place
        self.current_target = None
        self.target_bin_pos = None

    def _on_yolo_detection_complete(self, circles, inference_time_ms, frame_id):
        """
        Callback when YOLO worker completes detection.
        Runs on main thread (Qt signal).
        """
        self.latest_detections = circles
        self.yolo_inference_time = inference_time_ms
        # Results will be used in next _process_frame call

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
        Optimized: Uses background YOLO worker + frame skipping
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
            print(f"UI FPS: {fps:.1f}")
            if self.yolo_worker:
                print(f"YOLO Inference: {self.yolo_inference_time:.1f}ms")
            self._last_fps_time = time.time()

        # OPTIMIZATION: Don't copy frame unless necessary
        # We'll draw directly on the frame (camera should provide fresh frames)
        vis_frame = frame

        # If YOLO worker is active, send frame to background thread
        if self.yolo_worker:
            # Send frame to worker (worker will drop if still processing)
            self.yolo_worker.add_frame(frame.copy())  # Copy here since worker runs async

            # Use latest YOLO detections (may be from previous frame)
            circles = self.latest_detections
        else:
            # Fallback: Use Hough detector (runs on UI thread - fast enough)
            try:
                circles = self.detector.detect(frame)
            except Exception as e:
                circles = []
                cv2.putText(vis_frame, f"Error: {str(e)[:30]}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Process Detections
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

        # Update simulation widget with detected discs in real-time
        if self.detected_objects:
            self._update_simulation_discs()

        # Show detection count and performance info
        cv2.putText(vis_frame, f"Detected: {len(circles)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if self.yolo_worker:
            cv2.putText(vis_frame, f"YOLO: {self.yolo_inference_time:.0f}ms", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.putText(vis_frame, f"Frame {self._frame_count}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Update UI
        self.camera_widget.update_frame(vis_frame)

    def _update_simulation_discs(self):
        """Update simulation widget with current detected discs"""
        sim_discs = []
        scale_x = 400 / 480
        scale_y = 450 / 360

        for obj in self.detected_objects:
            # Fixed radius based on classification
            size_class = obj['class']
            if size_class == 'Small (5cm)':
                fixed_radius = 20
            elif size_class == 'Medium (7cm)':
                fixed_radius = 30
            else:  # Large (10cm)
                fixed_radius = 40

            sim_disc = {
                'x': int(obj['x'] * scale_x + 20),
                'y': int(obj['y'] * scale_y + 20),
                'radius': fixed_radius,
                'size_class': size_class,
                'radius_mm': obj['radius_mm']
            }
            sim_discs.append(sim_disc)

        self.sim_widget.set_discs(sim_discs)

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
        print(f"[DEBUG] _start_simulation called, detected_objects: {len(self.detected_objects)}")

        if not self.detected_objects:
            self.lbl_stats.setText("Status: No objects detected! Please detect discs first.")
            print("[DEBUG] No objects detected - cannot start simulation")
            return

        # Update discs (already done in real-time, but ensure it's current)
        self._update_simulation_discs()

        # Find largest object
        target = max(self.detected_objects, key=lambda x: x['radius_mm'])

        # Robot starts at bottom-left
        start_x, start_y = (50, 450)
        # Target is the scaled position of largest disc
        scale_x = 400 / 480
        scale_y = 450 / 360
        end_x = int(target['x'] * scale_x + 20)
        end_y = int(target['y'] * scale_y + 20)

        path = self.planner.generate_path((start_x, start_y), (end_x, end_y), num_points=100)

        # Store target info for multi-stage animation
        self.current_target = target
        self.current_target_pos = (end_x, end_y)

        # Determine bin position based on size
        bin_x = self.sim_widget.width() - 60  # Right side
        if target['class'] == 'Small (5cm)':
            bin_y = 100
        elif target['class'] == 'Medium (7cm)':
            bin_y = 220
        else:  # Large
            bin_y = 340
        self.target_bin_pos = (bin_x, bin_y)

        # Stage 0: Move to disc - CLEAR old paths and start fresh
        self.anim_stage = 0
        self.sim_widget.clear_robot_paths()  # Clear old paths
        self.sim_widget.add_robot_path(path)  # Add first segment
        self.sim_widget.set_robot_state("Moving")
        self.anim_path = path
        self.anim_idx = 0
        self.anim_timer.start(16)  # ~60 FPS for smooth animation

        self.lbl_stats.setText(f"Status: Moving to {target['class']} disc...")
        print(f"[DEBUG] Stage 0: Moving to {target['class']} at ({end_x}, {end_y})")

    def _animate_robot(self):
        """Animate robot with smooth easing - multi-stage pick and place"""
        if self.anim_idx < len(self.anim_path):
            # Smooth easing (ease-in-out)
            progress = self.anim_idx / len(self.anim_path)
            if progress < 0.5:
                # Ease in (accelerate)
                eased_progress = 2 * progress * progress
            else:
                # Ease out (decelerate)
                eased_progress = 1 - 2 * (1 - progress) * (1 - progress)

            # Use eased index for smoother motion
            eased_idx = int(eased_progress * len(self.anim_path))
            eased_idx = min(eased_idx, len(self.anim_path) - 1)

            x, y = self.anim_path[eased_idx]
            self.sim_widget.set_robot_pos(x, y)
            self.anim_idx += 1
        else:
            # Current stage complete, move to next stage
            self._next_animation_stage()

    def _next_animation_stage(self):
        """Progress to next stage of pick-and-place sequence"""
        # CRITICAL: Stop timer before transitioning
        self.anim_timer.stop()

        if self.anim_stage == 0:
            # Stage 0 complete: Arrived at disc, now pick it
            print("[DEBUG] Stage 1: Picking disc...")
            self.sim_widget.set_robot_state("Picking")
            self.lbl_stats.setText(f"Status: Picking {self.current_target['class']} disc...")

            # Wait a moment, then move to bin
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self._start_transport_to_bin)

        elif self.anim_stage == 1:
            # Stage 1 complete: Arrived at bin, now place
            print("[DEBUG] Stage 2: Placing disc in bin...")
            self.sim_widget.set_robot_state("Placing")
            self.lbl_stats.setText(f"Status: Placing {self.current_target['class']} in bin...")

            # Wait a moment, then finish
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self._finish_sorting)

    def _start_transport_to_bin(self):
        """Stage 1: Transport disc to appropriate bin"""
        self.anim_stage = 1

        # Generate path from current position to bin
        current_pos = self.sim_widget.robot_pos
        path = self.planner.generate_path(current_pos, self.target_bin_pos, num_points=100)

        # ADD second path segment (don't replace first one)
        self.sim_widget.add_robot_path(path)
        self.sim_widget.set_robot_state("Moving")
        self.anim_path = path
        self.anim_idx = 0
        self.anim_timer.start(16)

        self.lbl_stats.setText(f"Status: Transporting {self.current_target['class']} to bin...")
        print(f"[DEBUG] Stage 1: Transporting to bin at {self.target_bin_pos}")

    def _finish_sorting(self):
        """Complete the sorting sequence"""
        self.sim_widget.set_robot_state("Idle")
        self.sim_widget.sorted_count += 1
        self.lbl_stats.setText(f"Status: Sorting complete! {self.current_target['class']} placed in bin.")
        print(f"[DEBUG] Sorting complete - {self.current_target['class']} sorted")

        # Clear path
        self.sim_widget.set_robot_path([])

    def closeEvent(self, event):
        # Stop camera
        self.camera.stop()

        # Stop YOLO worker thread if running
        if self.yolo_worker:
            print("Stopping YOLO worker thread...")
            self.yolo_worker.stop()
            print("YOLO worker stopped")

        event.accept()
