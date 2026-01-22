# Real-time Optimization Options

## Performance Comparison (Jetson Nano)

| Method | FPS | Accuracy | Setup Difficulty |
|--------|-----|----------|------------------|
| **YOLOv8n + TensorRT** | 40-80 | ⭐⭐⭐⭐⭐ | Medium |
| Hough + CUDA | 25-40 | ⭐⭐⭐⭐ | Hard |
| MobileNet SSD | 50-90 | ⭐⭐⭐⭐ | Medium |
| Hybrid (ROI+Hough) | 30-50 | ⭐⭐⭐⭐⭐ | Medium |
| Current (CPU Hough) | 8-15 | ⭐⭐⭐ | Easy |

## Quick Start: YOLOv8 + TensorRT (RECOMMENDED)

### Installation:
```bash
conda activate AKIET_OLD
chmod +x setup_yolo.sh
./setup_yolo.sh
```

### Usage in main_window.py:
```python
# Replace this:
from src.detector_optimized import CircleDetector
self.detector = CircleDetector()

# With this:
from src.detector_yolo import YOLODetector
self.detector = YOLODetector(use_tensorrt=True)

# In _process_frame, add FPS display:
fps = self.detector.get_fps()
cv2.putText(vis_frame, f"FPS: {fps:.1f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
```

### Expected Results:
- **First run**: 2-3 minutes to convert to TensorRT
- **Subsequent runs**: Instant load, 40-80 FPS
- **Inference time**: 12-25ms per frame

## Alternative: Multi-threading Optimization

If you can't use YOLO, optimize current detector:

```python
# src/detector_multithread.py
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class MultiThreadDetector:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)

    def detect(self, image):
        # Parallel preprocessing
        future_gray = self.executor.submit(cv2.cvtColor, image, cv2.COLOR_BGR2GRAY)

        gray = future_gray.result()
        gray_blurred = cv2.bilateralFilter(gray, 9, 75, 75)

        circles = cv2.HoughCircles(
            gray_blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=60,
            param1=100,
            param2=50,
            minRadius=15,
            maxRadius=150
        )

        # ... rest of detection
```

## Advanced: Train Custom YOLO Model

For best disc detection results:

```bash
# 1. Collect 100-500 disc images
# 2. Label using Roboflow or labelImg
# 3. Train
yolo train data=disc_data.yaml model=yolov8n.pt epochs=100 imgsz=480

# 4. Use trained model
detector = YOLODetector(model_path='runs/detect/train/weights/best.pt')
```

## Hybrid Approach (Best Accuracy + Speed)

```python
class HybridDetector:
    def __init__(self):
        self.yolo = YOLODetector()  # Fast ROI detection
        self.hough = CircleDetector()  # Precise circle fitting

    def detect(self, image):
        # Step 1: YOLO finds potential disc regions (fast)
        yolo_results = self.yolo.detect(image)

        circles = []
        for (x, y, r) in yolo_results:
            # Step 2: Extract ROI
            x1, y1 = max(0, x-r-20), max(0, y-r-20)
            x2, y2 = min(image.shape[1], x+r+20), min(image.shape[0], y+r+20)
            roi = image[y1:y2, x1:x2]

            # Step 3: Precise circle fitting in ROI (accurate)
            roi_circles = self.hough.detect(roi)

            # Transform back to full image coordinates
            for (rx, ry, rr) in roi_circles:
                circles.append((rx+x1, ry+y1, rr))

        return circles
```

## Performance Tuning Tips

1. **Lower camera resolution**: 480x360 instead of 640x480
2. **Frame skipping**: Process every 2-3 frames
3. **ROI processing**: Only process center region
4. **Reduce max detections**: Stop after finding N objects
5. **Use INT8 quantization**: For TensorRT (faster, slightly less accurate)

```python
# Example: INT8 quantization
model.export(format='engine', device=0, half=False, int8=True)
```

## Monitoring Performance

Add to main_window.py:

```python
import time

class PerformanceMonitor:
    def __init__(self):
        self.times = []

    def start(self):
        self.start_time = time.time()

    def end(self):
        elapsed = time.time() - self.start_time
        self.times.append(elapsed)
        if len(self.times) > 30:
            self.times.pop(0)

    def get_fps(self):
        if not self.times:
            return 0
        return 1.0 / np.mean(self.times)

# Usage
monitor = PerformanceMonitor()

def _process_frame(self, frame):
    monitor.start()
    # ... processing ...
    monitor.end()

    fps = monitor.get_fps()
    print(f"FPS: {fps:.1f}")
```
