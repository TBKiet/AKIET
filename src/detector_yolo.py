"""
YOLOv5 detector optimized for Jetson with TensorRT
Ultra-fast real-time circle/disc detection

Requirements:
- torch, torchvision (install via pip or JetPack)
- YOLOv5 (clone from https://github.com/ultralytics/yolov5)
- TensorRT (comes with JetPack)

Setup:
    git clone https://github.com/ultralytics/yolov5
    cd yolov5
    pip install -r requirements.txt

Performance: 40-80 FPS on Jetson Nano with YOLOv5s
"""

import numpy as np
import time
from pathlib import Path
import sys
import os

# Add YOLOv5 to path if needed
YOLOV5_PATH = os.path.join(os.path.dirname(__file__), '..', 'yolov5')
if os.path.exists(YOLOV5_PATH) and YOLOV5_PATH not in sys.path:
    sys.path.insert(0, YOLOV5_PATH)

try:
    import torch
    TORCH_AVAILABLE = torch.cuda.is_available()
    if TORCH_AVAILABLE:
        print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠ CUDA not available, using CPU (slower)")

    # Try to import YOLOv5
    try:
        # Import YOLOv5 models
        from models.common import DetectMultiBackend
        from utils.general import non_max_suppression, scale_boxes
        from utils.torch_utils import select_device
        from utils.augmentations import letterbox
        YOLO_AVAILABLE = True
        print("✓ YOLOv5 imported successfully")
    except ImportError as e:
        print(f"YOLOv5 import error: {e}")
        print("Please clone YOLOv5: git clone https://github.com/ultralytics/yolov5")
        YOLO_AVAILABLE = False

except ImportError:
    TORCH_AVAILABLE = False
    YOLO_AVAILABLE = False
    print("Warning: torch not installed. Install with: pip install torch torchvision")


class YOLODetector:
    """
    YOLOv5-based circle detector with TensorRT optimization
    """
    def __init__(self, model_path=None, use_tensorrt=True, conf_threshold=0.5):
        """
        Initialize YOLOv5 detector

        Args:
            model_path: Path to YOLOv5 model (.pt or .engine)
            use_tensorrt: Convert to TensorRT for speed boost
            conf_threshold: Detection confidence threshold
        """
        if not YOLO_AVAILABLE:
            raise ImportError("YOLOv5 not available. Please clone: git clone https://github.com/ultralytics/yolov5")

        self.conf_threshold = conf_threshold
        self.model = None
        self.use_tensorrt = use_tensorrt and TORCH_AVAILABLE
        self.model_path = model_path
        self.device = select_device('0' if TORCH_AVAILABLE else 'cpu')
        self.img_size = 480  # Reduced from 640 for faster inference on Jetson
        self.half = TORCH_AVAILABLE  # Use FP16 if available

        # Performance tracking
        self.inference_times = []
        self.max_time_samples = 30

        # Load model
        if model_path and Path(model_path).exists():
            self._load_model(model_path)
        else:
            # Use pretrained YOLOv5n as fallback
            print("No custom model found, using pretrained YOLOv5n")
            print("Note: For best results, train a custom model on disc images")
            self._load_pretrained()

    def _load_model(self, model_path):
        """Load YOLOv5 model"""
        print(f"Loading YOLOv5 model from {model_path}...")

        model_path = Path(model_path)

        # Check if TensorRT engine exists
        engine_path = model_path.with_suffix('.engine')

        if engine_path.exists():
            print(f"Loading TensorRT engine: {engine_path}")
            self.model = DetectMultiBackend(str(engine_path), device=self.device)
        elif self.use_tensorrt and model_path.suffix == '.pt':
            print("Note: TensorRT export for YOLOv5 requires additional steps")
            print("Using PyTorch model for now. For TensorRT, use: python export.py --weights best.pt --include engine")
            self.model = DetectMultiBackend(str(model_path), device=self.device)
        else:
            self.model = DetectMultiBackend(str(model_path), device=self.device)

        self.img_size = self.model.stride * 32  # Ensure img_size is multiple of stride

        # Use FP16 for speedup on Jetson
        if self.half and hasattr(self.model, 'half'):
            self.model.half()

        print(f"✓ Model loaded successfully, image size: {self.img_size}")

    def _load_pretrained(self):
        """Load pretrained YOLOv5n and optimize for circle detection"""
        print("Loading pretrained YOLOv5n...")

        # Use YOLOv5n (fastest, good for Jetson)
        # This model is pretrained on COCO dataset
        model_name = 'yolov5n.pt'

        # Try to find the model in YOLOv5 directory or download it
        yolov5_weights = Path(YOLOV5_PATH) / model_name
        if yolov5_weights.exists():
            self.model = DetectMultiBackend(str(yolov5_weights), device=self.device)
        else:
            # Let YOLOv5 download it
            print(f"Downloading {model_name}...")
            self.model = DetectMultiBackend(model_name, device=self.device)

        self.img_size = 480  # Reduced for faster inference

        # Use FP16 for speedup on Jetson
        if self.half and hasattr(self.model, 'half'):
            self.model.half()

        # Classes that are typically round in COCO dataset:
        # 32: sports ball, 33: bottle, 34: wine glass, 36: frisbee
        # We'll detect all objects and filter by circularity
        self.detect_all_classes = True  # Detect everything, filter by shape

        print("✓ Using YOLOv5 + circularity filtering for disc detection")

    def _preprocess(self, image):
        """Preprocess image for YOLOv5 - optimized version"""
        import cv2

        # Resize with cv2 (faster than letterbox for simple resize)
        h, w = image.shape[:2]

        # Simple resize instead of letterbox (faster)
        if h != self.img_size or w != self.img_size:
            img = cv2.resize(image, (self.img_size, self.img_size), interpolation=cv2.INTER_LINEAR)
        else:
            img = image.copy()

        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Transpose HWC to CHW
        img = img.transpose((2, 0, 1))
        img = np.ascontiguousarray(img)

        # To tensor
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        return img, (w, h)  # Return original size for rescaling

    def detect(self, image):
        """
        Detect circles using YOLOv5 + circularity filtering

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

        # Preprocess
        img, orig_size = self._preprocess(image)

        # Inference
        with torch.no_grad():
            pred = self.model(img, augment=False, visualize=False)

        # NMS
        pred = non_max_suppression(pred, self.conf_threshold, 0.45, classes=None, agnostic=False, max_det=300)

        # Track inference time
        inference_time = time.time() - start_time
        self.inference_times.append(inference_time)
        if len(self.inference_times) > self.max_time_samples:
            self.inference_times.pop(0)

        detected_circles = []

        # Calculate scale factors
        orig_w, orig_h = orig_size
        scale_x = orig_w / self.img_size
        scale_y = orig_h / self.img_size

        # Process predictions
        for i, det in enumerate(pred):  # per image
            if len(det):
                # Convert to CPU once for all detections (much faster than .item() per detection)
                det_cpu = det.cpu().numpy()

                # Process detections - boxes are in img_size coordinates
                for detection in det_cpu:
                    x1, y1, x2, y2, conf, cls = detection

                    if conf < self.conf_threshold:
                        continue

                    # Rescale to original image size
                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)

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

        return detected_circles

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

    print("Testing YOLOv5 detector...")
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
