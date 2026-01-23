#!/bin/bash
# Quick setup for YOLOv5 with pretrained model

echo "=========================================="
echo "YOLOv5 Real-time Setup (5 minutes)"
echo "=========================================="

# Check conda
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "❌ Error: Activate conda first: conda activate AKIET_OLD"
    exit 1
fi

echo ""
echo "📦 Step 1: Cloning YOLOv5 and installing dependencies..."
if [ ! -d "yolov5" ]; then
    git clone https://github.com/ultralytics/yolov5
    cd yolov5
    pip install -r requirements.txt
    cd ..
    echo "✓ YOLOv5 cloned and installed"
else
    echo "✓ YOLOv5 directory already exists"
fi

echo ""
echo "📥 Step 2: Downloading YOLOv5n pretrained model..."
python3 << 'EOF'
import torch
import sys
sys.path.insert(0, 'yolov5')
from models.common import DetectMultiBackend

print("Downloading YOLOv5n (~4MB)...")
device = '0' if torch.cuda.is_available() else 'cpu'
model = DetectMultiBackend('yolov5n.pt', device=device)
print("✓ Downloaded: yolov5n.pt")
EOF

echo ""
echo "⚡ Step 3: TensorRT conversion (optional)..."
echo "To convert to TensorRT for 3-5x speedup, run:"
echo "  cd yolov5 && python export.py --weights yolov5n.pt --include engine --device 0 --half"
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from src.detector_yolo import YOLODetector
import numpy as np
import cv2
import torch
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print("For TensorRT conversion, run:")
    print("  cd yolov5 && python export.py --weights yolov5n.pt --include engine --device 0 --half")
else:
    print("⚠ CUDA not available, skipping TensorRT")
EOF

echo ""
echo "🧪 Step 4: Testing detector..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from src.detector_yolo import YOLODetector
import numpy as np
import cv2

print("\nTesting YOLOv5 detector...")
detector = YOLODetector(use_tensorrt=False)

# Create test image with circles
img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(img, (200, 200), 50, (200, 200, 200), -1)
cv2.circle(img, (400, 300), 70, (150, 150, 150), -1)

# Warm up
for i in range(3):
    _ = detector.detect(img)

# Test performance
print("\nPerformance test (10 frames):")
for i in range(10):
    circles = detector.detect(img)
    print(f"Frame {i+1}: {len(circles)} detected, "
          f"Time: {detector.get_avg_inference_time():.1f}ms, "
          f"FPS: {detector.get_fps():.1f}")

print("\n✓ Detector working!")
EOF

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "YOLOv5 is now configured!"
echo ""
echo "Next: Update main_window.py if needed"
echo ""
echo "Change these 2 lines:"
echo "  FROM: from src.detector_optimized import CircleDetector"
echo "    TO: from src.detector_yolo import YOLODetector"
echo ""
echo "  FROM: self.detector = CircleDetector()"
echo "    TO: self.detector = YOLODetector()"
echo ""
echo "Then run: python3 src/main.py"
echo ""
echo "Expected FPS with YOLOv5:"
echo "  - Jetson Nano: 25-40 FPS (PyTorch), 40-60 FPS (TensorRT)"
echo "  - Jetson Xavier: 50-70 FPS (PyTorch), 80-120 FPS (TensorRT)"
echo ""
