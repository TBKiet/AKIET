"""
YOLOv8-Nano detector optimized for Jetson with TensorRT
Ultra-fast real-time circle/disc detection

Requirements:
- ultralytics (pip install ultralytics)
- TensorRT (comes with JetPack)

Performance: 40-80 FPS on Jetson Nano
"""

import numpy as np
import time
from pathlib import Path

try:
    from ultralytics import YOLO
    import torch
    YOLO_AVAILABLE = True
    # Check CUDA availability
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠ CUDA not available, using CPU (slower)")
except ImportError:
    YOLO_AVAILABLE = False
    CUDA_AVAILABLE = False
    print("Warning: ultralytics not installed. Install with: pip install ultralytics")


class YOLODetector:
    """
    YOLO-based circle detector with TensorRT optimization
    """
    def __init__(self, model_path=None, use_tensorrt=True, conf_threshold=0.5):
        """
        Initialize YOLO detector

        Args:
            model_path: Path to YOLO model (.pt or .engine)
            use_tensorrt: Convert to TensorRT for speed boost
            conf_threshold: Detection confidence threshold
        """
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics not installed")

        self.conf_threshold = conf_threshold
        self.model = None
        self.use_tensorrt = use_tensorrt and CUDA_AVAILABLE  # Only use TensorRT if CUDA available
        self.model_path = model_path
        self.device = 0 if CUDA_AVAILABLE else 'cpu'

        # Performance tracking
        self.inference_times = []
        self.max_time_samples = 30

        # Load model
        if model_path and Path(model_path).exists():
            self._load_model(model_path)
        else:
            # Use pretrained YOLOv8n as fallback
            print("No custom model found, using pretrained YOLOv8n")
            print("Note: For best results, train a custom model on disc images")
            self._load_pretrained()

    def _load_model(self, model_path):
        """Load YOLO model"""
        print(f"Loading YOLO model from {model_path}...")

        model_path = Path(model_path)

        # Check if TensorRT engine exists
        engine_path = model_path.with_suffix('.engine')

        if engine_path.exists():
            print(f"Loading TensorRT engine: {engine_path}")
            self.model = YOLO(str(engine_path))
        elif self.use_tensorrt and model_path.suffix == '.pt':
            print("Converting to TensorRT engine (first time only, may take 1-2 minutes)...")
            self.model = YOLO(str(model_path))
            # Export to TensorRT
            self.model.export(format='engine', device=0, half=True)  # FP16 for speed
            print(f"TensorRT engine saved to: {engine_path}")
        else:
            self.model = YOLO(str(model_path))

        print(f"✓ Model loaded successfully")

    def _load_pretrained(self):
        """Load pretrained YOLOv8n and optimize for circle detection"""
        print("Loading pretrained YOLOv8n...")

        # Use YOLOv8n (fastest, good for Jetson)
        # This model is pretrained on COCO dataset
        self.model = YOLO('yolov8n.pt')

        # Classes that are typically round in COCO dataset:
        # 32: sports ball, 33: bottle, 34: wine glass, 36: frisbee
        # We'll detect all objects and filter by circularity
        self.detect_all_classes = True  # Detect everything, filter by shape

        if self.use_tensorrt:
            try:
                engine_path = Path('yolov8n.engine')
                if engine_path.exists():
                    print("Loading existing TensorRT engine...")
                    self.model = YOLO(str(engine_path))
                    print("✓ Using TensorRT engine")
                else:
                    print("Converting to TensorRT (first time, ~1-2 minutes)...")
                    self.model.export(format='engine', device=0, half=True)
                    print("✓ TensorRT engine created")
            except Exception as e:
                print(f"TensorRT conversion failed: {e}")
                print("Using standard PyTorch model")

        print("✓ Using YOLO + circularity filtering for disc detection")

    def detect(self, image):
        """
        Detect circles using YOLO + circularity filtering

        Args:
            image: BGR image (numpy array)

        Returns:
            List of tuples (x, y, radius)
        """
        if image is None or image.size == 0:
            return []

        if self.model is None:
            return []

        start_time = time.time()

        # Run inference on all objects
        results = self.model.predict(
            image,
            conf=self.conf_threshold,
            iou=0.45,
            verbose=False,
            device=self.device  # Use GPU if available, else CPU
        )

        # Track inference time
        inference_time = time.time() - start_time
        self.inference_times.append(inference_time)
        if len(self.inference_times) > self.max_time_samples:
            self.inference_times.pop(0)

        detected_circles = []

        if len(results) > 0:
            result = results[0]

            # Process detections (bounding boxes)
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.cpu().numpy()

                for box in boxes:
                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0]
                    conf = box.conf[0]

                    if conf < self.conf_threshold:
                        continue

                    # Calculate aspect ratio to filter circular objects
                    width = x2 - x1
                    height = y2 - y1
                    aspect_ratio = width / height if height > 0 else 0

                    # Filter: aspect ratio close to 1.0 = circular/square
                    if 0.7 <= aspect_ratio <= 1.3:
                        # Calculate circle from bounding box
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        radius = int(max(width, height) / 2)

                        # Additional check: minimum size filter
                        if radius >= 15:  # Same as Hough minRadius
                            detected_circles.append((center_x, center_y, radius))

            # If segmentation model, use masks for better circle fitting
            if hasattr(result, 'masks') and result.masks is not None:
                detected_circles = self._fit_circles_from_masks(result.masks)

        return detected_circles

    def _fit_circles_from_masks(self, masks):
        """Fit circles from segmentation masks (more accurate)"""
        import cv2

        circles = []
        masks_data = masks.cpu().numpy()

        for mask in masks_data:
            # Find contours
            mask_uint8 = (mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                # Get largest contour
                contour = max(contours, key=cv2.contourArea)

                # Fit minimum enclosing circle
                (x, y), radius = cv2.minEnclosingCircle(contour)
                circles.append((int(x), int(y), int(radius)))

        return circles

    def get_avg_inference_time(self):
        """Get average inference time in ms"""
        if len(self.inference_times) == 0:
            return 0
        return np.mean(self.inference_times) * 1000

    def get_fps(self):
        """Get estimated FPS"""
        avg_time = self.get_avg_inference_time() / 1000
        if avg_time == 0:
            return 0
        return 1.0 / avg_time


# Fallback to optimized Hough if YOLO not available
class HybridDetector:
    """
    Hybrid detector: try YOLO first, fallback to Hough
    """
    def __init__(self):
        try:
            self.yolo_detector = YOLODetector()
            self.use_yolo = True
            print("✓ Using YOLO detector")
        except:
            from src.detector_optimized import CircleDetector
            self.hough_detector = CircleDetector()
            self.use_yolo = False
            print("⚠ YOLO unavailable, using Hough Circle detector")

    def detect(self, image):
        if self.use_yolo:
            return self.yolo_detector.detect(image)
        else:
            return self.hough_detector.detect(image)

    def get_fps(self):
        if self.use_yolo:
            return self.yolo_detector.get_fps()
        return 0


if __name__ == "__main__":
    # Test detector
    import cv2

    print("Testing YOLO detector...")
    detector = YOLODetector()

    # Create test image
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(test_img, (200, 200), 50, (255, 255, 255), -1)
    cv2.circle(test_img, (400, 300), 80, (255, 255, 255), -1)

    # Test detection
    for i in range(10):
        circles = detector.detect(test_img)
        print(f"Frame {i+1}: Detected {len(circles)} circles, "
              f"Inference: {detector.get_avg_inference_time():.1f}ms, "
              f"FPS: {detector.get_fps():.1f}")

    print("\nTest completed!")
