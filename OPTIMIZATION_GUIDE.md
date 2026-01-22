"""
Optimized main_window.py changes:

1. Skip frame processing (only process every Nth frame)
2. Use optimized detector
3. Remove debug code
4. Enable real detection
"""

# In __init__ of MainWindow, add:
from src.detector_optimized import CircleDetector  # Use optimized detector
from src.camera_optimized import Camera  # Use optimized camera

self.camera = Camera(480, 360, 60)  # Lower res, higher FPS
self.detector = CircleDetector()
self.frame_skip = 2  # Process every 2nd frame for performance
self._last_process_time = 0

# Replace _process_frame with:
def _process_frame(self, frame):
    """
    Optimized frame processing with frame skipping
    """
    if not hasattr(self, '_frame_count'):
        self._frame_count = 0
    self._frame_count += 1

    # Skip frames for better performance
    if self._frame_count % self.frame_skip != 0:
        return

    # Measure processing time
    import time
    start_time = time.time()

    vis_frame = frame.copy()

    # 1. Detect Circles (with optimized detector)
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
        cv2.circle(vis_frame, (x, y), radius, (0, 255, 0), 2)
        cv2.circle(vis_frame, (x, y), 2, (0, 0, 255), 3)
        text = f"{size_class} ({radius_mm:.1f}mm)"
        cv2.putText(vis_frame, text, (x - 20, y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Prepare for simulation
        if "Medium" in size_class:
            color = QColor("yellow")
        elif "Small" in size_class:
            color = QColor("red")
        else:
            color = QColor("green")

        sim_discs.append({
            'x': x // 2 + 50,
            'y': y // 2,
            'radius': radius // 2,
            'color': color
        })

    # Calculate and display FPS
    process_time = time.time() - start_time
    fps = 1.0 / process_time if process_time > 0 else 0
    cv2.putText(vis_frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(vis_frame, f"Objects: {len(circles)}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Update Widgets
    self.camera_widget.update_frame(vis_frame)
    self.sim_widget.set_discs(sim_discs)

    # Update Stats
    self.lbl_stats.setText(f"Running | FPS: {fps:.1f} | Detected: {len(circles)}")
